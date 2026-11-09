"""R4 natural S49: negative admissions, original issuer and source audit."""
from __future__ import annotations

import asyncio
import hashlib
import json
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock

import pytest

from relay_self.s49_nonmotion_physical_fence import OriginalS49NonMotionFence
from test_d14_natural_world import make_report
from tools.bug0_d14_natural_active_post import (
    D14NaturalActiveAuditRejected,
    audit_active,
)
from tools.bug0_d14_natural_life import (
    MAX_ACTIONS,
    R4_GRANT,
    NaturalLifeLoop,
    NaturalLifeRejected,
    admissible_natural_attack,
)


def native_pair(*, target_delta=0.0, body_delta=0.0, other=False):
    def pos(x):
        return NS(x=x, y=64.0, z=0.0)

    def probe(seq, tx, bx):
        zombie = NS(
            name="zombie", entity_id=7, distance=1.5, position=pos(tx),
        )
        entities = (zombie, NS(name="cow", entity_id=8)) if other else (zombie,)
        return NS(
            session_id="native-session", seq=seq, request_id=f"probe-{seq}",
            snapshot=NS(
                nearby_entities=entities,
                nearby_entities_coverage=NS(
                    truncated=False, candidate_count=len(entities),
                ),
                health=20, food=20, oxygen_level=20,
                position=pos(bx), inventory=(),
            ),
        )
    return probe(4, 0.0, 0.0), probe(5, target_delta, body_delta)


@pytest.mark.parametrize(("target_delta", "body_delta", "other"), [
    (0.3, 0.0, False),
    (0.0, 0.06, False),
    (0.0, 0.0, True),
])
def test_natural_attack_requires_one_stable_close_target(
    target_delta, body_delta, other,
):
    a, b = native_pair(
        target_delta=target_delta, body_delta=body_delta, other=other,
    )
    assert admissible_natural_attack(a, b) is None


def test_source_precheck_does_not_grant_physical_action():
    a, b = native_pair()
    assert admissible_natural_attack(a, b) == 7
    b.snapshot.nearby_entities_coverage.truncated = True
    assert admissible_natural_attack(a, b) is None


def test_distinct_r4_grant_required_before_ledger_creation(tmp_path, monkeypatch):
    monkeypatch.delenv(R4_GRANT, raising=False)
    session = NS(started=NS(session_id="native-session"))
    with pytest.raises(NaturalLifeRejected, match="PHYSICAL_GRANT"):
        NaturalLifeLoop(session, tmp_path, {})
    assert list(tmp_path.iterdir()) == []


def make_controller(tmp_path, monkeypatch):
    monkeypatch.setenv(R4_GRANT, "1")
    report = {}
    session = NS(started=NS(session_id="native-session"), process_returncode=None)
    loop = NaturalLifeLoop(session, tmp_path, report)
    return loop, report


def test_action_budget_stops_without_new_effect(tmp_path, monkeypatch):
    loop, report = make_controller(tmp_path, monkeypatch)
    loop.owner._count = MAX_ACTIONS
    seen = []
    asyncio.run(loop.step(lambda *args, **kwargs: seen.append(args)))
    assert loop.stopped and seen == []
    assert report["life_stop_reason"] == "ORIGINAL_S49_BOUND_OR_UNRESOLVED"
    assert loop.nonmotion.actions == ()


def test_untyped_source_is_refused_by_original_s49(tmp_path, monkeypatch):
    loop, report = make_controller(tmp_path, monkeypatch)
    previous, current = native_pair()
    loop._read = AsyncMock(side_effect=[previous, current])
    loop.policy = NS(
        decide=lambda *args, **kwargs: NS(
            selected="DEFER", preferred="MOVE_AWAY",
            fallback="ATTACK", reason="NATIVE_ZOMBIE_NEAR",
        ),
    )
    saved = []
    asyncio.run(
        loop.step(lambda kind, line, native=None: saved.append((kind, native)))
    )
    assert [x[0] for x in saved] == ["LIFE_DECISION"]
    assert report["life_decisions"][0]["admission"] == "DEFER_ORIGINAL_S49_REFUSED"
    assert report["new_s49_actions"] == 0
    assert loop.nonmotion.actions == ()


