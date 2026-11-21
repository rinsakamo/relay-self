"""Stage27e read-only independent evidence from original Paper and original WAL.

This module never issues an Action, invokes an LLM, or classifies Goal success.
Paper player motion is independent position evidence, NOT an Action-ID causal proof.
"""
from __future__ import annotations

import hashlib
import math
import os
from pathlib import Path

from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.resident_paper_presence_join_dev import (
    parse_owned_paper_resident_trace,
)


class Stage27IndependentEvidenceError(ValueError):
    """Original preissue WAL or owned Paper byte source is not qualified."""


def capture_original_prepared_wal(
    journal: PhysicalActionJournal, evidence_dir: Path, *,
    action_id: str, self_id: str = "A",
) -> dict[str, object]:
    """Copy source WAL bytes after fsynced PREPARED, before ANY native LOOK.

    This is a separate, immutable raw-byte observation of the original journal,
    not a second journal writer and not proof of an arbitrary atomic World cut.
    Failure leaves the original PREPARED_UNRESOLVED state unchanged.
    """
    if not isinstance(journal, PhysicalActionJournal) or not journal.unresolved:
        raise Stage27IndependentEvidenceError("original PREPARED WAL required")
    source = journal.path
    evidence_dir = Path(evidence_dir)
    if (
        source.is_symlink() or not source.is_file()
        or evidence_dir.is_symlink() or not evidence_dir.is_dir()
        or journal._body["self_id"] != self_id
        or len(journal.records) != 1
        or journal.records[-1]["status"] != "PREPARED_UNRESOLVED"
        or journal.records[-1]["capability"] != "MOVE_PLACE"
        or journal.records[-1]["action_id"] != action_id
    ):
        raise Stage27IndependentEvidenceError("foreign or non-PLACE original WAL")
    before = source.read_bytes()
    same_source = PhysicalActionJournal.restore(source, self_id=self_id)
    if not same_source.unresolved or same_source.digest != journal.digest:
        raise Stage27IndependentEvidenceError("original WAL source changed")
    snapshot = evidence_dir / "stage27e-A-original-PREPARED.json"
    if snapshot.exists() or snapshot.is_symlink():
        raise Stage27IndependentEvidenceError("PREPARED snapshot already exists")
    with snapshot.open("xb") as out:
        out.write(before)
        out.flush()
        os.fsync(out.fileno())
    folder = os.open(evidence_dir, os.O_RDONLY)
    try:
        os.fsync(folder)
    finally:
        os.close(folder)
    if snapshot.read_bytes() != before or source.read_bytes() != before:
        raise Stage27IndependentEvidenceError("PREPARED raw-byte snapshot mismatch")
    snapshot_journal = PhysicalActionJournal.restore(snapshot, self_id=self_id)
    if (
        snapshot_journal.digest != journal.digest
        or snapshot_journal.records[-1]["action_id"] != action_id
        or not snapshot_journal.unresolved
    ):
        raise Stage27IndependentEvidenceError("PREPARED snapshot readback mismatch")
    return {
        "source_path": str(source),
        "snapshot_path": str(snapshot),
        "raw_sha256": hashlib.sha256(before).hexdigest(),
        "raw_bytes": len(before),
        "journal_digest": journal.digest,
        "action_id": action_id,
        "status": "PREPARED_UNRESOLVED",
        "captured_before_any_native_effect": True,
    }


