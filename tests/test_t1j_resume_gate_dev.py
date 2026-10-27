"""T1j one-shot DEV resume, stale source, authority and replay negatives."""
from types import SimpleNamespace as S
import pytest

from adapters.mineflayer.t1j_resume_gate_dev import S49DevResumeGate, ResumeDevRejected


def row(seq, tick, wt=None, food=20, *, status="ADMITTED", input=0,
        session="s", world="w", player="p", phase="CLEARED", x=0,
        boot="b", threat=False):
    return S(session_id=session, seq=seq, data=dict(
        status=status, assessment="NO_KNOWN_URGENT_SIGNAL",
        age_upper_ns="20000000", challenge_sent_ns="200",
        control=dict(phase=phase, since_ns="100", generation=4),
        snapshot=dict(tick=tick, world_tick=wt if wt is not None else tick,
                      index=tick, world=world, player=player, boot=boot,
                      input=input, threats=[] if not threat else ["z"],
                      threats_complete=True, food=food, health=20,
                      x=x, y=0, z=0, motion_blocks=0)))


def fixture(unresolved=False):
    ack = S(stop_id="STOP1", session_id="s", high_level_dev_stop_ack=True,
            full_tick_stillness_qualified=False, active_action_id="oldMOVE",
            clear_action_id="oldMOVE-clear", clear_ack_seq=50,
            world="w", player="p", last_idle_tick=70)
    owner = S(ack=ack, failed=False, requested=True, allows_action=False,
              session_id="s", stop_id="STOP1")
    ledger = S(session_id="s", failed=True, pending_meal=None,
               active_action=None, previous=row(40, 50))
    gate = S49DevResumeGate(
        stopped_owner=owner, frozen_ledger=ledger,
        unresolved_eat=unresolved, retired_action_ids=["oldMOVE", "t1f-epoch-0"])
    return gate, owner, ledger


def fresh():
    return (row(75, 90),
            S(session_id="s", seq=76, kind="probe", request_id="R",
              provenance=S(source="mineflayer"), snapshot=S(food=20)),
            row(77, 92))


def authorize(g):
    g.authorize(authority="DEV_EXPLICIT_OPERATOR_REAUTHORIZE",
                resume_id="R1", stop_id="STOP1", session_id="s",
                next_action_id="t1j-R1-move")


def test_one_use_and_old_stop_remains_latched():
    g, old, ledger = fixture()
    authorize(g)
    before, native, after = fresh()
    permit = g.reobserve(before=before, native_probe=native, after=after,
                         expected_probe_request_id="R")
    assert permit.unobserved_world_ticks == 41
    assert permit.after_world_tick == 92
    assert g.consume(permit) is permit
    assert old.requested and not old.allows_action
    with pytest.raises(ResumeDevRejected):
        g.consume(permit)
    with pytest.raises(ResumeDevRejected):
        S49DevResumeGate(stopped_owner=old, frozen_ledger=ledger)


def test_missing_explicit_authorization_never_admits():
    g, _, _ = fixture()
    a, b, c = fresh()
    with pytest.raises(ResumeDevRejected):
        g.reobserve(before=a, native_probe=b, after=c,
                    expected_probe_request_id="R")


def test_unknown_eat_never_receives_a_resume_gate():
    with pytest.raises(ResumeDevRejected):
        fixture(True)


@pytest.mark.parametrize(("authority", "resume_id", "next_id"), [
    ("DEV_EXPLICIT_OPERATOR_REAUTHORIZE", "R1", "t1f-epoch-0"),
    ("NOT_OPERATOR", "R1", "t1j-R1-move"),
    ("DEV_EXPLICIT_OPERATOR_REAUTHORIZE", "STOP1", "t1j-STOP1-move"),
])
def test_forged_authority_or_reused_action_rejected(authority, resume_id, next_id):
    g, _, _ = fixture()
    with pytest.raises(ResumeDevRejected):
        g.authorize(authority=authority, resume_id=resume_id, stop_id="STOP1",
                    session_id="s", next_action_id=next_id)


@pytest.mark.parametrize(("which", "overrides"), [
    ("before", {"status": "STALE"}), ("before", {"input": 1}),
    ("before", {"world": "foreign"}), ("before", {"threat": True}),
    ("before", {"phase": "MOVING"}), ("before", {"tick": 69}),
    ("after", {"food": 18}), ("after", {"x": 1}),
    ("after", {"boot": "new"}), ("after", {"session": "foreign"}),
    ("after", {"tick": 90}),
])
def test_world_food_control_and_tick_negative_controls(which, overrides):
    g, _, _ = fixture()
    authorize(g)
    before, native, after = fresh()
    changed = row(75 if which == "before" else 77,
                  overrides.get("tick", 90 if which == "before" else 92),
                  **{k: v for k, v in overrides.items() if k != "tick"})
    args = {"before": before, "native_probe": native, "after": after,
            "expected_probe_request_id": "R"}
    args[which] = changed
    with pytest.raises(ResumeDevRejected):
        g.reobserve(**args)
    with pytest.raises(ResumeDevRejected):
        g.reobserve(before=before, native_probe=native, after=after,
                    expected_probe_request_id="R")


def test_native_probe_request_cannot_be_replayed():
    g, _, _ = fixture()
    authorize(g)
    before, native, after = fresh()
    with pytest.raises(ResumeDevRejected):
        g.reobserve(before=before, native_probe=native, after=after,
                    expected_probe_request_id="foreign-request")