def _active_fixture(tmp_path, *, early=False):
    report, original, derivative = make_report(tmp_path, early=early)
    fence = OriginalS49NonMotionFence.create(
        tmp_path / "original_s49_nonmotion_fence.json",
        self_id="s49-original-self",
    )
    report.update({
        "classification": "DEV_D14_R4_NATURAL_ACTIVE_S49_SOURCE_OBSERVED",
        "s49_physical_issuer": "ORIGINAL_NORMAL_SESSION_ACTION_EXECUTOR",
        "native_session_id": "native-session",
        "original_s49_session_id": "native-session",
        "original_s49_intent_id": "natural-intent",
        "original_s49_supervisor_open": 0,
        "original_s49_fence_sha256": fence.sha256,
        "original_s49_fence_unresolved": False,
        "original_s49_fence_action_ids": [],
        "life_decision_count": 0,
        "life_outcome_count": 0,
        "move_admission": "NOT_CONNECTED_IN_R4",
        "intent_rearm": "NOT_CONNECTED_IN_R4",
        "c1_intent_experiences": 0,
    })
    return report, original, derivative, fence


def _audit(report, original, derivative, fence):
    return audit_active(
        report, original, derivative, fence,
        original_sha=hashlib.sha256(original.encode()).hexdigest(),
        derivative_sha=hashlib.sha256(derivative.encode()).hexdigest(),
    )


def test_zero_actions_and_actual_death_not_autonomy(tmp_path):
    report, original, derivative, fence = _active_fixture(tmp_path, early=True)
    result = _audit(report, original, derivative, fence)
    assert result["status"] == "PASS_DEV"
    assert result["eventual_reason"] == "SELF_DIED"
    assert result["original_s49_actions"] == 0
    assert result["long_run_autonomous_self_proven"] is False


def test_paper_console_carriage_returns_preserve_original_lines(tmp_path):
    report, original, derivative, fence = _active_fixture(tmp_path, early=True)
    prefix = "> \r  \r"
    lines = original.splitlines()
    mapping = {line: prefix + line for line in lines}
    original = "\n".join(mapping[line] for line in lines) + "\n"
    source = report["paper_source"]
    for key, value in source.items():
        if isinstance(value, str) and value in mapping:
            source[key] = mapping[value]
        elif isinstance(value, list):
            source[key] = [mapping.get(item, item) if isinstance(item, str) else item
                           for item in value]
    rows = [json.loads(line) for line in derivative.splitlines()]
    for row in rows:
        line = row.get("original_paper_line")
        if line in mapping:
            row["original_paper_line"] = mapping[line]
    derivative = "".join(json.dumps(row) + "\n" for row in rows)
    report["paper_original_sha256"] = hashlib.sha256(original.encode()).hexdigest()
    report["derivative_journal_sha256"] = hashlib.sha256(derivative.encode()).hexdigest()
    assert _audit(report, original, derivative, fence)["status"] == "PASS_DEV"


@pytest.mark.parametrize(("field", "invalid"), [
    ("new_s49_actions", 1),
    ("original_s49_fence_sha256", "fabricated"),
    ("original_s49_supervisor_open", 1),
    ("original_s49_fence_unresolved", True),
    ("learning_updates", 1),
    ("move_admission", "UNQUALIFIED_SUCCESS"),
    ("staged_hunger_effect", True),
    ("original_s49_session_id", "other-session"),
])
def test_forged_active_source_or_action_rejected(tmp_path, field, invalid):
    report, original, derivative, fence = _active_fixture(tmp_path)
    report[field] = invalid
    with pytest.raises(D14NaturalActiveAuditRejected):
        _audit(report, original, derivative, fence)


def test_derivative_life_action_cannot_claim_missing_original_fence(tmp_path):
    report, original, derivative, fence = _active_fixture(tmp_path)
    derivative += json.dumps({
        "record_type": "D14_R3_DERIVATIVE_SOURCE_REFERENCE",
        "kind": "LIFE_ACTION", "original_paper_line": "",
        "native_observation": {
            "action_id": "injected", "kind": "ATTACK", "terminal": "outcome",
        },
    }) + "\n"
    report["derivative_journal_sha256"] = hashlib.sha256(
        derivative.encode()
    ).hexdigest()
    report["life_outcome_count"] = 1
    with pytest.raises(D14NaturalActiveAuditRejected):
        _audit(report, original, derivative, fence)


