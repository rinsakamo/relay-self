"""S50 #627: offline single-writer / Executor-feedback ordering contract.

This is a pure adversarial checker, NOT a runtime arbiter, Action issuer,
teleport acknowledgement, Paper clock bridge, or qualification. Its callers
must independently authenticate source references before any physical grant.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence


class ControlLoopOrderRejected(ValueError):
    """Multiple writers, misordered effects, or missing source-bound closure."""


_EFFECTS = {"LOOK", "FORWARD_ON", "CLEAR_ALL"}
_SOURCE_EVENTS = {
    "SETUP_TP", "SETUP_HANDOFF", "ACTION_ISSUED",
    "LOOK", "FORWARD_ON", "CLEAR_ALL", "EXECUTOR_RESULT", "STOP",
}


def _identifier(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 256


def _source(row: Mapping[str, object]) -> None:
    if not _identifier(row.get("source_ref")):
        raise ControlLoopOrderRejected("missing bounded original source reference")


def audit_control_loop_order(events: Sequence[Mapping[str, object]]) -> dict:
    """Check one session's setup -> Self Action -> Executor result -> STOP.

    Only event syntax, provenance *reference presence*, and control ordering
    are checked. Referenced native/Paper originals and actual tick activity
    are NOT verified by this function.
    """
    if not isinstance(events, (tuple, list)) or not 1 <= len(events) <= 512:
        raise ControlLoopOrderRejected("missing/unbounded control trace")
    session = None
    phase = "SETUP"
    setup_seen = False
    action_id = None
    effect_stage = 0
    terminal = None
    has_world_evidence = False
    for expected_ordinal, row in enumerate(events, 1):
        if not isinstance(row, Mapping):
            raise ControlLoopOrderRejected("invalid control row")
        if type(row.get("ordinal")) is not int or row["ordinal"] != expected_ordinal:
            raise ControlLoopOrderRejected("nonconsecutive or duplicate control ordinal")
        sid = row.get("session_id")
        if not _identifier(sid) or (session is not None and session != sid):
            raise ControlLoopOrderRejected("foreign or missing session")
        session = sid
        kind = row.get("kind")
        writer = row.get("writer")
        aid = row.get("action_id")
        if kind not in _SOURCE_EVENTS | {"OBSERVE"}:
            raise ControlLoopOrderRejected("foreign/unclassified control event")
        if writer not in {"setup", "executor", "supervisor", "observer"}:
            raise ControlLoopOrderRejected("unknown control writer")
        if phase == "STOPPED":
            raise ControlLoopOrderRejected("source after terminal STOP")
        if kind == "OBSERVE":
            if writer not in {"executor", "observer"} or row.get("effect") is not None:
                raise ControlLoopOrderRejected("observer attempted physical mutation")
            _source(row)
            continue
        _source(row)
        if kind == "SETUP_TP":
            if phase != "SETUP" or setup_seen or writer != "setup" or aid is not None:
                raise ControlLoopOrderRejected("overlapping or duplicate World setup writer")
            setup_seen = True
        elif kind == "SETUP_HANDOFF":
            if phase != "SETUP" or not setup_seen or writer != "executor" or aid is not None:
                raise ControlLoopOrderRejected("unfenced setup to Self handoff")
            # Reference identity alone never attests packet confirmation or
            # that no delayed server correction can subsequently arrive.
            for field in (
                "teleport_confirm_ref", "client_pose_ref",
                "paper_pose_ref", "correction_settlement_ref",
            ):
                if not _identifier(row.get(field)):
                    raise ControlLoopOrderRejected("setup handoff original source incomplete")
            phase = "SELF_READY"
        elif kind == "ACTION_ISSUED":
            if phase != "SELF_READY" or writer != "supervisor" or not _identifier(aid):
                raise ControlLoopOrderRejected("second or unauthorized in-flight Action")
            phase = "SELF_ACTIVE"
            action_id = aid
            effect_stage = 0
        elif kind in _EFFECTS:
            if phase != "SELF_ACTIVE" or writer != "executor" or aid != action_id:
                raise ControlLoopOrderRejected("foreign/second motor writer")
            expected = ("LOOK", "FORWARD_ON", "CLEAR_ALL")[effect_stage] if effect_stage < 3 else None
            if kind != expected:
                raise ControlLoopOrderRejected("duplicated or out-of-order motor effect")
            effect_stage += 1
        elif kind == "EXECUTOR_RESULT":
            if phase != "SELF_ACTIVE" or writer != "executor" or aid != action_id:
                raise ControlLoopOrderRejected("result was not from sole Executor")
            if row.get("terminal") not in {"OUTCOME", "UNKNOWN", "TIMEOUT"}:
                raise ControlLoopOrderRejected("result not a supported Action terminal")
            if effect_stage not in {0, 3}:
                # Pre-FORWARD LOOK failures may close UNKNOWN after effect ACK.
                if not (effect_stage == 1 and row.get("terminal") == "UNKNOWN"):
                    raise ControlLoopOrderRejected("unreleased motor before result")
            if row.get("terminal") == "OUTCOME" and effect_stage != 3:
                raise ControlLoopOrderRejected("fabricated successful physical closure")
            if row.get("terminal") != "OUTCOME" and not _identifier(row.get("error_ref")):
                raise ControlLoopOrderRejected("UNKNOWN/TIMEOUT missing failure evidence")
            has_world_evidence = _identifier(row.get("world_evidence_ref"))
            if row.get("terminal") == "OUTCOME" and not has_world_evidence:
                raise ControlLoopOrderRejected("OUTCOME requires actual World readback")
            terminal = row["terminal"]
            phase = "SELF_READY"
        elif kind == "STOP":
            if writer != "executor" or phase not in {"SELF_READY", "SETUP"} or aid is not None:
                raise ControlLoopOrderRejected("STOP from second writer or open Action")
            phase = "STOPPED"
        else:
            raise ControlLoopOrderRejected("invalid control trace transition")
    if not setup_seen or phase != "STOPPED":
        raise ControlLoopOrderRejected("source-bound handoff/STOP not closed")
    return {
        "classification": "S50_OFFLINE_CONTROL_LOOP_ORDER_ONLY",
        "session_id": session,
        "terminal": terminal,
        "source_references_authenticated": False,
        "actual_server_effective_control_ticks": "NOT_ATTESTED",
        "pending_server_corrections_excluded": False,
        "self_feedback_delivered": False,
        "P1_wait_ticks_admitted": 0,
        "science_go": False,
    }
