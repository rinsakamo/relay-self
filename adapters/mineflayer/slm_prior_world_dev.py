"""Read-only prior real World original-source candidate, NEVER L8 training.

Require a fully preserved original S49 report + W3 native stdout and sealed
receipt from a different completed World. The S49 physical Action's EXECUTED
result is not a separately authenticated external Goal result. Consequently
the derived candidate is ALWAYS withheld from L8 memory admission.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from adapters.mineflayer.self_world_stage_w3_capture import audit_w3_sealed_stdout

_SHA = re.compile(r"[0-9a-f]{64}\Z")


class PriorWorldRejected(ValueError):
    """Unadmitted, incomplete, modified, or ambiguous original DEV source."""


@dataclass(frozen=True, slots=True)
class PriorWorldReadback:
    session_id: str
    stdout_sha256: str
    original_action_ids: tuple[str, ...]
    original_action_probe_seqs: tuple[int, ...]
    original_goal_labels: int = 0
    l8_admissible_episodes: int = 0
    s10_commit_permitted: bool = False
    action_authority: bool = False
    source_attested_independently: bool = False
    reason: str = "WITHHELD_NO_INDEPENDENT_EXTERNAL_GOAL"
    scope: str = "PREVIOUS_S49_DEV_W3_STDOUT_NOT_L10_GOAL_TRAINING"


def _no_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    obj = {}
    for k, v in pairs:
        if k in obj:
            raise PriorWorldRejected("duplicate JSON keys in original report")
        obj[k] = v
    return obj


def read_previous_s49_world(
    root: Path, *, expected_stdout_sha256: str,
) -> PriorWorldReadback:
    """Validate past source bytes, return only a *withheld* episode summary.

    Never signs, reconstructs, labels or commits an L8 training episode.
    The past S49 Action and W3 native stdout share an original producer;
    neither is an independent external Goal authority.
    """
    if (
        not isinstance(root, Path) or not root.is_absolute()
        or root.is_symlink() or not root.is_dir()
        or any(p.is_symlink() for p in root.parents)
        or type(expected_stdout_sha256) is not str
        or not _SHA.fullmatch(expected_stdout_sha256)
    ):
        raise PriorWorldRejected("explicit non-symlink absolute past source and SHA required")
    raw_report = root / "report.json"
    if not raw_report.is_file() or raw_report.is_symlink():
        raise PriorWorldRejected("missing previous S49 original report")
    if raw_report.stat().st_size > 3_000_000:
        raise PriorWorldRejected("unbounded previous S49 report")
    try:
        report = json.loads(raw_report.read_bytes(), object_pairs_hook=_no_duplicates)
        w3 = audit_w3_sealed_stdout(root / "native")
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        raise PriorWorldRejected("previous native original rejected") from exc
    if (
        type(report) is not dict or report.get("status") != "PASS"
        or report.get("node_exit") != 0 or report.get("server_exit") != 0
        or type(report.get("session_id")) is not str
        or not 1 <= len(report["session_id"]) <= 192
        or report["session_id"] != w3["session_id"]
        or w3["stdout_sha256"] != expected_stdout_sha256
        or report.get("w3_node_stdout_capture") != w3
        or report.get("real_model_calls") != 0
        or report.get("learning_in_world") is not False
    ):
        raise PriorWorldRejected("past session, saved SHA or original World result mismatch")

    original = report.get("actual_native_actions")
    if not isinstance(original, list) or len(original) != 2:
        raise PriorWorldRejected("past original S49 Action count not admitted")
    ids, seqs = [], []
    for row in original:
        if type(row) is not dict:
            raise PriorWorldRejected("past original S49 receipt missing")
        evidence = row.get("execution_evidence")
        if type(evidence) is not dict:
            raise PriorWorldRejected("past S49 native Action evidence missing")
        dispatch = evidence.get("dispatch_receipt")
        clear = evidence.get("cleanup_receipt")
        before = evidence.get("before_observation")
        after = evidence.get("after_observation")
        aid, pseq = row.get("action"), row.get("probe_seq")
        if (
            type(aid) is not str or not 1 <= len(aid) <= 192
            or type(pseq) is not int or pseq < 0
            or row.get("terminal") != "outcome"
            or row.get("source") != report["session_id"]
            or evidence.get("status") != "executed"
            or evidence.get("action_id") != aid
            or evidence.get("session_id") != report["session_id"]
            or evidence.get("goal_success_attested") is not False
            or evidence.get("learning_feedback_qualified") is not False
            or any(type(z) is not dict for z in (dispatch, clear, before, after))
            or dispatch.get("action_id") != aid
            or dispatch.get("result") != "applied"
            or dispatch.get("effect") != "set_control"
            or clear.get("action_id") != aid + "-s15-clear"
            or clear.get("result") != "applied"
            or clear.get("effect") != "clear_controls"
            or before.get("session_id") != report["session_id"]
            or after.get("session_id") != report["session_id"]
            or type(before.get("seq")) is not int
            or type(after.get("seq")) is not int
            or not pseq < before["seq"] < after["seq"] <= w3["last_seq"]
            or type(dispatch.get("seq")) is not int
            or type(clear.get("seq")) is not int
            or not before["seq"] < dispatch["seq"] < clear["seq"] < after["seq"]
        ):
            raise PriorWorldRejected("past original S49 executed/clear/source not consistent")
        ids.append(aid)
        seqs.append(pseq)
    if len(set(ids)) != len(ids) or seqs != sorted(seqs):
        raise PriorWorldRejected("past original Action IDs or native sequence invalid")
    return PriorWorldReadback(
        session_id=report["session_id"],
        stdout_sha256=expected_stdout_sha256,
        original_action_ids=tuple(ids),
        original_action_probe_seqs=tuple(seqs),
    )
