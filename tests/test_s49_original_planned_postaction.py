"""S #537 original S14 planned epoch source join (offline, NOT physical World)."""
from __future__ import annotations

import asyncio
import inspect
from dataclasses import replace

import pytest

import test_postmain_s42_world_contrast as s42
import test_s49_completed_decision_bridge as original
from adapters.mineflayer.s34_native_world_cognition_ci import _native_epoch_two
from adapters.mineflayer.s49_completed_decision_bridge import (
    read_original_s49_completions,
)
from adapters.mineflayer.s49_normal_session_real_ci import qualify
from adapters.mineflayer.s49_original_planned_postaction import (
    S49OriginalPlannedMove,
    S49PlannedReadbackRejected,
    bind_original_s49_planned,
    bounded_original_s49_planned_row,
)
from relay_self.action_supervision import ActionSupervisor
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance


def _source():
    """Synthetic S16 geometry + the REAL original planned coordinator code."""
    steps, probes, receipts = original._synthetic_original_shape()
    move = steps[0]
    probe = probes[move.choice.probe_seq]
    sid = probe.session_id
    receipt = receipts[move.action_request_id]
    consequence = receipt.consequence

    def native_observation(seq, dx=0.0):
        return replace(
            probe,
            seq=seq,
            provenance=Provenance("mineflayer", f"{sid}:{seq}"),
            snapshot=replace(
                probe.snapshot,
                position=replace(
                    probe.snapshot.position,
                    x=probe.snapshot.position.x + dx,
                ),
            ),
        )

    before = native_observation(probe.seq + 1)
    after = native_observation(probe.seq + 4, 0.31)
    consequence = replace(
        consequence,
        before_observation=before,
        after_observation=after,
        dispatch_receipt=replace(
            consequence.dispatch_receipt,
            seq=probe.seq + 2,
        ),
        cleanup_receipt=replace(
            consequence.cleanup_receipt,
            seq=probe.seq + 3,
            action_id=move.action_request_id + "-s15-clear",
        ),
    )
    fixed_receipt = replace(receipt, consequence=consequence)
    original_batch = read_original_s49_completions(
        tuple(steps), probes, {move.action_request_id: fixed_receipt},
    )

    retained, near, _, _, _ = s42._pair()
    intent = IntentCommitment()
    intent.commit(
        "escape-threat", objective="escape near zombie",
        at_ns=1, provenance=Provenance("test", "original-intent"),
    )
    values, epoch = _native_epoch_two(
        ActionSupervisor(), intent, retained, retained,
        expected_revision=retained.revision, native=near,
    )
    action = original_batch.steps[0]
    row = S49OriginalPlannedMove(
        action.step, action.probe, action.action_receipt,
        epoch, values["plan"], values["admission"],
    )
    return original_batch, row


def test_actual_original_planned_coordinator_is_retained_not_rerun():
    batch, move = _source()
    observed = bind_original_s49_planned(batch, (move,))
    assert observed.original_l0 is batch
    assert observed.moves[0] is move
    assert observed.moves[0].epoch is move.epoch
    assert move.epoch.decision.cognition_requested is False
    saved = bounded_original_s49_planned_row(observed)
    assert saved["status"] == "RECORDED"
    assert saved["move_epoch_count"] == 1
    assert saved["wait_epoch_count"] == 0
    assert saved["actions"][0]["action_id"] == batch.steps[0].step.action_request_id
    assert saved["s42_owner_receipt"].startswith("NOT_SUPPLIED")
    assert saved["b0_owner_receipt"].startswith("NOT_SUPPLIED")
    assert saved["l8_owner_receipt"].startswith("NOT_SUPPLIED")
    assert saved["provider_calls"] is None and saved["cpu_ns"] is None
    assert "snapshot" not in repr(saved)
    assert saved["new_model_calls"] == saved["new_native_reads"] == 0


@pytest.mark.parametrize("fault", [
    "missing", "extra", "copied_step", "copied_probe", "copied_receipt",
    "different_epoch", "forged_plan", "forged_admission", "foreign_session",
    "unknown_s16", "false_s42", "wrong_native_seq",
])
def test_forged_or_missing_s49_planned_source_is_rejected(fault):
    batch, row = _source()
    moves = (row,)
    if fault == "missing":
        moves = ()
    elif fault == "extra":
        moves = (row, row)
    elif fault == "copied_step":
        moves = (replace(row, step=replace(row.step)),)
    elif fault == "copied_probe":
        moves = (replace(row, probe=replace(row.probe)),)
    elif fault == "copied_receipt":
        moves = (replace(row, receipt=replace(row.receipt)),)
    elif fault == "different_epoch":
        moves = (replace(row, epoch=replace(row.epoch, executed_work_ids=())),)
    elif fault == "forged_plan":
        moves = (replace(row, plan=None),)
    elif fault == "forged_admission":
        moves = (replace(row, admission=None),)
    elif fault == "foreign_session":
        batch = replace(batch, session_id="foreign")
    elif fault == "unknown_s16":
        action = batch.steps[0]
        invalid = replace(action.action_receipt, consequence=replace(
            action.action_receipt.consequence, movement_distance=None,
        ))
        batch = replace(batch, steps=(replace(action, action_receipt=invalid), *batch.steps[1:]))
        moves = (replace(row, receipt=invalid),)
    elif fault == "false_s42":
        batch = replace(batch, real_s42_epoch_supplied=True)
    elif fault == "wrong_native_seq":
        source = batch.steps[0]
        consequence = replace(
            source.action_receipt.consequence,
            cleanup_receipt=replace(
                source.action_receipt.consequence.cleanup_receipt,
                seq=source.action_receipt.consequence.dispatch_receipt.seq,
            ),
        )
        invalid = replace(source.action_receipt, consequence=consequence)
        batch = replace(batch, steps=(replace(source, action_receipt=invalid), *batch.steps[1:]))
        moves = (replace(row, receipt=invalid),)
    with pytest.raises((S49PlannedReadbackRejected, ValueError)):
        bind_original_s49_planned(batch, moves)


def test_s49_original_planned_hook_is_default_off_and_preworld_gated(
    monkeypatch, tmp_path,
):
    signature = inspect.signature(qualify)
    assert signature.parameters["completed_planned"].default is None
    assert signature.parameters["completed_planned_dev"].default is False
    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    monkeypatch.delenv("S49_COMPLETED_PLANNED_DEV_ONLY", raising=False)
    path = tmp_path / "blocked.json"
    code = asyncio.run(qualify(
        path, tmp_path / "server.log", completed_planned_dev=True,
    ))
    assert code == 2
    assert not (tmp_path / "server.log").exists()
