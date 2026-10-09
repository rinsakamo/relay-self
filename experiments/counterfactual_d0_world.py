"""Frozen CF-D0-TOY-v1: offline action-conditioned counterfactual fixture.

Only symbolic reference interventions. No Mineflayer, model or physical action path.
See RelaySelf #421 D0 comment 6089562797. Not a scientific predictor.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from fractions import Fraction
from typing import Mapping

MANIFEST_VERSION = "CF-D0-TOY-v1"
EXPECTED_MANIFEST_SHA256 = (
    "44d4f46d7deb42bd36f9706c87ba1374ab8fbc2656a80236bdcafa59693b5506"
)
CLASS_COUNTS = (0, 5, 10, 15, 20)
SEEDS_PER_CLASS = 20
ACTIONS = ("DIRECT", "DETOUR", "INSPECT")

# This is a source-owned reference contract, not a model-facing payload.
_MANIFEST: dict[str, object] = {
    "action_ids": ["DIRECT", "DETOUR", "INSPECT"],
    "cost_per_health_loss": 1,
    "cost_per_tick": 1,
    "detour_ticks": 5,
    "direct_hazard_health_loss": 12,
    "direct_ticks": 2,
    "goal_reward": 20,
    "inspect_reveal": "perfect H; then safe route: DIRECT if H=0 else DETOUR",
    "inspect_ticks": 1,
    "latent_hazard_fn": "int(((7*seed+3)%20)<class_k)",
    "manifest_version": "CF-D0-TOY-v1",
    "not_visible": [
        "seed", "latent hazard H", "intervention utility", "oracle action"
    ],
    "seeds_per_class": 20,
    "semantic_hazard_counts": [0, 5, 10, 15, 20],
    "visible_evidence": [
        "class prior k of 20",
        "action meanings, route times, objective",
        "prior observations only",
    ],
}


class FixtureContractError(ValueError):
    """Fail closed on bad fixture input or a leakage-prone projected surface."""


@dataclass(frozen=True)
class WorldState:
    """Evaluation-only source state. Never hand this object to a predictor."""

    class_k: int
    seed: int
    latent_hazard: int


@dataclass(frozen=True)
class Consequence:
    """World consequence from one independent intervention on source state."""

    action: str
    elapsed_ticks: int
    health_loss: int
    goal_reached: bool
    observed_hazard: int | None
    utility: int


def _require_class(k: object) -> int:
    if type(k) is not int or k not in CLASS_COUNTS:
        raise FixtureContractError("unknown or non-integer frozen prior class")
    return k


def _require_seed(seed: object) -> int:
    if type(seed) is not int or not (0 <= seed < SEEDS_PER_CLASS):
        raise FixtureContractError("seed is outside frozen evaluation range")
    return seed


def manifest() -> dict[str, object]:
    """A defensive copy: mutations cannot alter the frozen source contract."""
    return deepcopy(_MANIFEST)


def manifest_sha256(value: Mapping[str, object] | None = None) -> str:
    target = manifest() if value is None else value
    try:
        canonical = json.dumps(
            target, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        )
    except (TypeError, ValueError, OverflowError) as exc:
        raise FixtureContractError("uncanonicalizable manifest") from exc
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def assert_manifest_identity(value: Mapping[str, object] | None = None) -> None:
    if manifest_sha256(value) != EXPECTED_MANIFEST_SHA256:
        raise FixtureContractError("CF-D0-TOY-v1 manifest drift")


def initial_state(class_k: int, seed: int) -> WorldState:
    """Reset state. The seed and hazard are evaluation-only, never E_t."""
    k = _require_class(class_k)
    s = _require_seed(seed)
    hidden_hazard = int(((7 * s + 3) % 20) < k)
    return WorldState(k, s, hidden_hazard)


def predictor_evidence(class_k: int) -> dict[str, object]:
    """Exactly the non-oracular E_t available to every comparator."""
    k = _require_class(class_k)
    return {
        "prior": {"hazardCount": k, "total": 20},
        "actions": {
            "DIRECT": {"elapsedTicks": 2, "healthLossIfHazard": 12},
            "DETOUR": {"elapsedTicks": 5, "healthLoss": 0},
            "INSPECT": {
                "elapsedTicksBeforeReveal": 1,
                "observes": "hazard",
                "followUp": {"hazardAbsent": "DIRECT", "hazardPresent": "DETOUR"},
            },
        },
        "utility": {
            "goalReward": 20,
            "tickPenalty": 1,
            "healthLossPenalty": 1,
        },
    }


def validate_predictor_evidence(value: object) -> int:
    """No unapproved fields, including hidden seeds or future outcomes."""
    if not isinstance(value, dict):
        raise FixtureContractError("evidence must be a JSON object")
    prior = value.get("prior")
    if not isinstance(prior, dict):
        raise FixtureContractError("source-grounded prior missing")
    k = _require_class(prior.get("hazardCount"))
    if value != predictor_evidence(k):
        raise FixtureContractError("source contract drift or hidden-field leakage")
    return k


def intervene(source: WorldState, action: str) -> Consequence:
    """One non-mutating do(action) from a preserved pre-action World state."""
    if not isinstance(source, WorldState):
        raise FixtureContractError("expected a reset WorldState")
    if source != initial_state(source.class_k, source.seed):
        raise FixtureContractError("WorldState does not match frozen reset")
    if type(action) is not str or action not in ACTIONS:
        raise FixtureContractError("unknown intervention")

    h = source.latent_hazard
    if action == "DIRECT":
        elapsed, health_loss, observed = 2, 12 * h, None
    elif action == "DETOUR":
        elapsed, health_loss, observed = 5, 0, None
    else:
        # Scripted follow-up, not a Self-generated policy.
        elapsed, health_loss, observed = 1 + (5 if h else 2), 0, h

    return Consequence(
        action=action,
        elapsed_ticks=elapsed,
        health_loss=health_loss,
        goal_reached=True,
        observed_hazard=observed,
        utility=20 - elapsed - health_loss,
    )


def controlled_counterfactuals(
    class_k: int, seed: int, order: tuple[str, ...] = ACTIONS,
) -> dict[str, Consequence]:
    """Reset to identical exogenous state independently for each action."""
    if len(order) != len(ACTIONS) or set(order) != set(ACTIONS):
        raise FixtureContractError("counterfactual intervention order is incomplete")
    if any(type(action) is not str for action in order):
        raise FixtureContractError("invalid action type")
    return {action: intervene(initial_state(class_k, seed), action)
            for action in order}


def expected_utility_from_evidence(value: object) -> dict[str, Fraction]:
    """Strong cheap baseline using ONLY predictor-visible information."""
    k = validate_predictor_evidence(value)
    p = Fraction(k, 20)
    return {
        "DIRECT": Fraction(18) - 12 * p,
        "DETOUR": Fraction(15),
        "INSPECT": Fraction(17) - 3 * p,
    }


def cheap_decision(value: object) -> str:
    utilities = expected_utility_from_evidence(value)
    highest = max(utilities.values())
    best = [action for action, score in utilities.items() if score == highest]
    if len(best) != 1:
        raise FixtureContractError("unfrozen objective tie")
    return best[0]


def hazard_brier_score(forecast_probability: object, observed: int) -> Fraction:
    """Exact proper score for a prospective event; never an LLM judge."""
    if type(observed) is not int or observed not in (0, 1):
        raise FixtureContractError("observed hazard is not binary")
    if isinstance(forecast_probability, bool) or not isinstance(
        forecast_probability, (int, float, Fraction)
    ):
        raise FixtureContractError("forecast probability must be numeric")
    try:
        probability = Fraction(forecast_probability)
    except (ValueError, OverflowError, ZeroDivisionError) as exc:
        raise FixtureContractError("invalid forecast probability") from exc
    if not 0 <= probability <= 1:
        raise FixtureContractError("forecast probability is outside [0,1]")
    return (probability - observed) ** 2


assert_manifest_identity()
