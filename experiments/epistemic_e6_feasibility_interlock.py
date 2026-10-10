"""AC Lane A E6: offline physical-feasibility interlock; NEVER launches a World.

Historical S31-B and S43 are distinct physical qualifications but are not
causal, geometrical, policy or experimentation proof for frozen E5. Even a
plausible caller-created 10/10 self-report is UNATTESTED and exits nonzero.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from experiments import epistemic_e5_prospective_gate as e5

VERSION = "AC-A-E6-NATIVE-FEASIBILITY-INTERLOCK-v1"
MANIFEST_SHA256 = "bf78c4f647a3a7b138b1b6189312be4395a82ed49711aff6b3fc1d35ec1bd2cf"
MANIFEST = {
    "version": VERSION,
    "base_e5": "640d9df6fdc0310ab6189a05084bd13993864a75",
    "source_e5": "2ede0bd82ab6c8ada2557a5477f9c6d6084e6cbae50a5e1a6b8ffc6d1626e2f3",
    "historical_qualifications": [
        {
            "owner": "S31B", "pr": 402,
            "head": "f7e3973c19752f208d2a21c61b765f02c2444f37",
            "status": "separate_native_request_id_2m_proof_not_e5",
        },
        {
            "owner": "S43", "pr": 380,
            "head": "ddfa0ccc2290b6a7e9b29f8fbcf3542d78649d5e",
            "status": "different_threshold_4m_and_near2m_far10m",
        },
    ],
    "historical_s31a_gamemode": "creative",
    "historical_s42_threshold_m": 4,
    "e5_s24_threshold_m": 1,
    "e5_distances_m": [0.2, 1.8],
    "missing_live_capabilities": [
        "e5_exact_near_0p2m_sensor_geometry",
        "e5_same_source_far_1p8_then_near_0p2_two_correlated_reads",
        "e5_real_action3_terminal_source_parent",
        "e5_distinct_action4_s15_s16_actual_outcome",
        "e5_damage_capable_controlled_world_not_creative",
        "e5_no_observe_arm_strict_probe_quarantine",
        "e5_post_decision_evaluator_native_health_movement",
        "e5_36_independent_reset_seed_and_equal_horizon",
        "e5_actual_cost_latency_health_damage_witnesses",
        "e5_explicit_unconsumed_physical_authorization",
    ],
    "preflight_mode": "read_only_static_or_claimed_fixture_never_launch",
    "candidate_claim": "E6_OFFLINE_FEASIBILITY_INTERLOCK_CI_PASS_ONLY",
    "physical_claim": "BLOCKED_WITHOUT_NEW_LIVE_WITNESSES_AND_AUTHORITY",
    "files": [
        "experiments/epistemic_e6_feasibility_interlock.py",
        "tests/test_epistemic_e6_feasibility_interlock.py",
        ".github/workflows/epistemic-e6-interlock.yml",
    ],
}

REQUIRED = tuple(MANIFEST["missing_live_capabilities"])
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_IDENT = re.compile(r"[A-Za-z0-9._:-]{1,128}\Z")
_FIELDS = {"capability", "state", "source_commit", "world_session",
           "witness_sha256", "details"}
_BUNDLE_FIELDS = {"manifest_sha256", "e5_manifest_sha256",
                  "source_kind", "claims"}
_HISTORICAL_SHA = frozenset(
    v["head"] for v in MANIFEST["historical_qualifications"]
)


class E6Rejected(ValueError):
    """Malformed self-report or impossible source/authority handoff."""


@dataclass(frozen=True, slots=True)
class E6Readiness:
    classification: str
    physical_effect: str
    physically_authenticated: bool
    execution_authorized: bool
    world_launched: bool
    e5_trial_count: int
    e5_block_count: int
    claimed_capabilities: int
    missing_capabilities: tuple[str, ...]
    historical_sources_reused_as_proof: bool


def digest(obj: object = MANIFEST) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _frozen() -> None:
    if digest() != MANIFEST_SHA256:
        raise E6Rejected("prospective E6 manifest drift")
    if e5.digest() != MANIFEST["source_e5"]:
        raise E6Rejected("frozen E5 authority drift")
    specs = e5.planned_trials()
    if (
        len(specs) != 36
        or len({t.block_id for t in specs}) != 12
        or e5.MANIFEST["distances_cm"] != [20, 180]
        or e5.MANIFEST["price_quarters"] != [1, 4]
        or MANIFEST["historical_s31a_gamemode"] != "creative"
        or MANIFEST["historical_s42_threshold_m"] == MANIFEST["e5_s24_threshold_m"]
    ):
        raise E6Rejected("historical test cannot be substituted for E5 controller")


def _exact_dict(item: object, fields: set[str], label: str) -> dict[str, Any]:
    if type(item) is not dict or set(item) != fields:
        raise E6Rejected(f"{label}: exact schema expected")
    return item


def _source_id(value: object, label: str) -> str:
    if type(value) is not str or not _IDENT.fullmatch(value):
        raise E6Rejected(f"{label}: invalid identifier")
    return value


def _sha(value: object, label: str) -> None:
    if type(value) is not str or not _SHA256.fullmatch(value):
        raise E6Rejected(f"{label}: invalid SHA256 string, not attestation")


def _n(value: object, label: str, *, min_value: int = 0) -> int:
    if type(value) is not int or value < min_value:
        raise E6Rejected(f"{label}: invalid non-negative integer")
    return value


def _b(value: object, label: str) -> None:
    if type(value) is not bool or not value:
        raise E6Rejected(f"{label}: must be explicitly true in claimed witness")


# Exact content shape is checked for each *claimed* capability. These are
# structurally consistent assertions only and are NEVER live authentication.
DETAIL_KEYS = (
    {"distance_cm", "entity_name", "coverage_complete", "source_policy"},
    {"first_distance_cm", "second_distance_cm", "first_request_id",
     "second_request_id", "first_seq", "second_seq", "same_session"},
    {"action3_id", "action3_state", "world3_status"},
    {"action3_id", "action4_id", "action4_state", "world4_status",
     "independently_authorized"},
    {"game_mode", "mob_ai_enabled", "damage_recorded"},
    {"policy_probe_count", "evaluator_probe_count", "evaluator_after_decision"},
    {"health_measured", "movement_measured", "damage_measured",
     "evaluator_after_decision"},
    {"trial_count", "distinct_sessions", "distinct_reset_ids",
     "matched_blocks", "same_initial_health", "equal_followup_horizon"},
    {"actual_elapsed_ms", "actual_probe_ms", "actual_damage_points",
     "actual_movement_m"},
    {"new_permission_ref", "user_owned", "independent_of_415",
     "explicit_for_e5"},
)


def _validate_details(index: int, item: object) -> None:
    d = _exact_dict(item, DETAIL_KEYS[index], REQUIRED[index])
    if index == 0:
        _n(d["distance_cm"], "0.2m source geometry")
        if (d["distance_cm"], d["entity_name"], d["source_policy"]) != (
            20, "zombie", "S24_THRESHOLD_100CM"
        ):
            raise E6Rejected("historical 2m/S42 4m is not E5 near0.2m")
        _b(d["coverage_complete"], "complete native entity coverage")
    elif index == 1:
        if (
            _n(d["first_distance_cm"], "far") != 180
            or _n(d["second_distance_cm"], "near") != 20
        ):
            raise E6Rejected("E5 first 1.8m and second 0.2m must be actual")
        _source_id(d["first_request_id"], "S29 first request")
        _source_id(d["second_request_id"], "S29 second request")
        if d["first_request_id"] == d["second_request_id"]:
            raise E6Rejected("replayed S29 request ID")
        a = _n(d["first_seq"], "first seq", min_value=1)
        b = _n(d["second_seq"], "second seq", min_value=1)
        if a >= b:
            raise E6Rejected("same source must have later correlated seq")
        _b(d["same_session"], "same S29 session")
    elif index == 2:
        _source_id(d["action3_id"], "original Action3")
        if (d["action3_state"], d["world3_status"]) != ("OUTCOME", "EXECUTED"):
            raise E6Rejected("no exact terminal source Action3/World parent")
    elif index == 3:
        _source_id(d["action3_id"], "original Action3")
        _source_id(d["action4_id"], "next Action4")
        if (
            d["action4_id"] == d["action3_id"]
            or (d["action4_state"], d["world4_status"]) != ("OUTCOME", "EXECUTED")
        ):
            raise E6Rejected("S15/S16 distinct terminal Action4 not established")
        _b(d["independently_authorized"], "Action4 independent authorization")
    elif index == 4:
        if d["game_mode"] != "survival":
            raise E6Rejected("creative mode cannot test survival damage value")
        _b(d["mob_ai_enabled"], "mob AI must be active for damage relevance")
        _b(d["damage_recorded"], "damage must be actually measured")
    elif index == 5:
        if _n(d["policy_probe_count"], "NO_OBSERVE source probe count") != 0:
            raise E6Rejected("NO_OBSERVE leaked a pre-decision observation")
        if _n(d["evaluator_probe_count"], "independent evaluator count") != 1:
            raise E6Rejected("post-decision evaluator unavailable")
        _b(d["evaluator_after_decision"], "post-decision quarantine")
    elif index == 6:
        for name in d:
            _b(d[name], name)
    elif index == 7:
        for k, expected in (
            ("trial_count", 36), ("distinct_sessions", 36),
            ("distinct_reset_ids", 36), ("matched_blocks", 12),
        ):
            if _n(d[k], k) != expected:
                raise E6Rejected("36 independently reset trial denominator not met")
        _b(d["same_initial_health"], "same baseline")
        _b(d["equal_followup_horizon"], "matched observation horizon")
    elif index == 8:
        for k, v in d.items():
            if type(v) not in (int, float) or not (0 <= v < 1e12):
                raise E6Rejected(f"{k}: actual bounded finite measurement required")
        if d["actual_elapsed_ms"] <= 0 or d["actual_probe_ms"] <= 0:
            raise E6Rejected("real elapsed/probe cost must be nonzero")
    elif index == 9:
        _source_id(d["new_permission_ref"], "new explicit user permission")
        _b(d["user_owned"], "user-owned permission")
        _b(d["independent_of_415"], "no #415 reuse")
        _b(d["explicit_for_e5"], "E5-specific authorization")


def plan() -> dict[str, object]:
    _frozen()
    planned = e5.planned_trials()
    return {
        "version": VERSION,
        "manifest_sha256": MANIFEST_SHA256,
        "frozen_e5_manifest_sha256": e5.MANIFEST_SHA256,
        "classification": "E6_PHYSICAL_START_BLOCKED",
        "world_launched": False,
        "physical_effect": "UNDETERMINED",
        "historical_sources": MANIFEST["historical_qualifications"],
        "historical_gamemode": MANIFEST["historical_s31a_gamemode"],
        "incompatible_thresholds_m": {
            "S42": MANIFEST["historical_s42_threshold_m"],
            "E5_S24": MANIFEST["e5_s24_threshold_m"],
        },
        "trial_ids": [v.trial_id for v in planned],
        "blocked_capabilities": list(REQUIRED),
        "next": "distinct prospective real-World authorization and witnessed "
                "calibration; no automatic launcher or capability grant",
    }


def check_claims(payload: object) -> E6Readiness:
    """Read-only exact-schema calibration report; no path can authorize World."""
    _frozen()
    b = _exact_dict(payload, _BUNDLE_FIELDS, "calibration claims")
    if (
        b["manifest_sha256"] != MANIFEST_SHA256
        or b["e5_manifest_sha256"] != e5.MANIFEST_SHA256
        or b["source_kind"] != "SELF_REPORTED"
    ):
        raise E6Rejected("E5/E6 source identity or self-reported kind mismatch")
    claims = b["claims"]
    if type(claims) is not list or len(claims) != len(REQUIRED):
        raise E6Rejected("all ten pre-registered capability slots are mandatory")
    missing: list[str] = []
    world_sessions: dict[int, str] = {}
    action3_ids: dict[int, str] = {}
    witness_hashes: set[str] = set()
    ids: list[str] = []
    for i, raw in enumerate(claims):
        c = _exact_dict(raw, _FIELDS, f"claim[{i}]")
        name = c["capability"]
        if name != REQUIRED[i]:
            raise E6Rejected("wrong order, duplicated or missing capability")
        if c["state"] not in ("MISSING", "DENIED", "CLAIMED"):
            raise E6Rejected("capability must not imply external PASS")
        if c["state"] == "CLAIMED":
            if c["source_commit"] is None or c["world_session"] is None:
                raise E6Rejected("claimed source must contain exact identity")
            if type(c["source_commit"]) is not str or not re.fullmatch(
                r"[0-9a-f]{40}", c["source_commit"]
            ):
                raise E6Rejected("source SHA must be an exact commit form")
            if c["source_commit"] in _HISTORICAL_SHA:
                raise E6Rejected("old S31-B/S43 evidence cannot qualify E5")
            session = _source_id(c["world_session"], "native session")
            _sha(c["witness_sha256"], "source witness")
            if c["witness_sha256"] in witness_hashes:
                raise E6Rejected("replayed witness hash across independent checks")
            witness_hashes.add(c["witness_sha256"])
            _validate_details(i, c["details"])
            if i in (0, 1, 2, 3):
                world_sessions[i] = session
            if i in (2, 3):
                action3_ids[i] = c["details"]["action3_id"]
            ids.append(name)
        else:
            if (
                c["source_commit"] is not None
                or c["world_session"] is not None
                or c["witness_sha256"] is not None
                or c["details"] is not None
            ):
                raise E6Rejected("missing/denied capability cannot smuggle evidence")
            missing.append(name)
    # E5's exact S29 parent is one original Action3 terminal/World
    # source, while S15's next Action4 is a separate execution session.
    if set(world_sessions) == {0, 1, 2, 3}:
        if (
            len({world_sessions[i] for i in (0, 1, 2)}) != 1
            or world_sessions[3] == world_sessions[0]
            or action3_ids[2] != action3_ids[3]
        ):
            raise E6Rejected("S29 two-probe/Action3 parent and separate Action4 source mismatch")
    return E6Readiness(
        classification=(
            "CLAIMED_CAPABILITIES_UNATTESTED" if not missing
            else "E6_PHYSICAL_START_BLOCKED"
        ),
        physical_effect="UNDETERMINED", physically_authenticated=False,
        execution_authorized=False, world_launched=False,
        e5_trial_count=36, e5_block_count=12,
        claimed_capabilities=len(ids),
        missing_capabilities=tuple(missing),
        historical_sources_reused_as_proof=False,
    )


def to_data(value: E6Readiness) -> dict[str, object]:
    return {f: getattr(value, f) for f in value.__dataclass_fields__}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="E6 read-only native feasibility interlock")
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--plan", action="store_true")
    actions.add_argument("--check", type=Path, metavar="SELF_REPORT.json")
    args = parser.parse_args(argv)
    try:
        if args.plan:
            report: dict[str, object] = plan()
            exit_code = 0  # planning is safe; no World admission implied
        else:
            assert args.check is not None
            if not args.check.is_file() or args.check.stat().st_size > 1_000_000:
                raise E6Rejected("self-report missing or exceeds the 1MB input bound")
            raw = json.loads(args.check.read_text(encoding="utf-8"))
            report = to_data(check_claims(raw))
            exit_code = 3 if report["classification"] == (
                "CLAIMED_CAPABILITIES_UNATTESTED"
            ) else 4
    except (E6Rejected, OSError, ValueError, TypeError) as exc:
        report = {"classification": "REJECTED", "reason": str(exc),
                  "world_launched": False, "physically_authenticated": False}
        exit_code = 2
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
