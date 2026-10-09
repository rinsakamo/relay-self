"""AC Lane A: bounded, zero-model, two-epoch epistemic redecision fixture.

Experiment-local only. Not a RelaySelf runtime, Action authority, or LLM qualification.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from fractions import Fraction
from uuid import uuid4

VERSION = "AC-A-EPISTEMIC-TWO-EPOCH-v1"
MANIFEST_SHA256 = "2bf1518d080160ca5c9f8ef2d4784684d60554399eead3cef187dc610af3d1ae"
MANIFEST = {
    "version": VERSION,
    "actions": ["DIRECT", "DETOUR", "OBSERVE"],
    "strategies": ["DIRECT", "DETOUR", "NO_OBSERVE", "SCOUT_SCRIPT", "REDECIDE", "CHEAP_BAYES", "ORACLE"],
    "hypotheses": ["NORMAL", "REVERSE", "ALWAYS_SAFE", "ALWAYS_RISK"],
    "training": "two grounded past DIRECT episodes for signal=0 and signal=1; hazard outcome source-bound",
    "test_signals": [0, 1],
    "signal_prior": "P(signal=0)=P(signal=1)=1/2 is explicitly stipulated fixture mechanics",
    "direct": {"ticks": 2, "damage_if_hazard": 8},
    "detour": {"ticks": 5, "damage": 0},
    "observe": {"ticks": 1, "reveals": "signal only", "max_count": 1},
    "utility": "20 - elapsed_ticks - damage; all paths reach goal",
    "world_lineage": "fresh session per independent intervention; same session, revision 0 -> 1 on OBSERVE",
    "epistemic_policy": "first epoch chooses based on training evidence and observation price; second epoch recomputes DIRECT/DETOUR from new signal",
    "scripted_control": "after OBSERVE: signal=0 -> DIRECT, signal=1 -> DETOUR; not Self redecision",
    "evaluator_only": ["case_id", "true_rule", "test_signal", "current_hazard", "full_information_oracle"],
    "model_visible": ["source_session", "world_revision", "past_grounded_signal_hazard_episodes", "signal_prior", "action_costs", "observed_signal_if_revision_1"],
    "paired_subjects": 8,
    "reference_interventions": 32,
    "scientific_model_calls": 0,
    "claim_ceiling": "deterministic two-epoch redecision + epistemic gain relative to restricted comparators; exact cheap controller matches fully",
}


class ContractError(ValueError):
    """World evidence mismatch, bad stage or illicit action."""


def canonical(data: object) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(data: object = MANIFEST) -> str:
    return hashlib.sha256(canonical(data).encode("utf-8")).hexdigest()


def verify_manifest(data: object = MANIFEST) -> None:
    if digest(data) != MANIFEST_SHA256:
        raise ContractError("manifest drift")


def hazard(rule: str, signal: int) -> int:
    if type(signal) is not int or signal not in (0, 1):
        raise ContractError("bad signal")
    result = {"NORMAL": signal, "REVERSE": 1 - signal, "ALWAYS_SAFE": 0, "ALWAYS_RISK": 1}
    if rule not in result:
        raise ContractError("bad rule")
    return result[rule]


@dataclass(frozen=True)
class Episode:
    source_session: str
    sequence: int
    observed_signal: int
    observed_hazard: int
    action: str = "DIRECT"


@dataclass(frozen=True)
class Evidence:
    source_session: str
    world_revision: int
    episodes: tuple[Episode, ...]
    observed_signal: int | None = None
    observation_event: str | None = None


@dataclass(frozen=True)
class Case:
    case_id: str
    rule: str
    test_signal: int


@dataclass(frozen=True)
class World:
    case: Case  # evaluation-only, never passed to a chooser
    source_session: str
    world_revision: int = 0
    observed_signal: int | None = None
    terminal: bool = False


@dataclass(frozen=True)
class Result:
    strategy: str
    first_action: str
    second_action: str | None
    observation_count: int
    ticks: int
    damage: int
    utility: int
    epoch_count: int
    observation_revision: int | None


def cases() -> tuple[Case, ...]:
    return tuple(
        Case(case_id=f"{rule}_{signal}", rule=rule, test_signal=signal)
        for rule in MANIFEST["hypotheses"] for signal in (0, 1)
    )


def fresh_world(case: Case, intervention: str) -> World:
    if case not in cases():
        raise ContractError("unregistered source case")
    if intervention not in MANIFEST["strategies"]:
        raise ContractError("unregistered intervention")
    return World(case, source_session=f"laneA/{uuid4().hex}")


def _episodes(world: World) -> tuple[Episode, ...]:
    return tuple(
        Episode(world.source_session, i - 2, i, hazard(world.case.rule, i))
        for i in (0, 1)
    )


def project(world: World) -> Evidence:
    if world.terminal:
        raise ContractError("terminal World does not expose a fresh cognition epoch")
    if world.world_revision not in (0, 1):
        raise ContractError("unsupported revision")
    return Evidence(
        world.source_session,
        world.world_revision,
        _episodes(world),
        observed_signal=world.observed_signal,
        observation_event=(f"{world.source_session}/observe/rev1" if world.world_revision == 1 else None),
    )


def validate_source(world: World, evidence: Evidence) -> None:
    if evidence != project(world):
        raise ContractError("source/revision/provenance mismatch")
    _validate_episode_data(evidence)


def _validate_episode_data(evidence: Evidence) -> None:
    if len(evidence.episodes) != 2:
        raise ContractError("incomplete episode history: UNKNOWN")
    if tuple(e.observed_signal for e in evidence.episodes) != (0, 1):
        raise ContractError("insufficient or contradictory signals: UNKNOWN")
    for i, episode in enumerate(evidence.episodes):
        if (
            episode.source_session != evidence.source_session
            or episode.sequence != i - 2
            or episode.action != "DIRECT"
            or type(episode.observed_hazard) is not int
            or episode.observed_hazard not in (0, 1)
        ):
            raise ContractError("invalid source-bound episode")
    if evidence.world_revision == 0 and (
        evidence.observed_signal is not None or evidence.observation_event is not None
    ):
        raise ContractError("future World evidence leaked")
    if evidence.world_revision == 1 and (
        evidence.observed_signal not in (0, 1)
        or evidence.observation_event != f"{evidence.source_session}/observe/rev1"
    ):
        raise ContractError("not a source-bound new observation")


def _learned_mapping(evidence: Evidence) -> tuple[int, int]:
    _validate_episode_data(evidence)
    return evidence.episodes[0].observed_hazard, evidence.episodes[1].observed_hazard


def utilities_before_observation(evidence: Evidence) -> dict[str, Fraction]:
    if evidence.world_revision != 0:
        raise ContractError("not a first epoch")
    h0, h1 = _learned_mapping(evidence)
    p = Fraction(h0 + h1, 2)
    observe = Fraction(sum(max(17 - 8 * h, 14) for h in (h0, h1)), 2)
    return {"DIRECT": 18 - 8 * p, "DETOUR": Fraction(15), "OBSERVE": observe}


def first_epoch(evidence: Evidence, *, allow_observation: bool = True) -> str:
    scores = utilities_before_observation(evidence)
    if not allow_observation:
        scores.pop("OBSERVE")
    max_score = max(scores.values())
    winners = [a for a, u in scores.items() if u == max_score]
    if len(winners) != 1:
        raise ContractError("UNKNOWN: ambiguous first-epoch action")
    return winners[0]


def observe(world: World, evidence: Evidence) -> tuple[World, Evidence]:
    validate_source(world, evidence)
    if world.world_revision != 0:
        raise ContractError("OBSERVE replay/second observation")
    next_world = replace(world, world_revision=1, observed_signal=world.case.test_signal)
    next_evidence = project(next_world)
    validate_source(next_world, next_evidence)
    return next_world, next_evidence


def second_epoch(evidence: Evidence) -> str:
    _validate_episode_data(evidence)
    if evidence.world_revision != 1:
        raise ContractError("not second epoch")
    mapping = _learned_mapping(evidence)
    assert evidence.observed_signal is not None
    estimated_hazard = mapping[evidence.observed_signal]
    return "DIRECT" if (17 - 8 * estimated_hazard) > 14 else "DETOUR"


def finish(world: World, evidence: Evidence, action: str) -> tuple[World, tuple[int, int, int]]:
    validate_source(world, evidence)
    if action not in ("DIRECT", "DETOUR"):
        raise ContractError("only bounded terminating actions")
    ticks = 2 if action == "DIRECT" else 5
    damage = 8 * hazard(world.case.rule, world.case.test_signal) if action == "DIRECT" else 0
    result = (ticks, damage, 20 - ticks - damage)
    return replace(world, terminal=True), result


def execute(case: Case, strategy: str) -> Result:
    verify_manifest()
    world = fresh_world(case, strategy)
    e0 = project(world)
    validate_source(world, e0)
    if strategy in ("DIRECT", "DETOUR"):
        first = strategy
    elif strategy == "NO_OBSERVE":
        first = first_epoch(e0, allow_observation=False)
    elif strategy in ("REDECIDE", "CHEAP_BAYES"):
        first = first_epoch(e0)
    elif strategy == "SCOUT_SCRIPT":
        first = "OBSERVE"
    elif strategy == "ORACLE":
        first = "DIRECT" if hazard(case.rule, case.test_signal) == 0 else "DETOUR"
    else:
        raise ContractError("unsupported strategy")
    if first != "OBSERVE":
        _, (ticks, damage, utility) = finish(world, e0, first)
        return Result(strategy, first, None, 0, ticks, damage, utility, 1, None)
    world, e1 = observe(world, e0)
    if strategy == "SCOUT_SCRIPT":
        second = "DIRECT" if e1.observed_signal == 0 else "DETOUR"
    else:
        second = second_epoch(e1)
    _, (tail_ticks, damage, _) = finish(world, e1, second)
    ticks = 1 + tail_ticks
    return Result(strategy, first, second, 1, ticks, damage, 20 - ticks - damage, 2, 1)


def intervention_matrix(case: Case, ordering: tuple[str, ...] | None = None) -> dict[str, Result]:
    order = ordering or tuple(MANIFEST["strategies"])
    if len(order) != len(MANIFEST["strategies"]) or set(order) != set(MANIFEST["strategies"]):
        raise ContractError("invalid intervention set")
    return {strategy: execute(case, strategy) for strategy in order}


def four_world_interventions(case: Case, ordering: tuple[str, ...] | None = None) -> dict[str, Result]:
    """Reference action interventions: DIRECT, DETOUR, scripted, genuine 2-epoch redecision."""
    order = ordering or ("DIRECT", "DETOUR", "SCOUT_SCRIPT", "REDECIDE")
    if len(order) != 4 or set(order) != {"DIRECT", "DETOUR", "SCOUT_SCRIPT", "REDECIDE"}:
        raise ContractError("invalid four-intervention set")
    return {strategy: execute(case, strategy) for strategy in order}


def expected_utility(rule: str, strategy: str) -> Fraction:
    return Fraction(sum(execute(Case(f"{rule}_{s}", rule, s), strategy).utility for s in (0, 1)), 2)
