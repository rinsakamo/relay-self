"""R6 offline contract: real-format entity source, S49 owner and safe STOP boundary."""
from __future__ import annotations

import asyncio
import hashlib
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from adapters.mineflayer.python_protocol import (
    MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
    MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
    MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
    MineflayerEntityFact,
    MineflayerNearbyEntitiesCoverage,
    MineflayerObservation,
    MineflayerPosition,
    MineflayerSnapshot,
)
from adapters.mineflayer.s31a_real_server_ci import _correlated_observe
from relay_self.c1_physical_action_fence import OriginalS49PhysicalFence
from test_d14_natural_active_s49 import _active_fixture
from tools.bug0_d14_natural_active_post import (
    D14NaturalActiveAuditRejected,
    audit_active,
)
from tools.bug0_d14_natural_life import (
    R4_GRANT,
    R6_GRANT,
    NaturalLifeLoop,
    NaturalLifeRejected,
)
from tools.bug0_d14_natural_motion import NaturalMotionRejected


def observation(seq: int, *, kind="probe", session_id="native-session",
                entity_id=7, distance=1.5):
    origin = MineflayerPosition(0.0, 64.0, 0.0)
    entity = MineflayerEntityFact(
        entity_id=entity_id, name="zombie", entity_type="mob",
        distance=distance, position=MineflayerPosition(distance, 64.0, 0.0),
    )
    coverage = MineflayerNearbyEntitiesCoverage(
        source_scope=MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
        max_distance=MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
        max_entities=MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
        candidate_count=1, truncated=False,
    )
    snapshot = MineflayerSnapshot(
        health=20, food=20, food_saturation=5, oxygen_level=20,
        position=origin, time=None, inventory=(),
        nearby_entities=(entity,), nearby_entities_coverage=coverage,
    )
    return MineflayerObservation(
        session_id=session_id, seq=seq, kind=kind, snapshot=snapshot,
        request_id=f"request-{seq}" if kind == "probe" else None,
    )


def controller(tmp_path, monkeypatch):
    monkeypatch.setenv(R4_GRANT, "1")
    monkeypatch.setenv("D14_R5_LOCAL_ONEWORLD_ONLY", "1")
    monkeypatch.setenv(R6_GRANT, "1")
    session = SimpleNamespace(
        started=SimpleNamespace(session_id="native-session"),
        process_returncode=None,
    )
    report = {}
    loop = NaturalLifeLoop(session, tmp_path, report)
    return loop, report


def test_r6_requires_separate_local_grant(tmp_path, monkeypatch):
    monkeypatch.setenv(R4_GRANT, "1")
    monkeypatch.setenv(R6_GRANT, "1")
    monkeypatch.delenv("D14_R5_LOCAL_ONEWORLD_ONLY", raising=False)
    session = SimpleNamespace(started=SimpleNamespace(session_id="native-session"))
    with pytest.raises(NaturalLifeRejected, match="EXPLICIT_LOCAL"):
        NaturalLifeLoop(session, tmp_path, {})


def test_r5_without_r6_does_not_instantiate_motion(tmp_path, monkeypatch):
    monkeypatch.setenv(R4_GRANT, "1")
    monkeypatch.setenv("D14_R5_LOCAL_ONEWORLD_ONLY", "1")
    monkeypatch.delenv(R6_GRANT, raising=False)
    session = SimpleNamespace(started=SimpleNamespace(session_id="native-session"))
    report = {}
    loop = NaturalLifeLoop(session, tmp_path, report)
    assert loop.motion is None
    assert report["move_admission"] == "NOT_CONNECTED_IN_R4"
    assert not (tmp_path / "original_s49_motion_fence.json").exists()


