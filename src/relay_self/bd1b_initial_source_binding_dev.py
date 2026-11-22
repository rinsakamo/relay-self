"""Strict byte-derived Native/Paper first-login receipt binding (CPU DEV).

This validates fields and internal revisions of *previously captured* original
A/B source receipts, never accepts them as authentic proof of a real Paper or
Native process. No World, Owner, GPU or file mutation occurs.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


class BD1bInitialSourceBindingHold(ValueError):
    """Foreign/stale/incomplete or internally contradictory A/B source."""


_NATIVE = (
    "self_id", "owner_identity", "resident_epoch", "world_id",
    "branch_id", "world_epoch", "native_session_id", "native_request_id",
    "native_sequence", "native_source_ref", "native_world_time",
)
_PAPER = (
    "paper_session_id", "paper_pid", "paper_boot_id", "presence_boot_id",
    "paper_tick", "paper_tick_ref", "paper_actor_uuid", "paper_log_sha256",
)
_FIELDS = frozenset((*_NATIVE, *_PAPER, "native_revision", "paper_revision"))
_HEX = re.compile(r"[0-9a-f]{64}")


def _revision(fields: dict[str, object]) -> str:
    # Independent canonical revision computation, not trust in a supplied string.
    value = json.dumps(fields, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def require_original_initial_a_b(
    initial: object, *, evidence_dir: Path,
    world_id: str, branch_id: str,
    original_sessions: tuple[tuple[str, str], ...],
    paper_session_id: str,
    paper_boot_id: str,
    actor_uuids: tuple[tuple[str, str], ...],
) -> None:
    """Read-only source-consistency check; source authorization stays external.

    Match initial native session against *original* A and B, not A's later
    post-reJOIN session. First-session owner root must be the actual original
    producer root sibling of the immutable evidence folder.
    """
    if (
        type(initial) is not list or len(initial) != 2
        or any(type(x) is not dict or set(x) != _FIELDS for x in initial)
        or [x["self_id"] for x in initial] != ["A", "B"]
        or not isinstance(evidence_dir, Path)
        or type(world_id) is not str or not world_id
        or type(branch_id) is not str or not branch_id
        or type(paper_session_id) is not str or not paper_session_id
        or type(paper_boot_id) is not str or not paper_boot_id
        or tuple(sid for sid, _ in original_sessions) != ("A", "B")
        or tuple(sid for sid, _ in actor_uuids) != ("A", "B")
    ):
        raise BD1bInitialSourceBindingHold("exact original A/B initial source required")
    sessions = dict(original_sessions)
    actors = dict(actor_uuids)
    if (not all(type(sessions[sid]) is str and sessions[sid] for sid in ("A", "B"))
            or sessions["A"] == sessions["B"]
            or not all(type(actors[sid]) is str and actors[sid] for sid in ("A", "B"))
            or actors["A"] == actors["B"]):
        raise BD1bInitialSourceBindingHold("original native/actor identity collision")
    shared = {}
    for row in initial:
        sid = row["self_id"]
        n = {k: row[k] for k in _NATIVE}
        p = {k: row[k] for k in _PAPER}
        if (_revision(n) != row["native_revision"]
                or _revision(p) != row["paper_revision"]):
            raise BD1bInitialSourceBindingHold("forged initial source revision")
        if (n["world_id"] != world_id or n["branch_id"] != branch_id
                or n["owner_identity"] != str(evidence_dir.parent / ("self-" + sid))
                or type(n["resident_epoch"]) is not int
                or n["resident_epoch"] != 1
                or type(n["world_epoch"]) is not int
                or n["world_epoch"] != 0
                or n["native_session_id"] != sessions[sid]
                or type(n["native_sequence"]) is not int
                or n["native_sequence"] < 0
                or type(n["native_world_time"]) is not int
                or n["native_world_time"] < 0
                or not all(type(n[k]) is str and n[k]
                           for k in ("native_request_id", "native_source_ref"))):
            raise BD1bInitialSourceBindingHold("original pre-reJOIN Native source mismatch")
        if (p["paper_session_id"] != paper_session_id
                or p["paper_boot_id"] != paper_boot_id
                or p["presence_boot_id"] != paper_boot_id
                or p["paper_actor_uuid"] != actors[sid]
                or type(p["paper_pid"]) is not int or p["paper_pid"] <= 0
                or type(p["paper_tick"]) is not int or p["paper_tick"] < 0
                or type(p["paper_log_sha256"]) is not str
                or _HEX.fullmatch(p["paper_log_sha256"]) is None
                or type(p["paper_tick_ref"]) is not str
                or re.fullmatch(
                    r"paper-main-thread:p0d:([A-Za-z0-9-]+):([A-Za-z0-9-]+):sha256:[a-f0-9]{64}",
                    p["paper_tick_ref"],
                ) is None):
            raise BD1bInitialSourceBindingHold("original Paper boot or actor mismatch")
        match = re.fullmatch(
            r"paper-main-thread:p0d:([A-Za-z0-9-]+):([A-Za-z0-9-]+):sha256:[a-f0-9]{64}",
            p["paper_tick_ref"],
        )
        assert match is not None
        if match.group(1) != paper_boot_id:
            raise BD1bInitialSourceBindingHold("first-paper nonce/boot source mismatch")
        for key in ("paper_session_id", "paper_pid", "paper_boot_id",
                    "presence_boot_id", "paper_tick", "paper_tick_ref",
                    "paper_log_sha256"):
            value = p[key]
            if key in shared and shared[key] != value:
                raise BD1bInitialSourceBindingHold("original A/B Paper source diverged")
            shared[key] = value
