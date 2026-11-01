"""M lifecycle coverage: genuine S/L8/M allowlist shape, synthetic cost receipts."""
from __future__ import annotations

from dataclasses import replace

import pytest

from experiments.metabolism_cognitive_lifecycle import (
    CognitionCostSample,
    CognitiveLifecycleRejected,
    CognitiveWorkReceipt,
    summarize_cognitive_lifecycle,
)


def audit(seq: int, **overrides):
    row = {
        "schema": "SLM_PASSIVE_DEV_AUDIT_V1",
        "status": "RECORDED", "reason": "complete",
        "session_id": "session-dev-1", "probe_seq": seq,
        "request_id": f"request-{seq}", "s_choice": "WAIT",
        "l1_candidate": None, "l1_status": None,
        "m_model_tension": "NO_MODEL_TENSION", "l1_model_status": None,
        "source_scope": "DEV_OPTIONAL_S_L_M_AUDIT_NOT_ACTION_INPUT",
        "native_source_attested": False, "action_authority": False,
        "new_native_reads": 0, "new_cognition_calls": 0, "action_issues": 0,
        "learning_updates": 0, "habit_grants": 0, "food_credits": 0,
    }
    row.update(overrides)
    return row


def usage(seq: int, level="L0", **kw):
    return CognitiveWorkReceipt(
        session_id="session-dev-1", probe_seq=seq,
        request_id=f"request-{seq}", receipt_id=f"meter-{seq}",
        level=level, **kw,
    )


def sample(seq: int, phase="EXPLORE", *, meter=None):
    return CognitionCostSample(
        epoch_id=f"epoch-{seq}", task_id="move-target", condition_id="grass",
        phase=phase, outcome="UNKNOWN", audit_row=audit(seq), usage=meter,
    )


def metric(summary, phase, name):
    return next(x for p in summary.phases if p.phase == phase
                for x in p.metrics if x.name == name)


def test_exploration_familiar_shift_recovery_and_no_claim():
    summary = summarize_cognitive_lifecycle((
        sample(1, meter=usage(1, "L2", provider_calls=2, input_tokens=100,
                              output_tokens=70, wall_ns=250_000_000)),
        sample(2, meter=usage(2, "L2", provider_calls=1, input_tokens=50,
                              output_tokens=30, wall_ns=125_000_000)),
        sample(3, "FAMILIAR", meter=usage(3, "L0", provider_calls=0,
                                           input_tokens=0, output_tokens=0,
                                           wall_ns=1200)),
        sample(4, "SHIFT", meter=usage(4, "L2", provider_calls=1,
                                        input_tokens=40, output_tokens=20)),
        sample(5, "RECOVER", meter=usage(5, "L1", provider_calls=0)),
    ))
    assert summary.epoch_count == 5
    assert metric(summary, "EXPLORE", "provider_calls").complete_total == 3
    assert metric(summary, "EXPLORE", "input_tokens").complete_total == 150
    assert metric(summary, "FAMILIAR", "provider_calls").complete_total == 0
    assert metric(summary, "FAMILIAR", "wall_ns").complete_total == 1200
    assert metric(summary, "SHIFT", "provider_calls").complete_total == 1
    assert metric(summary, "RECOVER", "input_tokens").complete_total is None
    assert "NOT_LEARNING_OR_CAUSAL_PROOF" in summary.interpretation
    assert summary.energy_debits == summary.learning_updates == summary.habit_grants == 0
    assert not summary.source_attested and not summary.action_authority


def test_absent_metric_is_not_zero_even_when_other_metric_is_zero():
    summary = summarize_cognitive_lifecycle((
        sample(1, "FAMILIAR", meter=usage(1, "L0", provider_calls=0)),
        sample(2, "FAMILIAR"),
    ))
    m = metric(summary, "FAMILIAR", "provider_calls")
    assert m.observed_sum == 0 and m.measured_count == 1 and m.missing_count == 1
    assert m.complete_total is None
    assert metric(summary, "FAMILIAR", "cpu_ns").observed_sum is None


def test_condition_shift_does_not_make_learning_claim():
    a = sample(1, meter=usage(1, provider_calls=1))
    b = replace(sample(2, "FAMILIAR", meter=usage(2, provider_calls=0)),
                condition_id="ice")
    out = summarize_cognitive_lifecycle((a, b))
    assert out.phases[0].conditions == ("grass",)
    assert out.phases[1].conditions == ("ice",)
    assert out.interpretation == "DESCRIPTIVE_DEV_ONLY_NOT_LEARNING_OR_CAUSAL_PROOF"


