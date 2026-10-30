"""L12: original G4.13 Action-end trajectory readback, never Action reward.

Consumes the exact *previously saved* real Paper G4.13 ZIP via L11's
SHA-bound validator, not Minecraft, the original Node JSONL stream or S16
per-Action Goal receipts. Observed endpoint progress is not action causality.
"""
from __future__ import annotations

import argparse
import json
import math
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path

from adapters.mineflayer.l11_saved_real_goal_originals_dev import (
    L11OriginalBoundaryAudit,
    L11OriginalRejected,
    audit_l11_g413_saved_originals,
)

SCHEMA = "L12_G413_S49_ENDPOINT_PROGRESS_NO_GOAL_REWARD_V1"
EXPECTED_FIELDS = frozenset({
    "action_id", "before_seq", "after_seq", "end_x", "end_z",
    "goal_error_at_S16_end_m", "native_displacement_m",
    "native_travel_x", "native_travel_z", "s16_status", "s16_terminal",
})
MAX_ACTIONS = 32


class L12ProgressRejected(ValueError):
    """No optimistic fallback when source is absent, altered or unjoined."""


@dataclass(frozen=True, slots=True)
class L12ActionProgress:
    """Readback of two different measured windows, not physical action reward."""

    world: str
    session_id: str
    action_id: str
    before_native_seq: int
    after_native_seq: int
    source_report_sha256: str
    ordinal: int
    s16_executed: bool
    previous_endpoint_goal_error_m: float
    after_endpoint_goal_error_m: float
    observed_endpoint_goal_reduction_m: float
    endpoint_step_m: float
    original_action_reported_displacement_m: float
    endpoint_advance_minus_action_displacement_m: float
    at_s16_inside_goal_tolerance: bool
    # None means no independently admitted external Goal witness. This is
    # NOT equivalent to False (externally proved goal failure).
    external_action_goal_reached: bool | None = None
    per_action_goal_attested: bool = False
    causal_motor_contribution_attested: bool = False
    native_source_packet_authenticated: bool = False


@dataclass(frozen=True, slots=True)
class L12GoalTrainingGate:
    schema: str
    producer_artifact_id: int
    original_s49_action_rows: int
    original_t2_world_ticks: int
    action_progress: tuple[L12ActionProgress, ...]
    action_end_inside_tolerance: int
    action_end_outside_tolerance: int
    endpoint_step_exceeds_action_displacement: int
    post_terminal_goal_reductions_m: tuple[float, ...]
    independent_per_action_goal_receipts: int = 0
    original_native_pre_action_world_body_receipts: int = 0
    independent_native_s16_jsonl_receipts: int = 0
    qualified_l10_training_pairs: int = 0
    l10_retention_action_authorized: bool = False
    s10_learning_updates: int = 0
    s11_habit_grants: int = 0
    physical_actions_started: int = 0
    new_worlds_started: int = 0
    physical_learning_attested: bool = False
    qualification_go: bool = False
    science_go: bool = False
    classification: str = "L12_REAL_S49_ENDPOINT_PROGRESS_ONLY_NO_PER_ACTION_GOAL_TRAINING"


def _number(x: object) -> float:
    if type(x) not in (int, float) or not math.isfinite(x):
        raise L12ProgressRejected("original trajectory fields must be finite numeric values")
    return float(x)


def _read_pinned(archive: Path, scope: str) -> dict:
    # L11 already checked filename/path/ZIP safety, all four original
    # file SHA pins and the successful original S49/T2 contract.
    with zipfile.ZipFile(archive) as z:
        return json.loads(z.read(f"{scope}/goal_report.json"))


def _action_rows(scope: str, report: dict, original_report_sha256: str) -> tuple[L12ActionProgress, ...]:
    actions = report.get("native_actions")
    goal = report.get("goal_l2")
    initial = report.get("initial_native_xz")
    l1 = report.get("goal_l1")
    if (not isinstance(actions, list) or not 1 <= len(actions) <= MAX_ACTIONS
            or not isinstance(initial, dict) or not isinstance(goal, dict)
            or not isinstance(l1, dict)):
        raise L12ProgressRejected("missing bounded native source-to-goal trajectory")
    tx, tz = _number(goal.get("target_x")), _number(goal.get("target_z"))
    px, pz = _number(initial.get("x")), _number(initial.get("z"))
    initial_seq = initial.get("seq")
    tolerance = _number(l1.get("tolerance_m"))
    if type(initial_seq) is not int or initial_seq < 0 or not 0 < tolerance <= 1:
        raise L12ProgressRejected("unqualified original initial endpoint/tolerance")
    prior_error = math.hypot(px-tx, pz-tz)
    prev_seq = initial_seq
    output = []
    for ordinal, action in enumerate(actions, 1):
        if not isinstance(action, dict) or not EXPECTED_FIELDS.issubset(action):
            raise L12ProgressRejected("original Action endpoint fields incomplete")
        before, after = action["before_seq"], action["after_seq"]
        if (type(before) is not int or type(after) is not int
                or not prev_seq < before < after):
            raise L12ProgressRejected("initial/previous Action source order mismatch")
        end_x, end_z = _number(action["end_x"]), _number(action["end_z"])
        error = _number(action["goal_error_at_S16_end_m"])
        movement = _number(action["native_displacement_m"])
        motion_x = _number(action["native_travel_x"])
        motion_z = _number(action["native_travel_z"])
        if (
            movement < 0 or error < 0
            or not math.isclose(math.hypot(end_x-tx, end_z-tz), error,
                                rel_tol=0, abs_tol=1e-9)
            or not math.isclose(math.hypot(motion_x, motion_z), movement,
                                rel_tol=0, abs_tol=1e-9)
            or action["s16_status"] != "executed"
            or action["s16_terminal"] != "outcome"
        ):
            raise L12ProgressRejected("original S16 source/geometry or movement mismatch")
        # This compares two different windows: adjacent Action-end positions
        # and one Action's reported displacement. Difference may arise during
        # the time between endpoints; it is NOT proven physical coasting.
        step = math.hypot(end_x-px, end_z-pz)
        output.append(L12ActionProgress(
            world=scope, session_id=report["session_id"],
            action_id=action["action_id"], before_native_seq=before,
            after_native_seq=after, source_report_sha256=original_report_sha256,
            ordinal=ordinal, s16_executed=True,
            previous_endpoint_goal_error_m=prior_error,
            after_endpoint_goal_error_m=error,
            observed_endpoint_goal_reduction_m=prior_error-error,
            endpoint_step_m=step,
            original_action_reported_displacement_m=movement,
            endpoint_advance_minus_action_displacement_m=step-movement,
            at_s16_inside_goal_tolerance=error <= tolerance,
        ))
        px, pz, prior_error, prev_seq = end_x, end_z, error, after
    return tuple(output)


