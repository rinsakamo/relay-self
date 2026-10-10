"""E2 offline seam: existing main Present and Action owners, not S18+ runtime.

The fixture World is evaluator-owned. This module creates NO new Self owner, semantic
scheduler, physical Mineflayer Action or model call. No unmerged E1 imports.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from fractions import Fraction
from uuid import uuid4

from experiments.present_skill_epoch import (
    PresentFact,
    PresentProjection,
    build_present,
    projection_is_current,
)
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution

VERSION = "AC-A-E2-MAIN-CONTRACT-SEAM-v1"
MANIFEST_SHA256 = "2b39188164f2a900332f7d2b3bd182043357e6779342a4173f79810b9e611a77"
MANIFEST = {
    "version": VERSION,
    "base_main": "4348a614900c1d0828581a8eec2c523ba5ae237f",
    "e1_head": "f013d1b407dccff8d927899a98ba7dbfc9e40a4b",
    "rules": ["NORMAL", "REVERSE", "ALWAYS_SAFE", "ALWAYS_RISK"],
    "signals": [0, 1],
    "reference_arms": ["DIRECT", "DETOUR", "SCOUT_SCRIPT", "REDECIDE"],
    "comparison_arms": ["NO_OBSERVE", "CHEAP_BAYES"],
    "direct": {"ticks": 2, "damage_if_hazard": 8},
    "detour": {"ticks": 5, "damage": 0},
    "observe": {"ticks": 1, "reveals": "signal", "max_count": 1,
                "mode": "source projection, not Action"},
    "prior": "P(signal=0)=P(signal=1)=1/2",
    "history": "two simulated source-bound DIRECT outcomes (signals 0 and 1)",
    "utility": "20 - ticks - damage",
    "physical_action": "main IntentCommitment, SkillExecution, ActionLifecycle, "
                       "ActionSupervisor; explicit test authorization",
    "evidence": "existing PresentProjection with source/revision checks; "
                "E1 independent observation event",
    "claims": "offline main-contract seam only; NOT S18+ runtime/cognition/physical qualification",
    "model_calls": 0,
    "physical_minecraft_actions": 0,
}


class ContractError(ValueError):
    """Fail closed on stale, forged, ambiguous, or unauthorized fixture requests."""


def manifest_digest(manifest: object = MANIFEST) -> str:
    raw = json.dumps(manifest, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def verify_manifest() -> None:
    if manifest_digest() != MANIFEST_SHA256:
        raise ContractError("frozen E2 manifest drift")


def hazard(rule: str, signal: int) -> int:
    if type(signal) is not int or signal not in (0, 1):
        raise ContractError("UNKNOWN: invalid signal")
    mapping = {"NORMAL": signal, "REVERSE": 1 - signal,
               "ALWAYS_SAFE": 0, "ALWAYS_RISK": 1}
    if rule not in mapping:
        raise ContractError("UNKNOWN: invalid hidden rule")
    return mapping[rule]


@dataclass(frozen=True, slots=True)
class Case:
    rule: str
    signal: int


@dataclass(frozen=True, slots=True)
class Decision:
    action: str
    session: str
    revision: int


@dataclass(frozen=True, slots=True)
class Forecast:
    action: str
    probability_hazard: Fraction
    expected_ticks: Fraction
    expected_utility: Fraction
    horizon: int


@dataclass(frozen=True, slots=True)
class Result:
    strategy: str
    rule: str  # evaluator-only result, never projected to Present
    test_signal: int  # evaluator-only
    first_action: str
    second_action: str | None
    observation_count: int
    epoch_count: int
    action_history: tuple[ActionState, ...]
    ticks: int
    damage: int
    utility: int
    prediction_brier_e0: Fraction
    prediction_brier_e1: Fraction | None
    net_expected_information_value: Fraction
    source_revision_at_action: int
    open_actions_after: int
    source_session: str = ""
    handoff: EvidenceHandoff | None = None
    model_calls: int = 0


@dataclass(frozen=True, slots=True)
class EvidenceHandoff:
    """Read-only Lane B/C proposal, NOT a Memory commit or Action receipt."""

    source: str
    world_revision: int
    observed_present: tuple[PresentFact, ...]
    action_candidates: tuple[str, ...]
    conditional_predictions: tuple[Forecast, ...]
    selected_action: str
    information_acquired: bool
    observed_outcome: tuple[int, int]  # ticks, damage; actually observed only
    prediction_error: Fraction | None  # unobserved hazard on DETOUR stays UNKNOWN
    uncertainty: Fraction  # source-matched Bernoulli variance, not oracle confidence
    observe_ticks: int
    total_world_ticks: int
    model_calls: int


class FixtureWorld:
    """Single-test evaluator World; cannot attest to real physical World truth."""

    def __init__(self, case: Case) -> None:
        if case not in cases():
            raise ContractError("UNKNOWN: unregistered case")
        self.case = case
        self.session = "e2/" + uuid4().hex
        self.revision = 0
        self.observed_signal: int | None = None
        self.terminal = False
        self.observe_count = 0
        self.supervisor = ActionSupervisor()
        self.intent = IntentCommitment()
        self.intent.commit(
            "intent-" + self.session, objective="reach goal", at_ns=1,
            provenance=Provenance("fixture.intent", self.session + "/commit"),
        )

    def project(self) -> PresentProjection:
        if self.terminal:
            raise ContractError("terminal World cannot project another epoch")
        facts = [
            PresentFact(
                "source_session", self.session,
                Provenance("fixture.world", self.session + "/source"),
            ),
            PresentFact(
                "prior", (Fraction(1, 2), Fraction(1, 2)),
                Provenance("fixture.prior", "binary-uniform-v1"),
            ),
        ]
        for signal in (0, 1):
            facts.append(PresentFact(
                "history:" + str(signal), hazard(self.case.rule, signal),
                Provenance("fixture.world", self.session + "/past-direct/" + str(signal)),
            ))
        if self.revision == 1:
            facts.extend((
                PresentFact(
                    "observed_signal", self.observed_signal,
                    Provenance("fixture.world", self.session + "/observe/rev1/value"),
                ),
                PresentFact(
                    "observation_event", self.session + "/observe/rev1",
                    Provenance("fixture.world", self.session + "/observe/rev1/event"),
                ),
            ))
        return build_present(
            intent_commitment=self.intent, source_revision=self.revision, facts=facts,
        )

    def validate(self, present: PresentProjection) -> None:
        if not isinstance(present, PresentProjection):
            raise ContractError("UNKNOWN: Present type mismatch")
        if not projection_is_current(
            present, current_source_revision=self.revision,
        ) or present != self.project():
            raise ContractError("UNKNOWN: stale or forged source/revision/intent evidence")

    def observe(self, present: PresentProjection) -> PresentProjection:
        self.validate(present)
        if self.revision != 0 or self.observe_count != 0:
            raise ContractError("UNKNOWN: duplicate OBSERVE")
        # Existing read-only projection pattern; no ActionLifecycle or issue created.
        self.revision = 1
        self.observed_signal = self.case.signal
        self.observe_count = 1
        return self.project()

    def execute_terminal(
        self, present: PresentProjection, decision: Decision,
    ) -> tuple[int, int, tuple[ActionState, ...]]:
        self.validate(present)
        if (
            decision.session != self.session
            or decision.revision != self.revision
            or decision.action not in ("DIRECT", "DETOUR")
        ):
            raise ContractError("UNKNOWN: stale or unapproved terminal candidate")
        if self.supervisor.open_actions:
            raise ContractError("UNKNOWN: conflicting in-flight Action")
        proof = Provenance("fixture.e2", self.session + "/rev" + str(self.revision))
        skill = SkillExecution.start(
            "skill-" + self.session, skill_id="E2_GOAL",
            intent_commitment=self.intent, at_ns=2, provenance=proof,
        )
        proposed = ActionLifecycle.propose(
            "action-" + self.session, skill_execution=skill,
            intent_commitment=self.intent, at_ns=3, provenance=proof,
        )
        # Explicit authorization from a TEST caller; no bypass of ActionLifecycle.
        authorized = proposed.authorize(
            at_ns=4, provenance=proof, authority="e2-explicit-fixture-authorization",
        )
        self.supervisor.issue(
            authorized, at_ns=5, deadline_ns=20, provenance=proof,
        )
        ticks = 2 if decision.action == "DIRECT" else 5
        damage = (
            8 * hazard(self.case.rule, self.case.signal)
            if decision.action == "DIRECT" else 0
        )
        self.supervisor.record_outcome(
            proposed.action_id, at_ns=6, provenance=proof,
        )
        self.terminal = True
        closed = self.supervisor.get(proposed.action_id)
        return ticks, damage, tuple(event.state for event in closed.events)


def cases() -> tuple[Case, ...]:
    return tuple(Case(rule, signal) for rule in MANIFEST["rules"] for signal in (0, 1))


def _history(present: PresentProjection) -> tuple[int, int]:
    if present.objective != "reach goal" or present.fact("source_session") is None:
        raise ContractError("UNKNOWN: wrong Present objective/source")
    prior = present.fact("prior")
    if prior is None or prior.value != (Fraction(1, 2), Fraction(1, 2)):
        raise ContractError("UNKNOWN: source prior unavailable")
    values: list[int] = []
    for i in (0, 1):
        fact = present.fact("history:" + str(i))
        if fact is None or type(fact.value) is not int or fact.value not in (0, 1):
            raise ContractError("UNKNOWN: insufficient source history")
        values.append(fact.value)
    return values[0], values[1]


def forecast(world: FixtureWorld, present: PresentProjection) -> tuple[Forecast, ...]:
    """Action-conditioned *hypotheses*, not World-observed outcomes."""
    world.validate(present)
    h = _history(present)
    if present.source_revision == 0:
        p = Fraction(sum(h), 2)
        observe_expected = Fraction(sum(max(17 - 8 * x, 14) for x in h), 2)
        return (
            Forecast("DIRECT", p, Fraction(2), 18 - 8 * p, 1),
            Forecast("DETOUR", Fraction(0), Fraction(5), Fraction(15), 1),
            Forecast("OBSERVE", p, Fraction(1), observe_expected, 2),
        )
    if present.source_revision != 1:
        raise ContractError("UNKNOWN: unsupported temporal horizon")
    signal = present.fact("observed_signal")
    event = present.fact("observation_event")
    if (
        signal is None or type(signal.value) is not int or signal.value not in (0, 1)
        or event is None or event.value != world.session + "/observe/rev1"
    ):
        raise ContractError("UNKNOWN: missing source-bound observation event")
    p = Fraction(h[signal.value])
    return (
        Forecast("DIRECT", p, Fraction(2), 18 - 8 * p, 1),
        Forecast("DETOUR", Fraction(0), Fraction(5), Fraction(15), 1),
    )


def choose_first(
    world: FixtureWorld, present: PresentProjection, *, allow_observe: bool = True,
) -> Decision:
    if present.source_revision != 0:
        raise ContractError("UNKNOWN: first epoch requires revision 0")
    options = forecast(world, present)
    if not allow_observe:
        options = options[:2]
    best = max(x.expected_utility for x in options)
    winners = [x.action for x in options if x.expected_utility == best]
    if len(winners) != 1:
        raise ContractError("UNKNOWN: tied actions")
    return Decision(winners[0], world.session, 0)


def choose_second(world: FixtureWorld, present: PresentProjection) -> Decision:
    if present.source_revision != 1:
        raise ContractError("UNKNOWN: second epoch requires revision 1")
    options = forecast(world, present)
    best = max(x.expected_utility for x in options)
    winners = [x.action for x in options if x.expected_utility == best]
    if len(winners) != 1:
        raise ContractError("UNKNOWN: tied actions")
    return Decision(winners[0], world.session, 1)


def expected_information_value(world: FixtureWorld, present: PresentProjection) -> Fraction:
    scores = forecast(world, present)
    if present.source_revision != 0:
        raise ContractError("UNKNOWN: information value defined only at E0")
    return scores[2].expected_utility - max(scores[0].expected_utility,
                                               scores[1].expected_utility)


def run(case: Case, strategy: str) -> Result:
    verify_manifest()
    if strategy not in MANIFEST["reference_arms"] + MANIFEST["comparison_arms"]:
        raise ContractError("UNKNOWN: unsupported strategy")
    world = FixtureWorld(case)
    e0 = world.project()
    e0_forecast = forecast(world, e0)
    p0 = e0_forecast[0].probability_hazard
    brier0 = (p0 - hazard(case.rule, case.signal)) ** 2
    information_value = expected_information_value(world, e0)
    if strategy in ("DIRECT", "DETOUR"):
        first = Decision(strategy, world.session, 0)
    elif strategy == "SCOUT_SCRIPT":
        first = Decision("OBSERVE", world.session, 0)
    else:
        first = choose_first(
            world, e0, allow_observe=strategy != "NO_OBSERVE",
        )
    tail: Decision | None = None
    brier1: Fraction | None = None
    latest = e0
    if first.action == "OBSERVE":
        latest = world.observe(e0)
        # E0 selection is now stale: there MUST be a fresh decision from E1.
        if strategy == "SCOUT_SCRIPT":
            observation = latest.fact("observed_signal")
            assert observation is not None
            label = "DIRECT" if observation.value == 0 else "DETOUR"
            tail = Decision(label, world.session, latest.source_revision)
        else:
            tail = choose_second(world, latest)
        p1 = forecast(world, latest)[0].probability_hazard
        brier1 = (p1 - hazard(case.rule, case.signal)) ** 2
    final = tail or first
    action_revision = latest.source_revision
    # Capture source-verified projection and hypotheses BEFORE World is terminal.
    qualified_predictions = forecast(world, latest)
    prior_p = qualified_predictions[0].probability_hazard
    duration, damage, history = world.execute_terminal(latest, final)
    ticks = duration + world.observe_count
    handoff = EvidenceHandoff(
        source=world.session,
        world_revision=action_revision,
        observed_present=latest.facts,
        action_candidates=tuple(f.action for f in qualified_predictions),
        conditional_predictions=qualified_predictions,
        selected_action=final.action,
        information_acquired=world.observe_count == 1,
        observed_outcome=(duration, damage),
        prediction_error=(prior_p - Fraction(int(damage > 0))) ** 2
        if final.action == "DIRECT" else None,
        uncertainty=prior_p * (1 - prior_p),
        observe_ticks=world.observe_count,
        total_world_ticks=ticks,
        model_calls=0,
    )
    return Result(
        strategy, case.rule, case.signal, first.action,
        tail.action if tail is not None else None, world.observe_count,
        1 + world.observe_count, history, ticks, damage, 20 - ticks - damage,
        brier0, brier1, information_value, action_revision,
        len(world.supervisor.open_actions), source_session=world.session, handoff=handoff,
    )


def expected_utility(rule: str, strategy: str) -> Fraction:
    if rule not in MANIFEST["rules"]:
        raise ContractError("UNKNOWN: unsupported rule")
    return Fraction(sum(run(Case(rule, s), strategy).utility for s in (0, 1)), 2)



def exported_episode(result: Result) -> EvidenceHandoff:
    if result.handoff is None or result.source_session != result.handoff.source:
        raise ContractError("UNKNOWN: no source-bound recorded episode")
    return result.handoff
