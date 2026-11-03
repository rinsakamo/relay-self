"""Z2c: post-outcome Gemma H2 diagnosis contract on the frozen Z2b H1.

This is an OFFLINE H2 about a completed World. It cannot rewrite H1, admit
a learned L1, qualify B2, or issue a new Minecraft Action. The H2 model
sees the original H1 choice/contradictory falsification and EXACT Paper
predicted/observed x,z, but NOT a precomputed numeric error; it must report
the measured distance itself under a strict schema.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass

from adapters.mineflayer.l_mp11_gemma_wire_contract import (
    GemmaWireRejected,
    enforce_gemma_thinking_off,
)
from adapters.mineflayer.l_zombie_z2b_policy_contract import (
    STRATEGIES,
    ZombiePolicyRejected,
    _canonical,
    _unique_pairs,
)

SCHEMA_NAME = "relay_l_zombie_z2c_h2_feedback_v1"
TARGET = "ZOMBIE_XZ_AT_EXACT_PLUS_20_PAPER_TICKS_M"
ISSUES = (
    "OLD_FALSIFICATION_NAMES_OTHER_RULE",
    "PREPARATION_VS_WORLD_FREEZE_COORDINATES_CONFUSED",
    "CHASE_CAUSALITY_UNATTESTED",
)
RECONSIDERATIONS = (
    "KEEP_WITH_LIMITS", "RESTRICT_APPLICABILITY",
    "PROPOSE_ALTERNATIVE", "ABSTAIN_PENDING_MORE_EVIDENCE",
)
APPLICABILITY = (
    "CONDITIONS_UNRESOLVED",
    "HYPOTHESIS_OPEN_GROUND_SINGLE_VISIBLE_PLAYER",
    "DO_NOT_APPLY_STATIONARY_WHEN_TARGET_APPROACH_OBSERVED",
)
SOURCE_IDS = ("Z2B_ORIGINAL_MODEL_H1", "Z2B_ORIGINAL_PAPER_T37_T57")
MAX_ERROR = 30.0
NUMERIC_TOLERANCE_M = 0.02


@dataclass(frozen=True, slots=True)
class FrozenH2Revision:
    reconsideration: str
    proposed_strategy: str
    proposed_speed_m_per_tick: float | None
    proposed_applicability: str
    diagnosed_issues: tuple[str, ...]
    observed_error_m: float
    reported_cheap_relation: str
    rationale: str
    next_falsification_target: str
    next_test_error_threshold_m: float
    next_falsification_test: str
    source_ids: tuple[str, ...]
    original_h1_policy_sha256: str
    paper_original_sha256: str
    h2_request_sha256: str
    h2_response_sha256: str
    revision_sha256: str
    classification: str = "H2_SOURCE_BOUND_PROPOSED_NOT_ADMITTED"
    learning_authorized: bool = False
    action_authorized: bool = False
    qualification_go: bool = False


def schema() -> dict:
    def enum(values):
        return {"type": "string", "enum": list(values)}
    properties = {
        "measurement_target": enum((TARGET,)),
        "evaluated_prior_strategy": enum(STRATEGIES),
        "observed_horizontal_error_m": {
            "type": "number", "minimum": 0, "maximum": MAX_ERROR,
        },
        "error_basis": enum(("ORIGINAL_PAPER_EXACT_TICK_XZ",)),
        "old_falsification_named_strategy": enum(STRATEGIES),
        "diagnosed_issues": {
            "type": "array", "minItems": 2, "maxItems": len(ISSUES),
            "uniqueItems": True, "items": enum(ISSUES),
        },
        "cheap_relation": enum(("TIED", "BETTER_THAN_BOTH", "WORSE_THAN_BOTH", "MIXED")),
        "reconsideration": enum(RECONSIDERATIONS),
        "proposed_strategy": enum(STRATEGIES),
        "proposed_speed_m_per_tick": {
            "anyOf": [
                {"type": "number", "minimum": 0, "maximum": 0.3},
                {"type": "null"},
            ],
        },
        "proposed_applicability": enum(APPLICABILITY),
        "next_falsification_target": enum(STRATEGIES),
        "next_test_error_threshold_m": {
            "type": "number", "minimum": 0.05, "maximum": 5.0,
        },
        "next_falsification_test": {
            "type": "string", "minLength": 24, "maxLength": 240,
        },
        "rationale": {
            "type": "string", "minLength": 32, "maxLength": 280,
        },
        "evidence_ids": {
            "type": "array", "minItems": 2, "maxItems": 2,
            "uniqueItems": True, "items": enum(SOURCE_IDS),
        },
    }
    return {
        "type": "json_schema",
        "json_schema": {
            "name": SCHEMA_NAME, "strict": True,
            "schema": {
                "type": "object", "additionalProperties": False,
                "required": list(properties),
                "properties": properties,
            },
        },
    }


def build_request(
    *, model: str, old_policy: dict, completed_world: dict,
    paper_original_sha256: str,
) -> dict:
    """Feedback only after the SAME past World has completed.

    Do not put independently scored errors in the model-facing source:
    Gemma must recognize and calculate horizontal discrepancy from points.
    """
    if (
        type(model) is not str or not 0 < len(model) <= 128
        or type(old_policy) is not dict or type(completed_world) is not dict
        or type(paper_original_sha256) is not str
        or len(paper_original_sha256) != 64
    ):
        raise ZombiePolicyRejected("valid historical source/served model required")
    if (
        old_policy.get("strategy") != "STATIONARY"
        or old_policy.get("speed_m_per_tick") is not None
        or "CONSTANT_VELOCITY" not in old_policy.get("falsification_test", "")
        or completed_world.get("strategy") != "STATIONARY"
        or completed_world.get("policy_sha256") != old_policy.get("policy_sha256")
        or completed_world.get("original_paper_sha256") != paper_original_sha256
        or completed_world.get("target_tick") != completed_world.get("issued_tick", 0) + 20
        or completed_world.get("frozen_before_next_tick") is not True
        or completed_world.get("model_live_in_world_calls") != 0
        or completed_world.get("model_prepared_xz_m") is None
    ):
        raise ZombiePolicyRejected("only the exact completed Z2b STATIONARY H1 source is admissible")
    context = {
        "epoch": "AFTER_Z2B_WORLD_COMPLETED_NO_NEXT_WORLD",
        "old_policy": {
            "strategy": old_policy["strategy"],
            "applicability": old_policy["applicability"],
            "reason": old_policy["reason"],
            "falsification_test": old_policy["falsification_test"],
            "policy_sha256": old_policy["policy_sha256"],
        },
        "world_source": {
            "paper_original_sha256": paper_original_sha256,
            "world_uuid": completed_world["world_uuid"],
            "zombie_uuid": completed_world["zombie_uuid"],
            "issued_tick": completed_world["issued_tick"],
            "target_tick": completed_world["target_tick"],
            "original_predicted_xz_m": completed_world["model_prepared_xz_m"],
            "original_actual_xz_m": completed_world["future_actual_xz_m"],
            "cheap_stationary_predicted_xz_m": completed_world["model_prepared_xz_m"],
            "cheap_velocity_predicted_xz_m": completed_world["model_prepared_xz_m"],
            "known_information_boundary": (
                "Previous epoch had no future World player position. "
                "The deployed TARGET_APPROACH strategy COULD acquire the current "
                "player x,z at freeze time in Paper; do not conflate these."
            ),
            "causal_chase": "NOT_ATTESTED",
            "native_client_exact_tick_join": "UNATTESTED",
        },
        "source_ids": list(SOURCE_IDS),
    }
    return {
        "model": model, "temperature": 0, "seed": 1,
        "max_tokens": 640, "stream": False, "cache_prompt": False,
        "reasoning_effort": "none",
        "chat_template_kwargs": {"enable_thinking": False},
        "response_format": schema(),
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are RelaySelf L2 at H2, AFTER a completed physical World. "
                    "Do not issue player/zombie actions, learn or deploy a strategy. "
                    "The original H1 prediction must stay immutable. "
                    "Compute horizontal Euclidean error in meters from supplied "
                    "predicted vs actual x,z; it is deliberately NOT provided. "
                    "Independently compare original STATIONARY, cheap stationary "
                    "and cheap velocity (the three positions are identical). "
                    "Identify that old H1 falsely names CONSTANT_VELOCITY in its "
                    "falsification and conflates preparation vs future freeze "
                    "coordinate availability. Causal chase is unproven. "
                    "Choose a falsifiable NEXT hypothesis, not a proved model update. "
                    "A new numeric test threshold is only a predeclared candidate, "
                    "not a validated old-world tolerance. Falsification target "
                    "MUST be the NEW proposed strategy, except ABSTAIN may test "
                    "the old STATIONARY rule. No claim of B2/learning/holdout. "
                    "Native strict JSON only; no thinking channel."
                ),
            },
            {"role": "user", "content": json.dumps(
                context, sort_keys=True, separators=(",", ":"),
            )},
        ],
    }


def _finite_number(value: object, *, low: float, high: float) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ZombiePolicyRejected("H2 numeric non-finite, string or bool")
    if not low <= value <= high:
        raise ZombiePolicyRejected("H2 numeric outside bounded range")
    return float(value)


def validate_h2(
    answer: object, *, prior: dict, world: dict,
) -> None:
    props = schema()["json_schema"]["schema"]["properties"]
    if type(answer) is not dict or set(answer) != set(props):
        raise ZombiePolicyRejected("exact H2 native JSON required")
    if (
        answer["measurement_target"] != TARGET
        or answer["evaluated_prior_strategy"] != prior["strategy"]
        or answer["error_basis"] != "ORIGINAL_PAPER_EXACT_TICK_XZ"
        or answer["old_falsification_named_strategy"] != "CONSTANT_VELOCITY"
    ):
        raise ZombiePolicyRejected("H2 did not identify the actual old strategy/error target")
    predicted = world["model_prepared_xz_m"]
    actual = world["future_actual_xz_m"]
    if (
        type(predicted) is not list or type(actual) is not list
        or len(predicted) != 2 or len(actual) != 2
    ):
        raise ZombiePolicyRejected("original measured xz missing")
    for val in predicted + actual:
        _finite_number(val, low=-30_000_000, high=30_000_000)
    recomputed = math.dist(predicted, actual)
    stated = _finite_number(answer["observed_horizontal_error_m"], low=0, high=MAX_ERROR)
    if abs(stated-recomputed) > NUMERIC_TOLERANCE_M:
        raise ZombiePolicyRejected("model did not reproduce original measured numeric error")
    cheap_s = _finite_number(world["cheap_stationary_error_m"], low=0, high=MAX_ERROR)
    cheap_v = _finite_number(world["cheap_velocity_error_m"], low=0, high=MAX_ERROR)
    if (
        answer["cheap_relation"] != "TIED"
        or abs(cheap_s-recomputed) > 1e-8
        or abs(cheap_v-recomputed) > 1e-8
    ):
        raise ZombiePolicyRejected("not a true CHEAP tie on same original World")
    issues = answer["diagnosed_issues"]
    if (
        type(issues) is not list or not 2 <= len(issues) <= 3
        or any(type(x) is not str or x not in ISSUES for x in issues)
        or len(set(issues)) != len(issues)
        or not set(ISSUES[:2]).issubset(issues)
    ):
        raise ZombiePolicyRejected("H2 missed known original falsification/temporal confusion")
    if (
        type(answer["evidence_ids"]) is not list
        or set(answer["evidence_ids"]) != set(SOURCE_IDS)
        or len(answer["evidence_ids"]) != 2
    ):
        raise ZombiePolicyRejected("H2 lacks both original H1+outcome source IDs")
    reconsideration = answer["reconsideration"]
    proposal = answer["proposed_strategy"]
    if reconsideration not in RECONSIDERATIONS or proposal not in STRATEGIES:
        raise ZombiePolicyRejected("unrecognized H2 reconsideration/strategy")
    if reconsideration == "KEEP_WITH_LIMITS" and proposal != prior["strategy"]:
        raise ZombiePolicyRejected("keep cannot silently switch strategy")
    if reconsideration == "PROPOSE_ALTERNATIVE" and proposal in (prior["strategy"], "ABSTAIN"):
        raise ZombiePolicyRejected("alternative must actually propose another forecast")
    if reconsideration == "ABSTAIN_PENDING_MORE_EVIDENCE" and proposal != "ABSTAIN":
        raise ZombiePolicyRejected("abstain claim must be an actual abstention")
    speed = answer["proposed_speed_m_per_tick"]
    if proposal == "TARGET_APPROACH":
        _finite_number(speed, low=0.000000001, high=0.3)
    elif speed is not None:
        raise ZombiePolicyRejected("new speed only permitted for TARGET_APPROACH")
    if answer["proposed_applicability"] not in APPLICABILITY:
        raise ZombiePolicyRejected("unqualified applicability")
    target = answer["next_falsification_target"]
    if target != (prior["strategy"] if proposal == "ABSTAIN" else proposal):
        raise ZombiePolicyRejected("new falsification references wrong strategy")
    _finite_number(answer["next_test_error_threshold_m"], low=0.05, high=5.0)
    for key, low, high in (
        ("rationale", 32, 280), ("next_falsification_test", 24, 240),
    ):
        value = answer[key]
        if type(value) is not str or not low <= len(value) <= high:
            raise ZombiePolicyRejected("missing bounded falsifiable H2 rationale")
    if "1.5m" in answer["next_falsification_test"].replace(" ", ""):
        raise ZombiePolicyRejected("unvalidated historical threshold reused as scientific fact")


def freeze_h2(
    *, request_raw: bytes, response_raw: bytes,
    expected_request: dict, old_policy: dict, world: dict,
) -> FrozenH2Revision:
    if (
        type(request_raw) is not bytes or type(response_raw) is not bytes
        or request_raw != _canonical(expected_request)
        or expected_request.get("response_format") != schema()
        or expected_request.get("reasoning_effort") != "none"
        or expected_request.get("chat_template_kwargs") != {"enable_thinking": False}
        or expected_request.get("stream") is not False
        or expected_request.get("cache_prompt") is not False
        or expected_request.get("temperature") != 0
        or expected_request.get("seed") != 1
    ):
        raise ZombiePolicyRejected("original H2 HTTP/schema/reasoning contract mismatch")
    try:
        source = json.loads(response_raw.decode("utf-8"), object_pairs_hook=_unique_pairs)
        enforce_gemma_thinking_off(source)
        if (
            type(source) is not dict
            or type(source.get("choices")) is not list
            or len(source["choices"]) != 1
            or source["choices"][0].get("finish_reason") != "stop"
        ):
            raise ZombiePolicyRejected("real model H2 incomplete")
        answer = json.loads(
            source["choices"][0]["message"]["content"],
            object_pairs_hook=_unique_pairs,
        )
        validate_h2(answer, prior=old_policy, world=world)
    except (ValueError, TypeError, KeyError, IndexError, UnicodeError, GemmaWireRejected) as exc:
        raise ZombiePolicyRejected("real H2 response failed strict numeric/semantic contract") from exc
    fields = {
        "reconsideration": answer["reconsideration"],
        "proposed_strategy": answer["proposed_strategy"],
        "proposed_speed_m_per_tick": answer["proposed_speed_m_per_tick"],
        "proposed_applicability": answer["proposed_applicability"],
        "diagnosed_issues": tuple(answer["diagnosed_issues"]),
        "observed_error_m": answer["observed_horizontal_error_m"],
        "reported_cheap_relation": answer["cheap_relation"],
        "rationale": answer["rationale"],
        "next_falsification_target": answer["next_falsification_target"],
        "next_test_error_threshold_m": answer["next_test_error_threshold_m"],
        "next_falsification_test": answer["next_falsification_test"],
        "source_ids": tuple(answer["evidence_ids"]),
        "original_h1_policy_sha256": old_policy["policy_sha256"],
        "paper_original_sha256": world["original_paper_sha256"],
        "h2_request_sha256": hashlib.sha256(request_raw).hexdigest(),
        "h2_response_sha256": hashlib.sha256(response_raw).hexdigest(),
    }
    return FrozenH2Revision(
        **fields,
        revision_sha256=hashlib.sha256(_canonical(fields)).hexdigest(),
    )


def revision_json(value: FrozenH2Revision) -> bytes:
    if not isinstance(value, FrozenH2Revision):
        raise ZombiePolicyRejected("typed H2 proposal required")
    return _canonical(asdict(value)) + b"\n"