def correlate_owned_paper_position(
    *, before: bytes, after: bytes, paper_session_id: str, world_uuid: str,
    native_start_xyz: tuple[float, float, float],
    native_settled_xyz: tuple[float, float, float],
    tolerance_m: float = 0.3,
) -> dict[str, object]:
    """Compare append-only owned Paper main-thread positions with native readback.

    Inputs MUST be obtained through the same OwnedPaperWorld.read_owned_log.
    Paper and native tick counters are intentionally NEVER equated. Missing
    Paper movement returns UNATTESTED rather than inventing a zero displacement.
    """
    if (
        type(before) is not bytes or type(after) is not bytes
        or not after.startswith(before)
        or type(tolerance_m) not in (float, int)
        or not math.isfinite(tolerance_m) or not 0 < tolerance_m <= 1
        or any(
            type(v) not in (int, float) or not math.isfinite(v)
            for point in (native_start_xyz, native_settled_xyz)
            for v in point
        )
        or any(len(point) != 3 for point in (native_start_xyz, native_settled_xyz))
    ):
        raise Stage27IndependentEvidenceError("original Paper window or XYZ invalid")
    ref = f"owned-paper:{paper_session_id}:sha256:"
    pre = parse_owned_paper_resident_trace(
        owned_paper_session_id=paper_session_id,
        expected_world_uuid=world_uuid, owned_paper_log=before,
        log_ref=ref + hashlib.sha256(before).hexdigest(),
    )
    post = parse_owned_paper_resident_trace(
        owned_paper_session_id=paper_session_id,
        expected_world_uuid=world_uuid, owned_paper_log=after,
        log_ref=ref + hashlib.sha256(after).hexdigest(),
    )
    if pre.boot_id != post.boot_id or post.events[:len(pre.events)] != pre.events:
        raise Stage27IndependentEvidenceError("Paper boot/events changed across window")
    identities: dict[str, str] = {}
    for event in pre.events:
        if event.event == "JOIN" and event.name in ("RelayA", "RelayB"):
            if event.name in identities:
                raise Stage27IndependentEvidenceError("duplicate original Paper JOIN")
            identities[event.name] = event.actor_uuid
    if set(identities) != {"RelayA", "RelayB"} or len(set(identities.values())) != 2:
        raise Stage27IndependentEvidenceError("two original Paper actors required")
    a_events = [e for e in pre.events if e.name == "RelayA"]
    if not a_events or a_events[-1].event == "QUIT":
        raise Stage27IndependentEvidenceError("original A not Paper-resident")
    new_events = post.events[len(pre.events):]
    if any(
        e.name == name and e.actor_uuid != identities[name]
        for e in new_events for name in ("RelayA", "RelayB")
    ) or any(e.event in {"JOIN", "QUIT"} for e in new_events if e.name == "RelayA"):
        raise Stage27IndependentEvidenceError("A actor/session changed during Action")
    new_a = [e for e in new_events if e.name == "RelayA"]
    start = a_events[-1]
    last = new_a[-1] if new_a else start
    paper_before_xyz = (start.x, start.y, start.z)
    paper_after_xyz = (last.x, last.y, last.z)
    movement = math.dist(paper_before_xyz, paper_after_xyz)
    native_start_gap = math.dist(paper_before_xyz, native_start_xyz)
    native_end_gap = math.dist(paper_after_xyz, native_settled_xyz)
    qualified = (
        any(e.event == "MOVE" for e in new_a)
        and movement >= 0.1
        and native_start_gap <= tolerance_m
        and native_end_gap <= tolerance_m
    )
    return {
        "status": (
            "PAPER_A_POSITION_CORRELATED_DEV" if qualified
            else "PAPER_A_POSITION_UNATTESTED_DEV"
        ),
        "paper_a_actor_uuid": identities["RelayA"],
        "paper_b_actor_uuid": identities["RelayB"],
        "paper_boot_id": pre.boot_id,
        "paper_pre_sha256": pre.lines_sha256,
        "paper_post_sha256": post.lines_sha256,
        "paper_pre_log_bytes": len(before),
        "paper_post_log_bytes": len(after),
        "paper_a_start_xyz": list(paper_before_xyz),
        "paper_a_after_xyz": list(paper_after_xyz),
        "paper_a_displacement_m": movement,
        "native_start_position_gap_m": native_start_gap,
        "native_settled_position_gap_m": native_end_gap,
        "paper_a_move_events_after_preissue": sum(e.event == "MOVE" for e in new_a),
        "paper_b_move_events_after_preissue": sum(
            e.event == "MOVE" for e in new_events if e.name == "RelayB"
        ),
        "paper_position_independently_correlated": qualified,
        "paper_action_causality_attested": False,
        "goal_or_skill_success_attested": False,
        "source_note": "Paper P0D_RESIDENT append-only MAIN_THREAD samples; no native Action ID",
    }
