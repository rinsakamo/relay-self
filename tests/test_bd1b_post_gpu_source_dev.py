"""Offline original-class boundary; no inference or real Paper process."""

from dataclasses import replace

import pytest

from adapters.llama_cpp.relay_engine import LlamaCppRelayProvider
from relay_self.bd1b_coverage_adoption_turn_dev import prepare_coverage_adoption_turn
from relay_self.bd1b_owner_source_dev import BD1bSourceHold, build_bd1b_owner_source
from relay_self.bd1b_post_gpu_source_dev import verify_post_gpu_source
from relay_self.exploration_continuity_dev import ExplorationContinuity
from relay_self.provenance import Provenance
from relay_self.resident_llama_inference_lane_dev import (
    LlamaCppSingleSlotWitness,
    ResidentLlamaInferenceLane,
)
from test_bd1b_coverage_adoption_turn_dev import arguments
from test_bd1b_owner_present_dev import _configured
from test_bd1b_owner_source_dev import _files


def attach(bridge, monkeypatch):
    provider = LlamaCppRelayProvider(endpoint="http://127.0.0.1:8080", model="fixture", timeout=4.0)
    witness = LlamaCppSingleSlotWitness(provider=provider, backend_ref="fixture")
    monkeypatch.setattr(witness, "require_idle", lambda: None)
    lane = ResidentLlamaInferenceLane(
        provider=provider, cognitive_work=bridge.cognitive_work, witness=witness
    )
    bridge.attach_observation_only_bounded_l1(lane)
    return lane