def test_only_raw_entity_event_can_become_s49_candidate(tmp_path, monkeypatch):
    loop, report = controller(tmp_path, monkeypatch)
    event = observation(4, kind="entities")
    probe = observation(5)
    assert loop.motion is not None
    assert loop.motion.current_candidate(probe) is None
    with pytest.raises(NaturalMotionRejected, match="ONLY_NATIVE_ENTITIES"):
        loop.capture_native_event(probe)
    loop.capture_native_event(event)
    assert loop.motion.current_candidate(probe) is event
    assert report["stop_settling"].endswith("PHYSICAL_STOP_UNATTESTED")
    assert loop.owner._count == 0
    assert loop.motion.fence.actions == ()


def test_entity_stream_replays_foreign_frames_and_stale_probe_fail_closed(
    tmp_path, monkeypatch,
):
    loop, _ = controller(tmp_path, monkeypatch)
    original = observation(4, kind="entities")
    loop.capture_native_event(original)
    with pytest.raises(NaturalMotionRejected, match="REPLAYED"):
        loop.capture_native_event(original)
    with pytest.raises(NaturalMotionRejected, match="INVALID_NATIVE"):
        loop.capture_native_event(observation(
            6, kind="entities", session_id="another-session",
        ))
    assert loop.motion is not None
    assert loop.motion.current_candidate(observation(4)) is None
    assert loop.motion.current_candidate(observation(200)) is None
    assert loop.motion.current_candidate(observation(5, entity_id=8)) is None


def test_native_event_callback_passes_original_received_instance_not_forged_probe():
    event = observation(4, kind="entities")
    probe = observation(5)
    messages = iter((event, probe))

    class Session:
        async def send_observe(self, request_id):
            assert request_id == "request-5"

        async def receive(self):
            return next(messages)

    captured = []
    result = asyncio.run(_correlated_observe(
        Session(), "request-5", on_entity_event=captured.append,
    ))
    assert result is probe
    assert captured == [event]
    assert captured[0] is event


def test_r6_move_prefers_original_owner_and_keeps_stop_unproven(
    tmp_path, monkeypatch,
):
    loop, report = controller(tmp_path, monkeypatch)
    event = observation(4, kind="entities")
    loop.capture_native_event(event)
    pre, current = observation(5), observation(6)
    loop._read = AsyncMock(side_effect=[pre, current])
    loop.policy = SimpleNamespace(
        decide=lambda *_args, **_kwargs: SimpleNamespace(
            selected="DEFER", preferred="MOVE_AWAY", fallback="ATTACK",
            reason="ZOMBIE_NEAR",
        ),
    )
    original_move = {
        "action_id": "test-only-stub-not-a-world-outcome",
        "terminal": "outcome", "kind": "MOVE_AWAY",
        "effective_physical_stop": "UNATTESTED",
    }
    assert loop.motion is not None
    loop.motion.issue_original_move = AsyncMock(return_value=original_move)
    saved = []
    asyncio.run(loop.step(
        lambda kind, line, native=None: saved.append((kind, native))
    ))
    loop.motion.issue_original_move.assert_awaited_once()
    assert saved[-1][0] == "LIFE_ACTION"
    assert report["life_action_outcomes"] == [original_move]
    assert report["new_s49_actions"] == 0  # stub produced no physical issuance
    assert loop.owner._post_move_settling_unqualified is False
    # Stub is only an offline callsite test, never qualification of Action.


def test_motion_fence_unresolved_blocks_native_safe_stop(tmp_path, monkeypatch):
    loop, _ = controller(tmp_path, monkeypatch)
    assert loop.motion is not None
    loop.motion.fence.prepare(
        session_id=loop.sid,
        intent_id=loop.intent.current_intent.intent_id,
        action_id="unresolved-test-only", probe=observation(5),
    )
    with pytest.raises(NaturalLifeRejected, match="UNRESOLVED"):
        loop.stop_due_to_native_loss("NATIVE_READBACK_LOST")
    assert loop.motion.fence.unresolved


