"""Q1i read-only Original SelfOwnerCut checkpoint envelope and lineage audit.

Reference: I lane src/relay_self/self_owner_checkpoint_dev.py and
preset_registry_checkpoint.py, observed 2026-11-22, HEAD
7597ed1f2897198402d99ae772643d4dc7e3f6d4.

An independently pinned typed checkpoint's bytes may be structurally
consistent with an original Owner cut without authenticating that producer,
the cut's time, world events, PatternRegistry semantics or reboot authority.
This is a deliberately strict bounded *subset*, never the product decoder.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from experiments.q_lane_evidence_audit_dev import QEvidenceHold, _raw_file


class QTypedOwnerCutHold(QEvidenceHold):
    """Original SelfOwnerCut bytes, scope, or history fail conservative admission."""


_OWNER_FIELDS = {
    "schema", "generation_id", "self_id", "world_id", "branch_id",
    "former_native_session_id", "last_observed_world_tick", "intent_events",
    "skills", "pattern_registry", "peer_deliveries", "pending_question_refs",
}
_PATTERN_FIELDS = {
    "pattern_id", "version", "schema_id", "kind", "predicate", "goal_id",
    "skill_id", "skill_version", "target_kind", "origin", "provenance",
}
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_GEN = re.compile(r"g-[0-9]{12}\Z")
_MAX_EVENTS = 128
_MAX_SKILLS = 64
_MAX_PEERS = 128
_MAX_QUESTIONS = 128


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in items:
        if key in obj:
            raise QTypedOwnerCutHold("duplicate JSON key in owner checkpoint")
        obj[key] = value
    return obj


def _constant(value: str) -> None:
    raise QTypedOwnerCutHold(f"nonfinite JSON constant {value} refused")


def _canon(value: Any) -> bytes:
    return (
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            allow_nan=False,
        ) + "\n"
    ).encode("utf-8")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _exact(row: object, keys: set[str], name: str) -> dict[str, Any]:
    if type(row) is not dict or set(row) != keys:
        raise QTypedOwnerCutHold(f"{name} exact fields unavailable")
    return row


def _text(value: object) -> bool:
    return type(value) is str and bool(value.strip())


def _natural(value: object) -> bool:
    return type(value) is int and value >= 0


def _array(value: object, *, limit: int, name: str) -> list:
    if type(value) is not list or len(value) > limit:
        raise QTypedOwnerCutHold(f"{name} bounded list unavailable")
    return value


def _provenance(item: object) -> None:
    row = _exact(item, {"source", "reference"}, "original provenance")
    if any(not _text(row[k]) for k in row):
        raise QTypedOwnerCutHold("empty original provenance")


def _patterns(raw: object, *, schema: int, expected_self_id: str) -> dict:
    if schema == 1:
        row = _exact(raw, {"revision", "patterns"}, "v1 registry")
        patterns = _array(row["patterns"], limit=64, name="registry patterns")
        if not _natural(row["revision"]):
            raise QTypedOwnerCutHold("invalid schema revision")
        accepted = []
    else:
        row = _exact(raw, {
            "schema", "self_id", "revision", "patterns", "accepted_presets",
            "registry_ref",
        }, "v2 pattern registry")
        if (
            type(row["schema"]) is not int or row["schema"] != 2
            or row["self_id"] != expected_self_id or not _natural(row["revision"])
        ):
            raise QTypedOwnerCutHold("foreign or invalid accepted-pattern registry")
        original = {k: v for k, v in row.items() if k != "registry_ref"}
        registry_sha = _sha(json.dumps(
            original, sort_keys=True, separators=(",", ":"),
            allow_nan=False,
        ).encode())
        if row["registry_ref"] != "schema-registry:v2@" + registry_sha:
            raise QTypedOwnerCutHold("registry reference SHA changed")
        patterns = _array(row["patterns"], limit=64, name="registry patterns")
        accepted = _array(row["accepted_presets"], limit=64, name="accepted Presets")
        # Preset internals are not rehydrated: the actual product decoder
        # must validate SkillParameterPreset, event receipt and permissions.
        for entry in accepted:
            _exact(entry, {"pattern_version", "preset", "receipt"}, "accepted Preset")
            receipt = _exact(entry["receipt"], {
                "self_id", "event_id", "preset_ref", "provenance",
            }, "acceptance receipt")
            if (
                receipt["self_id"] != expected_self_id
                or not _text(receipt["event_id"])
                or not _text(receipt["preset_ref"])
            ):
                raise QTypedOwnerCutHold("accepted Preset from foreign/empty Self")
            _provenance(receipt["provenance"])
    seen: set[str] = set()
    for item in patterns:
        pattern = _exact(item, _PATTERN_FIELDS, "registry pattern")
        if (
            not _text(pattern["pattern_id"]) or pattern["pattern_id"] in seen
            or not _natural(pattern["version"]) or pattern["version"] == 0
            or not _text(pattern["schema_id"])
            or not _text(pattern["kind"]) or not _text(pattern["predicate"])
            or not _text(pattern["origin"])
        ):
            raise QTypedOwnerCutHold("duplicate or malformed Schema Pattern")
        seen.add(pattern["pattern_id"])
        _provenance(pattern["provenance"])
    return {
        "schema": schema, "revision": row["revision"],
        "pattern_count": len(patterns), "accepted_preset_count": len(accepted),
        "pattern_semantics_attested": False,
        "preset_semantics_attested": False,
    }


def _intents(raw: object) -> dict[str, dict[str, object]]:
    events = _array(raw, limit=_MAX_EVENTS, name="Intent events")
    committed: dict[str, dict[str, object]] = {}
    active: str | None = None
    pending = False
    previous_ns = -1
    for item in events:
        e = _exact(item, {
            "kind", "intent_id", "objective", "reason", "at_ns", "provenance",
        }, "Intent event")
        if not _text(e["intent_id"]) or not _natural(e["at_ns"]):
            raise QTypedOwnerCutHold("invalid Intent event ID/time")
        if e["at_ns"] < previous_ns:
            raise QTypedOwnerCutHold("Intent event time moved backwards")
        previous_ns = e["at_ns"]
        _provenance(e["provenance"])
        kind, ident = e["kind"], e["intent_id"]
        if kind == "committed":
            if (
                active is not None or ident in committed or not _text(e["objective"])
                or e["reason"] is not None
            ):
                raise QTypedOwnerCutHold("duplicate, foreign or active Intent commit")
            committed[ident] = {"at_ns": e["at_ns"], "final_kind": "active"}
            active, pending = ident, False
            continue
        if (
            active != ident or e["objective"] is not None or not _text(e["reason"])
        ):
            raise QTypedOwnerCutHold("unbound or malformed Intent state transition")
        if kind == "reconsideration_requested":
            if pending:
                raise QTypedOwnerCutHold("duplicate pending reconsideration")
            pending = True
        elif kind in ("reconsidered_continue", "reconsidered_release"):
            if not pending:
                raise QTypedOwnerCutHold("reconsideration without a request")
            pending = False
            if kind == "reconsidered_release":
                committed[ident]["final_kind"] = kind
                active = None
        elif kind in ("completed", "failed", "invalidated"):
            # An actual Owner may complete/fail an Intent after any
            # previous reconsideration request; the product owner replays
            # these transitions. Never claim complete semantic equivalence.
            committed[ident]["final_kind"] = kind
            active, pending = None, False
        else:
            raise QTypedOwnerCutHold("unknown Intent event kind")
    return committed


def _skills(raw: object, intents: dict[str, dict[str, object]]) -> dict[str, dict]:
    rows = _array(raw, limit=_MAX_SKILLS, name="Skill executions")
    seen: dict[str, dict] = {}
    for raw_skill in rows:
        item = _exact(raw_skill, {
            "execution_id", "skill_id", "intent_id", "events",
        }, "Skill execution")
        if (
            not all(_text(item[k]) for k in ("execution_id", "skill_id", "intent_id"))
            or item["execution_id"] in seen or item["intent_id"] not in intents
        ):
            raise QTypedOwnerCutHold("unbound or duplicate Skill execution")
        actions = _array(item["events"], limit=2, name="Skill state transitions")
        if not actions:
            raise QTypedOwnerCutHold("Skill requires started state")
        previous_ns = -1
        states: list[str] = []
        for event in actions:
            e = _exact(event, {
                "state", "at_ns", "reason", "provenance",
            }, "Skill state")
            if not _natural(e["at_ns"]) or e["at_ns"] < previous_ns:
                raise QTypedOwnerCutHold("Skill state chronology invalid")
            previous_ns = e["at_ns"]
            _provenance(e["provenance"])
            if e["state"] == "started":
                if states or e["reason"] is not None:
                    raise QTypedOwnerCutHold("Skill cannot start twice")
            elif e["state"] in ("failed", "succeeded", "cancelled"):
                if states != ["started"] or not _text(e["reason"]):
                    raise QTypedOwnerCutHold("unqualified terminal Skill state")
            else:
                raise QTypedOwnerCutHold("unrecognized Skill transition")
            states.append(e["state"])
        if actions[0]["at_ns"] < intents[item["intent_id"]]["at_ns"]:
            raise QTypedOwnerCutHold("Skill started before committed Intent")
        seen[item["execution_id"]] = {
            "skill_id": item["skill_id"], "intent_id": item["intent_id"],
            "last_state": states[-1], "start_ns": actions[0]["at_ns"],
        }
    return seen


def _peers_and_questions(payload: dict) -> tuple[int, int]:
    peers = _array(payload["peer_deliveries"], limit=_MAX_PEERS, name="peer receipts")
    msgs: set[str] = set()
    for entry in peers:
        item = _exact(entry, {
            "message_id", "sender_self_id", "recipient_self_id",
            "sent_world_tick", "received_world_tick", "payload_ref",
        }, "peer receipt")
        if (
            not all(_text(item[k]) for k in (
                "message_id", "sender_self_id", "recipient_self_id", "payload_ref",
            ))
            or item["message_id"] in msgs
            or item["sender_self_id"] == item["recipient_self_id"]
            or payload["self_id"] not in (
                item["sender_self_id"], item["recipient_self_id"],
            )
            or not _natural(item["sent_world_tick"])
            or not _natural(item["received_world_tick"])
            or item["sent_world_tick"] > item["received_world_tick"]
            or item["received_world_tick"] > payload["last_observed_world_tick"]
        ):
            raise QTypedOwnerCutHold("duplicate, foreign or future peer receipt")
        msgs.add(item["message_id"])
    questions = _array(
        payload["pending_question_refs"], limit=_MAX_QUESTIONS,
        name="pending Questions",
    )
    if any(not _text(q) for q in questions) or len(questions) != len(set(questions)):
        raise QTypedOwnerCutHold("duplicate/unbound pending Question")
    return len(peers), len(questions)


def audit_q1i_typed_owner_cut(
    evidence_dir: Path, *, checkpoint_file: str,
    expected_checkpoint_sha256: str,
    expected_generation_id: str, expected_self_id: str,
    expected_world_id: str, expected_branch_id: str,
    expected_former_native_session_id: str,
) -> dict[str, Any]:
    """Bounded independently pinned actual SelfOwnerCut *shape* and history.

    Does NOT grant full typed restore, PatternRegistry acceptance, peer
    transport, original memory ownership, native session or physical rights.
    """
    if (
        not isinstance(evidence_dir, Path)
        or not evidence_dir.is_dir() or evidence_dir.is_symlink()
        or type(expected_checkpoint_sha256) is not str
        or _HEX64.fullmatch(expected_checkpoint_sha256) is None
        or type(expected_generation_id) is not str
        or _GEN.fullmatch(expected_generation_id) is None
        or any(not _text(v) for v in (
            expected_self_id, expected_world_id, expected_branch_id,
            expected_former_native_session_id,
        ))
    ):
        raise QTypedOwnerCutHold("typed owner checkpoint scope or external pin incomplete")
    try:
        raw = _raw_file(evidence_dir, checkpoint_file)
        if _sha(raw) != expected_checkpoint_sha256:
            raise QTypedOwnerCutHold("typed owner cut bytes differ from external SHA")
        envelope = json.loads(
            raw, object_pairs_hook=_pairs, parse_constant=_constant,
        )
        e = _exact(envelope, {"payload", "sha256"}, "Owner cut envelope")
        payload = e["payload"]
        keys = set(_OWNER_FIELDS)
        if type(payload) is dict and payload.get("schema") == 2 and (
            "cognition_sha256" in payload
        ):
            keys.add("cognition_sha256")
        p = _exact(payload, keys, "Owner cut payload")
        if (
            type(p["schema"]) is not int or p["schema"] not in (1, 2)
            or not _natural(p["last_observed_world_tick"])
            or any(p[k] != expected for k, expected in (
                ("generation_id", expected_generation_id),
                ("self_id", expected_self_id),
                ("world_id", expected_world_id),
                ("branch_id", expected_branch_id),
                ("former_native_session_id", expected_former_native_session_id),
            ))
        ):
            raise QTypedOwnerCutHold("typed Owner scope/generation mismatch")
        digest = _sha(_canon(p))
        if type(e["sha256"]) is not str or e["sha256"] != digest:
            raise QTypedOwnerCutHold("Owner payload canonical SHA mismatch")
        if _canon(e) != raw:
            raise QTypedOwnerCutHold("noncanonical Owner checkpoint bytes")
        if "cognition_sha256" in p and (
            type(p["cognition_sha256"]) is not str
            or _HEX64.fullmatch(p["cognition_sha256"]) is None
        ):
            raise QTypedOwnerCutHold("unqualified Owner cognition source SHA")
        registry = _patterns(
            p["pattern_registry"], schema=p["schema"],
            expected_self_id=expected_self_id,
        )
        if (
            p["schema"] == 2 and registry["accepted_preset_count"] == 0
            and "cognition_sha256" not in p
        ):
            raise QTypedOwnerCutHold("v2 owner cut needs accepted Preset or cognition SHA")
        committed = _intents(p["intent_events"])
        skills = _skills(p["skills"], committed)
        peers, questions = _peers_and_questions(p)
    except (QEvidenceHold, OSError, UnicodeError, TypeError, ValueError, KeyError) as exc:
        if isinstance(exc, QTypedOwnerCutHold):
            raise
        raise QTypedOwnerCutHold("untrusted original typed owner checkpoint") from exc
    return {
        "classification": "Q1I_TYPED_OWNER_CUT_SHAPE_AND_LINEAGE_CPU_OFFLINE_DEV",
        "raw_checkpoint_sha256": _sha(raw),
        "payload_canonical_sha256": digest,
        "generation_id": expected_generation_id,
        "self_id": expected_self_id,
        "world_id": expected_world_id,
        "branch_id": expected_branch_id,
        "former_native_session_id": expected_former_native_session_id,
        "last_observed_world_tick": p["last_observed_world_tick"],
        "owner_schema": p["schema"],
        "intent_count": len(committed), "skill_count": len(skills),
        "peer_receipt_count": peers, "pending_question_count": questions,
        "skills": skills, "intents": committed,
        "registry": registry,
        "independent_original_producer_attested": False,
        "independent_actual_checkpoint_capture_time_attested": False,
        "full_product_semantic_decode_attested": False,
        "pattern_registry_semantics_attested": False,
        "original_native_paper_source_attested": False,
        "original_stage28_full_generation_verified": False,
        "real_world_attested": False,
        "qual_go": False,
        "science_run": False,
    }
