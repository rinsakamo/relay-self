"""Offline-only A/B/C evidence reconciliation. Never an Action or learning authority.

The pinned GitHub references are human-audited *metadata*, not native source
attestation. This script cannot qualify physical World outcomes, LearningUpdate,
Habit, compute power, or a production cognitive allocation policy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

VERSION = "AC-INTEGRATION-I0-v1"
FROZEN_SHA256 = "94b5d0d5fe447218403df74d2d2bdc1483b55718eb9a757fb8a21a69fe17a42b"
DEFAULT_MANIFEST = Path(__file__).with_name("ac_integration_i0_manifest.json")

_TOP_FIELDS = frozenset(
    {
        "version", "baseline_main", "owner_issue", "scope", "lanes", "joint_result",
        "joint_runtime_go", "physical_world_effect", "retained_update",
        "production_selector_go", "forbidden_promotions",
    }
)
_LANE_FIELDS = {
    "A": frozenset(
        {
            "lane", "issue", "pr", "head", "ci_run", "evidence", "physical_effect",
            "physical_trials", "planned_physical_trials", "cheap_comparator",
        }
    ),
    "B": frozenset(
        {
            "lane", "issue", "pr", "head", "ci_run", "evidence",
            "simulated_source_actions", "physical_source_actions", "learning_commit",
            "handoff", "feedback_direction",
        }
    ),
    "C": frozenset(
        {
            "lane", "issue", "pr", "head", "ci_run", "evidence",
            "heldout_opportunities", "resource_correct", "no_feedback_correct",
            "simple_gate_correct", "simple_gate_utility_tenths", "resource_utility_tenths",
            "physical_compute", "production_selector",
        }
    ),
}
_PRESENTED_FIELDS = frozenset({"lane", "issue", "pr", "head", "ci_run", "evidence"})


class EvidenceRejected(ValueError):
    """Nonconforming or unqualified reference; fail closed."""


class PromotionDenied(EvidenceRejected):
    """No offline meta-ledger can authorize runtime claims."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EvidenceRejected(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_json(text: str) -> Any:
    try:
        return json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=lambda value: (_ for _ in ()).throw(
                EvidenceRejected(f"nonfinite JSON constant: {value}")
            ),
        )
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise EvidenceRejected("invalid JSON") from exc


