"""Lossless *decoded typed* S15/S16 evidence for subsequent Self demo runs.

Captures original immutable Mineflayer protocol objects, not raw wire bytes.
This module cannot reconstruct an earlier run whose frames were not retained.
No goal-success label, S17 feedback or production Habit permission is inferred.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict
from typing import Any

from adapters.mineflayer.execution import WorldConsequence, WorldConsequenceStatus

EVIDENCE_SCHEMA = "SELF_NATIVE_ACTION_DECODED_FRAMES_V1"


class NativeEvidenceRejected(ValueError):
    """Unlinked, forged or incomplete native Action evidence."""


def _number(x: object) -> float:
    if type(x) not in (int, float) or not math.isfinite(x):
        raise NativeEvidenceRejected("source coordinate/movement is not finite")
    return float(x)


def verify_native_action_evidence(
    value: object, *,
    action_id: str,
    session_id: str,
    movement_m: float,
) -> None:
    """Check exact source/seq/dispatch/cleanup and independently recalc xz."""
    if not isinstance(value, dict) or set(value) != {
        "schema", "action_id", "binding_id", "action_ref", "session_id",
        "status", "before_observation", "dispatch_receipt",
        "cleanup_receipt", "after_observation", "movement_m",
        "cleanup_attempted", "goal_success_attested",
        "learning_feedback_qualified",
    }:
        raise NativeEvidenceRejected("missing/unrecognized Action evidence fields")
    if (
        value["schema"] != EVIDENCE_SCHEMA
        or value["action_id"] != action_id
        or value["session_id"] != session_id
        or not isinstance(value["binding_id"], str)
        or not value["binding_id"]
        or value["action_ref"] != "MOVE_BACKWARD"
        or value["status"] != "executed"
        or value["cleanup_attempted"] is not True
        or value["goal_success_attested"] is not False
        or value["learning_feedback_qualified"] is not False
    ):
        raise NativeEvidenceRejected("Action/session/status/permission mismatch")
    frames = (
        value["before_observation"],
        value["dispatch_receipt"],
        value["cleanup_receipt"],
        value["after_observation"],
    )
    if any(
        not isinstance(frame, dict)
        or frame.get("session_id") != session_id
        or type(frame.get("seq")) is not int
        or frame["seq"] < 0
        for frame in frames
    ):
        raise NativeEvidenceRejected("source session/seq missing or foreign")
    if not all(x["seq"] < y["seq"] for x, y in zip(frames, frames[1:])):
        raise NativeEvidenceRejected("nonmonotonic Action observation/effect order")
    for index in (0, 3):
        frame = frames[index]
        if frame.get("kind") not in ("entities", "probe"):
            raise NativeEvidenceRejected("missing native observation frame")
        if (
            not isinstance(frame.get("snapshot"), dict)
            or not isinstance(frame["snapshot"].get("position"), dict)
            or not isinstance(frame["snapshot"].get("nearby_entities"), list)
            or not isinstance(frame["snapshot"].get("nearby_entities_coverage"), dict)
            or frame.get("provenance") != {
                "source": "mineflayer",
                "reference": f"{session_id}:{frame['seq']}",
            }
        ):
            raise NativeEvidenceRejected("full decoded native snapshot/provenance absent")
    dispatch, cleanup = frames[1], frames[2]
    if (
        dispatch.get("action_id") != action_id
        or dispatch.get("effect") != "set_control"
        or dispatch.get("result") != "applied"
        or dispatch.get("error") is not None
        or cleanup.get("action_id") != f"{action_id}-s15-clear"
        or cleanup.get("effect") != "clear_controls"
        or cleanup.get("result") != "applied"
        or cleanup.get("error") is not None
        or dispatch.get("provenance") != {
            "source": "mineflayer",
            "reference": f"{session_id}:{dispatch['seq']}",
        }
        or cleanup.get("provenance") != {
            "source": "mineflayer",
            "reference": f"{session_id}:{cleanup['seq']}",
        }
    ):
        raise NativeEvidenceRejected("dispatch/cleanup original effect receipts invalid")
    before = frames[0]["snapshot"]["position"]
    after = frames[3]["snapshot"]["position"]
    if any(set(v) != {"x", "y", "z"} for v in (before, after)):
        raise NativeEvidenceRejected("coordinate vector incomplete")
    movement = math.hypot(
        _number(after["x"]) - _number(before["x"]),
        _number(after["z"]) - _number(before["z"]),
    )
    if (
        not math.isclose(movement, _number(value["movement_m"]), abs_tol=1e-9)
        or not math.isclose(movement, _number(movement_m), abs_tol=1e-9)
        or movement < 0.05
    ):
        raise NativeEvidenceRejected("World movement not independently reproducible")


def _source_frame(message: Any) -> dict[str, Any]:
    # dataclasses.asdict preserves Python tuples; protocol JSON converts
    # them to arrays. Validate the exact durable JSON shape we actually save.
    frame = json.loads(json.dumps(asdict(message), allow_nan=False))
    frame["provenance"] = asdict(message.provenance)
    return frame


def capture_native_action_evidence(
    consequence: WorldConsequence,
) -> dict[str, Any]:
    """Read existing immutable S16 result; never trigger a new native probe."""
    if (
        not isinstance(consequence, WorldConsequence)
        or consequence.status is not WorldConsequenceStatus.EXECUTED
        or consequence.before_observation is None
        or consequence.after_observation is None
        or consequence.dispatch_receipt is None
        or consequence.cleanup_receipt is None
        or consequence.movement_distance is None
    ):
        raise NativeEvidenceRejected("fully observed existing S16 receipt required")
    result = {
        "schema": EVIDENCE_SCHEMA,
        "action_id": consequence.action_id,
        "binding_id": consequence.binding_id,
        "action_ref": consequence.action_ref,
        "session_id": consequence.session_id,
        "status": consequence.status.value,
        "before_observation": _source_frame(consequence.before_observation),
        "dispatch_receipt": _source_frame(consequence.dispatch_receipt),
        "cleanup_receipt": _source_frame(consequence.cleanup_receipt),
        "after_observation": _source_frame(consequence.after_observation),
        "movement_m": consequence.movement_distance,
        "cleanup_attempted": consequence.cleanup_attempted,
        "goal_success_attested": False,
        "learning_feedback_qualified": False,
    }
    verify_native_action_evidence(
        result, action_id=consequence.action_id,
        session_id=consequence.session_id,
        movement_m=consequence.movement_distance,
    )
    return result
