"""M post-owner S cost window against pinned original S/L8 product.

Original S42 epochs in this test are real deterministic coordinator objects
with synthetic native probes. Positive model usage is an explicit synthetic
rebind of a separate genuine RelayEngine result, not deployed integration.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

import test_metabolism_same_process_slm_product as slm
from experiments.metabolism_relay_engine_usage import (
    OwnerEngineCall,
    OwnerEpochEngineBinding,
)
from experiments.metabolism_s_completed_cost_window import (
    SCompletedEpochCostSource,
    SCompletedCostWindow,
    bounded_completed_s_cost_window_row,
    observe_completed_s_cost_window,
)
from relay_self.action_supervision import ActionSupervisor
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    CognitionMode,
    OpenCognitionRequest,
    ProviderCallFacts,
    ProviderExpression,
    RelayEngine,
)
from relay_self.runtime_coordination import coordinate_decision_epoch


def owner_source(data, **changes):
    (_, _ledger, _decision, probe, epoch, _supervisor,
     _views, _resource, *_unused) = data
    source = SCompletedEpochCostSource(
        original_s_epoch=epoch,
        original_slm_tap=slm.host_tap(data),
        epoch_id=f"actual-s-{probe.seq}",
        task_id="same-task",
        condition_id="grass",
        phase="FAMILIAR",
    )
    return replace(source, **changes)


def model_case(data):
    source = owner_source(data)
    native_tap = source.original_slm_tap
    request = OpenCognitionRequest(
        request_id="model-request-02",
        instruction="Reason about a changed body surface.",
        intent_id="test-only", focus="SURFACE", context=(),
    )
    calls = []

    def provider(req, *, mode):
        assert mode is CognitionMode.OPEN
        calls.append(req)
        return ProviderExpression(
            text="private synthetic text NEVER part of M output",
            provenance=Provenance("test-fixture", "not-physical"),
            call_facts=ProviderCallFacts(prompt_tokens=23, completion_tokens=11),
        )

    engine = RelayEngine(provider)
    epoch = coordinate_decision_epoch(
        ActionSupervisor(), at_ns=10,
        provenance=Provenance("fixture", "same-coordinator-class"),
        decision_step=lambda: request, relay_engine=engine.open,
    )
    assert calls == [request]
    # Source-join envelope is explicitly SYNTHETIC. Actual original S/L8/M
    # only supplies the deterministic S choice, not this model result.
    tap = replace(
        native_tap, original_s_epoch=epoch,
        probe_seq=native_tap.probe_seq + 1,
        request_id=native_tap.request_id + "-next",
    )
    bind = OwnerEpochEngineBinding(
        session_id=tap.session_id,
        probe_seq=tap.probe_seq,
        native_request_id=tap.request_id,
        meter_id="meter-fixture-1",
        level="L2",
    )
    model = SCompletedEpochCostSource(
        original_s_epoch=epoch, original_slm_tap=tap,
        epoch_id=f"synthetic-model-{tap.probe_seq}",
        task_id="same-task", condition_id="ice", phase="SHIFT",
        engine_call=OwnerEngineCall(request, epoch.cognition_result),
        binding=bind,
    )
    return source, model, calls


def test_original_s42_deterministic_epoch_is_counted_as_unknown_not_zero():
    data = slm.common_epoch()
    owner, supervisor = data[1], data[5]
    before = owner.body, owner.credit_count, supervisor.last_at_ns
    report = observe_completed_s_cost_window((owner_source(data),), enabled=True)
    assert report.status == "RECORDED"
    assert report.admitted_epochs == report.unknown_cost_epochs == 1
    assert report.model_measured_epochs == 0
    provider_metric = report.summary.phases[0].metrics[0]
    assert provider_metric.name == "provider_calls"
    assert provider_metric.measured_count == 0
    assert provider_metric.missing_count == 1
    assert provider_metric.complete_total is None
    assert (owner.body, owner.credit_count, supervisor.last_at_ns) == before
    assert bounded_completed_s_cost_window_row(report)["new_model_calls"] == 0


def test_mixed_original_s_and_synthetic_model_epoch_preserves_missingness():
    data = slm.common_epoch()
    original, model, calls = model_case(data)
    report = observe_completed_s_cost_window((original, model), enabled=True)
    assert report.status == "RECORDED"
    assert report.attempted_epochs == 2 and report.admitted_epochs == 2
    assert report.unknown_cost_epochs == report.model_measured_epochs == 1
    familiar, shift = report.summary.phases
    assert familiar.phase == "FAMILIAR"
    assert shift.phase == "SHIFT"
    assert familiar.metrics[0].complete_total is None
    assert shift.metrics[0].complete_total == 1
    assert shift.metrics[1].complete_total == 23
    assert shift.metrics[2].complete_total == 11
    assert shift.metrics[4].complete_total is None
    assert len(calls) == 1  # reading window never re-executes provider
    assert "private synthetic text" not in repr(report)
    assert report.summary.source_attested is False


def test_atomic_defer_if_later_trial_reuses_source_or_mismatches_task():
    data = slm.common_epoch()
    original, model, _ = model_case(data)
    variants = (
        replace(model, original_slm_tap=replace(
            model.original_slm_tap,
            probe_seq=original.original_slm_tap.probe_seq,
        )),
        replace(model, task_id="other-task"),
        replace(model, original_slm_tap=replace(
            model.original_slm_tap, session_id="foreign-session",
        )),
        replace(model, epoch_id=original.epoch_id),
        replace(model, original_slm_tap=replace(
            model.original_slm_tap, action_authority=True,
        )),
    )
    for bad in variants:
        result = observe_completed_s_cost_window((original, bad), enabled=True)
        assert result.status == "DEFERRED"
        assert result.admitted_epochs == result.unknown_cost_epochs == 0
        assert result.summary is None
        assert bounded_completed_s_cost_window_row(result)["admitted_epochs"] == 0


def test_foreign_engine_result_cannot_mint_new_provider_usage():
    data = slm.common_epoch()
    original, model, _ = model_case(data)
    altered = replace(
        model, engine_call=replace(
            model.engine_call,
            result=replace(model.engine_call.result, elapsed_ns=999),
        ),
    )
    out = observe_completed_s_cost_window((original, altered), enabled=True)
    assert out.status == "DEFERRED" and out.summary is None


@pytest.mark.parametrize("bad_sources", [
    (), (None,), tuple(None for _ in range(65)),
    None, "not a tuple",
])
def test_invalid_bounded_or_nonoriginal_source_rejected(bad_sources):
    report = observe_completed_s_cost_window(bad_sources, enabled=True)
    assert report.status == "DEFERRED" and report.summary is None


def test_disabled_does_not_touch_source():
    class Unreadable:
        def __getattribute__(self, name):
            raise AssertionError(f"disabled window accessed {name}")
    source = Unreadable()
    report = observe_completed_s_cost_window((source,))
    assert report.status == "DISABLED" and report.attempted_epochs == 0


@pytest.mark.parametrize("attack", [
    {"action_authority": True}, {"source_attested": True},
    {"native_reads": 1}, {"model_invocations": 1},
    {"energy_debits": 1}, {"action_issues": 1},
    {"learning_updates": 1}, {"habit_grants": 1},
    {"admitted_epochs": 1}, {"summary": "forged"},
])
def test_bounded_window_telemetry_rejects_forged_report(attack):
    original = observe_completed_s_cost_window((), enabled=False)
    with pytest.raises(ValueError):
        bounded_completed_s_cost_window_row(replace(original, **attack))


def test_no_hidden_absence_of_meter_in_one_phase():
    data = slm.common_epoch()
    original = owner_source(data)
    next_epoch = replace(
        original,
        epoch_id="followup-epoch",
        original_slm_tap=replace(
            original.original_slm_tap,
            probe_seq=original.original_slm_tap.probe_seq + 1,
            request_id=original.original_slm_tap.request_id + "-followup",
        ),
        phase="SHIFT",
    )
    # The exact S owner epoch object has not changed; no fake model is
    # attributed to the later synthetic source, both are UNMEASURED.
    result = observe_completed_s_cost_window(
        (original, next_epoch), enabled=True,
    )
    assert result.status == "RECORDED"
    assert result.model_measured_epochs == 0
    assert result.unknown_cost_epochs == 2