def audit_l12_real_action_goal_gate(archive: Path) -> L12GoalTrainingGate:
    """Read only *saved real* L11-admitted report/T2; never mint Goal labels."""
    try:
        parent: L11OriginalBoundaryAudit = audit_l11_g413_saved_originals(archive)
        if (parent.action_goal_labels_admitted != 0
                or parent.l10_qualified_episode_pairs != 0
                or parent.l10_current_world_body_cues_admitted
                or parent.s10_learning_updates != 0
                or parent.action_issues != 0):
            raise L12ProgressRejected("parent promoted an unqualified Goal/source")
        all_rows = []
        final_drifts = []
        for world in parent.worlds:
            report = _read_pinned(archive, world.source)
            rows = _action_rows(world.source, report, world.original_report_sha256)
            if (
                len(rows) != world.original_s49_outcomes
                or rows[-1].after_native_seq != world.last_s16_seq
                or not math.isclose(rows[-1].after_endpoint_goal_error_m,
                                    world.last_s16_goal_error_m,
                                    rel_tol=0, abs_tol=1e-9)
            ):
                raise L12ProgressRejected("original S49 terminal Action join drift")
            drift = rows[-1].after_endpoint_goal_error_m - world.final_goal_error_m
            if world.final_probe_seq <= rows[-1].after_native_seq:
                raise L12ProgressRejected("later native Goal observation missing")
            # Any post-Action improvement must remain a distinct later read;
            # never assign it to an S16 Action or Goal-success label.
            final_drifts.append(drift)
            all_rows.extend(rows)
        if len(all_rows) != parent.original_s49_outcomes:
            raise L12ProgressRejected("Action witness totals inconsistent")
        return L12GoalTrainingGate(
            schema=SCHEMA, producer_artifact_id=parent.artifact_id,
            original_s49_action_rows=len(all_rows),
            original_t2_world_ticks=parent.original_t2_world_ticks,
            action_progress=tuple(all_rows),
            action_end_inside_tolerance=sum(r.at_s16_inside_goal_tolerance for r in all_rows),
            action_end_outside_tolerance=sum(not r.at_s16_inside_goal_tolerance for r in all_rows),
            endpoint_step_exceeds_action_displacement=sum(
                r.endpoint_advance_minus_action_displacement_m > 1e-6
                for r in all_rows
            ),
            post_terminal_goal_reductions_m=tuple(final_drifts),
        )
    except (L11OriginalRejected, ValueError, OSError, TypeError, KeyError,
            zipfile.BadZipFile) as exc:
        raise L12ProgressRejected("original L11 evidence refused or incompatible") from exc


def require_l10_qualified_goal_training(review: L12GoalTrainingGate) -> None:
    """Owner-preserving hard gate: this artifact can NEVER train L10 as Goal.

    A separate new source-qualified S/R/V contract must handle future Goal
    receipts. This function intentionally has no branch to approve L11 rows.
    """
    if not isinstance(review, L12GoalTrainingGate):
        raise L12ProgressRejected("typed real-original review required")
    raise L12ProgressRejected(
        "no independent per-Action external Goal or native World/Body source; "
        "real Action-end progress cannot authorize L10 training"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-zip", type=Path)
    ns = parser.parse_args(argv)
    if ns.artifact_zip is None:
        print(json.dumps({
            "schema": SCHEMA,
            "classification": "L12_REAL_ORIGINAL_BYTES_NOT_SUPPLIED",
            "qualified_l10_training_pairs": 0, "new_worlds_started": 0,
        }, sort_keys=True))
        return 0
    try:
        outcome = audit_l12_real_action_goal_gate(ns.artifact_zip)
    except L12ProgressRejected as exc:
        print(json.dumps({
            "schema": SCHEMA, "classification": "L12_SOURCE_GATE_BLOCKED",
            "reason": str(exc), "qualified_l10_training_pairs": 0,
            "new_worlds_started": 0,
        }, sort_keys=True))
        return 2
    print(json.dumps(asdict(outcome), sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