def audit_r6_fixture(tmp_path):
    report, original, derivative, nonmotion = _active_fixture(tmp_path)
    motion = OriginalS49PhysicalFence.create(
        tmp_path / "original_s49_motion_fence.json",
        self_id="s49-original-self",
    )
    report.update({
        "classification": "DEV_D14_R6_NATURAL_ORIGINAL_S49_MOTION_SOURCE_OBSERVED",
        "move_admission": "R6_ORIGINAL_S49_NATIVE_ENTITIES_S14_DURABLE_FENCE",
        "stop_settling": "R6_S15_CLEAR_ACK_ONLY_PHYSICAL_STOP_UNATTESTED",
        "original_s49_move_fence_sha256": motion.sha256,
        "original_s49_move_fence_unresolved": False,
        "original_s49_move_fence_action_ids": [],
        "r6_native_entities_event_count": 0,
        "original_s49_post_move_settling_unqualified": False,
    })
    return report, original, derivative, nonmotion, motion


def test_r6_zero_move_audit_is_source_only_not_autonomous(tmp_path):
    report, original, derivative, nonmotion, motion = audit_r6_fixture(tmp_path)
    result = audit_active(
        report, original, derivative, nonmotion,
        original_sha=hashlib.sha256(original.encode()).hexdigest(),
        derivative_sha=hashlib.sha256(derivative.encode()).hexdigest(),
        motion_fence=motion,
    )
    assert result["status"] == "PASS_DEV"
    assert result["original_s49_motion_actions"] == 0
    assert result["native_entity_event_independently_attested"] is False
    assert result["effective_physical_stop_attested"] is False
    assert result["long_run_autonomous_self_proven"] is False


def test_r6_audit_requires_separate_original_motion_fence(tmp_path):
    report, original, derivative, nonmotion, _motion = audit_r6_fixture(tmp_path)
    with pytest.raises(D14NaturalActiveAuditRejected, match="SCOPE_MISMATCH"):
        audit_active(
            report, original, derivative, nonmotion,
            original_sha=hashlib.sha256(original.encode()).hexdigest(),
            derivative_sha=hashlib.sha256(derivative.encode()).hexdigest(),
        )


@pytest.mark.parametrize(("field", "forged"), [
    ("new_s49_actions", 1),
    ("original_s49_move_fence_sha256", "forged"),
    ("original_s49_post_move_settling_unqualified", True),
    ("stop_settling", "STOP_VERIFIED"),
    ("r6_native_entities_event_count", -1),
])
def test_r6_audit_rejects_forged_source(tmp_path, field, forged):
    report, original, derivative, nonmotion, motion = audit_r6_fixture(tmp_path)
    report[field] = forged
    with pytest.raises(D14NaturalActiveAuditRejected):
        audit_active(
            report, original, derivative, nonmotion,
            original_sha=hashlib.sha256(original.encode()).hexdigest(),
            derivative_sha=hashlib.sha256(derivative.encode()).hexdigest(),
            motion_fence=motion,
        )


def test_r6_injected_move_without_original_ledger_not_an_action(tmp_path):
    report, original, derivative, nonmotion, motion = audit_r6_fixture(tmp_path)
    derivative += json.dumps({
        "record_type": "D14_R3_DERIVATIVE_SOURCE_REFERENCE",
        "kind": "LIFE_ACTION",
        "original_paper_line": "",
        "native_observation": {
            "kind": "MOVE_AWAY", "action_id": "forged", "terminal": "outcome",
            "native_event_seq": 4, "native_admitted_seq": 5,
            "effective_physical_stop": "UNATTESTED",
        },
    }) + "\n"
    report["derivative_journal_sha256"] = hashlib.sha256(
        derivative.encode()
    ).hexdigest()
    report["life_outcome_count"] = 1
    report["new_s49_actions"] = 1
    with pytest.raises(D14NaturalActiveAuditRejected):
        audit_active(
            report, original, derivative, nonmotion,
            original_sha=hashlib.sha256(original.encode()).hexdigest(),
            derivative_sha=hashlib.sha256(derivative.encode()).hexdigest(),
            motion_fence=motion,
        )