def digest(doc: Any) -> str:
    canonical = json.dumps(
        doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _exact_fields(record: Any, keys: frozenset[str], context: str) -> dict[str, Any]:
    if not isinstance(record, dict) or set(record) != keys:
        raise EvidenceRejected(f"{context}: missing, extra, or malformed fields")
    return record


def _exact_int(value: Any, expected: int, context: str) -> None:
    if type(value) is not int or value != expected:
        raise EvidenceRejected(f"{context}: invalid integer or boolean masquerading as integer")


def _exact_string(value: Any, expected: str, context: str) -> None:
    if type(value) is not str or value != expected:
        raise EvidenceRejected(f"{context}: invalid classification or identity")


def validate_manifest(doc: Any, *, check_digest: bool = True) -> dict[str, Any]:
    m = _exact_fields(doc, _TOP_FIELDS, "manifest")
    _exact_string(m["version"], VERSION, "version")
    _exact_string(
        m["baseline_main"], "4348a614900c1d0828581a8eec2c523ba5ae237f", "base"
    )
    _exact_int(m["owner_issue"], 464, "owner issue")
    _exact_string(m["scope"], "OFFLINE_READ_ONLY_EVIDENCE_LEDGER", "scope")
    _exact_string(m["joint_result"], "I0_OFFLINE_READ_ONLY_RECONCILED", "result")
    _exact_string(m["physical_world_effect"], "UNDETERMINED", "physical effect")
    _exact_string(m["retained_update"], "NOT_ATTESTED", "retained update")
    if m["joint_runtime_go"] is not False or m["production_selector_go"] is not False:
        raise PromotionDenied("production admission is forbidden")
    expected_forbidden = [
        "physical_world_success", "production_habit_commit", "action_authorization",
        "automatic_l0_promotion", "high_overhead_allocator_go",
    ]
    if m["forbidden_promotions"] != expected_forbidden:
        raise EvidenceRejected("missing or altered non-promotion contracts")
    lanes = m["lanes"]
    if type(lanes) is not list or len(lanes) != 3:
        raise EvidenceRejected("expected three distinct lanes")
    expected_identity = {
        "A": (457, 460, "640d9df6fdc0310ab6189a05084bd13993864a75", 38015748304),
        "B": (455, 459, "127663c2a4da4533a39c52c96362a7f549038093", 38015628355),
        "C": (456, 458, "c3027114eaf2c4c47368b47578a5fa18572a2c0f", 38015616541),
    }
    seen = set()
    for row in lanes:
        if not isinstance(row, dict) or row.get("lane") not in _LANE_FIELDS:
            raise EvidenceRejected("unknown lane")
        lane = row["lane"]
        if lane in seen:
            raise EvidenceRejected("duplicate lane")
        seen.add(lane)
        _exact_fields(row, _LANE_FIELDS[lane], f"lane {lane}")
        issue, pr, head, run = expected_identity[lane]
        _exact_int(row["issue"], issue, f"{lane} issue")
        _exact_int(row["pr"], pr, f"{lane} PR")
        _exact_string(row["head"], head, f"{lane} head")
        _exact_int(row["ci_run"], run, f"{lane} CI")
    if seen != set(_LANE_FIELDS):
        raise EvidenceRejected("missing lane")
    a, b, c = (next(row for row in lanes if row["lane"] == key) for key in "ABC")
    for key, expected in {
        "evidence": "E5_OFFLINE_RECEIPT_ADMISSION_CI_PASS",
        "physical_effect": "UNDETERMINED",
        "cheap_comparator": "CHEAP_EXACT_PRESERVED",
    }.items():
        _exact_string(a[key], expected, f"A {key}")
    _exact_int(a["physical_trials"], 0, "A physical trials")
    _exact_int(a["planned_physical_trials"], 36, "A planned trials")
    for key, expected in {
        "evidence": "SERIALIZED_SOURCE_AND_EXPLICIT_HANDOFF_GATE_QUALIFIED",
        "learning_commit": "NOT_ATTESTED",
        "handoff": "READ_ONLY_NON_AUTHORITATIVE",
        "feedback_direction": "NONE_WITHOUT_CRITERION",
    }.items():
        _exact_string(b[key], expected, f"B {key}")
    _exact_int(b["simulated_source_actions"], 8, "B simulated actions")
    _exact_int(b["physical_source_actions"], 0, "B physical actions")
    for key, expected in {
        "evidence": "SIMPLE_GATE_SUFFICIENT_UNDER_FROZEN_UTILITY",
        "physical_compute": "NOT_MEASURED",
        "production_selector": "DENIED",
    }.items():
        _exact_string(c[key], expected, f"C {key}")
    for key, expected in {
        "heldout_opportunities": 1440,
        "resource_correct": 1131,
        "no_feedback_correct": 1068,
        "simple_gate_correct": 1088,
        "simple_gate_utility_tenths": 66532,
        "resource_utility_tenths": 29872,
    }.items():
        _exact_int(c[key], expected, f"C {key}")
    if c["simple_gate_utility_tenths"] <= c["resource_utility_tenths"]:
        raise PromotionDenied("complex selector loses frozen cost-aware grand null")
    if check_digest and digest(m) != FROZEN_SHA256:
        raise EvidenceRejected("frozen manifest SHA256 mismatch")
    return m


def reconcile(
    manifest: Any,
    presented: Any | None = None,
    *,
    request: str = "offline",
) -> dict[str, Any]:
    m = validate_manifest(manifest)
    if presented is not None:
        if type(presented) is not list or len(presented) != 3:
            raise EvidenceRejected("presented evidence must have exactly three lane pointers")
        pins = {row["lane"]: row for row in m["lanes"]}
        seen: set[str] = set()
        for candidate in presented:
            row = _exact_fields(candidate, _PRESENTED_FIELDS, "presented pointer")
            lane = row["lane"]
            if type(lane) is not str or lane not in pins or lane in seen:
                raise EvidenceRejected("replayed or unknown source lane")
            seen.add(lane)
            for key in _PRESENTED_FIELDS:
                original = pins[lane][key]
                if type(row[key]) is not type(original) or row[key] != original:
                    raise EvidenceRejected(f"unmatched {lane} source metadata: {key}")
        if seen != set(pins):
            raise EvidenceRejected("omitted lane")
    if request != "offline":
        raise PromotionDenied("no physical, Action, retained update or selector promotion")
    return {
        "classification": "I0_OFFLINE_READ_ONLY_RECONCILED",
        "manifest_sha256": FROZEN_SHA256,
        "joint_runtime_go": False,
        "physical_world_effect": "UNDETERMINED",
        "retained_update": "NOT_ATTESTED",
        "production_selector_go": False,
        "grand_null": "SIMPLE_GATE_SUFFICIENT_UNDER_FROZEN_UTILITY",
        "source_authentication": "NOT_PROVIDED_BY_LEDGER",
        "recorded_lane_order": ["A", "B", "C"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--presented", type=Path)
    parser.add_argument("--request", choices=("offline", "runtime"), default="offline")
    args = parser.parse_args()
    try:
        manifest = strict_json(args.manifest.read_text(encoding="utf-8"))
        presented = (
            strict_json(args.presented.read_text(encoding="utf-8"))
            if args.presented is not None else None
        )
        answer = reconcile(manifest, presented, request=args.request)
    except PromotionDenied as exc:
        answer = {"classification": "I0_PROMOTION_DENIED", "error": str(exc)}
        rc = 3
    except (EvidenceRejected, OSError) as exc:
        answer = {"classification": "I0_REJECTED", "error": str(exc)}
        rc = 2
    else:
        rc = 0
    print(json.dumps(answer, sort_keys=True, ensure_ascii=False))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