@pytest.mark.parametrize("attack", [
    {"action_authority": True}, {"new_cognition_calls": 1},
    {"action_issues": 1}, {"learning_updates": 1}, {"food_credits": 1},
    {"native_source_attested": True}, {"schema": "MADE_UP"},
    {"source_scope": "PHYSICAL_CERTIFIED"}, {"status": "DEFERRED"},
    {"s_choice": "EAT"}, {"l1_candidate": "MOVE_AWAY"},
    {"m_model_tension": "MOVE_MODEL_INSUFFICIENT"},
    {"probe_seq": True}, {"probe_seq": -1},
])
def test_fake_authority_status_or_source_rejected(attack):
    with pytest.raises(CognitiveLifecycleRejected):
        summarize_cognitive_lifecycle((
            replace(sample(1), audit_row=audit(1, **attack)),
        ))


def test_raw_world_and_energy_forbidden():
    row = audit(1)
    row["true_energy"] = 999.0
    with pytest.raises(CognitiveLifecycleRejected):
        summarize_cognitive_lifecycle((replace(sample(1), audit_row=row),))


def test_duplicate_stale_wrong_session_or_task_rejected():
    a = sample(1)
    variants = (
        replace(sample(2), audit_row=audit(1)),
        replace(sample(2), epoch_id="epoch-1"),
        replace(sample(2), audit_row=audit(2, session_id="other")),
        replace(sample(2), task_id="different-goal"),
        replace(sample(2), audit_row=audit(2, request_id="request-1")),
    )
    for bad in variants:
        with pytest.raises(CognitiveLifecycleRejected):
            summarize_cognitive_lifecycle((a, bad))


@pytest.mark.parametrize("bad", [
    {"provider_calls": -1}, {"provider_calls": True}, {"wall_ns": -1},
    {"output_tokens": -1}, {"provider_calls": 0, "input_tokens": 10},
])
def test_illegal_cognitive_receipts_rejected(bad):
    with pytest.raises(CognitiveLifecycleRejected):
        summarize_cognitive_lifecycle((sample(1, meter=usage(1, **bad)),))


def test_missing_and_empty_meter_stay_unknown():
    out = summarize_cognitive_lifecycle((sample(1),))
    assert metric(out, "EXPLORE", "provider_calls").complete_total is None
    with pytest.raises(CognitiveLifecycleRejected):
        summarize_cognitive_lifecycle((sample(1, meter=usage(1)),))


def test_meter_must_be_tied_to_exact_original_source():
    original = usage(1, "L2", provider_calls=1)
    for bad in (
        replace(original, session_id="foreign"),
        replace(original, probe_seq=2),
        replace(original, request_id="foreign"),
        replace(original, receipt_id=""),
        replace(original, measurement_scope="ATTESTED"),
        replace(original, level="L3"),
    ):
        with pytest.raises(CognitiveLifecycleRejected):
            summarize_cognitive_lifecycle((sample(1, meter=bad),))


def test_bounded_records_and_duplicate_meter():
    with pytest.raises(CognitiveLifecycleRejected):
        summarize_cognitive_lifecycle((sample(1),), max_epochs=True)
    with pytest.raises(CognitiveLifecycleRejected):
        summarize_cognitive_lifecycle(tuple(sample(i) for i in range(65)))
    a = sample(1, meter=usage(1, provider_calls=1))
    b = sample(2, meter=replace(usage(2, provider_calls=2),
                                receipt_id="meter-1"))
    with pytest.raises(CognitiveLifecycleRejected):
        summarize_cognitive_lifecycle((a, b))


def test_consistent_l8_shadow_does_not_mint_habit():
    row = audit(1, s_choice="MOVE_AWAY", l1_candidate="WAIT",
                l1_status="l1_shadow_differs_from_s",
                l1_model_status="MODEL_AMBIGUOUS",
                m_model_tension="MOVE_MODEL_AMBIGUOUS")
    out = summarize_cognitive_lifecycle((replace(sample(1), audit_row=row),))
    assert out.habit_grants == 0


def test_inputs_immutable_and_output_excludes_raw_source():
    row = audit(1)
    src = replace(sample(1, meter=usage(1, provider_calls=0)), audit_row=row)
    before = row.copy()
    out = summarize_cognitive_lifecycle((src,))
    assert row == before and not hasattr(out, "audit_row")