def test_policy_rotation_does_not_replace_s49_or_physical_history(
    tmp_path, monkeypatch,
):
    loop, report = make_controller(tmp_path, monkeypatch)
    original_supervisor = loop.owner.supervisor
    original_owner = loop.owner
    old_l0 = loop.policy
    loop.cycles = 64
    loop._rotate_native_cursor()
    assert report["life_policy_epochs"] == 2
    assert loop.policy is not old_l0
    assert loop.owner is original_owner
    assert loop.owner.supervisor is original_supervisor
    assert loop.intent.current_intent.intent_id == report["original_s49_intent_id"]
    assert loop.nonmotion.actions == ()
    loop._rotate_native_cursor()
    assert report["life_policy_epochs"] == 2


def test_native_loss_is_stop_no_reissue_or_fake_death(tmp_path, monkeypatch):
    loop, report = make_controller(tmp_path, monkeypatch)
    loop.stop_due_to_native_loss("NATIVE_READBACK_UNAVAILABLE_ACTION_STOP")
    assert loop.stopped
    assert report["life_stop_reason"] == "NATIVE_READBACK_UNAVAILABLE_ACTION_STOP"
    assert loop.owner._count == 0
    assert loop.nonmotion.actions == ()


def _append_source_native_stop(report, original, derivative, *, after_terminal=False):
    rows = []
    sample_no = 0
    samples = []
    for line in derivative.splitlines():
        event = json.loads(line)
        if after_terminal and event["kind"] in ("LIMIT", "TERMINAL"):
            continue
        rows.append(line)
        if event["kind"] == "SAMPLE":
            sample_no += 1
            if sample_no <= 2:
                paper_sample = event["original_paper_line"]
                samples.append(paper_sample)
                rows.append(json.dumps({
                    "record_type": "D14_R3_DERIVATIVE_SOURCE_REFERENCE",
                    "kind": "NATIVE_OBSERVATION_FAILED",
                    "original_paper_line": paper_sample,
                    "native_observation": {
                        "error": "source not correlated",
                        "request_id": f"native-read-{sample_no}",
                    },
                }))
                if sample_no == 2:
                    safe = {
                        "reason": "NATIVE_READBACK_UNAVAILABLE_ACTION_STOP",
                        "after_sample": paper_sample,
                        "last_failed_request_id": "native-read-2",
                        "consecutive_failures": 2,
                        "paper_only_after": True,
                    }
                    rows.append(json.dumps({
                        "record_type": "D14_R3_DERIVATIVE_SOURCE_REFERENCE",
                        "kind": "NATIVE_SAFE_STOP",
                        "original_paper_line": paper_sample,
                        "native_observation": safe,
                    }))
    if after_terminal:
        for line in derivative.splitlines():
            if json.loads(line)["kind"] in ("LIMIT", "TERMINAL"):
                rows.append(line)
    updated = "\n".join(rows) + "\n"
    report["native_observation_safe_stop"] = safe
    report["derivative_journal_sha256"] = hashlib.sha256(
        updated.encode()
    ).hexdigest()
    return updated


def test_source_attested_native_loss_keeps_paper_without_fake_action(tmp_path):
    report, original, derivative, fence = _active_fixture(tmp_path)
    derivative = _append_source_native_stop(report, original, derivative)
    result = _audit(report, original, derivative, fence)
    assert result["status"] == "PASS_DEV"
    assert result["native_safe_stops"] == 1
    assert result["active_l0_stopped_after_native_loss"] is True
    assert result["observed_world_ticks"] == 10000
    assert result["original_s49_actions"] == 0
    assert result["long_run_autonomous_self_proven"] is False


def test_native_loss_cannot_be_claimed_after_paper_terminal(tmp_path):
    report, original, derivative, fence = _active_fixture(tmp_path)
    safe = {
        "reason": "NATIVE_READBACK_UNAVAILABLE_ACTION_STOP",
        "after_sample": "invented",
        "last_failed_request_id": "fake",
        "consecutive_failures": 2,
        "paper_only_after": True,
    }
    derivative += json.dumps({
        "record_type": "D14_R3_DERIVATIVE_SOURCE_REFERENCE",
        "kind": "NATIVE_SAFE_STOP",
        "original_paper_line": "invented",
        "native_observation": safe,
    }) + "\n"
    report["native_observation_safe_stop"] = safe
    report["derivative_journal_sha256"] = hashlib.sha256(
        derivative.encode()
    ).hexdigest()
    with pytest.raises(D14NaturalActiveAuditRejected):
        _audit(report, original, derivative, fence)
