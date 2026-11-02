"""Z2b: offline-prepared Gemma L2 rule, NOT a within-20-tick inference.

The real model selects a conditional strategy during an earlier epoch.
At an exact Paper tick, only arithmetic executes. This module does not
issue Actions, talk to Paper, call HTTP, or admit learning. One old-world
experience does not demonstrate generalization or improvement over CHEAP.
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

TARGET = "NEXT_ZOMBIE_XZ_AT_PLUS_20_SERVER_TICKS_M"
SCHEMA_NAME = "relay_l_zombie_prepared_policy_v1"
STRATEGIES = ("STATIONARY", "CONSTANT_VELOCITY", "TARGET_APPROACH", "ABSTAIN")
APPLICABILITY = ("SINGLE_VISIBLE_TARGET_OPEN_GROUND", "CONDITIONS_UNRESOLVED")
EVIDENCE_IDS = ("Z1B_T40_T60", "Z2A_T46_T66")
EXPECTED_PRIOR_SHA = (
    "31dd510390c75492c023889f7f0d876c702bebea422314fe8151474762b7e49e",
    "3e70f39251d30cd16952e8a2fdf8a5141bbe0ea777c6160ba7a0b5609fb6c32d",
)
MAX_SPEED = 0.30


class ZombiePolicyRejected(ValueError):
    """Invalid source history, real model protocol, or prospective proposal."""


@dataclass(frozen=True, slots=True)
class PreparedZombiePolicy:
    strategy: str
    speed_m_per_tick: float | None
    applicability: str
    reason: str
    falsification_test: str
    cited_ids: tuple[str, ...]
    prior_source_sha256: tuple[str, str]
    model_request_sha256: str
    model_response_sha256: str
    policy_sha256: str
    source_kind: str = "PREPARED_L2_POLICY_UNADMITTED_V1"
    no_action_authority: bool = True
    no_learning_admission: bool = True


def _canonical(obj: object) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode()


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise ZombiePolicyRejected("duplicate JSON field")
        result[key] = value
    return result


def schema() -> dict:
    def enum(*values):
        return {"type": "string", "enum": list(values)}
    return {
        "type": "json_schema",
        "json_schema": {
            "name": SCHEMA_NAME, "strict": True,
            "schema": {
                "type": "object", "additionalProperties": False,
                "required": [
                    "measurement_target", "strategy", "speed_m_per_tick",
                    "applicability", "reason", "falsification_test",
                    "evidence_ids",
                ],
                "properties": {
                    "measurement_target": enum(TARGET),
                    "strategy": enum(*STRATEGIES),
                    "speed_m_per_tick": {
                        "anyOf": [
                            {"type": "number", "minimum": 0, "maximum": MAX_SPEED},
                            {"type": "null"},
                        ],
                    },
                    "applicability": enum(*APPLICABILITY),
                    "reason": {"type": "string", "minLength": 20, "maxLength": 160},
                    "falsification_test": {
                        "type": "string", "minLength": 20, "maxLength": 160,
                    },
                    "evidence_ids": {
                        "type": "array", "minItems": 1, "maxItems": 2,
                        "uniqueItems": True,
                        "items": enum(*EVIDENCE_IDS),
                    },
                },
            },
        },
    }


def request(model: str, *, original_prior: tuple[dict, dict]) -> dict:
    """Only previously completed Worlds; the next World's data is forbidden."""
    if type(model) is not str or not model or len(model) > 128:
        raise ZombiePolicyRejected("real served model name required")
    if type(original_prior) is not tuple or len(original_prior) != 2:
        raise ZombiePolicyRejected("two previous physical Paper source summaries required")
    for prior, sha in zip(original_prior, EXPECTED_PRIOR_SHA, strict=True):
        if (
            type(prior) is not dict
            or prior.get("raw_original_sha256") != sha
            or prior.get("source_scope") != "COMPLETED_PREVIOUS_WORLD"
            or prior.get("zombie_uuid") is None
            or prior.get("start_xz_m") is None
            or prior.get("end_xz_m") is None
        ):
            raise ZombiePolicyRejected("previous Worlds must be pinned by original SHA")
    system = (
        "You are RelaySelf L2 preparing a READ-ONLY conditional 20 Paper-tick "
        "zombie position prediction strategy for a FUTURE and separate Minecraft World. "
        "You will NOT see its current zombie coordinates until execution. "
        "Choose STATIONARY, CONSTANT_VELOCITY, TARGET_APPROACH, or ABSTAIN. "
        "TARGET_APPROACH needs a positive speed in m/Paper-tick and means advance "
        "from current zombie x,z toward the CURRENT player's x,z with clamped "
        "20-tick movement; no guaranteed causal chase is known. "
        "STATIONARY, CONSTANT_VELOCITY and ABSTAIN require speed=null. "
        "Do not pretend old worlds' outcomes are new World observations. "
        "The next World is not held waiting for model inference. "
        "Return compact JSON under schema, no thinking or extra keys."
    )
    body = {
        "model": model, "max_tokens": 384, "temperature": 0, "seed": 1,
        "stream": False, "cache_prompt": False, "reasoning_effort": "none",
        "chat_template_kwargs": {"enable_thinking": False},
        "response_format": schema(),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps({
                "measurement_target": TARGET,
                "prior_experiences": original_prior,
                "allowed_evidence_ids": EVIDENCE_IDS,
                "output_instruction": (
                    "Output the 7 required fields only. Identify a falsifiable "
                    "condition and explicitly recognize limited evidence."
                ),
            }, sort_keys=True, separators=(",", ":"))},
        ],
    }
    return body


