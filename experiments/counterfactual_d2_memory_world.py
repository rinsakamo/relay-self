"""Frozen #424 CF-D2-MEMORY-XOR-v1 zero-model counterfactual fixture.

Evaluation-only, no model, server, socket, Mineflayer, learning or action path.
A known XOR mechanism and provenance-bound training episode let a CHEAP rule
achieve the same maximum utility; no claim of LLM predictor usefulness.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from fractions import Fraction
from typing import Mapping

DESIGN_RECEIPT = 6089883947
VERSION = "CF-D2-MEMORY-XOR-v1"
MANIFEST_SHA256 = "fddf90f049dc11d3737bde30ac3a2b50ec14cbe164dfe1e5bd2ac4207f726976"
ACTIONS = ("DIRECT", "DETOUR", "INSPECT")
TEST_CUES = ((0, 1), (1, 0), (1, 1))
_THETAS = (0, 1)

_MANIFEST: dict[str, object] = {
    "actions": ["DIRECT", "DETOUR", "INSPECT"],
    "cue_values": [0, 1],
    "cues": ["u", "v"],
    "detour": {"health_loss": 0, "ticks": 5},
    "direct": {"health_loss": "12*H", "ticks": 2},
    "eval_only": [
        "theta", "current H", "session id", "future truth", "intervention oracle"
    ],
    "evidence_with_memory_addition":
        "one provenance-bound past DIRECT damage at training cues 0,0",
    "evidence_without_memory": [
        "current u and v", "known hypothesis family",
        "action costs", "terminal utility",
    ],
    "hazard_function": "H=u xor v xor theta",
    "inspect": {
        "followup": "DIRECT if H=0 else DETOUR",
        "observation": "H",
        "ticks": 1,
    },
    "intervention_count": 18,
    "latent_theta_values": [0, 1],
    "model_call_budget": 0,
    "subject_count": 6,
    "test_cues": [[0, 1], [1, 0], [1, 1]],
    "training": {
        "action": "DIRECT", "cues": [0, 0],
        "observed_damage": "12*theta",
    },
    "utility": "20*reached - ticks - health_loss",
    "version": VERSION,
    "visible_family":
        "hazard depends on u xor v xor one episode-stable unknown bit theta",
}


class D2ContractError(ValueError):
    """Bad or unbound evidence, interventions or frozen source identity."""


@dataclass(frozen=True)
class EpisodeSession:
    """World/evaluator-only hidden state and trustworthy session provenance."""

    session_id: str
    theta: int


@dataclass(frozen=True)
class GroundedEpisode:
    """Prior actual observation with source ID held OUTSIDE model-facing E_t."""

    session_id: str
    u: int
    v: int
    action: str
    health_loss: int


@dataclass(frozen=True)
class Outcome:
    """Interventional counterfactual result; never add to pre-action E_t."""

    action: str
    elapsed_ticks: int
    health_loss: int
    observed_hazard: int | None
    utility: int


def _bit(value: object, label: str) -> int:
    if type(value) is not int or value not in (0, 1):
        raise D2ContractError(f"{label} must be exactly a Boolean bit")
    return value


def _test_cues(value: object) -> tuple[int, int]:
    if (not isinstance(value, tuple) or len(value) != 2
            or value not in TEST_CUES):
        raise D2ContractError("test cue outside frozen unseen-cue set")
    u, v = value
    _bit(u, "u")
    _bit(v, "v")
    return u, v


def session(theta: int) -> EpisodeSession:
    t = _bit(theta, "theta")
    return EpisodeSession(session_id=f"source-T{t}", theta=t)


def _check_session(source: EpisodeSession) -> EpisodeSession:
    if not isinstance(source, EpisodeSession):
        raise D2ContractError("expected evaluation-only EpisodeSession")
    if source != session(source.theta):
        raise D2ContractError("untrusted World session identity")
    return source


def manifest() -> dict[str, object]:
    return deepcopy(_MANIFEST)


def manifest_sha256(value: Mapping[str, object] | None = None) -> str:
    try:
        canonical = json.dumps(
            manifest() if value is None else value,
            sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError, OverflowError) as exc:
        raise D2ContractError("manifest is not canonical JSON") from exc
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def check_manifest(value: Mapping[str, object] | None = None) -> None:
    if manifest_sha256(value) != MANIFEST_SHA256:
        raise D2ContractError("CF-D2 frozen design manifest drift")


def grounded_episode(source: EpisodeSession) -> GroundedEpisode:
    source = _check_session(source)
    return GroundedEpisode(
        session_id=source.session_id,
        u=0, v=0, action="DIRECT",
        health_loss=12 * source.theta,
    )


def _trusted_episode(
    source: EpisodeSession, episode: GroundedEpisode,
) -> GroundedEpisode:
    source = _check_session(source)
    if not isinstance(episode, GroundedEpisode):
        raise D2ContractError("prior episode is not source-qualified")
    if episode != grounded_episode(source):
        raise D2ContractError("prior episode source mismatch or forgery")
    return episode


def predictor_evidence(
    source: EpisodeSession,
    cues: tuple[int, int],
    *,
    include_memory: bool,
    episode: GroundedEpisode | None = None,
) -> dict[str, object]:
    """Make an exact E_t; hidden World state/session never serialized."""
    _check_session(source)
    u, v = _test_cues(cues)
    if type(include_memory) is not bool:
        raise D2ContractError("include_memory must be an explicit bool")
    if include_memory:
        if episode is None:
            raise D2ContractError("missing source-bound historical episode")
        observed = _trusted_episode(source, episode)
        prior_memory: dict[str, object] | None = {
            "u": observed.u, "v": observed.v,
            "action": observed.action,
            "observedHealthLoss": observed.health_loss,
        }
    else:
        if episode is not None:
            raise D2ContractError("unrequested memory cannot be silently added")
        prior_memory = None

    return {
        "cues": {"u": u, "v": v},
        "hypothesisFamily": "H=u xor v xor theta; theta stable unknown bit",
        "priorTheta1": 0.5,
        "priorEpisode": prior_memory,
        "actions": {
            "DIRECT": {"ticks": 2, "healthLoss": "12*H"},
            "DETOUR": {"ticks": 5, "healthLoss": 0},
            "INSPECT": {
                "ticks": 1, "observes": "H",
                "followup": "DIRECT if H=0 else DETOUR",
            },
        },
        "objective": {
            "rewardGoalReached": 20,
            "penaltyPerTick": 1,
            "penaltyPerHealthLoss": 1,
        },
    }


def validate_source_bound_evidence(
    source: EpisodeSession,
    cues: tuple[int, int],
    evidence: object,
    *,
    include_memory: bool,
) -> None:
    """Trusted World/Memory owner must supply the independent source identity.

    Merely checking JSON shape cannot reject plausible evidence from a
    *different* session. This function must never be run as an LLM judge.
    """
    correct = grounded_episode(source) if include_memory else None
    expected = predictor_evidence(
        source, cues, include_memory=include_memory, episode=correct,
    )
    if not isinstance(evidence, dict):
        raise D2ContractError("source-bound evidence must be an object")
    try:
        canonical_actual = json.dumps(
            evidence, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        )
        canonical_expected = json.dumps(
            expected, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        )
    except (TypeError, ValueError, OverflowError) as exc:
        raise D2ContractError("uncanonicalizable evidence") from exc
    if canonical_actual != canonical_expected:
        raise D2ContractError("source-bound evidence mismatch or oracle leakage")


def infer_hazard_probability(
    evidence: object,
    *,
    source: EpisodeSession,
    cues: tuple[int, int],
    include_memory: bool,
) -> Fraction:
    """CHEAP source-matched comparator, not an LLM WorldModel."""
    validate_source_bound_evidence(
        source, cues, evidence, include_memory=include_memory,
    )
    if not include_memory:
        return Fraction(1, 2)
    # Training action DIRECT at u=v=0 has actual damage 12*theta.
    prior_episode = evidence["priorEpisode"]
    observed_damage = prior_episode["observedHealthLoss"]
    inferred_theta = observed_damage // 12
    u, v = _test_cues(cues)
    return Fraction(u ^ v ^ inferred_theta)


def expected_action_utilities(p_hazard: Fraction) -> dict[str, Fraction]:
    if not isinstance(p_hazard, Fraction) or not 0 <= p_hazard <= 1:
        raise D2ContractError("unknown or invalid hazard probability")
    return {
        "DIRECT": 18 - 12 * p_hazard,
        "DETOUR": Fraction(15),
        "INSPECT": 17 - 3 * p_hazard,
    }


def cheap_choice(
    evidence: object,
    *,
    source: EpisodeSession,
    cues: tuple[int, int],
    include_memory: bool,
) -> str:
    p = infer_hazard_probability(
        evidence, source=source, cues=cues, include_memory=include_memory,
    )
    values = expected_action_utilities(p)
    highest = max(values.values())
    candidates = [a for a, utility in values.items() if utility == highest]
    if len(candidates) != 1:
        raise D2ContractError("unresolved choice tie")
    return candidates[0]


def intervene(
    source: EpisodeSession, cues: tuple[int, int], action: str,
) -> Outcome:
    """Separate evaluator-only do(action) from immutable state."""
    source = _check_session(source)
    u, v = _test_cues(cues)
    if type(action) is not str or action not in ACTIONS:
        raise D2ContractError("unknown intervention")
    hazard = u ^ v ^ source.theta
    if action == "DIRECT":
        elapsed, health_loss, observed = 2, 12 * hazard, None
    elif action == "DETOUR":
        elapsed, health_loss, observed = 5, 0, None
    else:
        elapsed, health_loss, observed = 1 + (5 if hazard else 2), 0, hazard
    return Outcome(action, elapsed, health_loss, observed, 20 - elapsed - health_loss)


def all_counterfactuals(
    source: EpisodeSession,
    cues: tuple[int, int],
    order: tuple[str, ...] = ACTIONS,
) -> dict[str, Outcome]:
    """World reset before every separate intervention, never reuse state."""
    _check_session(source)
    _test_cues(cues)
    if (not isinstance(order, tuple) or len(order) != 3
            or any(type(a) is not str for a in order)
            or set(order) != set(ACTIONS)):
        raise D2ContractError("invalid counterfactual action permutation")
    return {a: intervene(session(source.theta), cues, a) for a in order}


def brier_score(p: Fraction, true_hazard: int) -> Fraction:
    if not isinstance(p, Fraction) or not 0 <= p <= 1:
        raise D2ContractError("forecast outside [0,1]")
    h = _bit(true_hazard, "World H")
    return (p - h) ** 2


check_manifest()
