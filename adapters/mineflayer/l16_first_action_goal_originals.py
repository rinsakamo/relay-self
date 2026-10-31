"""L16: inspect S49's sole original Mineflayer session, read-only.

Source-shaped Goal geometry is a DEV diagnostic, NEVER an externally admitted
L13 Goal receipt, L10 training pair, or causal learning/physical attestation.
The original recorder is S7; this module never creates or issues an Action.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

from adapters.mineflayer.python_protocol import (
    MineflayerEffectResult,
    MineflayerObservation,
    MineflayerStreamDecoder,
)
from relay_self.l14_original_bridge_goal_window import (
    L14SourceRejected,
    MAX_RECEIVED,
    MAX_RECEIVED_LINES,
    MAX_SENT,
    MAX_SENT_LINES,
    _json,
    _lines,
    _strict_receipt,
)

PLAN_SCHEMA = "L16_PRE_WORLD_OPERATOR_SPATIAL_GOAL_V1"
WINDOW_SCHEMA = "L16_S49_FIRST_ACTION_ORIGINAL_GOAL_SOURCE_V1"


class L16SourceRejected(ValueError):
    """No independently qualified physical learning source may be inferred."""


@dataclass(frozen=True, slots=True)
class L16GoalPlan:
    target_x: float
    target_z: float
    tolerance_m: float = 0.49
    stable_probe_delta_max_m: float = 0.05

    def __post_init__(self) -> None:
        for value in (
            self.target_x, self.target_z, self.tolerance_m,
            self.stable_probe_delta_max_m,
        ):
            if type(value) not in (int, float) or not math.isfinite(value):
                raise L16SourceRejected("finite spatial Goal plan required")
        if not (0 < self.tolerance_m <= 16
                and 0 < self.stable_probe_delta_max_m <= 0.1):
            raise L16SourceRejected("spatial Goal bounds invalid")

    def original_bytes(self) -> bytes:
        """Operator's fixed plan before World, NOT a third-party Goal owner."""
        value = {
            "schema": PLAN_SCHEMA,
            "target_x": self.target_x,
            "target_z": self.target_z,
            "tolerance_m": self.tolerance_m,
            "stable_probe_delta_max_m": self.stable_probe_delta_max_m,
            "independent_external_goal_owner": False,
            "authorizes_learning": False,
        }
        return (json.dumps(value, allow_nan=False, sort_keys=True,
                           separators=(",", ":")) + "\n").encode("utf-8")


@dataclass(frozen=True, slots=True)
class L16FirstActionWindow:
    schema: str
    session_id: str
    action_id: str
    before_seq: int
    dispatch_seq: int
    cleanup_seq: int
    after_seq: int
    goal_probe_seq: int
    second_goal_probe_seq: int
    plan_sha256: str
    received_sha256: str
    sent_sha256: str
    observed_goal_status: str
    distance_first_m: float
    distance_second_m: float
    complete_single_action_captured_prefix: bool = True
    independent_external_goal_authenticated: bool = False
    physical_no_intervention_proven: bool = False
    qualified_real_l10_pairs: int = 0
    l10_adoptions: int = 0
    action_issues: int = 0
    s10_updates: int = 0
    s11_habit_grants: int = 0