def validate_selection(obj: dict) -> None:
    fields = set(schema()["json_schema"]["schema"]["required"])
    if type(obj) is not dict or set(obj) != fields:
        raise ZombiePolicyRejected("exact seven-key Gemma response required")
    if obj["measurement_target"] != TARGET:
        raise ZombiePolicyRejected("wrong position/tick/unit target")
    strat = obj["strategy"]
    speed = obj["speed_m_per_tick"]
    if strat not in STRATEGIES or type(strat) is not str:
        raise ZombiePolicyRejected("invalid strategy")
    if strat == "TARGET_APPROACH":
        if type(speed) not in (float, int) or not math.isfinite(speed) or not 0 < speed <= MAX_SPEED:
            raise ZombiePolicyRejected("approach requires bounded positive speed")
    elif speed is not None:
        raise ZombiePolicyRejected("non-approach and abstaining model may not invent speed")
    if obj["applicability"] not in APPLICABILITY:
        raise ZombiePolicyRejected("invalid applicability")
    for field in ("reason", "falsification_test"):
        value = obj[field]
        if type(value) is not str or not 20 <= len(value) <= 160:
            raise ZombiePolicyRejected("concrete bounded model reason/test required")
    ids = obj["evidence_ids"]
    if (type(ids) is not list or not 1 <= len(ids) <= 2
            or any(type(x) is not str or x not in EVIDENCE_IDS for x in ids)
            or len(set(ids)) != len(ids)):
        raise ZombiePolicyRejected("unknown/duplicate source evidence IDs")


