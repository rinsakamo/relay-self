"""S12 S49 discrimination preflight: stop before spending a World permission.

Current S49 may issue only a source-admitted MOVE_AWAY (MOVE_BACKWARD).
WAIT does not issue an Action, and S11/L5 proposals are shadow-only.
V's independently recomputed two-feature cheap policy matches L5 on
the current *synthetic* fixture. These facts cannot constitute a live
two-executable-action Goal/Memory benefit experiment.

Pure read-only classification, not experiment configuration/approval.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from adapters.mineflayer.self_s10_memory_ablation import S10ShadowAB
from adapters.mineflayer.self_s11_l5_shadow_intake import (
    S11Disposition,
    S11ReadOnlyReview,
)

V_EXACT_HEAD = "53d50029da64a95c56bb56c6d48b5d14ce94e84a"
L5_EXACT_HEAD = "17c5357fd5625274ee567ad979b780e77bf7b1e7"
S11_EXACT_HEAD = "69a150cc6f687e5b379713ba4c5e0ba2de60b38f"
V_CHEAP_CLASSIFICATION = "V_L5_TWO_FEATURE_CHEAP_NULL_REPRODUCES_CONTEXTUAL_SHADOW"
S49_EXECUTABLE_CANDIDATE = "MOVE_AWAY"
S49_EXECUTION_REF = "MOVE_BACKWARD"
S49_WAIT_IS_NONISSUING = True


class S12PreflightRejected(ValueError):
    """Unqualified lane claims or unsafe promotion of source-shaped evidence."""


class S12Readiness(str, Enum):
    NOT_READY = "NO_DISCRIMINATING_WORLD_ACTION_OR_GOAL"
    ABSTAIN = "L5_ABSTAINED_NO_DISCRIMINATING_WORLD_ACTION_OR_GOAL"
    UNPAIRED = "L5_ACTION_VOCAB_UNPAIRED_NO_DISCRIMINATING_WORLD_ACTION_OR_GOAL"


@dataclass(frozen=True, slots=True)
class S12Preflight:
    status: S12Readiness
    s49_executable_candidate_refs: tuple[str, ...]
    s49_nonissuing_refs: tuple[str, ...]
    s11_session_id: str
    s11_probe_seq: int
    v_two_feature_parity: bool
    v_source_class: str
    blockers: tuple[str, ...]
    real_world_actions_issued: int = 0
    independent_physical_goal_receipts: int = 0
    actual_paired_heldout_trials: int = 0
    fresh_world_permission: bool = False
    action_authority: bool = False
    experiment_ready: bool = False
    learning_updates: int = 0
    habit_grants: int = 0
    science_qualified: bool = False


def assess_s12(
    *,
    s10: S10ShadowAB,
    s11: S11ReadOnlyReview,
    v_cheap: Mapping[str, object],
) -> S12Preflight:
    """S-owned fail-closed readiness check using actual independent V result.

    The same V cheap table reuses *synthetic* L5 training fixtures.
    It is evidence against a claim of additional L5 value, not evidence
    of real Goal parity. R6 original byte review does not fill R1/R2/Goal.
    No path in this function can start or authorize a physical experiment.
    """
    if (
        not isinstance(s10, S10ShadowAB)
        or not isinstance(s11, S11ReadOnlyReview)
        or not isinstance(v_cheap, Mapping)
    ):
        raise S12PreflightRejected("typed independent S10/S11/V inputs required")
    if (
        s10.disposition != "RECALL_DIFFERENCE_NO_L0_DECISION_EFFECT"
        or s10.present_hint != "recall"
        or s10.withheld_hint == "recall"
        or s10.present_selection != s10.withheld_selection
        or s10.physical_runs != 0
        or s10.issued_actions != 0
        or s10.goal_attested
        or s10.memory_caused_physical_action
        or s10.learning_updates != 0
        or s10.habit_grants != 0
        or s10.scientific_go
        or s11.session_id != s10.session_id
        or s11.probe_seq != s10.probe_seq
        or s11.fixed_l0_selection != s10.present_selection
        or s11.status not in set(S11Disposition)
        or s11.action_authority
        or s11.source_byte_authenticated_here
        or s11.goal_evidence_authenticated_here
        or s11.physical_actions != 0
        or s11.habit_grants != 0
        or s11.learning_updates != 0
        or s11.science_qualified
        or s11.memory_causal_benefit_established
    ):
        raise S12PreflightRejected("original fixed S10/S11 no-authority boundary required")
    expected_v = {
        "schema": "RELAYSELF_V_L5_STRONG_CHEAP_NULL_V1",
        "l5_exact_head": L5_EXACT_HEAD,
        "s11_exact_head": S11_EXACT_HEAD,
        "source_class": "PINNED_L5_SYNTHETIC_FIXTURE_NOT_REAL_WORLD",
        "independent_cheap_policy": "SAME_TRAINING_TWO_FEATURE_FOUR_CELL_RATE_LOOKUP",
        "training_source_shaped_episodes": 16,
        "paired_s10_world_outcomes": 0,
        "heldout_original_goal_receipts": 0,
        "paired_s11_original_action_vocabulary": False,
        "four_contexts_tested": 4,
        "cheap_matches_l5_all_contexts": True,
        "memory_shifts_shadow_ref": True,
        "physical_goal_effect": "NOT_MEASURED",
        "learning_mechanism_advantage_over_strongest_cheap": False,
        "s11_action_authorized": False,
        "scientific_g3": "NO_GO",
        "classification": V_CHEAP_CLASSIFICATION,
    }
    if set(v_cheap) != set(expected_v) or any(
        type(v_cheap[key]) is not type(value) or v_cheap[key] != value
        for key, value in expected_v.items()
    ):
        raise S12PreflightRejected("exact V original cheap null/claim ceiling required")
    if s10.present_selection != S49_EXECUTABLE_CANDIDATE:
        raise S12PreflightRejected("S49 observed baseline must be executable MOVE_AWAY")
    if s11.status is S11Disposition.L5_ABSTAINED:
        status = S12Readiness.ABSTAIN
    elif s11.status is S11Disposition.UNPAIRED_SOURCE:
        status = S12Readiness.UNPAIRED
    else:
        status = S12Readiness.NOT_READY
    return S12Preflight(
        status=status,
        s49_executable_candidate_refs=(S49_EXECUTABLE_CANDIDATE,),
        s49_nonissuing_refs=("WAIT",),
        s11_session_id=s11.session_id,
        s11_probe_seq=s11.probe_seq,
        v_two_feature_parity=True,
        v_source_class=expected_v["source_class"],
        blockers=(
            "S49_ONLY_MOVE_AWAY_HAS_CURRENT_ACTION_EXECUTOR_ADMISSION",
            "S49_WAIT_IS_NONISSUING_NOT_AN_ALTERNATIVE_EXECUTED_ACTION",
            "L5_S11_SHADOW_NOT_AN_EXECUTABLE_ACTION_AUTHORITY",
            "V_TWO_FEATURE_SAME_INFORMATION_CHEAP_PARITY",
            "L5_OPTION_A_B_NOT_SOURCE_PAIRED_TO_S49_MOVE_AWAY",
            "NO_SEPARATELY_S_R_V_ADMITTED_PHYSICAL_GOAL_OR_R1_R2_TYPED_OUTCOME",
            "NO_MATCHED_INDEPENDENT_HELDOUT_OR_COST_MEASUREMENT",
            "S8_S9_PHYSICAL_AUTHORIZATION_CONSUMED",
        ),
    )