def inspect_l16_first_action_prefix(
    *, received_original: bytes, sent_original: bytes,
    s7_receipt: dict, plan: L16GoalPlan, plan_original: bytes,
    action_id: str, session_id: str, before_seq: int, dispatch_seq: int,
    cleanup_seq: int, after_seq: int, first_probe_seq: int,
    second_probe_seq: int,
    first_probe_request_id: str, second_probe_request_id: str,
) -> L16FirstActionWindow:
    """Verify exact S7 first-Action prefix; abstain from L13 authority."""
    if not isinstance(plan, L16GoalPlan) or plan.original_bytes() != plan_original:
        raise L16SourceRejected("pre-World fixed plan original was modified")
    if not all(isinstance(v, str) and v for v in (
        action_id, session_id, first_probe_request_id,
        second_probe_request_id,
    )):
        raise L16SourceRejected("source identity required")
    if first_probe_request_id == second_probe_request_id:
        raise L16SourceRejected("duplicate terminal probe request")
    seqs = (before_seq, dispatch_seq, cleanup_seq, after_seq,
            first_probe_seq, second_probe_seq)
    if (any(type(v) is not int for v in seqs)
            or not (0 < before_seq < dispatch_seq < cleanup_seq
                    < after_seq < first_probe_seq < second_probe_seq)):
        raise L16SourceRejected("S49 terminal sequence invalid")
    try:
        rlines = _lines(
            received_original, MAX_RECEIVED, MAX_RECEIVED_LINES, "received",
        )
        slines = _lines(sent_original, MAX_SENT, MAX_SENT_LINES, "sent")
        _strict_receipt(s7_receipt, received_original, sent_original,
                        rlines, slines)
        decoder = MineflayerStreamDecoder()
        frames = []
        for row in rlines:
            _json(row)
            frames.append(decoder.decode(row.decode("utf-8")))
    except (L14SourceRejected, ValueError, UnicodeError) as exc:
        raise L16SourceRejected("invalid S7 original stream/index") from exc
    if (len(frames) != second_probe_seq + 1
            or frames[0].seq != 0
            or decoder.session_id != session_id
            or not all(frame.session_id == session_id
                       for frame in frames)):
        raise L16SourceRejected("source prefix incomplete or session changed")
    before, dispatch, cleanup, after, first, second = (
        frames[n] for n in seqs
    )
    if not (isinstance(before, MineflayerObservation)
            and before.kind == "probe"
            and isinstance(after, MineflayerObservation)
            and after.kind == "probe"
            and isinstance(first, MineflayerObservation)
            and isinstance(second, MineflayerObservation)
            and first.kind == second.kind == "probe"
            and first.request_id == first_probe_request_id
            and second.request_id == second_probe_request_id):
        raise L16SourceRejected("S49/terminal native probes do not match")
    if not (isinstance(dispatch, MineflayerEffectResult)
            and isinstance(cleanup, MineflayerEffectResult)
            and (dispatch.action_id, dispatch.effect, dispatch.result,
                 dispatch.error) == (action_id, "set_control", "applied", None)
            and (cleanup.action_id, cleanup.effect, cleanup.result,
                 cleanup.error) ==
            (f"{action_id}-s15-clear", "clear_controls", "applied", None)):
        raise L16SourceRejected("S49 existing motor / cleanup ACK absent")
    if any(
        isinstance(frame, MineflayerEffectResult)
        and frame.seq not in (dispatch_seq, cleanup_seq)
        for frame in frames
    ):
        raise L16SourceRejected("another physical effect in recorded prefix")
    if any(
        not isinstance(frame, MineflayerObservation)
        for frame in frames[after_seq + 1:]
    ):
        raise L16SourceRejected("non-observation after S16 clearance")
    sent = [_json(line) for line in slines]
    effects = [item for item in sent if item.get("type") == "effect"]
    observes = [item.get("request_id") for item in sent
                if item.get("type") == "observe"]
    if (any(item.get("type") not in ("observe", "effect") for item in sent)
            or len(effects) != 2
            or not (
                effects[0].get("action_id") == action_id
                and effects[0].get("effect") == "set_control"
                and effects[0].get("control") == "back"
                and effects[0].get("state") is True
                and effects[1].get("action_id") == f"{action_id}-s15-clear"
                and effects[1].get("effect") == "clear_controls"
            )
            or observes[-2:] != [
                first_probe_request_id, second_probe_request_id,
            ]):
        raise L16SourceRejected("outbound single Action/Goal requests differ")
    distance_first = math.hypot(
        first.snapshot.position.x - plan.target_x,
        first.snapshot.position.z - plan.target_z,
    )
    distance_second = math.hypot(
        second.snapshot.position.x - plan.target_x,
        second.snapshot.position.z - plan.target_z,
    )
    movement = math.hypot(
        first.snapshot.position.x - second.snapshot.position.x,
        first.snapshot.position.z - second.snapshot.position.z,
    )
    if (movement > plan.stable_probe_delta_max_m
            or (distance_first <= plan.tolerance_m)
            != (distance_second <= plan.tolerance_m)):
        observed = "UNDETERMINED"
    else:
        observed = ("REACHED" if distance_second <= plan.tolerance_m
                    else "NOT_REACHED")
    return L16FirstActionWindow(
        schema=WINDOW_SCHEMA, session_id=session_id, action_id=action_id,
        before_seq=before_seq, dispatch_seq=dispatch_seq,
        cleanup_seq=cleanup_seq, after_seq=after_seq,
        goal_probe_seq=first_probe_seq,
        second_goal_probe_seq=second_probe_seq,
        plan_sha256=hashlib.sha256(plan_original).hexdigest(),
        received_sha256=s7_receipt["received_sha256"],
        sent_sha256=s7_receipt["sent_sha256"],
        observed_goal_status=observed,
        distance_first_m=distance_first,
        distance_second_m=distance_second,
    )


def load_original_prefix(root: Path) -> tuple[bytes, bytes, dict, bytes]:
    """Read only the sealed original files; never recover lost raw bytes."""
    if not isinstance(root, Path) or not root.is_absolute():
        raise L16SourceRejected("physical capture root must be absolute")
    names = ("native_bridge_received_original.jsonl",
             "native_bridge_sent_original.jsonl",
             "native_bridge_source_receipt.json",
             "l16_pre_world_goal_plan.json")
    if any((root / name).is_symlink() for name in names):
        raise L16SourceRejected("source path symlink")
    a, b, c, d = ((root / name).read_bytes() for name in names)
    if len(c) > 8192 or not c.endswith(b"\n"):
        raise L16SourceRejected("invalid index original")
    try:
        index = _json(c)
    except L14SourceRejected as exc:
        raise L16SourceRejected("invalid source index") from exc
    return a, b, index, d
