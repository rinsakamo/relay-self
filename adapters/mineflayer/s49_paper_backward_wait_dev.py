"""S49 backward-Action / Paper WAIT candidate protocol, offline DEV only.

Unlike the older S50 *forward* recording this screen is scoped to S49's own
typed MOVE_BACKWARD S16 cleanup. The Paper text is CALLER INPUT, not a live
server feed. Paper's command arrival cannot prove when a native control ceased,
nor prove full-tick inactivity, absent other Action issuers or R custody.
Never issue a physical Action or a P1 SourceBoundTick(WAIT).
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path
from uuid import UUID

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_wait_owner_fence_dev import review_s49_owner_wait_fence
from adapters.mineflayer.s49_wait_typed_capture_dev import S49TypedClosureCaptureDev

SCHEMA = "S49_BACKWARD_PAPER_SAME_ACTION_DEV_V1"
BEGIN = "S49_DEV_BACK_WAIT_BEGIN"
TICK = "S49_DEV_BACK_WAIT_TICK"
KEYS = frozenset({"marker_id", "action_id", "session_id", "world", "tick", "index"})
RUN_KEYS = KEYS | {"run_id"}
INPUT_KEYS = RUN_KEYS | {"input_idle"}


def _sha(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _parse_paper(
    raw: str, *, action_id: str, session_id: str, marker_id: str, world: str,
) -> tuple[int, tuple[tuple[int, str], ...]]:
    """Check exactly one marked post-clear command and eight Paper callbacks.

    The BEGIN line is a Paper-observed marker after a *reported* native clear.
    It is not proof of the actual server-effective clear tick.
    """
    if not isinstance(raw, str) or not raw:
        raise BoundaryRejected("missing S49 Paper original")
    entries = []
    observer_run = None
    for raw_line in raw.splitlines(keepends=True):
        line = raw_line.rstrip("\r\n")
        if not line.startswith("S49_DEV_BACK_WAIT_"):
            continue
        tokens = line.split()
        if len(tokens) not in (7, 8, 9) or tokens[0] not in {BEGIN, TICK}:
            raise BoundaryRejected("unexpected Paper S49 row shape")
        values = {}
        for token in tokens[1:]:
            if token.count("=") != 1:
                raise BoundaryRejected("malformed Paper S49 field")
            key, value = token.split("=", 1)
            if not key or not value or key in values:
                raise BoundaryRejected("empty or duplicate S49 field")
            values[key] = value
        if set(values) not in (KEYS, RUN_KEYS, INPUT_KEYS):
            raise BoundaryRejected("missing/foreign S49 Paper source field")
        if "input_idle" in values and values["input_idle"] != "true":
            raise BoundaryRejected("Paper reports active Self input at callback")
        run_id = values.get("run_id")
        if run_id is not None:
            try:
                parsed = UUID(run_id)
            except (ValueError, AttributeError) as exc:
                raise BoundaryRejected("malformed Paper observer run ID") from exc
            if str(parsed) != run_id or parsed.version != 4:
                raise BoundaryRejected("noncanonical Paper observer run ID")
        if not entries:
            observer_run = run_id
        elif run_id != observer_run:
            raise BoundaryRejected("mixed or restarted Paper observer run")
        if (values.get("action_id") != action_id
                or values.get("session_id") != session_id
                or values.get("marker_id") != marker_id
                or values.get("world") != world):
            raise BoundaryRejected("foreign S49 Paper Action/session/world")
        try:
            tick = int(values["tick"])
            index = int(values["index"])
        except (KeyError, ValueError) as exc:
            raise BoundaryRejected("invalid S49 Paper tick/index") from exc
        if (tick < 1 or str(tick) != values["tick"]
                or index < 0 or str(index) != values["index"]):
            raise BoundaryRejected("invalid S49 Paper clock")
        entries.append((tokens[0], tick, index, _sha(raw_line)))
    if len(entries) != 9:
        raise BoundaryRejected("S49 Paper requires BEGIN + 8 ordered callbacks")
    start = entries[0]
    if start[0] != BEGIN or start[2] != 0:
        raise BoundaryRejected("S49 Paper BEGIN index/ordering invalid")
    begin_tick = start[1]
    projected = []
    for i, (kind, tick, index, digest) in enumerate(entries[1:], 1):
        if kind != TICK or index != i or tick != begin_tick + i:
            raise BoundaryRejected("S49 Paper callback gap/replay/reorder")
        projected.append((tick, "s49-paper-line-sha256:" + digest))
    return begin_tick, tuple(projected)


def _save_once(path: Path, record: dict) -> None:
    """Private, non-replacing derived DEV report; never source custody."""
    if (not isinstance(path, Path) or not path.is_absolute()
            or not path.parent.is_dir() or path.parent.is_symlink()
            or os.path.lexists(path)):
        raise BoundaryRejected("fresh absolute derived report path required")
    contents = (json.dumps(record, sort_keys=True, indent=2, allow_nan=False)
                + "\n").encode("utf-8")
    fd = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL
        | getattr(os, "O_NOFOLLOW", 0), 0o600,
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(contents)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


async def project_s49_backward_paper_dev(
    typed_capture: S49TypedClosureCaptureDev,
    paper_original: str, *,
    output_path: Path,
    observer_transcript: str | None = None,
    expected_player_uuid: str | None = None,
) -> dict:
    """One-shot offline correlation from the original typed owner closure.

    Paper inputs may be built by test fixtures. Success means only consistent
    source *shape*, never a qualified real Minecraft run.
    """
    if not isinstance(typed_capture, S49TypedClosureCaptureDev):
        raise BoundaryRejected("typed original S49 owner required")
    owner = typed_capture._executor
    if (typed_capture.state != "CAPTURED"
            or typed_capture.projection is None
            or owner.wait_phase != "NEW"
            or not isinstance(output_path, Path)
            or not output_path.is_absolute()
            or output_path.is_symlink() or os.path.lexists(output_path)):
        raise BoundaryRejected("unused typed S49 closure and fresh report required")
    evidence = typed_capture.projection
    marker = owner._wait_fence._marker
    world = owner._wait_fence._world
    session = evidence.session_id
    action = evidence.action_id
    report = {
        "schema": SCHEMA, "status": "FAIL_CLOSED",
        "session_id": session, "action_id": action, "marker_id": marker,
        "paper_world": world, "typed_s16_sha256": evidence.evidence_sha256,
        "paper_input_sha256": None, "owner_rows": [], "owner_review": None,
        "observer_transcript_review": None,
        "source_authentication": "UNATTESTED_CALLER_PAPER_INPUT",
        "server_effective_control_release": "NOT_ATTESTED",
        "whole_tick_self_inactivity": "NOT_ATTESTED",
        "all_action_issuers_idle": "NOT_ATTESTED",
        "qualification_go": False, "science_go": False,
        "source_bound_tick": None, "wait_interval_ref": None,
        "wait_ticks_admitted": 0, "p1_fatigue_recovered": 0.0,
    }
    try:
        if observer_transcript is not None or expected_player_uuid is not None:
            # This is a stricter optional source-shape join, NEVER R custody.
            if not isinstance(observer_transcript, str):
                raise BoundaryRejected("full Paper observer transcript missing")
            from adapters.mineflayer.s49_paper_transcript_dev import (
                review_s49_paper_transcript_dev,
            )
            audit = review_s49_paper_transcript_dev(
                typed_capture, observer_transcript,
                expected_player_uuid=expected_player_uuid,
            )
            if audit["normalized_paper_sha256"] != _sha(paper_original):
                raise BoundaryRejected("Paper full transcript and callback slice differ")
            report["observer_transcript_review"] = audit
        if marker != action + "-" + session:
            raise BoundaryRejected("S49 Paper marker not action/session bound")
        decoded = evidence.decoded_evidence
        if (decoded.get("action_id") != action
                or decoded.get("session_id") != session
                or decoded.get("action_ref") != "MOVE_BACKWARD"
                or decoded.get("status") != "executed"
                or decoded.get("dispatch_receipt", {}).get("effect") != "set_control"
                or decoded["dispatch_receipt"].get("result") != "applied"
                or decoded.get("cleanup_receipt", {}).get("effect") != "clear_controls"
                or decoded["cleanup_receipt"].get("result") != "applied"
                or decoded["cleanup_receipt"].get("action_id")
                != action + "-s15-clear"):
            raise BoundaryRejected("not the original backward S16 clear ACK")
        start, sources = _parse_paper(
            paper_original, action_id=action, session_id=session,
            marker_id=marker, world=world,
        )
        typed_capture.arm_owner_wait()
        report["paper_input_sha256"] = _sha(paper_original)

        async def samples():
            for tick, reference in sources:
                await asyncio.sleep(0)  # cancellable DEV task; not Paper time
                yield tick, reference

        rows = await owner.screen_wait_samples(
            samples(), seal_source_ref="s49-paper-stream-sha256:"
            + report["paper_input_sha256"],
        )
        if tuple(row["source_ref"] for row in rows[1:9]) != tuple(
            ref for _, ref in sources
        ):
            raise BoundaryRejected("Paper bytes not bound to owner emissions")
        result = review_s49_owner_wait_fence(
            rows, session_id=session, marker_id=marker, world=world,
            first_world_tick=start + 1, last_world_tick=start + 8,
        )
        if result["wait_interval_ref"] is not None or result["wait_ticks_admitted"]:
            raise BoundaryRejected("offline candidate cannot grant physical WAIT")
        report["owner_review"] = result
        report["status"] = "SAME_ACTION_PAPER_SHAPE_ONLY"
    except BaseException as exc:
        report["failure_type"] = type(exc).__name__
        report["status"] = (
            "CANCELLED_NOT_QUALIFIED" if isinstance(exc, asyncio.CancelledError)
            else "REJECTED_NOT_QUALIFIED"
        )
        if owner.wait_phase in {"ARMED", "SAMPLING", "ABORTED"}:
            owner.abort_wait(reason_source_ref="S49_PAPER_DEV_ABORT")
        report["owner_rows"] = list(owner.wait_original_rows)
        _save_once(output_path, report)
        raise
    report["owner_rows"] = list(owner.wait_original_rows)
    _save_once(output_path, report)
    return report
