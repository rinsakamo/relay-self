"""Read-only cross-file source check for an original Schema3 typed World/Self cut.

It verifies exact externally supplied SHA pins and cross-consistency of
original A/B prelogin cognition/WAL, typed generation and producer's saved
Native/Paper receipt *bytes*. This does NOT authenticate Paper, a real clock,
operator, Git custody or a model POST.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from relay_self.exploration_schema_record_dev import encode_recorded_schema
from relay_self.innate_schema import SchemaMode
from relay_self.persistent_cognition import load_persistent_cognition
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.self_owner_checkpoint_dev import verify_typed_generation


class BD1bSchema3ReadbackHold(RuntimeError):
    """Unqualified or contradictory Schema3 original source bytes."""


@dataclass(frozen=True, slots=True)
class OriginalSchema3SourceReadback:
    generation_id: str
    world_id: str
    source_branch_id: str
    original_native_sessions: tuple[tuple[str, str], ...]
    original_prelogin_cognition_sha256: tuple[tuple[str, str], ...]
    generation_committed_sha256: str
    producer_report_sha256: str
    prelogin_manifest_sha256: str
    classification: str = "BD1B_SCHEMA3_SOURCE_BYTES_CROSSCHECK_CPU_ONLY"
    original_paper_provenance_attested: bool = False
    original_native_provenance_attested: bool = False
    original_model_post_attested: bool = False
    physical_action_replay_authorized: bool = False


def _file(path: Path, *, limit: int = 1_000_000) -> bytes:
    if (path.is_symlink() or not path.is_file()
            or path.stat().st_nlink != 1
            or path.stat().st_size > limit):
        raise BD1bSchema3ReadbackHold("bounded non-symlink original source required")
    return path.read_bytes()


def _pinned(raw: bytes, claim: str) -> None:
    if (type(claim) is not str or re.fullmatch(r"[0-9a-f]{64}", claim) is None
            or hashlib.sha256(raw).hexdigest() != claim):
        raise BD1bSchema3ReadbackHold("external exact source digest missing or changed")


def _json(raw: bytes):
    try:
        return json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise BD1bSchema3ReadbackHold("original source JSON unreadable") from exc


def _pair(rows, *, key: str):
    if (type(rows) is not list or len(rows) != 2
            or any(type(row) is not list or len(row) != 2
                   or row[0] not in ("A", "B") or type(row[1]) is not str
                   for row in rows)
            or sorted(row[0] for row in rows) != ["A", "B"]):
        raise BD1bSchema3ReadbackHold("original A/B " + key + " is partial")
    return {sid: value for sid, value in rows}


def audit_schema3_original_source_bytes(
    *, evidence_dir: Path, generation: Path,
    expected_committed_sha256: str,
    expected_producer_report_sha256: str,
    expected_prelogin_manifest_sha256: str,
) -> OriginalSchema3SourceReadback:
    """Re-read raw originals independently; do not write or start any process."""
    evidence = Path(evidence_dir).absolute()
    generation = Path(generation).absolute()
    if (evidence.is_symlink() or not evidence.is_dir()
            or generation.is_symlink()
            or generation.parent != evidence / "typed-world-self-generations"
            or generation.parent.is_symlink()
            or not re.fullmatch(r"g-[0-9]{12}", generation.name)):
        raise BD1bSchema3ReadbackHold("foreign or noncanonical typed generation")
    _pinned(
        _file(generation / "COMMITTED.json"),
        expected_committed_sha256,
    )
    _pinned(
        _file(evidence / "resident-presence-result.json"),
        expected_producer_report_sha256,
    )
    _pinned(
        _file(evidence / "stage28b-schema3-prelogin.json"),
        expected_prelogin_manifest_sha256,
    )
    report = _json(_file(evidence / "resident-presence-result.json"))
    prelogin = _json(_file(evidence / "stage28b-schema3-prelogin.json"))
    cuts = verify_typed_generation(generation)
    if (tuple(c.self_id for c in cuts) != ("A", "B")
            or any(c.schema_snapshot is None or c.cognition_sha256 is None
                   or c.schema_snapshot.get("exploratory").mode is not SchemaMode.FULL
                   for c in cuts)):
        raise BD1bSchema3ReadbackHold("same-generation FULL original Schema3 source missing")
    by_id = {c.self_id: c for c in cuts}
    if (type(prelogin) is not dict
            or prelogin.get("classification") != "BD1B_ORIGINAL_PRELOGIN_SCHEMA3_UNAUDITED_DEV"
            or prelogin.get("self_ids") != ["A", "B"]
            or prelogin.get("schema_modes") != ["FULL", "FULL"]
            or prelogin.get("original_registered_before_native") is not True
            or prelogin.get("real_paper_independently_audited") is not False
            or prelogin.get("real_model_post_attempted") is not False
            or prelogin.get("registrations") != [
                encode_recorded_schema(
                    by_id[sid].schema_snapshot, self_id=sid,
                    registry=by_id[sid].pattern_registry,
                ) for sid in ("A", "B")
            ]):
        raise BD1bSchema3ReadbackHold("recorded prelogin Schema does not match original cut")
    cognition = _pair(prelogin.get("cognition_sha256"), key="cognition")
    wals = _pair(prelogin.get("wal_sha256"), key="WAL")
    for sid in ("A", "B"):
        owner = by_id[sid]
        raw = _file(evidence / f"stage28b-schema3-{sid}-prelogin-cognition.json")
        _pinned(raw, cognition[sid])
        pre = load_persistent_cognition(
            evidence / f"stage28b-schema3-{sid}-prelogin-cognition.json"
        )
        if (pre.identity.self_id != sid
                or pre.pattern_registry != owner.pattern_registry
                or pre.exploration_continuity is not None):
            raise BD1bSchema3ReadbackHold("prelogin original cognition/registry changed")
        wal = evidence / f"stage28b-schema3-{sid}-prelogin-wal.json"
        _pinned(_file(wal), wals[sid])
        PhysicalActionJournal.restore(wal, self_id=sid).require_clear()
        PhysicalActionJournal.restore(
            generation / "selves" / sid / "physical-wal.json", self_id=sid,
        ).require_clear()
    step = report.get("steps")
    if (type(report) is not dict or type(step) is not list or len(step) != 1
            or type(step[0]) is not dict):
        raise BD1bSchema3ReadbackHold("original producer's one trial missing")
    step = step[0]
    if (report.get("classification") != "REAL_PAPER_TWO_SELF_TYPED_STOPPED_WORLD_CUT_DEV"
            or report.get("schema3_original_typed_owner_qualified") is not True
            or report.get("schema3_original_independent_audit") is not False
            or report.get("schema3_prelogin_record") != str(
                evidence / "stage28b-schema3-prelogin.json"
            )
            or report.get("world_uuid") != cuts[0].world_id
            or report.get("typed_world_self_generation") != str(generation)
            or step.get("typed_world_self_generation") != str(generation)
            or report.get("typed_world_self_saved_tick") != step.get("typed_world_self_saved_tick")
            or type(report.get("typed_world_self_saved_tick")) is not int
            or report["typed_world_self_saved_tick"] < max(
                cut.last_observed_world_tick for cut in cuts
            )
            or any(report.get(name) is not False for name in (
                "real_b_physical_action", "real_b_physical_wal_outcome",
                "real_gpu", "autonomous_l1_skill_selection",
                "real_60_second_autosave_attested",
            ))
            or step.get("real_l1_l2_gpu_executed") is not False
            or step.get("b_actual_physical_action") is not False
            or step.get("b_physical_wal_outcome") is not False):
        raise BD1bSchema3ReadbackHold("producer report differs from original typed source")
    initial_raw = _file(evidence / "initial-native-paper-source.json")
    initial = _json(initial_raw)
    if (type(initial) is not list or len(initial) != 2
            or step.get("initial_native_paper_source") != initial
            or sorted(row.get("self_id") for row in initial if type(row) is dict) != ["A", "B"]
            or any(row.get("world_id") != cuts[0].world_id
                   or row.get("branch_id") != cuts[0].branch_id
                   or row.get("paper_session_id") != step.get("paper_session_id")
                   for row in initial)):
        raise BD1bSchema3ReadbackHold("original Native/Paper pair receipt mismatch")
    new_a = step.get("a_relogin_evidence")
    if (type(new_a) is not dict
            or type(new_a.get("native_session_id")) is not str
            or not new_a["native_session_id"]
            or step.get("a_original_native_session") == new_a["native_session_id"]
            or new_a["native_session_id"] != by_id["A"].former_native_session_id
            or step.get("b_original_native_session") != by_id["B"].former_native_session_id):
        raise BD1bSchema3ReadbackHold("retired original A/B Native session identity mismatch")
    expected = (
        ("a_first_logout_receipt_file", "A-first-logout-original.json",
         "A", step.get("a_original_native_session")),
        ("final_a_logout_receipt_file", "A-final-logout-original.json",
         "A", new_a["native_session_id"]),
        ("final_b_logout_receipt_file", "B-final-logout-original.json",
         "B", step.get("b_original_native_session")),
    )
    for field, name, sid, native in expected:
        receipt_ref = step.get(field)
        path = evidence / name
        raw = _file(path)
        if (type(receipt_ref) is not dict
                or receipt_ref.get("path") != str(path)
                or receipt_ref.get("sha256") != hashlib.sha256(raw).hexdigest()):
            raise BD1bSchema3ReadbackHold("producer original logout bytes not pinned")
        receipt = _json(raw)
        if (type(receipt) is not dict
                or receipt.get("self_id") != sid
                or receipt.get("native_session_id") != native
                or any(receipt.get(key) is not True for key in (
                    "physical_issuer_revoked", "no_physical_inflight",
                    "physical_wal_clear", "native_terminated",
                    "stale_gpu_fenced", "peer_transport_drained",
                ))):
            raise BD1bSchema3ReadbackHold("logout receipt contradicts original Self")
    return OriginalSchema3SourceReadback(
        generation.name, cuts[0].world_id, cuts[0].branch_id,
        tuple((c.self_id, c.former_native_session_id) for c in cuts),
        tuple((sid, cognition[sid]) for sid in ("A", "B")),
        expected_committed_sha256, expected_producer_report_sha256,
        expected_prelogin_manifest_sha256,
    )
