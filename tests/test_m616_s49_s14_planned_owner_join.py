"""M #616 planned owner join tests. All observation frames are SYNTHETIC.

Run against pinned S #701 with actual S14 coordinator implementation.
No World, Action, model or metabolic owner is run by these fixtures.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace

import pytest
import test_postmain_s42_world_contrast as s42
from adapters.mineflayer.s34_native_world_cognition_ci import _native_epoch_two
from adapters.mineflayer.s49_completed_decision_bridge import (
    read_original_s49_completions,
)
from adapters.mineflayer.s49_original_planned_postaction import (
    S49OriginalPlannedMove,
    bind_original_s49_planned,
    bounded_original_s49_planned_row,
)
import test_metabolism_s49_owner_admission as m_fixture
from experiments.metabolism_s49_s14_planned_owner_join import (
    M616S14PlannedLease,
    bounded_m_s14_planned_row,
    observe_s49_s14_planned,
)
from relay_self.action_supervision import ActionSupervisor
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from tools.m616_s49_live_owner_dev import M616OriginalS49CompletedTap
from tools.m616_s49_s14_live_owner_dev import (
    M616S14LiveTap,
    run_s49_s14_with_m_readback,
)


def _sources():
    original = m_fixture._owner_batch()
    # Original S callback independently creates a fresh wrapper, but its
    # individual original L0/probe/S16 Python objects are exactly shared.
    second_wrapper = read_original_s49_completions(
        tuple(item.step for item in original.steps),
        {item.probe.seq: item.probe for item in original.steps},
        {
            item.step.action_request_id: item.action_receipt
            for item in original.steps if item.action_receipt is not None
        },
    )
    assert original is not second_wrapper
    assert original.steps[0].step is second_wrapper.steps[0].step
    retained, near, _, _, _ = s42._pair()
    intent = IntentCommitment()
    intent.commit(
        "escape-threat", objective="escape near zombie", at_ns=1,
        provenance=Provenance("test", "original-planned"),
    )
    values, epoch = _native_epoch_two(
        ActionSupervisor(), intent, retained, retained,
        expected_revision=retained.revision, native=near,
    )
    moves = tuple(
        S49OriginalPlannedMove(
            entry.step, entry.probe, entry.action_receipt,
            epoch, values["plan"], values["admission"],
        )
        for entry in second_wrapper.steps if entry.action_receipt is not None
    )
    planned = bind_original_s49_planned(second_wrapper, moves)
    old = M616OriginalS49CompletedTap(enabled=True)
    old(original)
    assert old.readout["status"] == "RECORDED"
    assert old.original_s16_receipts["status"] == "RECORDED"
    return original, planned, old.readout, old.original_s16_receipts


def _observe(**changes):
    source = _sources()
    params = dict(zip(
        ("original_l0", "original_planned", "m_admission_row", "m_s16_row"), source,
    ))
    params.update(changes)
    return observe_s49_s14_planned(enabled=True, **params)


def test_s14_original_planned_source_admitted_without_minted_s42_or_b0():
    original, planned, m_admission, m_s16 = _sources()
    admitted = _observe()
    assert admitted.status == "RECORDED"
    assert admitted.original_planned is not None
    assert admitted.reason == "same_original_s49_s14_s16_source"
    assert admitted.session_id == original.session_id
    assert admitted.action_rows[0][0] == original.steps[0].step.action_request_id
    assert m_admission["provider_calls"] is None
    assert m_s16["s42_owner_receipt"].startswith("NOT_SUPPLIED")
    assert planned.moves[0].epoch.decision.cognition_requested is False
    row = bounded_m_s14_planned_row(admitted)
    assert row["status"] == "RECORDED"
    assert row["move_epoch_count"] == 1
    assert row["wait_epoch_count"] == 0
    assert row["s42_owner_receipt"].startswith("NOT_SUPPLIED")
    assert row["b0_owner_receipt"].startswith("NOT_SUPPLIED")
    assert row["l8_owner_receipt"].startswith("NOT_SUPPLIED")
    assert row["provider_calls"] is None and row["gpu_ns"] is None
    assert row["new_native_reads"] == row["new_model_calls"] == 0
    assert "snapshot" not in repr(row)


@pytest.mark.parametrize("attack", (
    "no_planned", "no_l0", "copied_step", "copied_probe", "copied_s16",
    "replayed_wrapper", "foreign_session", "missing_action", "extra_move",
    "foreign_epoch", "forged_s42", "forged_b0", "m_admission_deferred",
    "m_s16_deferred", "tampered_m_action", "wrong_s16_seq",
))
def test_fake_or_replayed_planned_source_atomic_deferred(attack):
    original, planned, old, s16 = _sources()
    if attack == "no_planned":
        planned = None
    elif attack == "no_l0":
        original = None
    elif attack == "copied_step":
        entry = planned.original_l0.steps[0]
        replaced = replace(entry, step=replace(entry.step))
        planned = replace(planned, original_l0=replace(
            planned.original_l0, steps=(replaced, *planned.original_l0.steps[1:]),
        ))
    elif attack == "copied_probe":
        entry = planned.original_l0.steps[0]
        replaced = replace(entry, probe=replace(entry.probe))
        planned = replace(planned, original_l0=replace(
            planned.original_l0, steps=(replaced, *planned.original_l0.steps[1:]),
        ))
    elif attack == "copied_s16":
        entry = planned.original_l0.steps[0]
        replaced = replace(entry, action_receipt=replace(entry.action_receipt))
        planned = replace(planned, original_l0=replace(
            planned.original_l0, steps=(replaced, *planned.original_l0.steps[1:]),
        ))
    elif attack == "replayed_wrapper":
        planned = replace(planned, original_l0=original)
    elif attack == "foreign_session":
        planned = replace(planned, session_id="foreign")
    elif attack == "missing_action":
        planned = replace(planned, moves=())
    elif attack == "extra_move":
        planned = replace(planned, moves=planned.moves * 2)
    elif attack == "foreign_epoch":
        first = planned.moves[0]
        planned = replace(planned, moves=(
            replace(first, epoch=replace(first.epoch, executed_work_ids=())),
        ))
    elif attack == "forged_s42":
        planned = replace(planned, real_s42_owner_supplied=True)
    elif attack == "forged_b0":
        planned = replace(planned, real_b0_owner_supplied=True)
    elif attack == "m_admission_deferred":
        old = dict(old, status="DEFERRED")
    elif attack == "m_s16_deferred":
        s16 = dict(s16, status="DEFERRED")
    elif attack == "tampered_m_action":
        s16 = dict(s16, actions=[dict(s16["actions"][0], event_seq=999)])
    elif attack == "wrong_s16_seq":
        first = planned.moves[0]
        planned = replace(planned, moves=(
            replace(first, receipt=replace(first.receipt)),
        ))
    out = observe_s49_s14_planned(
        enabled=True, original_l0=original,
        original_planned=planned,
        m_admission_row=old, m_s16_row=s16,
    )
    assert out.status == "DEFERRED"
    assert out.original_planned is None and out.action_rows == ()
    saved = bounded_m_s14_planned_row(out)
    assert saved["actions"] == [] and saved["session_id"] is None
    assert saved["source_attested"] is False


def test_planned_lease_default_off_and_replay_rejected():
    class NeverTouch:
        def __getattribute__(self, name):
            raise AssertionError(name)

    obj = NeverTouch()
    disabled = observe_s49_s14_planned(
        original_l0=obj, original_planned=obj,
        m_admission_row=obj, m_s16_row=obj,
    )
    assert disabled.status == "DISABLED"
    assert bounded_m_s14_planned_row(disabled)["actions"] == []
    original, planned, adm, s16 = _sources()
    lease = M616S14PlannedLease(enabled=True)
    kw = {
        "original_l0": original, "original_planned": planned,
        "m_admission_row": adm, "m_s16_row": s16,
    }
    assert lease.admit(**kw).status == "RECORDED"
    assert lease.admit(**kw).status == "DEFERRED"


def test_s14_one_original_qualify_and_callback_order(tmp_path):
    original, planned, _, _ = _sources()
    report = m_fixture._saved_report(original)
    report["original_planned_observer"] = "CALLBACK_RETURNED"
    report["original_planned_readback"] = bounded_original_s49_planned_row(planned)
    events = []
    async def original_qualify(
        path, _server, *,
        completed_l0, completed_l0_dev,
        completed_planned, completed_planned_dev,
    ):
        events.append("qualify")
        assert completed_l0_dev and completed_planned_dev
        completed_l0(original)
        completed_planned(planned)
        events.extend(("original_l0", "original_planned"))
        path.write_text(json.dumps(report), encoding="utf-8")
        return 0

    code, result = asyncio.run(run_s49_s14_with_m_readback(
        original_qualify=original_qualify,
        report_path=tmp_path / "s49.json",
        server_log=tmp_path / "s49.log",
        tap=M616S14LiveTap(enabled=True),
    ))
    assert code == 0
    assert result["status"] == "RECORDED"
    assert result["m_original_s14_planned"]["status"] == "RECORDED"
    assert result["m_admission"]["status"] == "RECORDED"
    assert result["m_original_s16_receipts"]["status"] == "RECORDED"
    assert events == ["qualify", "original_l0", "original_planned"]
    assert result["new_action_issues"] == 0
    assert result["metabolic_energy"] == "UNKNOWN_NO_B0_OWNER"


@pytest.mark.parametrize("failure", ("owner_failed", "callback_missing", "duplicate"))
def test_no_owner_failure_or_duplicate_can_be_promoted(tmp_path, failure):
    original, planned, _, _ = _sources()
    report = m_fixture._saved_report(original)
    report["original_planned_observer"] = "CALLBACK_RETURNED"
    report["original_planned_readback"] = bounded_original_s49_planned_row(planned)
    if failure == "owner_failed":
        report["status"] = "FAIL"
    async def original_qualify(
        path, _server, *,
        completed_l0, completed_l0_dev,
        completed_planned, completed_planned_dev,
    ):
        completed_l0(original)
        if failure != "callback_missing":
            completed_planned(planned)
        if failure == "duplicate":
            completed_planned(planned)
        path.write_text(json.dumps(report), encoding="utf-8")
        return 1 if failure == "owner_failed" else 0

    code, result = asyncio.run(run_s49_s14_with_m_readback(
        original_qualify=original_qualify,
        report_path=tmp_path / "s.json", server_log=tmp_path / "log",
        tap=M616S14LiveTap(enabled=True),
    ))
    assert result["status"] == "DEFERRED"
    assert code in (0, 1)
