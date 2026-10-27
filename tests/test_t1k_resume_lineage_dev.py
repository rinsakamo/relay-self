"""T1k deterministic generation ownership and replay negative controls."""
from dataclasses import replace

import pytest

from adapters.mineflayer.t1h_stop_owner_dev import S49DevStopOwner, StopDevAck
from adapters.mineflayer.t1j_resume_gate_dev import ResumeDevPermit, ResumeDevRejected
from adapters.mineflayer.t1k_resume_lineage_dev import T1kStopResumeLineage


def stopped(stop_id: str, action_id: str) -> S49DevStopOwner:
    owner = S49DevStopOwner("session")
    owner.request(stop_id, active_action_id=action_id,
                  expected_clear_action_id=action_id + "-clear")
    owner.ack = StopDevAck(
        stop_id, "session", action_id, action_id + "-clear",
        100, stop_id + "-marker", "world", "player", 90, 97,
    )
    return owner


def permit(n: int, stop: str) -> ResumeDevPermit:
    return ResumeDevPermit(
        resume_id=f"T1J-R{n}", stop_id=stop, session_id="session",
        next_action_id=f"t1j-T1J-R{n}-move",
        world="world", player="player", old_stop_ack_last_server_tick=97,
        before_source_seq=100, after_source_seq=102,
        native_probe_seq=101, after_world_tick=200,
        unobserved_world_ticks=10,
    )


def first_generation():
    chain = T1kStopResumeLineage("session")
    old = stopped("STOP1", "old-move")
    fresh = S49DevStopOwner("session")
    chain.begin(old, 1)
    chain.admit(permit(1, "STOP1"), fresh)
    return chain, old, fresh


def test_two_generations_still_retain_all_prior_stop_latches():
    chain, old, first_owner = first_generation()
    first_owner.request("STOP2", active_action_id="t1j-T1J-R1-move",
                        expected_clear_action_id="t1j-T1J-R1-move-clear")
    first_owner.ack = StopDevAck(
        "STOP2", "session", "t1j-T1J-R1-move", "t1j-T1J-R1-move-clear",
        151, "stop2-marker", "world", "player", 130, 137,
    )
    chain.finish(expected_second_stop=True, stop_ack=first_owner.ack)
    second_owner = S49DevStopOwner("session")
    chain.begin(first_owner, 2)
    chain.admit(permit(2, "STOP2"), second_owner)
    chain.finish(expected_second_stop=False)
    assert not old.allows_action and not first_owner.allows_action
    assert second_owner.allows_action
    assert chain.summary() == {
        "generations": 2, "stopped_owner_ids_distinct": True,
        "resume_id_count": 2, "retired_effect_id_count": 4,
        "old_owners_still_latched": True, "has_open_generation": False,
        "failed": False, "classification": "T1K_BOUNDED_TWO_GENERATION_DEV",
    }


@pytest.mark.parametrize("fault", ["no_stop_ack", "wrong_ack", "reused_resume_id",
                                    "same_owner", "foreign_stop", "reused_action_id"])
def test_lineage_fails_closed_without_new_motor_grant(fault):
    chain, _old, fresh = first_generation()
    if fault == "no_stop_ack":
        with pytest.raises(ResumeDevRejected):
            chain.finish(expected_second_stop=True)
        return
    fresh.request("STOP2", active_action_id="t1j-T1J-R1-move")
    fresh.ack = StopDevAck("STOP2", "session", "t1j-T1J-R1-move",
                            "t1j-T1J-R1-move-clear", 155,
                            "marker2", "world", "player", 150, 157)
    if fault == "wrong_ack":
        with pytest.raises(ResumeDevRejected):
            chain.finish(expected_second_stop=True,
                         stop_ack=replace(fresh.ack, stop_id="FORGED"))
        return
    chain.finish(expected_second_stop=True, stop_ack=fresh.ack)
    if fault == "same_owner":
        with pytest.raises(ResumeDevRejected):
            chain.begin(_old, 2)
        return
    chain.begin(fresh, 2)
    second = S49DevStopOwner("session")
    candidate = permit(2, "STOP2")
    if fault == "reused_resume_id":
        candidate = replace(candidate, resume_id="T1J-R1")
    elif fault == "foreign_stop":
        candidate = replace(candidate, stop_id="FOREIGN")
    elif fault == "reused_action_id":
        candidate = replace(candidate, next_action_id="t1j-T1J-R1-move")
    with pytest.raises(ResumeDevRejected):
        chain.admit(candidate, second)


def test_second_generation_cannot_be_issued_without_first_closure():
    chain, _, owner = first_generation()
    with pytest.raises(ResumeDevRejected):
        chain.begin(owner, 2)
    assert chain.failed


@pytest.mark.parametrize("fault", ["marker", "stop", "session", "action", "clear",
                                  "seq", "world", "player", "idle", "failed_owner"])
def test_second_stop_requires_independent_bound_evidence(fault):
    chain, old, owner = first_generation()
    aid = "t1j-T1J-R1-move"
    owner.request("STOP2", active_action_id=aid)
    ack = StopDevAck("STOP2", "session", aid, aid + "-clear", 151,
                     "marker2", "world", "player", 130, 137)
    changes = {
        "marker": {"marker_id": old.ack.marker_id},
        "stop": {"stop_id": old.stop_id}, "session": {"session_id": "foreign"},
        "action": {"active_action_id": "old-move"},
        "clear": {"clear_action_id": "old-move-clear"},
        "seq": {"clear_ack_seq": 102}, "world": {"world": "foreign"},
        "player": {"player": "foreign"}, "idle": {"first_idle_tick": 97},
        "failed_owner": {},
    }
    owner.ack = replace(ack, **changes[fault])
    owner.failed = fault == "failed_owner"
    with pytest.raises(ResumeDevRejected):
        chain.finish(expected_second_stop=True, stop_ack=owner.ack)
    assert chain.failed and not old.allows_action and not owner.allows_action
