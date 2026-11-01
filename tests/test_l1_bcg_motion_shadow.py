"""L-BCG offline fixture tests: NOT authenticated Minecraft evidence."""
from __future__ import annotations

from dataclasses import replace

import pytest

from relay_self.l1_bcg_motion_shadow import (
    Attention,
    BCGRejected,
    MotionContext,
    MotorOutcome,
    MotorSourceAdmission,
    compare_conditional_motion_shadow,
)


def _ctx(
    i: int, *, fast: bool, near: bool, fatigue: bool = False,
    energy: bool = False, obstacle: bool = False,
) -> MotionContext:
    return MotionContext(
        self_id="self-a", session_id=f"session-{i}", world_id=f"world-{i}",
        world_revision=i + 1, body_source_ref=f"body:{i}",
        world_source_ref=f"world-observed:{i}", source_kind="OBSERVED",
        remaining_m=0.1 if near else 0.7, tolerance_m=0.0,
        gait="RUN" if fast else "WALK", fatigue_high=fatigue,
        energy_low=energy, obstacle=obstacle, freshness_ok=True,
        regime="plain-flat",
    )


def _sha(i: int) -> str:
    return f"{i:064x}"


def _fixture(
    *, xor: bool = False,
) -> tuple[tuple[MotorOutcome, ...], MotorSourceAdmission]:
    rows = []
    for i in range(8):
        fast = i >= 4
        near = i % 4 < 2
        risk = (fast != near) if xor else fast
        c = _ctx(
            i, fast=fast, near=near, fatigue=i % 2 == 0,
            energy=i % 4 >= 2,
        )
        rows.append(MotorOutcome(
            context=c, action_id=f"action-{i}",
            original_s16_sha256=_sha(i + 1),
            original_settling_sha256=_sha(i + 101),
            settling_m=1.0 if risk else 0.0,
            settling_grade="PHYSICAL_POST_CLEAR_VERIFIED",
        ))
    return tuple(rows), MotorSourceAdmission(
        s16_digests=frozenset(row.original_s16_sha256 for row in rows),
        settling_digests=frozenset(row.original_settling_sha256 for row in rows),
    )


def _review(
    c: MotionContext, training: tuple[MotorOutcome, ...],
    admission: MotorSourceAdmission, *, enabled: bool = True,
):
    return compare_conditional_motion_shadow(
        current=c, training=training, admission=admission, memory_enabled=enabled,
    )


def test_unseen_combination_uses_learned_gait_and_differs_from_baselines() -> None:
    rows, admission = _fixture()
    # No training World contains exactly this joint combination of cue values.
    heldout = _ctx(90, fast=True, near=False, fatigue=True, energy=False)
    result = _review(heldout, rows, admission)
    assert result.selected_axes == ("fast_gait",)
    assert result.advice is Attention.RECHECK
    assert result.matched_worlds == 4
    assert result.cheap_fixed_clearance is Attention.CONTINUE
    assert result.cheap_one_bit is Attention.RECHECK
    assert result.cheap_recent is Attention.RECHECK
    assert result.action_issues == result.learning_updates == result.habit_grants == 0
    assert not result.action_authority and not result.physical_improvement_attested
    safe = _review(_ctx(91, fast=False, near=False), rows, admission)
    assert safe.advice is Attention.CONTINUE
    assert safe.cheap_one_bit is Attention.RECHECK


def test_training_learns_two_axis_interaction_instead_of_embedded_recheck_bit() -> None:
    rows, admission = _fixture(xor=True)
    a = _review(_ctx(90, fast=True, near=False), rows, admission)
    b = _review(_ctx(91, fast=True, near=True), rows, admission)
    assert a.selected_axes == ("clearance_band", "fast_gait")
    assert a.advice is Attention.RECHECK
    assert b.advice is Attention.CONTINUE


def test_no_memory_and_empty_training_abstain() -> None:
    rows, admission = _fixture()
    c = _ctx(90, fast=True, near=False)
    assert _review(c, rows, admission, enabled=False).reason == "MEMORY_OFF"
    assert _review(c, rows, admission, enabled=False).advice is Attention.DEFER
    empty = _review(c, (), MotorSourceAdmission(frozenset(), frozenset()))
    assert empty.reason == "NO_ADMITTED_TRAINING"
    assert empty.advice is Attention.DEFER


def test_unseen_world_hazard_and_changed_regime_defer_or_reject() -> None:
    rows, admission = _fixture()
    c = _ctx(90, fast=True, near=False, obstacle=True)
    result = _review(c, rows, admission)
    assert result.reason == "UNSEEN_CUE_VALUE"
    assert result.advice is Attention.DEFER
    with pytest.raises(BCGRejected, match="foreign"):
        _review(replace(c, regime="different-physics"), rows, admission)


@pytest.mark.parametrize("change", [
    "duplicate_world",
    "same_target_world",
    "unadmitted_action",
    "unadmitted_settling",
    "provisional",
    "not_observed",
    "missing_digest",
    "nan_settling",
])
def test_source_and_goal_leakage_fences(change: str) -> None:
    rows, admission = _fixture()
    c = _ctx(90, fast=True, near=False)
    first = rows[0]
    if change == "duplicate_world":
        bad = replace(rows[1], context=replace(rows[1].context, world_id="world-0"))
        rows = (first, bad, *rows[2:])
    elif change == "same_target_world":
        c = replace(c, world_id="world-0")
    elif change == "unadmitted_action":
        rows = (replace(first, original_s16_sha256=_sha(200)), *rows[1:])
    elif change == "unadmitted_settling":
        rows = (replace(first, original_settling_sha256=_sha(201)), *rows[1:])
    elif change == "provisional":
        rows = (replace(first, settling_grade="PROVISIONAL_PAPER_ONLY"), *rows[1:])
    elif change == "not_observed":
        rows = (replace(first, context=replace(first.context, source_kind="PREDICTED")), *rows[1:])
    elif change == "missing_digest":
        rows = (replace(first, original_settling_sha256=""), *rows[1:])
    elif change == "nan_settling":
        rows = (replace(first, settling_m=float("nan")), *rows[1:])
    with pytest.raises(BCGRejected):
        _review(c, rows, admission)


def test_stale_inferred_current_cannot_become_physical_fact() -> None:
    rows, admission = _fixture()
    c = _ctx(90, fast=True, near=False)
    with pytest.raises(BCGRejected, match="stale"):
        _review(replace(c, freshness_ok=False), rows, admission)
    with pytest.raises(BCGRejected, match="inferred"):
        _review(replace(c, source_kind="INFERRED"), rows, admission)


def test_conflicting_observations_abstain_instead_of_auto_promote() -> None:
    rows, admission = _fixture()
    # Reverse one outcome per speed to spoil stable single-axis cells;
    # no stable two-axis cell may invent a majority from one World.
    spoiled = tuple(
        replace(\n            row,\n            context=replace(row.context, fatigue_high=False),\n            settling_m=1.0 if (i % 2 == 0) else 0.0,\n        )
        for i, row in enumerate(rows)
    )
    result = _review(_ctx(90, fast=True, near=False), spoiled, admission)
    assert result.advice is Attention.DEFER
    assert result.reason == "NO_STABLE_CONDITIONAL_RULE"
