"""P1-D: V-review-only, outcome-blind solo Fatigue study candidate and roster.

No real source authentication, S Action decision, World running, V admission or
scientific effect test lives here. Descriptive arithmetic is NOT SCIENCE.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA = "RELAYSELF_P1D_SOLO_FATIGUE_COMPARISON_CANDIDATE_V1"
CLASS = "P1_D_OFFLINE_CANDIDATE_NOT_V_ADMITTED"
ARMS = (
    "FATIGUE_OFF_L0", "ON_FIXED_L0_WAIT", "ON_FSM_SENSOR", "ON_L1",
    "ON_L1_SHAM", "ON_L2",
)
SEEDS = tuple(range(73101, 73109))
STATUSES = (
    "NOT_RUN", "HORIZON", "DEATH", "INFRA_ABORT", "SOLO_INVALID",
    "SOURCE_UNQUALIFIED",
)
PHYSICAL = frozenset(("HORIZON", "DEATH"))
SHA = "0123456789abcdef"
CONTRASTS = (
    ("ON_L1", "ON_FIXED_L0_WAIT"),
    ("ON_L1", "ON_FSM_SENSOR"),
    ("ON_L2", "ON_L1"),
    ("ON_L1", "ON_L1_SHAM"),
    ("ON_FIXED_L0_WAIT", "FATIGUE_OFF_L0"),
)


class P1DRejected(ValueError):
    """Study proposal/source shape/roster mismatch; never auto-repair."""


def candidate() -> dict[str, Any]:
    """Numerical parameters are V-editable before eventual separate freeze."""
    return {
        "schema": SCHEMA,
        "authority_issue": 619,
        "research_index_issue": 620,
        "status": "UNAPPROVED_PROSPECTIVE_PROPOSAL_OFFLINE_ONLY",
        "p1c_parent_head": "3bfadb10315494eb71fba6e851f9d190124257d8",
        "world_profile_path": "experiments/config/p1_solo_no_agents_v1.json",
        "world_profile_requirements": [
            "R_SOURCE_ATTESTED_SOLO_NO_AGENTS_PER_TICK",
            "S_REAL_BODY_MOVEMENT_CAP_AND_WAIT_INTERVAL_APPLIED",
            "S_ACTION_AUTHORIZATION_AND_TRUE_OUTCOMES",
            "M02_ONE_SERVER_PHYSICS_LEDGER_BASAL_IN_WAIT",
            "FROZEN_CLONED_CHUNK_WORLD_AND_PLAYER_POSE_PER_SEED",
            "FROZEN_S_GOLDEN_AND_RETAINED_STATE",
            "INDEPENDENT_R_QUALIFICATION_AND_V_APPROVAL",
        ],
        "world_ticks_max_candidate": 2400,
        "independent_seed_ids_candidate": list(SEEDS),
        "arms_order": list(ARMS),
        "slots_candidate": len(SEEDS) * len(ARMS),
        "world_task": "SAME_PER_SEED_FINITE_OPERATOR_STAGED_FOOD_AND_OBSTACLE_WAYPOINTS_NO_ACTOR",
        "same_before_action_conditions": [
            "FULL_TERRAIN_CHUNK_CLONE_AND_SOURCE_WORLD_SEED",
            "EXACT_NATIVE_START_XYZ_YAW_PITCH",
            "FOOD_SATURATION_HEALTH_AND_ITEM_INVENTORY",
            "WEATHER_TIME_DIFFICULTY_WORLD_TICK_PHASE",
            "IDENTICAL_EXTERNAL_FOOD_STAGING_SCHEDULE",
            "SAME_M02_BASAL_AND_WALK_RATES_ACROSS_ARMS",
            "SAME_ACTION_AND_SAFETY_GRANTS",
            "PAIRED_EXOGENOUS_SEED_NOT_PAIRED_REALIZED_PATH",
        ],
        "arm_definition": {
            "FATIGUE_OFF_L0": "P1_PHYSICS_OFF_UNMODIFIED_L0_NO_WAIT_CONTROL",
            "ON_FIXED_L0_WAIT": "P1_ON_WAIT_AT_EACH_20TH_WORLD_TICK_FIXED_EXOGENOUS_RULE",
            "ON_FSM_SENSOR": "P1_ON_EQUAL_QUANTIZED_SENSOR_HYSTERESIS_0P7_START_0P3_STOP",
            "ON_L1": "P1_ON_EXISTING_S_L1_ONLY_WHEN_REAL_WORLD_BRIDGE_EXISTS",
            "ON_L1_SHAM": "SAME_L1_OUTPUT_AND_PHYSICS_WITH_NOOP_TOGGLE_PATH",
            "ON_L2": "P1_ON_S_L2_AVAILABLE_SAME_SENSOR_AND_AUTHORIZED_ACTIONS",
        },
        "primary": "VERIFIED_EDIBLE_FOOD_CONSUMED_BY_WORLD_TICK_HORIZON",
        "secondary": [
            "ACTUAL_WORLD_SURVIVAL_TICKS_AND_TERMINAL_DEATH",
            "SOURCE_MEASURED_MOVE_BLOCKS_AND_BLOCKED_TICKS",
            "DISTINCT_EXPLICIT_WAIT_WORLD_TICKS_AND_BODY_FATIGUE_TRUE_EVALUATOR_ONLY",
            "NATIVE_HUNGER_SATURATION_HEALTH_AND_M02_BASAL",
            "L0_L1_L2_RELATED_COMPUTATION_WALL_CPU_TOKENS_AND_GPU_SEPARATELY",
        ],
        "contrasts": [list(x) for x in CONTRASTS],
        "minimum_practical_food_difference_candidate": 1.0,
        "minimum_independent_seed_replications_for_interpretation": 8,
        "statistics": "PAIRED_SEED_DESCRIPTIVE_ONLY_V_MUST_CHOOSE_POWER_AND_INFERENCE",
        "stopping_rule": "TRUE_WORLD_TICK_HORIZON_OR_DEATH_OR_ABORT_KEEP_EVERY_ATTEMPT",
        "invalid_rule": "INVALID_AND_CENSORED_TRIALS_RETAINED_NOT_CONVERTED_TO_ZERO_OR_DEATH",
        "pair_rule": "MATCH_WORLD_START_NOT_REALIZED_DISTANCE_OR_FOOD_PATH",
        "selection_rule": "NO_POSTHOC_SEED_ARM_REPLACEMENT_OR_POLICY_TUNING",
        "golden_freeze": "NOT_PRESENT",
        "r_source_admission": "NOT_PRESENT",
        "s_wait_and_l1_l2_action_binding": "NOT_PRESENT",
        "v_final_preregistration": "NOT_APPROVED",
        "science_grant": False,
        "science_trials": 0,
        "power_claim": False,
        "production_go": False,
    }


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def validate_plan(raw: object) -> str:
    if type(raw) is not dict or raw != candidate():
        raise P1DRejected("modified or unfrozen P1-D candidate; V must reapprove prospectively")
    return _hash(raw)


def load_plan(path: str | Path) -> dict[str, Any]:
    def unique(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise P1DRejected("duplicate plan key")
            result[key] = value
        return result

    def bad_constant(value: str) -> None:
        raise P1DRejected("nonfinite JSON numeric input")

    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique,
                         parse_constant=bad_constant)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise P1DRejected("candidate file cannot be read") from exc
    validate_plan(raw)
    return raw


def roster() -> tuple[tuple[int, str], ...]:
    """Seed-blocked, fixed SHA ordering to keep host/order effects auditable."""
    return tuple((seed, arm) for seed in SEEDS for arm in sorted(
        ARMS, key=lambda name: hashlib.sha256(f"P1D:{seed}:{name}".encode()).hexdigest()
    ))


@dataclass(frozen=True)
class CheapWaitState:
    waiting: bool = False


def cheap_wait_proposal(arm: str, world_tick: int, *, sensor_reading: float | None = None,
                        state: CheapWaitState = CheapWaitState()) -> tuple[bool, CheapWaitState]:
    """Reference-only proposal to WAIT, not a generated World Action or interval."""
    if type(world_tick) is not int or world_tick < 0 or not isinstance(state, CheapWaitState):
        raise P1DRejected("invalid reference World tick or cheap state")
    if arm == "FATIGUE_OFF_L0":
        return False, CheapWaitState()
    if arm == "ON_FIXED_L0_WAIT":
        return world_tick % 20 == 19, CheapWaitState()
    if arm == "ON_FSM_SENSOR":
        if type(sensor_reading) not in (int, float) or not math.isfinite(sensor_reading):
            raise P1DRejected("FSM sees only a finite quantized Self fatigue reading")
        next_wait = sensor_reading > 0.3 if state.waiting else sensor_reading >= 0.7
        return next_wait, CheapWaitState(next_wait)
    raise P1DRejected("L1/L2/sham need real S cognition; no evaluator oracle")


def _nonnegative_real(x: object) -> bool:
    return type(x) in (int, float) and math.isfinite(x) and x >= 0


def _sha(x: object) -> bool:
    return type(x) is str and len(x) == 64 and all(c in SHA for c in x)


@dataclass(frozen=True)
class Trial:
    """Offline envelope only; R and V cannot authenticate by trusting this."""

    seed: int
    arm: str
    status: str
    session_id: str = ""
    world_start_sha256: str = ""
    original_source_sha256: str = ""
    world_ticks_observed: int | None = None
    edible_food_consumed: int | None = None
    wait_ticks: int | None = None
    observed_move_blocks: float | None = None
    cpu_ms: float | None = None
    llm_tokens: int | None = None


def _check_trial(trial: Trial, horizon: int) -> None:
    if (not isinstance(trial, Trial)
            or type(trial.seed) is not int or trial.seed not in SEEDS
            or trial.arm not in ARMS or trial.status not in STATUSES):
        raise P1DRejected("foreign or invalid trial slot")
    numerical = (trial.world_ticks_observed, trial.edible_food_consumed,
                 trial.wait_ticks, trial.observed_move_blocks, trial.cpu_ms,
                 trial.llm_tokens)
    if trial.status == "NOT_RUN":
        if any(n is not None for n in numerical) or any((trial.session_id,
            trial.world_start_sha256, trial.original_source_sha256)):
            raise P1DRejected("NOT_RUN cannot claim physical or cognitive evidence")
        return
    if type(trial.session_id) is not str or not trial.session_id.strip():
        raise P1DRejected("all started attempts require nonblank session")
    if trial.status in PHYSICAL:
        if (not _sha(trial.world_start_sha256)
                or not _sha(trial.original_source_sha256)
                or type(trial.world_ticks_observed) is not int
                or not 0 < trial.world_ticks_observed <= horizon
                or type(trial.edible_food_consumed) is not int
                or trial.edible_food_consumed < 0
                or type(trial.wait_ticks) is not int
                or not 0 <= trial.wait_ticks <= trial.world_ticks_observed
                or not _nonnegative_real(trial.observed_move_blocks)
                or not _nonnegative_real(trial.cpu_ms)
                or type(trial.llm_tokens) is not int or trial.llm_tokens < 0):
            raise P1DRejected("invalid physics endpoint/source/cost units")
        if trial.status == "HORIZON" and trial.world_ticks_observed != horizon:
            raise P1DRejected("normal horizon result must reach actual World tick horizon")
    else:
        # Preserve invalid/aborted original evidence, but prevent incomplete
        # attempts from being reinterpreted as measured physical outcomes.
        if any(x is not None for x in (
            trial.edible_food_consumed, trial.wait_ticks,
            trial.observed_move_blocks, trial.cpu_ms, trial.llm_tokens,
        )):
            raise P1DRejected("censored/invalid attempt cannot enter endpoint arithmetic")
        if trial.world_ticks_observed is not None and (
            type(trial.world_ticks_observed) is not int
            or not 0 <= trial.world_ticks_observed <= horizon
        ):
            raise P1DRejected("invalid abort World tick descriptor")
        if (trial.world_start_sha256 and not _sha(trial.world_start_sha256)) or (
            trial.original_source_sha256 and not _sha(trial.original_source_sha256)
        ):
            raise P1DRejected("invalid retained source digest shape")


def unrun_roster() -> tuple[Trial, ...]:
    return tuple(Trial(seed, arm, "NOT_RUN") for seed, arm in roster())


def describe(records: tuple[Trial, ...], *, plan: dict[str, Any]) -> dict[str, Any]:
    """Full-roster descriptive arithmetic; never infer causal or science GO."""
    plan_sha = validate_plan(plan)
    if type(records) is not tuple or len(records) != len(SEEDS) * len(ARMS):
        raise P1DRejected("all expected attempt slots must be preserved")
    slots = [(x.seed, x.arm) for x in records if isinstance(x, Trial)]
    if tuple(slots) != roster():
        raise P1DRejected("reordered, duplicate, foreign or missing trial slots")
    horizon = plan["world_ticks_max_candidate"]
    for t in records:
        _check_trial(t, horizon)
    seen_sessions = [t.session_id for t in records if t.status != "NOT_RUN"]
    if len(seen_sessions) != len(set(seen_sessions)):
        raise P1DRejected("session evidence reused across trial slots")
    all_slots = {(t.seed, t.arm): t for t in records}
    summaries: dict[str, Any] = {}
    for first, second in CONTRASTS:
        paired = []
        reasons = Counter()
        for seed in SEEDS:
            a, b = all_slots[(seed, first)], all_slots[(seed, second)]
            if a.status not in PHYSICAL or b.status not in PHYSICAL:
                reasons["UNPAIRED_MISSING_CENSORED_OR_INVALID"] += 1
                continue
            if a.world_start_sha256 != b.world_start_sha256:
                reasons["UNPAIRED_DIFFERENT_NATIVE_WORLD_START"] += 1
                continue
            paired.append({
                "seed": seed, "edible_food_difference": a.edible_food_consumed - b.edible_food_consumed,
                "survival_fraction_difference": (
                    a.world_ticks_observed - b.world_ticks_observed) / horizon,
                "wait_world_ticks_difference": a.wait_ticks - b.wait_ticks,
            })
        summaries[f"{first}_MINUS_{second}"] = {
            "n_paired_arithmetic_only": len(paired),
            "mean_food_delta_if_observable": (
                sum(v["edible_food_difference"] for v in paired) / len(paired)
                if paired else None
            ),
            "mean_survival_fraction_delta_if_observable": (
                sum(v["survival_fraction_difference"] for v in paired) / len(paired)
                if paired else None
            ),
            "paired_seed_descriptors": paired,
            "unpaired_reasons": dict(sorted(reasons.items())),
        }
    return {
        "classification": CLASS,
        "plan_sha256": plan_sha,
        "expected_slots": len(records),
        "statuses": dict(sorted(Counter(t.status for t in records).items())),
        "per_arm_status": {arm: dict(sorted(Counter(t.status for t in records if t.arm == arm).items()))
                           for arm in ARMS},
        "contrasts": summaries,
        "no_source_originals_authenticated_by_this_code": True,
        "no_v_preregistration_or_power": True,
        "science_go": False,
        "scientific_effect_claim": False,
    }


if __name__ == "__main__":
    print(json.dumps(describe(unrun_roster(), plan=candidate()), sort_keys=True))