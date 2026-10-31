"""Self-supervised L1 motor expectation *DEV shadow*, never S10 Goal learning.

The only training observations are source-checked S49 MOVE_BACKWARD native
position changes from an older, completed separate Minecraft World. Predict
the next original S49 executed motor displacement; score against the cheap
last-value predictor on the SAME next-World outcomes. No actual Action choice
or Minecraft resource accounting is changed, and no physical improvement
is claimed without real held-out measurements.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from adapters.mineflayer.python_protocol import (
    MineflayerObservation,
    MineflayerStreamDecoder,
)
from adapters.mineflayer.slm_prior_world_dev import read_previous_s49_world


class MotorExpectationRejected(ValueError):
    """Source mismatch, untrusted physics sample or forged motor evidence."""


@dataclass(frozen=True, slots=True)
class MotorHistory:
    source_session_id: str
    source_stdout_sha256: str
    original_action_ids: tuple[str, ...]
    displacement_m: tuple[float, ...]
    source_scope: str = "S49_W3_NODE_STDOUT_OBSERVED_MOTOR_DEV_NOT_INDEPENDENT_TCP"
    independent_source_attested: bool = False
    external_goal_labels: int = 0
    s10_updates: int = 0
    action_authority: bool = False

    def __post_init__(self):
        if (
            type(self.source_session_id) is not str or not self.source_session_id
            or type(self.source_stdout_sha256) is not str
            or len(self.source_stdout_sha256) != 64
            or not all(x in "0123456789abcdef" for x in self.source_stdout_sha256)
            or len(self.original_action_ids) != 2
            or len(set(self.original_action_ids)) != 2
            or any(type(x) is not str or not x for x in self.original_action_ids)
            or len(self.displacement_m) != 2
            or any(
                type(x) is not float or not math.isfinite(x) or not 0 < x <= 8
                for x in self.displacement_m
            )
            or self.source_scope
            != "S49_W3_NODE_STDOUT_OBSERVED_MOTOR_DEV_NOT_INDEPENDENT_TCP"
            or self.independent_source_attested is not False
            or self.external_goal_labels != 0
            or self.s10_updates != 0
            or self.action_authority is not False
        ):
            raise MotorExpectationRejected("only bounded non-authorizing actual motor source")


def read_previous_motor_history(
    root: Path, *, expected_stdout_sha256: str,
) -> MotorHistory:
    """Re-audit W3 original + report and recompute real S49 motor deltas.

    Do not treat an S49 executed Action as a Goal success, nor infer physical
    idle beyond the S16 after observation. This is node-stdout based.
    """
    previous = read_previous_s49_world(
        root, expected_stdout_sha256=expected_stdout_sha256,
    )
    data = (root / "native" / "w3-node-stdout.raw.jsonl").read_bytes()
    if not data or len(data) > 32 * 1024 * 1024:
        raise MotorExpectationRejected("unbounded previous native W3 input")
    decoder = MineflayerStreamDecoder()
    try:
        frames = [decoder.decode(raw.decode("utf-8")) for raw in data.splitlines(keepends=True)]
        report = json.loads((root / "report.json").read_bytes())
    except (ValueError, UnicodeError, TypeError) as exc:
        raise MotorExpectationRejected("original native motor frames rejected") from exc
    if (
        decoder.session_id != previous.session_id
        or len(frames) < 3
        or any(x.seq != i or x.session_id != previous.session_id
               for i, x in enumerate(frames))
    ):
        raise MotorExpectationRejected("original W3 session/sequence drift")
    original_actions = report.get("actual_native_actions")
    if type(original_actions) is not list or len(original_actions) != 2:
        raise MotorExpectationRejected("actual Action source scope changed")
    values = []
    for action, expected_id in zip(original_actions, previous.original_action_ids, strict=True):
        evidence = action["execution_evidence"]
        before = evidence["before_observation"]
        after = evidence["after_observation"]
        bi, ai = before["seq"], after["seq"]
        if (
            action["action"] != expected_id or action["terminal"] != "outcome"
            or evidence.get("action_ref") != "MOVE_BACKWARD"
            or type(bi) is not int or type(ai) is not int
            or not 0 <= bi < ai < len(frames)
        ):
            raise MotorExpectationRejected("only executed original MOVE_BACKWARD is predicted")
        a, z = frames[bi], frames[ai]
        if (
            not isinstance(a, MineflayerObservation)
            or not isinstance(z, MineflayerObservation)
            or a.kind != "probe" or z.kind != "probe"
            or a.session_id != previous.session_id
            or z.session_id != previous.session_id
        ):
            raise MotorExpectationRejected("before/after must be original native probes")
        expected_before = before["snapshot"]["position"]
        expected_after = after["snapshot"]["position"]
        if any(
            not math.isclose(
                getattr(obs.snapshot.position, coord), expected[coord],
                rel_tol=0, abs_tol=1e-9,
            )
            for obs, expected in ((a, expected_before), (z, expected_after))
            for coord in ("x", "y", "z")
        ):
            raise MotorExpectationRejected("original report and decoded W3 position mismatch")
        delta = math.hypot(
            a.snapshot.position.x - z.snapshot.position.x,
            a.snapshot.position.z - z.snapshot.position.z,
        )
        if (
            not math.isfinite(delta) or not 0 < delta <= 8
            or type(action.get("movement_m")) not in (int, float)
            or type(evidence.get("movement_m")) not in (int, float)
            or not math.isclose(delta, action["movement_m"], rel_tol=0, abs_tol=1e-8)
            or not math.isclose(delta, evidence["movement_m"], rel_tol=0, abs_tol=1e-8)
        ):
            raise MotorExpectationRejected("movement is not a verified original source delta")
        values.append(float(delta))
    return MotorHistory(
        previous.session_id, previous.stdout_sha256, previous.original_action_ids,
        tuple(values),
    )


def score_motor_expectation(
    history: MotorHistory, *, current_session_id: str,
    current_actions: list[dict],
) -> dict[str, object]:
    """Post-cleanup holdout scoring. Does not grant future/motor policy."""
    if not isinstance(history, MotorHistory):
        raise MotorExpectationRejected("validated past source required")
    if type(current_session_id) is not str or not current_session_id:
        raise MotorExpectationRejected("current session required")
    if current_session_id == history.source_session_id:
        raise MotorExpectationRejected("no same-session training/holdout leak")
    if type(current_actions) is not list or len(current_actions) > 2:
        raise MotorExpectationRejected("only original bounded S49 Actions allowed")
    prior_mean = sum(history.displacement_m) / len(history.displacement_m)
    cheap_last = history.displacement_m[-1]
    outcomes = []
    for row in current_actions:
        evidence = row.get("execution_evidence")
        if (
            type(evidence) is not dict or row.get("terminal") != "outcome"
            or row.get("source") != current_session_id
            or evidence.get("action_ref") != "MOVE_BACKWARD"
            or evidence.get("source_status") not in (None, "executed")
            or evidence.get("status") != "executed"
            or evidence.get("goal_success_attested") is not False
            or type(row.get("movement_m")) not in (float, int)
            or not math.isfinite(row["movement_m"])
            or not 0 < row["movement_m"] <= 8
        ):
            raise MotorExpectationRejected("no valid actual heldout MOVE_BACKWARD")
        measured = float(row["movement_m"])
        outcomes.append({
            "action_id": row["action"],
            "actual_m": measured,
            "model_abs_error_m": abs(measured - prior_mean),
            "cheap_last_abs_error_m": abs(measured - cheap_last),
        })
    model_mae = (
        sum(x["model_abs_error_m"] for x in outcomes) / len(outcomes)
        if outcomes else None
    )
    cheap_mae = (
        sum(x["cheap_last_abs_error_m"] for x in outcomes) / len(outcomes)
        if outcomes else None
    )
    # Minecraft numeric jitter must not become a fake predictive win.
    # A 0.1 mm MAE margin is predeclared for the *offline* readback here;
    # it is a DEV comparison tolerance, not a physical qualification.
    margin_m = 0.0001
    comparison = "NOT_EVALUATED"
    if model_mae is not None:
        if model_mae + margin_m < cheap_mae:
            comparison = "MODEL_MEAN_BETTER_THAN_CHEAP_LAST"
        elif cheap_mae + margin_m < model_mae:
            comparison = "CHEAP_LAST_BETTER_THAN_MODEL_MEAN"
        else:
            comparison = "CHEAP_EQUIVALENT_WITHIN_MARGIN"
    return {
        "schema": "S49_L1_MOTOR_EXPECTATION_DEV_V1",
        "status": "HELDOUT_SCORED" if outcomes else "NO_CURRENT_MOTOR_OUTCOME",
        "past_session": history.source_session_id,
        "current_session": current_session_id,
        "training_observations": len(history.displacement_m),
        "holdout_observations": len(outcomes),
        "model": "MEAN_OF_PAST_TWO_REAL_MOVE_BACKWARD",
        "model_expected_m": prior_mean,
        "cheap_control": "LAST_PRIOR_REAL_MOVE_BACKWARD",
        "cheap_expected_m": cheap_last,
        "model_mae_m": model_mae,
        "cheap_mae_m": cheap_mae,
        "comparison_margin_m": margin_m,
        "comparison_status": comparison,
        "beats_cheap_control": (
            comparison == "MODEL_MEAN_BETTER_THAN_CHEAP_LAST"
            if model_mae is not None else None
        ),
        "holdout": outcomes,
        "source_independently_attested": False,
        "real_goal_training_labels": 0,
        "l8_learning_updates": 0,
        "s10_updates": 0,
        "action_authority": False,
        "policy_changed": False,
        "scope": "DEV_SELF_SUPERVISED_MOTOR_FORECAST_NOT_GOAL_L1_HABIT",
    }
