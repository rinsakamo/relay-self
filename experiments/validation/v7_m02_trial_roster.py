"""V7 M0.2 prospective 20-slot ledger; metadata checks, NEVER source attestation.

This registry makes dropped/duplicate attempts and science-vs-DEV contamination
visible. It neither starts a World nor upgrades any original/qualification.
The frozen V7 manifest controls all arms, seeds and physical eligibility.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from experiments.validation import v7_m02_physics as v7

SCHEMA = "RELAYSELF_V7_M02_PRESCIENCE_ROSTER_V1"
STATUS = "V7_M02_PRE_SCIENCE_ROSTER_REVIEW_ONLY"
MODES = {"DEV", "QUALIFICATION"}
OUTCOMES = {"PASS_CLAIMED", "FAILED", "BLOCKED", "UNDETERMINED"}
HEXDIGEST = re.compile(r"[0-9a-f]{64}\Z")
RUN_ID = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{7,79}\Z")
ARM_CONFIG_DIGESTS = {
    "BASE_ON": "e9361faa7eac2e3c63bf2f6760765f7f8ae5a4b3631c6819f7ad8ac5c04a540e",
    "SHAM_ON": "e9361faa7eac2e3c63bf2f6760765f7f8ae5a4b3631c6819f7ad8ac5c04a540e",
    "BASAL_ZERO": "260e3b14e7f536ff7416dffc8ed713397e6f324af1074e80af296856a84cd2c0",
    "WALK_ZERO": "f7d7c5ec9c94d95bbaf13af07ac25c518c3fe71e74216df2bfd2600c15b4bb40",
    "BOTH_ZERO": "b8c5991f4e1c5b60e487747696b329e8d7d079c7d1090baccda99566410103cb",
}


def _check(ok: bool, reason: str) -> None:
    if not ok:
        raise v7.V7Rejected(reason)


def _manifest_digest() -> str:
    v7.load_manifest()
    return hashlib.sha256(v7.MANIFEST.read_bytes()).hexdigest()


def _slot_id(seed: int, arm: str) -> str:
    return f"{seed}-{arm}"


def new_roster() -> dict[str, Any]:
    """Create the complete *unexecuted* prospective science slot roster."""
    return {
        "schema": SCHEMA,
        "v7_manifest_sha256": _manifest_digest(),
        "science_execution_authorized": False,
        "historical_qualification_grant_reused": False,
        "science_trials_executed": 0,
        "slots": [
            {
                "slot_id": _slot_id(seed, arm),
                "seed": seed,
                "arm": arm,
                "config_sha256": ARM_CONFIG_DIGESTS[arm],
                "science_status": "NOT_RUN",
                "prescience_attempts": [],
            }
            for seed in v7.SEEDS for arm in v7.ARMS
        ],
    }


def read_roster(path: Path) -> dict[str, Any]:
    _check(path.is_file() and not path.is_symlink()
           and path.stat().st_size <= 128_000, "roster file invalid")
    return json.loads(path.read_text(encoding="utf-8"),
                      object_pairs_hook=v7.unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(
                          v7.V7Rejected("nonfinite roster value")))


def review_roster(data: Any) -> dict[str, Any]:
    """Fail closed on roster omissions/promotion; do NOT attest sources.

    PRE-SCIENCE attempts are additive metadata references only. All real
    science slots remain NOT_RUN until a *separate* admitted protocol with
    original S/R/V review and explicit science authorization exists.
    """
    expected = new_roster()
    _check(type(data) is dict and set(data) == set(expected),
           "roster top-level shape")
    for field in ("schema", "v7_manifest_sha256",
                  "science_execution_authorized",
                  "historical_qualification_grant_reused",
                  "science_trials_executed"):
        _check(type(data[field]) is type(expected[field])
               and data[field] == expected[field],
               "science promotion/manifest/grant integrity")
    slots = data["slots"]
    _check(type(slots) is list and len(slots) == len(expected["slots"]),
           "all twenty prospective slots required")
    seen_slots: set[str] = set()
    seen_attempts: set[str] = set()
    counts = {"DEV": 0, "QUALIFICATION": 0}
    for slot in slots:
        _check(type(slot) is dict and set(slot) ==
               {"slot_id", "seed", "arm", "config_sha256",
                "science_status", "prescience_attempts"},
               "slot shape")
        seed, arm = slot["seed"], slot["arm"]
        _check(type(seed) is int and seed in v7.SEEDS
               and type(arm) is str and arm in v7.ARMS,
               "foreign seed/arm")
        sid = _slot_id(seed, arm)
        _check(slot["slot_id"] == sid and sid not in seen_slots,
               "duplicate/mismatched prospective slot")
        seen_slots.add(sid)
        _check(slot["config_sha256"] == ARM_CONFIG_DIGESTS[arm],
               "non-pinned S five-arm configuration")
        _check(slot["science_status"] == "NOT_RUN",
               "science trial cannot be promoted from prescience")
        attempts = slot["prescience_attempts"]
        _check(type(attempts) is list and len(attempts) <= 100,
               "prescience attempts not retained/bounded")
        for attempt in attempts:
            _check(type(attempt) is dict and set(attempt) == {
                "attempt_id", "mode", "outcome", "original_bundle_sha256",
                "r_review", "science_trial", "grant_reused",
            }, "attempt shape")
            aid, mode = attempt["attempt_id"], attempt["mode"]
            _check(type(aid) is str and RUN_ID.fullmatch(aid) is not None
                   and aid not in seen_attempts, "duplicate/invalid attempt")
            seen_attempts.add(aid)
            _check(type(mode) is str and mode in MODES,
                   "SCIENCE attempt not admitted")
            _check(attempt["outcome"] in OUTCOMES
                   and type(attempt["outcome"]) is str,
                   "invalid outcome classification")
            digest = attempt["original_bundle_sha256"]
            _check(digest is None or (
                type(digest) is str and HEXDIGEST.fullmatch(digest) is not None
            ), "malformed original digest reference")
            _check(type(attempt["r_review"]) is str
                   and attempt["r_review"] in
                   {"NOT_RUN", "REVIEW_ONLY", "PASS_CLAIMED", "FAIL_CLAIMED"},
                   "unqualified R review label")
            _check(attempt["science_trial"] is False
                   and attempt["grant_reused"] is False,
                   "attempt falsely promoted or consumed grant reused")
            counts[mode] += 1
    _check(seen_slots == {x["slot_id"] for x in expected["slots"]},
           "missing prospective slot")
    return {
        "classification": STATUS,
        "prospective_science_slots": len(seen_slots),
        "prescience_attempts_preserved": counts,
        "actual_v7_science_trials": 0,
        "v7_science_go": False,
        "r_physical_authentication_by_this_review": False,
        "qualified_physics_effect_by_this_review": False,
        "production_go": False,
        "required_next": [
            "S_DISPOSABLE_DEV_PAIRED_FIVE_ARM_SOURCE",
            "R_INDEPENDENT_CHANGED_CONFIG_AND_WORLD_ORIGINAL_REVIEW",
            "V_NATIVE_TICK_PACKET_CHARGE_SOURCE_ATTESTATION",
            "SEPARATE_EXPLICIT_SCIENCE_EXECUTION_AUTHORIZATION",
        ],
    }


def main() -> None:
    print(json.dumps(review_roster(new_roster()), sort_keys=True))


if __name__ == "__main__":
    main()
