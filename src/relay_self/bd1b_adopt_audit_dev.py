"""Independent, read-only consistency audit of a CPU synthetic ADOPT bundle.

The bundle is UNSIGNED and does not attest an actual Gemini/Gemma/Paper issuer,
a trusted filesystem writer, crash durability, or a runtime decision. A separate
process verifies that the captured immutable files agree with each other.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


class AdoptionAuditHold(ValueError):
    """Reject missing, inconsistent, or modified original evidence."""


_FILES = (
    "cognition.before.json", "cognition.after.json",
    "physical.before.wal", "physical.after.wal",
)


def _unique(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise AdoptionAuditHold("duplicate JSON field")
        obj[key] = value
    return obj


def _json(raw: bytes):
    try:
        return json.loads(raw, object_pairs_hook=_unique)
    except (UnicodeError, ValueError) as exc:
        raise AdoptionAuditHold("malformed JSON evidence") from exc


def _canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _require(condition, reason):
    if not condition:
        raise AdoptionAuditHold(reason)


def audit_adopt_bundle(directory: str | Path) -> dict:
    """Verify a run's captured bytes, not live Self state or filesystem history."""
    base = Path(directory)
    _require(base.is_dir() and not base.is_symlink(), "bundle directory missing")
    manifest = base / "manifest.json"
    _require(manifest.is_file() and not manifest.is_symlink(), "manifest missing")
    evidence = _json(manifest.read_bytes())
    _require(type(evidence) is dict, "manifest must be a mapping")
    keys = {
        "version", "kind", "ticket", "request", "request_sha256",
        "source", "candidate_input", "candidate_set_sha256",
        "readback", "provider_decision", "job_binding", "job_state_before", "job_state_after",
        "inquiry_ref", "pending_before", "pending_after", "file_sha256",
    }
    _require(set(evidence) == keys, "manifest keys missing or unexpected")
    _require(
        evidence["version"] == 1 and evidence["kind"] == "CPU_SYNTHETIC",
        "unattested evidence kind",
    )
    hashes = evidence["file_sha256"]
    _require(
        type(hashes) is dict and set(hashes) == set(_FILES),
        "missing file hashes",
    )
    originals = {}
    for name in _FILES:
        path = base / name
        _require(path.is_file() and not path.is_symlink(), "evidence file missing")
        raw = path.read_bytes()
        _require(_sha(raw) == hashes[name], "evidence bytes changed: " + name)
        originals[name] = raw

    ticket, request = evidence["ticket"], evidence["request"]
    source, freeze = evidence["source"], evidence["candidate_input"]
    readback = evidence["readback"]
    _require(
        all(type(x) is dict for x in (ticket, request, source, freeze, readback)),
        "typed source/request/receipt required",
    )
    _require(
        ticket["mode"] == "bounded"
        and ticket["self_id"] == source["self_id"]
        and ticket["native_session_id"] == source["native_session_id"]
        and ticket["world_epoch"] == source["world_epoch"]
        and ticket["self_epoch"] == source["resident_epoch"]
        and ticket["request_id"] == request["request_id"],
        "original ticket/request/scope mismatch",
    )
    _require(
        request["think_allowed"] is False
        and request["focus"] == evidence["inquiry_ref"]
        and [(x["choice_id"], x["description"]) for x in request["choices"]]
        == [
            ("1", "ADOPT — adopt this inquiry as my own OPEN Question"),
            ("2", "HOLD — do not adopt now; leave it pending"),
            ("3", "DECLINE — do not adopt this inquiry"),
        ],
        "wrong bounded choice set",
    )
    _require(
        _sha(_canonical({
            "type": "BoundedChoiceRequest", "mode": "bounded",
            "request": request,
        })) == evidence["request_sha256"],
        "submitted request digest mismatch",
    )
    _require(
        freeze["self_id"] == ticket["self_id"]
        and freeze["self_scope"] == [
            ticket["self_epoch"], ticket["native_session_id"], ticket["world_epoch"]
        ]
        and freeze["world_uuid"] == source["world_id"]
        and freeze["fork"] == source["branch_id"]
        and freeze["paper_session"] == source["paper_session_id"]
        and freeze["paper_boot"] == source["paper_boot_id"]
        and freeze["probe_session"] == source["native_session_id"]
        and freeze["probe_seq"] == source["native_probe_seq"]
        and freeze["probe_request_id"] == source["native_probe_ref"]
        and freeze["probe_provenance"] == source["native_probe_source_ref"]
        and freeze["request_id"] == request["request_id"]
        and freeze["choices"] == [
            [x["choice_id"], x["description"]] for x in request["choices"]
        ]
        and freeze["context"] == [
            [x["key"], x["value_json"], x["provenance"]["reference"]]
            for x in request["context"]
        ]
        and freeze["presets"] == [],
        "candidate inputs do not match source or request",
    )
    _require(
        _sha(_canonical(freeze)) == evidence["candidate_set_sha256"],
        "candidate SHA256 mismatch",
    )
    _require(
        readback["ticket"] == ticket
        and readback["self_id"] == ticket["self_id"]
        and readback["work_ref"] == ticket["work_ref"]
        and readback["request_id"] == ticket["request_id"]
        and readback["owner_scope"] == freeze["self_scope"]
        and readback["source"] == source
        and readback["inquiry_ref"] == evidence["inquiry_ref"]
        and readback["candidate_set_sha256"] == evidence["candidate_set_sha256"]
        and readback["verified_submitted_request_sha256"] == evidence["request_sha256"]
        and readback["selection"] == "ADOPT"
        and readback["provider_status"] == "resolved"
        and readback["provider_choice_id"] == "1",
        "issuer readback does not match submission/source",
    )
    provider = evidence["provider_decision"]
    _require(
        type(provider) is dict
        and provider["status"] == readback["provider_status"]
        and provider["choice_id"] == readback["provider_choice_id"]
        and provider["reason"] == readback["provider_reason"]
        and provider["call_facts"] == readback["call_facts"],
        "original provider result disagrees with readback",
    )
    _require(
        evidence["job_state_before"] == "unused"
        and evidence["job_state_after"] == "committed",
        "single-use transition missing",
    )
    _require(
        evidence["job_binding"] == {
            "ticket": ticket, "work_ref": ticket["work_ref"],
            "request_sha256": evidence["request_sha256"],
            "candidate_set_sha256": evidence["candidate_set_sha256"],
            "owner_scope": freeze["self_scope"],
        },
        "consumption binding mismatch",
    )

    before = _json(originals["cognition.before.json"])
    after = _json(originals["cognition.after.json"])
    _require(
        before["identity"]["self_id"] == ticket["self_id"]
        and after["identity"] == before["identity"]
        and after["schema_version"] == 4,
        "original Self identity/schema mismatch",
    )
    registry = before.get("pattern_registry")
    if registry is not None:
        _require(
            freeze["registry_revision"] == registry["revision"],
            "candidate registry revision disagrees with original cognition",
        )
    prior = before.get("exploration_continuity")
    current = after.get("exploration_continuity")
    _require(type(current) is dict, "Question continuity missing")
    prior_rev = 0 if prior is None else prior["revision"]
    prior_questions = [] if prior is None else prior["questions"]
    prior_attempts = [] if prior is None else prior["attempts"]
    _require(
        current["self_id"] == ticket["self_id"]
        and current["revision"] == prior_rev + 1
        and current["questions"][:-1] == prior_questions
        and current["attempts"] == prior_attempts
        and len(current["questions"]) == len(prior_questions) + 1,
        "Question CAS/history mismatch",
    )
    q = current["questions"][-1]
    _require(
        q["question_ref"] == evidence["inquiry_ref"]
        and q["open"] is True
        and q["origin"]["source"] == "issuer-adopt",
        "adopted Question mismatch",
    )
    origin = _json(q["origin"]["reference"].encode("utf-8"))
    _require(
        origin == {
            "work_ref": ticket["work_ref"],
            "request_id": ticket["request_id"],
            "choice_id": "1",
        },
        "Question origin not bound to original job",
    )
    without = dict(after)
    without.pop("exploration_continuity")
    without["schema_version"] = before["schema_version"]
    earlier = dict(before)
    earlier.pop("exploration_continuity", None)
    # Opting into v4 writes the explicit nullable registry key. An older v2
    # original did not contain that key; only the None representation is an
    # allowed schema-encoding difference, never an installed registry.
    if "pattern_registry" not in earlier:
        _require(
            "pattern_registry" in without and without["pattern_registry"] is None,
            "unexpected Schema registry installation",
        )
        without.pop("pattern_registry")
    _require(without == earlier, "unrelated cognition fields changed")
    old_pending = evidence["pending_before"]
    new_pending = evidence["pending_after"]
    _require(
        type(old_pending) is list and type(new_pending) is list
        and len(old_pending) == len(set(old_pending))
        and len(new_pending) == len(set(new_pending))
        and new_pending == sorted(set(old_pending) | {evidence["inquiry_ref"]}),
        "pending Question publication mismatch",
    )
    _require(
        originals["physical.before.wal"] == originals["physical.after.wal"],
        "physical WAL changed during adoption",
    )
    return {
        "classification": "CPU_SYNTHETIC_ADOPT_BUNDLE_CONSISTENT",
        "self_id": ticket["self_id"],
        "inquiry_ref": evidence["inquiry_ref"],
        "request_sha256": evidence["request_sha256"],
        "candidate_set_sha256": evidence["candidate_set_sha256"],
    }


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: python -m relay_self.bd1b_adopt_audit_dev DIRECTORY", file=sys.stderr)
        return 2
    try:
        result = audit_adopt_bundle(args[0])
    except (AdoptionAuditHold, KeyError, TypeError, OSError, IndexError) as exc:
        print("HOLD: " + str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
