"""DEV next-epoch candidate: explicit gate and same original NormalWorldL0 budgets.

Offline only. This is NOT a substitute for the disposable Paper World test,
S16 authorization, independent R qualification, or P1 fatigue telemetry.
"""
from __future__ import annotations

import asyncio
import inspect
import json
from dataclasses import replace

import pytest

import test_postmain_two_epoch_continuation as s19
from adapters.mineflayer import s49_normal_session_real_ci as original
from adapters.mineflayer.normal_action import NormalWorldL0
from relay_self.provenance import Provenance
from relay_self.reactive_l0 import L0ActionGrant, ReactiveL0Rejected
from test_self_live_think import native_probe


def _pair(sid: str, event_seq: int, distance: float):
    event = replace(
        native_probe(event_seq, distance, sid=sid),
        kind="entities", request_id=None,
    )
    probe = replace(
        native_probe(event_seq + 1, distance, sid=sid),
        snapshot=event.snapshot,
        request_id=f"s49-actual:{sid}:event-{event_seq}",
    )
    return event, probe


def _grant(event, probe):
    entity_id = event.snapshot.nearby_entities[0].entity_id
    return L0ActionGrant(
        authority_id=f"dev-original-operator-{event.seq}",
        action_id=f"native-move-{event.seq}",
        intent_id="escape-threat",
        session_id=event.session_id,
        event_seq=event.seq, probe_seq=probe.seq,
        entity_id=entity_id,
        granted=True,
        provenance=Provenance(
            "dev-independent-test-operator",
            f"{event.session_id}:event-{event.seq}",
        ),
    )


@pytest.mark.parametrize("next_distance,next_actions", [(10.0, 2), (2.0, 3)])
def test_original_host_can_consume_fourth_event_with_same_instance(
    next_distance, next_actions,
):
    sid = "same-native-session"
    retained = s19._epoch_one()[1].new_state
    host = NormalWorldL0(
        sid, "escape-threat", retained,
        max_events=4, max_action_requests=next_actions,
    )
    steps = []
    for event_seq, distance in (
        (10, 10.0), (20, 2.0), (30, 2.0), (40, next_distance),
    ):
        event, probe = _pair(sid, event_seq, distance)
        permit = _grant(event, probe) if distance < 4 else None
        steps.append(host.decide(event, probe, grant=permit))
    assert len(steps) == 4
    assert [step.choice.selection.value for step in steps] == [
        "WAIT", "MOVE_AWAY", "MOVE_AWAY",
        "WAIT" if next_distance == 10.0 else "MOVE_AWAY",
    ]
    assert host.events == 4
    assert host.action_requests == next_actions
    assert sum(step.asks_for_action for step in steps) == next_actions
    assert steps[-1].choice.probe_seq == 41
    assert retained is host.retained
    with pytest.raises(ReactiveL0Rejected):
        event, probe = _pair(sid, 50, 10.0)
        host.decide(event, probe, grant=None)


@pytest.mark.parametrize("next_distance", [10.0, 2.0])
def test_fourth_epoch_near_move_requires_original_independent_grant(next_distance):
    sid = "same-native-session"
    retained = s19._epoch_one()[1].new_state
    host = NormalWorldL0(
        sid, "escape-threat", retained, max_events=4, max_action_requests=3,
    )
    event, probe = _pair(sid, 40, 2.0)
    with pytest.raises(ReactiveL0Rejected, match="fresh independent Action grant"):
        host.decide(event, probe, grant=None)
    assert host.events == 0
    assert host.action_requests == 0


@pytest.mark.parametrize("choice", ["WAIT", "MOVE_AWAY", "UNKNOWN"])
def test_dev_gate_rejects_before_any_java_node_or_action(
    tmp_path, monkeypatch, choice,
):
    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.delenv("S49_NEXT_EPOCH_DEV_ONLY", raising=False)
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    def forbid_world(*args, **kwargs):
        raise AssertionError("DEV missing opt-in launched Minecraft")
    monkeypatch.setattr(original, "_fetch_official_server", forbid_world)
    report = tmp_path / "candidate.json"
    status = asyncio.run(original.qualify(
        report, tmp_path / "paper.log", dev_next_epoch=choice,
    ))
    assert status == 2
    result = json.loads(report.read_text())
    assert result["status"] == "BLOCKED"
    assert result["actual_native_actions"] == []
    assert result.get("qualification_go") is not True
    assert "next original L0 epoch" not in result.get("classification", "")


def test_default_signature_remains_three_epoch_without_dev_optin():
    signature = inspect.signature(original.qualify)
    assert signature.parameters["dev_next_epoch"].default is None
    original_code = inspect.getsource(original.qualify)
    assert "max_events=4 if dev_next_epoch is not None else 3" in original_code
    assert "max_action_requests=(" in original_code
    assert "S49_NEXT_EPOCH_DEV_ONLY" in original_code