def test_both_and_unchanged(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    bridge = case[1]
    turns = [prepare_coverage_adoption_turn(**arguments(case, sid)) for sid in ("A", "B")]
    before = _files(bridge)
    states = {
        s: (o.retained, o.intent.events, dict(o.skills), set(o.pending_questions))
        for s, o in bridge.owners.items()
    }
    lane = attach(bridge, monkeypatch)
    for turn in turns:
        kw = arguments(case, turn.self_id)
        kw.pop("self_id")
        readout = verify_post_gpu_source(**kw, lane=lane, turn=turn)
        assert readout.source == turn.source
        assert readout.candidate_set_sha256 == turn.candidate_set_sha256
        with pytest.raises(BD1bSourceHold):
            build_bd1b_owner_source(**kw, self_id=turn.self_id)
    assert _files(bridge) == before
    assert all(
        (o.retained, o.intent.events, o.skills, o.pending_questions) == states[s]
        for s, o in bridge.owners.items()
    )


@pytest.mark.parametrize(
    "failure",
    [
        "lane",
        "resident",
        "probe",
        "native",
        "paper",
        "pid",
        "boot",
        "log",
        "ack",
        "nonce",
        "actor",
        "swap",
        "world",
        "epoch",
        "other_epoch",
        "registry",
        "continuity",
        "intent",
        "fence",
        "action",
        "turn",
        "work_ref",
    ],
)
def test_reject(tmp_path, monkeypatch, failure):
    case = _configured(tmp_path, monkeypatch, need=True)
    bridge = case[1]
    kw = arguments(case)
    kw.pop("self_id")
    turn = prepare_coverage_adoption_turn(**arguments(case))
    lane = attach(bridge, monkeypatch)
    owner = bridge.owners["A"]
    if failure == "lane":
        lane = ResidentLlamaInferenceLane(
            provider=lane.provider, cognitive_work=bridge.cognitive_work, witness=lane.witness
        )
    elif failure == "resident":
        lane.cognitive_work = object()
    elif failure == "probe":
        owner.current_worldbody_observation = replace(owner.current_worldbody_observation)
    elif failure == "native":
        bridge.sessions["A"].started.session_id = "foreign"
    elif failure == "paper":
        bridge.paper._session_id = "foreign"
    elif failure == "pid":
        kw["boot"] = replace(kw["boot"], paper_pid=kw["boot"].paper_pid + 1)
    elif failure == "boot":
        kw["boot"] = replace(kw["boot"], paper_boot_id="foreign")
    elif failure in ("log", "ack", "nonce"):
        read = bridge.paper.read_owned_log
        def altered(sid):
            log = read(sid)
            if failure == "ack":
                return log.replace(b"P0D_TICK_ACK", b"P0D_TICK_BAD")
            if failure == "nonce":
                return log.replace(b"nonce=next-nonce", b"nonce=other-nonce")
            return log + b"growth\n"

        monkeypatch.setattr(bridge.paper, "read_owned_log", altered)
    elif failure == "actor":
        kw["links"] = (replace(kw["links"][0], paper_actor_uuid="foreign"), kw["links"][1])
    elif failure == "swap":
        kw["links"] = (replace(kw["links"][0], self_id="B"), replace(kw["links"][1], self_id="A"))
    elif failure == "world":
        kw["world"] = replace(kw["world"], epoch=kw["world"].epoch + 1)
    elif failure == "epoch":
        bridge.cognitive_work._states["A"].epoch += 1
    elif failure == "other_epoch":
        bridge.cognitive_work._states["B"].epoch += 1
    elif failure == "registry":
        owner.pattern_registry = replace(owner.pattern_registry, revision=2)
    elif failure == "continuity":
        owner.retained = replace(
            owner.retained, exploration_continuity=ExplorationContinuity("A", 1)
        )
    elif failure == "intent":
        owner.intent.commit(
            "new", objective="test", at_ns=1, provenance=Provenance("test", "intent")
        )
    elif failure == "fence":
        bridge.cognitive_work.fence_self("A")
    elif failure == "action":
        bridge.physical._observation_only = False
    elif failure == "work_ref":
        turn = replace(turn, work_ref="coverage-adoption-work-forged")
    else:
        turn = replace(turn, candidate_set_sha256="0" * 64)
    before = _files(bridge)
    with pytest.raises(BD1bSourceHold):
        verify_post_gpu_source(**kw, lane=lane, turn=turn)
    assert _files(bridge) == before


def test_log_changes_between_reads_hold(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    bridge = case[1]
    turn = prepare_coverage_adoption_turn(**arguments(case))
    lane = attach(bridge, monkeypatch)
    kw = arguments(case)
    kw.pop("self_id")
    read = bridge.paper.read_owned_log
    count = 0

    def changing(sid):
        nonlocal count
        count += 1
        return read(sid) + (b"growth\n" if count > 1 else b"")

    monkeypatch.setattr(bridge.paper, "read_owned_log", changing)
    with pytest.raises(BD1bSourceHold):
        verify_post_gpu_source(**kw, lane=lane, turn=turn)


def test_lane_from_another_real_resident_holds(tmp_path):
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()
    with pytest.MonkeyPatch.context() as patch:
        first = _configured(first_root, patch, need=True)
        turn = prepare_coverage_adoption_turn(**arguments(first))
        lane = attach(first[1], patch)
    with pytest.MonkeyPatch.context() as patch:
        second = _configured(second_root, patch, need=True)
        other_lane = attach(second[1], patch)
        kw = arguments(first)
        kw.pop("self_id")
        assert other_lane.cognitive_work is not lane.cognitive_work
        with pytest.raises(BD1bSourceHold):
            verify_post_gpu_source(**kw, lane=other_lane, turn=turn)


def test_retired_original_owner_holds(tmp_path, monkeypatch):
    import asyncio

    case = _configured(tmp_path, monkeypatch, need=True)
    turn = prepare_coverage_adoption_turn(**arguments(case))
    lane = attach(case[1], monkeypatch)
    resident = case[1].cognitive_work
    resident.fence_self("A")
    receipt = asyncio.run(resident.retire_self("A"))
    resident.mark_offline(receipt)
    kw = arguments(case)
    kw.pop("self_id")
    with pytest.raises(BD1bSourceHold):
        verify_post_gpu_source(**kw, lane=lane, turn=turn)
