"""B20: no-generative, evidence-bound Grand Null and product-promotion gate.

This is a static manifest adjudicator; not independent GitHub verification,
physical source attestation or an external scientific/security review.
Every evidence item is a still-unmerged experimental Draft. It deliberately
retains positive benefits of cheap mechanisms versus WEAKER comparators.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

SCHEMA = "AC_B_B20_B11_B19_EVIDENCE_SYNTHESIS_V1"
MAIN_SHA = "4348a614900c1d0828581a8eec2c523ba5ae237f"
FROZEN_S17_SHA = "64868337510a960c140e96d5d3d20949ad53fb8e"
EXPECTED = (
    ("B11", 481, 485, "8dd1f0cc115285293736f5d36950469d3866a9db",
     38030146847, "CHEAP_TAG_TIE"),
    ("B12", 489, 491, "33686285cd2ffe5865538fd11113c8736f6c36a4",
     38030776737, "EXPERIMENTAL_SIGNED_GRANT_WITH_DISJOINT_S17_SOURCE"),
    ("B13", 493, 496, "71affb6fd5bbbdc9b41ee245ab1d6f46d2307ab0",
     38031339497, "SHARED_SIMULATOR_S10_S11_ADMISSION_NOT_CAUSATION"),
    ("B14", 498, 501, "7edbc294778494f4c1585a2db94f8bc36a607a6a",
     38033351256, "CHEAP_TAG_MATCHES_HABIT_READAPTATION"),
    ("B15", 504, 506, "68f23eb7b51cf761c6f8eccc575fc2749a55755c",
     38035317588, "NOISY_SILENT_CHANGE_CHEAP_TIE_FALSE_ALARM"),
    ("B16", 508, 510, "f4e31933c464f9b39f854dd2408134544d3f9f76",
     38036245443, "CHEAP_QUORUM_GAIN_OVER_ONE_SHOT_AND_TIE_S10"),
    ("B17", 517, 520, "c299b8b57a9e5d16e740f3ad8459c84181a0e865",
     38038315538, "CHEAP_EARLY_STOP_SOURCE_DIVERSITY_POSITIVE_NO_S10_GAIN"),
    ("B18", 521, 524, "616ae873c73cd87cd81cd3b79a7fc989a91eb6d7",
     38039043328, "CHEAP_EMPIRICAL_Q_RISK_ADAPTATION_AND_S11_TIE"),
    ("B19", 527, 530, "20efc7ea5c35c556f6d83907357c418d3501cfa8",
     38042242916, "INFORMATION_NEUTRAL_THINK_COST_DOMINATED_CHEAP_TIE"),
)
POSITIVE_CHEAP = (
    "B16_4_OF_5_QUORUM_BEATS_FIRST_SHOT_UNDER_FIXED_NOISE",
    "B17_DECISION_DETERMINACY_REDUCES_SOURCE_ACTIONS",
    "B17_SECOND_TEST_SOURCE_TURNS_WRONG_DECISION_INTO_ABSTENTION_UNDER_ASSUMED_CLEAN_CHANNEL",
    "B18_CHEAP_Q_LEARNS_RISK_COST_DEPENDENT_QUERY_CHOICE",
    "B19_WORK_TICK_REACCOUNTING_CAN_REVERSE_SOURCE_ONLY_QUERY_ADVANTAGE",
)
PROMOTIONS = (
    "PROMOTE_PRODUCTION_HABIT_OWNER",
    "VERIFIED_S17_TO_S11_PHYSICAL_BRIDGE",
    "LIVE_L2_RESOURCE_GAIN",
    "VERIFIED_L2_TO_L1_DISTILLATION",
    "L0_REFLEX_COMPILE",
)
MISSING_GATES = (
    "AUTHENTICATED_COMMON_PHYSICAL_ACTION_OUTCOME",
    "NON_BYPASSABLE_PRODUCTION_S11_OWNER",
    "CAUSALLY_DISCRIMINATING_HELDOUT_L2_VS_CHEAP",
    "MEASURED_COMPUTE_AND_CALIBRATED_BODY_COST_FOR_COST_CLAIMS",
)
BOUNDED_TERMINAL = (
    "B11_B19_BOUNDED_GRAND_NULL_SYNTHESIZED_WITH_EXPLICIT_POSITIVE_CONTROLS"
)


class InvalidFrozenEvidence(ValueError):
    """Reject record splicing, elevated claims, and invented physical authority."""


@dataclass(frozen=True, slots=True)
class EvidenceSynthesis:
    terminal: str
    qualified_offline_draft_count: int
    cheap_baseline_tie_count: int
    generic_positive_controls: tuple[str, ...]
    production_s11_owner_qualified: bool
    physical_s17_s11_source_qualified: bool
    authentic_l2_gain_qualified: bool
    live_body_cost_measurement_qualified: bool
    source_authority: str


@dataclass(frozen=True, slots=True)
class PromotionDecision:
    proposed_claim: str
    status: str
    missing_witnesses: tuple[str, ...]
    terminal: str


def read_frozen_manifest() -> dict[str, object]:
    path = Path(__file__).with_name("ac_b_b20_manifest.json")
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise InvalidFrozenEvidence("top-level manifest must be an object")
    return obj


def check_frozen_evidence(manifest: Mapping[str, object]) -> EvidenceSynthesis:
    """Validation of the documented FIXED heads, not a live GitHub query."""
    if not isinstance(manifest, Mapping) or manifest.get("schema") != SCHEMA:
        raise InvalidFrozenEvidence("wrong immutable prospectively frozen schema")
    a = manifest.get("authority")
    if not isinstance(a, dict) or (
        a.get("issue") != 533
        or a.get("parent_lane_B") != 431
        or a.get("parent_AC") != 426
        or a.get("read_only_lane_C") != 432
        or a.get("main") != MAIN_SHA
        or a.get("S17") != FROZEN_S17_SHA
        or a.get("B19_exact") != EXPECTED[-1][3]
        or a.get("pr_base_branch") !=
        "self/ac-b-b19-resource-vs-epistemic-value-20261010"
        or a.get("C15_static_endpoint_PR") != 525
        or a.get("C15_static_head") !=
        "5e738596b805522d8516b43fa1b7ee001bfc5b2b"
    ):
        raise InvalidFrozenEvidence("cross-lane/frozen authority mismatch")
    records = manifest.get("prospective_entries")
    if not isinstance(records, list) or len(records) != len(EXPECTED):
        raise InvalidFrozenEvidence("all 9 exact frozen experiment receipts required")
    preceding = FROZEN_S17_SHA
    for r, (step, issue, pr, head, ci, cls) in zip(records, EXPECTED):
        if not isinstance(r, dict) or (
            r.get("step") != step
            or r.get("issue") != issue
            or r.get("pr") != pr
            or r.get("head") != head
            or r.get("base") != preceding
            or r.get("ci_run") != ci
            or r.get("classification") != cls
            or r.get("source_type") != (
                "DISJOINT_OFFLINE_S17_FAKE_AND_B11_SIM"
                if step == "B12" else "OFFLINE_LOCAL_TEST_WORLD"
            )
            or r.get("production_authority") is not False
            or r.get("actual_llm_l2") is not False
            or r.get("cheap_comparator_no_worse") is not True
        ):
            raise InvalidFrozenEvidence(f"{step}: receipt/claim/lineage altered")
        if (
            not re.fullmatch(r"[0-9a-f]{40}", head)
            or not re.fullmatch(r"[0-9a-f]{40}", preceding)
        ):
            raise InvalidFrozenEvidence("invalid complete exact SHA")
        preceding = head

    if tuple(manifest.get("bounded_generic_positive", ())) != POSITIVE_CHEAP:
        raise InvalidFrozenEvidence("bounded cheap positive-control result altered")
    if tuple(manifest.get("disallowed_promotions", ())) != PROMOTIONS:
        raise InvalidFrozenEvidence("unqualified promotion was admitted")
    if tuple(manifest.get("pending_physical_prerequisites", ())) != MISSING_GATES:
        raise InvalidFrozenEvidence("physical/security admission conditions changed")
    if manifest.get("terminal_if_verified") != BOUNDED_TERMINAL:
        raise InvalidFrozenEvidence("experimental Grand Null promoted")
    limits = manifest.get("limits")
    if not isinstance(limits, list) or not any(
        "Minecraft" in str(v)
        for v in limits
    ):
        # Precise wording here is a documented static limitation, not
        # cryptographic validation of the original sources.
        raise InvalidFrozenEvidence("Minecraft source limit missing")
    return EvidenceSynthesis(
        terminal=BOUNDED_TERMINAL,
        qualified_offline_draft_count=9,
        cheap_baseline_tie_count=9,
        generic_positive_controls=POSITIVE_CHEAP,
        production_s11_owner_qualified=False,
        physical_s17_s11_source_qualified=False,
        authentic_l2_gain_qualified=False,
        live_body_cost_measurement_qualified=False,
        source_authority="FROZEN_EXPERIMENT_METADATA_ONLY_NOT_REAL_WORLD",
    )


def promotion_gate(
    claimed: str, *,
    caller_supplied_witnesses: tuple[str, ...] = (),
    manifest: Mapping[str, object] | None = None,
) -> PromotionDecision:
    """Conservative: arbitrary caller-supplied 'certificates' have NO issuer.

    Even if a caller strings together all desired labels, this module has no
    independently authenticated witness verifier. Therefore no promotion can
    be admitted through this experimental B20 API.
    """
    check_frozen_evidence(manifest if manifest is not None
                          else read_frozen_manifest())
    if claimed not in PROMOTIONS:
        raise InvalidFrozenEvidence("unknown production elevation request")
    if not isinstance(caller_supplied_witnesses, tuple) or any(
        not isinstance(x, str) for x in caller_supplied_witnesses
    ):
        raise InvalidFrozenEvidence("unverified witness token shape")
    return PromotionDecision(
        proposed_claim=claimed,
        status="BLOCKED_NO_INDEPENDENT_SOURCE_AUTHORITY",
        missing_witnesses=MISSING_GATES,
        terminal=BOUNDED_TERMINAL,
    )


def synthesize() -> dict[str, object]:
    r = check_frozen_evidence(read_frozen_manifest())
    return {
        "terminal": r.terminal,
        "offline_experiment_drafts": r.qualified_offline_draft_count,
        "cheap_equal_or_better_comparator_count": r.cheap_baseline_tie_count,
        "distinct_cheap_positive_controls": list(r.generic_positive_controls),
        "physical_s17_s11_bridge": r.physical_s17_s11_source_qualified,
        "production_s11_owner": r.production_s11_owner_qualified,
        "native_l2_measured_gain": r.authentic_l2_gain_qualified,
        "physical_resource_calibration": r.live_body_cost_measurement_qualified,
        "blocked_promotions": [
            {"claim": c, "status": promotion_gate(c).status}
            for c in PROMOTIONS
        ],
        "no_actual_world_model_gpu_spend": True,
    }