def freeze_from_http(
    *, original_request: bytes, original_response: bytes,
    expected_request: dict,
) -> PreparedZombiePolicy:
    """Preserve original HTTP, validate exact native JSON/schema/thinking OFF."""
    if not isinstance(original_request, bytes) or not isinstance(original_response, bytes):
        raise ZombiePolicyRejected("original request/response bytes required")
    if original_request != _canonical(expected_request):
        raise ZombiePolicyRejected("model request changed after source pin")
    if expected_request.get("response_format") != schema() or (
        expected_request.get("reasoning_effort") != "none"
        or expected_request.get("chat_template_kwargs") != {"enable_thinking": False}
        or expected_request.get("stream") is not False
        or expected_request.get("cache_prompt") is not False
        or expected_request.get("temperature") != 0
        or expected_request.get("seed") != 1
    ):
        raise ZombiePolicyRejected("no native strict Schema + thinking OFF protocol")
    try:
        result = json.loads(original_response.decode("utf-8"), object_pairs_hook=_unique_pairs)
        enforce_gemma_thinking_off(result)
        if (
            type(result) is not dict
            or type(result.get("choices")) is not list
            or len(result["choices"]) != 1
            or result["choices"][0].get("finish_reason") != "stop"
        ):
            raise ZombiePolicyRejected("model response incomplete")
        msg = result["choices"][0]["message"]
        selection = json.loads(msg["content"], object_pairs_hook=_unique_pairs)
        validate_selection(selection)
    except (UnicodeError, ValueError, KeyError, TypeError, GemmaWireRejected) as exc:
        raise ZombiePolicyRejected("invalid genuine Gemma strict response") from exc
    try:
        req_context = json.loads(expected_request["messages"][1]["content"])
        old = tuple(x["raw_original_sha256"] for x in req_context["prior_experiences"])
    except (KeyError, IndexError, ValueError, TypeError) as exc:
        raise ZombiePolicyRejected("broken previous World source provenance") from exc
    if old != EXPECTED_PRIOR_SHA:
        raise ZombiePolicyRejected("unexpected old real-world original SHA")
    fields = {
        "strategy": selection["strategy"],
        "speed_m_per_tick": selection["speed_m_per_tick"],
        "applicability": selection["applicability"],
        "reason": selection["reason"],
        "falsification_test": selection["falsification_test"],
        "cited_ids": tuple(selection["evidence_ids"]),
        "prior_source_sha256": old,
        "model_request_sha256": hashlib.sha256(original_request).hexdigest(),
        "model_response_sha256": hashlib.sha256(original_response).hexdigest(),
    }
    digest = hashlib.sha256(_canonical(fields)).hexdigest()
    return PreparedZombiePolicy(**fields, policy_sha256=digest)


def prediction_from_prior(
    policy: PreparedZombiePolicy, *,
    first_xz: tuple[float, float], issued_xz: tuple[float, float],
    player_xz: tuple[float, float], prior_ticks: int = 10,
) -> tuple[float, float] | None:
    """Pure instantaneous 20-tick use of an earlier-model policy, NOT L2 inference."""
    if (
        not isinstance(policy, PreparedZombiePolicy)
        or type(prior_ticks) is not int or not 1 <= prior_ticks <= 40
        or any(type(p) not in (float, int) or not math.isfinite(p)
               for pair in (first_xz, issued_xz, player_xz)
               if type(pair) is tuple and len(pair) == 2 for p in pair)
        or any(type(pair) is not tuple or len(pair) != 2
               for pair in (first_xz, issued_xz, player_xz))
    ):
        raise ZombiePolicyRejected("finite bounded before-only position tuples required")
    if policy.strategy == "ABSTAIN":
        return None
    x, z = issued_xz
    if policy.strategy == "STATIONARY":
        return (x, z)
    if policy.strategy == "CONSTANT_VELOCITY":
        return (
            x + (x-first_xz[0])*20/prior_ticks,
            z + (z-first_xz[1])*20/prior_ticks,
        )
    if policy.strategy == "TARGET_APPROACH":
        dx, dz = player_xz[0]-x, player_xz[1]-z
        distance = math.hypot(dx, dz)
        amount = min(distance, policy.speed_m_per_tick*20)
        if distance == 0:
            return (x, z)
        return (x + dx*amount/distance, z + dz*amount/distance)
    raise ZombiePolicyRejected("unknown strategy cannot be applied")


def policy_json(policy: PreparedZombiePolicy) -> bytes:
    if not isinstance(policy, PreparedZombiePolicy):
        raise ZombiePolicyRejected("typed prepared policy required")
    return _canonical(asdict(policy)) + b"\n"
