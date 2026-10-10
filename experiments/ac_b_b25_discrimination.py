"""B25: an ACTUALLY ISSUED unseen Action separates a GIVEN 2-model bank.

B24's identical 11 training outcomes underdetermine NORMAL vs TWIN.
One novel real simulator Action success/failure updates a prespecified
hypothesis bank; a cheap one-bit model shares exactly the same hypotheses,
source receipts and decisions. The second family is EXPERIMENTER-SUPPLIED.
No actual LLM L2, Minecraft, production S11 or model discovery.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from experiments.ac_b_b11_governed_habit import empty_repertoire
from experiments.ac_b_b24_structural_transfer import (
    ANCHORS,
    HELDOUT,
    Episode,
    StructuralAgent,
    StructuralWorld,
    WorldAction,
    apply_degree2,
    validate_cue,
)

CANDIDATES = ("H0_DEG2", "H1_HIGHER_ORDER")
WORLDS = ("NORMAL", "TWIN")
ARMS = ("FULL_HYPOTHESIS_S11", "CHEAP_HYPOTHESIS_BIT", "FIXED_DEG2", "FLAT_TAG")
FIRST_PROBE = HELDOUT[0]


class InvalidHypothesisEvidence(ValueError):
    """A source result or candidate revision cannot support the requested inference."""


def known_residual(cue: tuple[int, int, int, int]) -> int:
    """EXPERIMENTER-GIFTED higher-order interaction, not inferred from training."""
    a, b, c, d = validate_cue(cue)
    return (
        (a & b & c) ^ (a & b & d) ^ (a & c & d)
        ^ (b & c & d) ^ (a & b & c & d)
    )


def predict(
    coefficients: tuple[int, ...],
    cue: tuple[int, int, int, int],
    candidate: str,
) -> int:
    if candidate not in CANDIDATES:
        raise InvalidHypothesisEvidence("candidate not in frozen hypothesis bank")
    base = apply_degree2(coefficients, validate_cue(cue))
    return base ^ (
        known_residual(cue) if candidate == "H1_HIGHER_ORDER" else 0
    )


@dataclass(frozen=True, slots=True)
class DiscriminatingUpdate:
    event_id: str
    cue: tuple[int, int, int, int]
    actual_action: int
    source_succeeded: bool
    before: tuple[str, ...]
    after: tuple[str, ...]


@dataclass(slots=True)
class HypothesisState:
    """Local finite-model selection, NOT native LLM reasoning."""

    candidates: tuple[str, ...] = CANDIDATES
    updates: list[DiscriminatingUpdate] = field(default_factory=list)

    def observe(
        self,
        agent: StructuralAgent,
        receipt: WorldAction,
    ) -> DiscriminatingUpdate:
        if (
            agent.arm != "STRUCTURAL_S11"
            or not agent.world.observed(receipt)
            or not agent.memory
            or agent.memory[-1].original_action is not receipt
            or agent.memory[-1].phase != "NOVEL"
            or agent.model is None
        ):
            raise InvalidHypothesisEvidence(
                "model elimination requires the latest original observed novel Memory Action"
            )
        before = self.candidates
        if not before:
            raise InvalidHypothesisEvidence("no remaining hypothesis")
        survivors = tuple(
            candidate for candidate in before
            if (predict(agent.model, receipt.cue, candidate) == receipt.action)
            == receipt.succeeded
        )
        if not survivors:
            raise InvalidHypothesisEvidence(
                "actual World outcome contradicts both predeclared hypotheses"
            )
        if not set(survivors).issubset(before):
            raise InvalidHypothesisEvidence("hypothesis set cannot grow without evidence")
        update = DiscriminatingUpdate(
            event_id=receipt.event_id, cue=receipt.cue,
            actual_action=receipt.action, source_succeeded=receipt.succeeded,
            before=before, after=survivors,
        )
        self.candidates = survivors
        self.updates.append(update)
        return update


@dataclass(slots=True)
class B25CognitiveArm:
    """Wrap B24's original ACTUAL World + Memory + native S11 owner."""

    policy: str
    agent: StructuralAgent
    hypotheses: HypothesisState = field(default_factory=HypothesisState)
    cheap_mode: str | None = None
    discriminating_event: str | None = None
    first_probe_correct: bool | None = None
    novel_choice_trace: list[tuple[tuple[int, int, int, int], int]] = field(
        default_factory=list
    )

    def __post_init__(self) -> None:
        if (
            self.policy not in ARMS
            or not isinstance(self.agent, StructuralAgent)
            or self.agent.world.actions_executed != 0
            or self.agent.memory
            or self.agent.episodes
        ):
            raise InvalidHypothesisEvidence(
                "B25 requires exact fresh originally issued source World"
            )
        wanted = (
            "STRUCTURAL_S11" if self.policy == "FULL_HYPOTHESIS_S11"
            else "FLAT_TAG" if self.policy == "FLAT_TAG"
            else "CHEAP_DEG2"
        )
        if self.agent.arm != wanted:
            raise InvalidHypothesisEvidence("frozen S11/cheap source arm mismatch")

    def learn_from_world(self) -> None:
        for i, cue in enumerate(ANCHORS):
            self.agent.encounter(cue, "TRAIN", f"b25-train-{i}")
        if self.agent.world.actions_executed != 16:
            raise InvalidHypothesisEvidence("11 completed source anchors required")
        self.agent.learn_structure()
        if self.policy != "FLAT_TAG" and self.agent.model is None:
            raise InvalidHypothesisEvidence("source-verified degree2 coefficients missing")

    def _select_novel(
        self, cue: tuple[int, int, int, int],
    ) -> int:
        if cue not in HELDOUT or self.agent.model is None:
            raise InvalidHypothesisEvidence("unseen relevant hypothesis cue required")
        if self.policy == "FULL_HYPOTHESIS_S11":
            remaining = self.hypotheses.candidates
            if not remaining:
                raise InvalidHypothesisEvidence("unresolved out-of-bank source outcome")
            # Before the first actual discriminating report, both models are
            # still viable. Use H0 as preregistered tie-break.
            return predict(self.agent.model, cue, remaining[0])
        if self.policy == "CHEAP_HYPOTHESIS_BIT":
            return predict(
                self.agent.model, cue,
                self.cheap_mode or "H0_DEG2",
            )
        raise InvalidHypothesisEvidence("only two model-updating arms")

    def _update_after_source(
        self,
        cue: tuple[int, int, int, int],
        observed: WorldAction,
    ) -> None:
        if (
            not self.agent.world.observed(observed)
            or not self.agent.memory
            or self.agent.memory[-1].original_action is not observed
            or self.agent.memory[-1].phase != "NOVEL"
            or observed.cue != cue
        ):
            raise InvalidHypothesisEvidence("cannot learn without latest actual Memory")
        if self.policy == "FULL_HYPOTHESIS_S11":
            self.hypotheses.observe(self.agent, observed)
        else:
            if self.policy != "CHEAP_HYPOTHESIS_BIT":
                raise InvalidHypothesisEvidence("only cheap two-hypothesis update")
            if self.discriminating_event is None:
                if cue != FIRST_PROBE or self.agent.model is None:
                    raise InvalidHypothesisEvidence("first source probe not issued")
                base = predict(self.agent.model, cue, "H0_DEG2")
                if observed.action != base:
                    raise InvalidHypothesisEvidence("first observation not H0 probe")
                if predict(self.agent.model, cue, "H1_HIGHER_ORDER") == base:
                    raise InvalidHypothesisEvidence("first probe cannot discriminate")
                self.cheap_mode = (
                    "H0_DEG2" if observed.succeeded else "H1_HIGHER_ORDER"
                )
            else:
                if observed.succeeded != (
                    observed.action == predict(
                        self.agent.model, cue, self.cheap_mode
                    )
                ):
                    raise InvalidHypothesisEvidence(
                        "subsequent observation contradicts selected cheap hypothesis"
                    )

    def novel_encounter(
        self, cue: tuple[int, int, int, int], number: int,
    ) -> Episode:
        if self.policy not in ARMS[:2] or cue != HELDOUT[number]:
            raise InvalidHypothesisEvidence("novel hypotheses must follow frozen order")
        trial_id = f"b25-unseen-{number}"
        if self.agent._known_action(cue, trial_id) is not None:
            raise InvalidHypothesisEvidence("heldout cue was already experienced")
        first_action = self._select_novel(cue)
        first = self.agent.world.act(cue, first_action)
        self.agent._remember("NOVEL", cue, trial_id, first)
        self._update_after_source(cue, first)
        if self.discriminating_event is None:
            self.discriminating_event = first.event_id
            self.first_probe_correct = first.succeeded
        observed = [first]
        if not first.succeeded:
            second = self.agent.world.act(cue, 1 - first_action)
            self.agent._remember("NOVEL", cue, trial_id, second)
            self._update_after_source(cue, second)
            observed.append(second)
            if not second.succeeded:
                raise InvalidHypothesisEvidence("no original recovered successful Action")
        self.agent._retain(cue, observed[-1])
        item = Episode(
            phase="NOVEL", cue=cue, trial_id=trial_id,
            first_action=first_action,
            attempts=tuple(x.action for x in observed),
            original_event_ids=tuple(x.event_id for x in observed),
            first_correct=first.succeeded,
            confirmed_success=observed[-1].succeeded,
            used_cached_L1=False,
        )
        self.agent.episodes.append(item)
        self.agent.new_relevant_predictions += 1
        self.novel_choice_trace.append((cue, first_action))
        return item

    def run(self) -> dict[str, object]:
        self.learn_from_world()
        examples = self.agent.completed_training_examples()
        if self.policy in ARMS[:2]:
            for index, cue in enumerate(HELDOUT):
                self.novel_encounter(cue, index)
        else:
            for index, cue in enumerate(HELDOUT):
                self.agent.encounter(cue, "NOVEL", f"b25-unseen-{index}")
        for index, cue in enumerate(HELDOUT):
            self.agent.encounter(cue, "REPLAY", f"b25-replay-{index}")
        if self.agent.world.actions_executed != len(self.agent.memory):
            raise InvalidHypothesisEvidence("issued Actions and original source Memory differ")
        if any(
            not self.agent.world.observed(x.original_action)
            for x in self.agent.memory
        ):
            raise InvalidHypothesisEvidence("fabricated or missing original Memory receipt")
        n = [x for x in self.agent.episodes if x.phase == "NOVEL"]
        replay = [x for x in self.agent.episodes if x.phase == "REPLAY"]
        if len(n) != 5 or len(replay) != 5 or len(self.agent.episodes) != 21:
            raise InvalidHypothesisEvidence("complete training/new/replay encounters missing")
        return {
            "policy": self.policy,
            "actual_world_actions": self.agent.world.actions_executed,
            "training_action_attempts": sum(
                len(x.attempts) for x in self.agent.episodes if x.phase == "TRAIN"
            ),
            "first_novel_correct": sum(x.first_correct for x in n),
            "first_novel_actions": sum(len(x.attempts) for x in n),
            "replay_actions": sum(len(x.attempts) for x in replay),
            "completed_successful_encounters": sum(
                x.confirmed_success for x in self.agent.episodes
            ),
            "memory_events": len(self.agent.memory),
            "trained_examples": examples,
            "coefficients": self.agent.model,
            "first_novel_choices": tuple(x.first_action for x in n),
            "first_novel_truth": tuple(x.first_correct for x in n),
            "source_discriminating_event": self.discriminating_event,
            "first_probe_correct": self.first_probe_correct,
            "surviving_structural_candidates": (
                self.hypotheses.candidates
                if self.policy == "FULL_HYPOTHESIS_S11" else ()
            ),
            "cheap_one_bit_selection": self.cheap_mode,
            "native_S11_revision": self.agent.owner.revision,
            "native_S11_rules": len(self.agent.owner.rules),
            "reused_cached_L1_on_replay": all(x.used_cached_L1 for x in replay),
            "decision_trace": tuple(
                (x.phase, x.cue, x.first_action, x.attempts, x.first_correct)
                for x in self.agent.episodes
            ),
        }


def execute_arm(world_kind: str, policy: str) -> tuple[B25CognitiveArm, dict[str, object]]:
    if world_kind not in WORLDS or policy not in ARMS:
        raise InvalidHypothesisEvidence("only prospectively frozen source World/arm")
    source = StructuralWorld(
        session=f"b25-{world_kind.lower()}-{policy.lower()}",
        twin=world_kind == "TWIN",
    )
    native = (
        "STRUCTURAL_S11" if policy == "FULL_HYPOTHESIS_S11"
        else "FLAT_TAG" if policy == "FLAT_TAG"
        else "CHEAP_DEG2"
    )
    agent = StructuralAgent(
        arm=native, world=source,
        owner=empty_repertoire(
            f"b25-{world_kind.lower()}-{policy.lower()}-original-s11"
        ),
    )
    runner = B25CognitiveArm(policy, agent)
    return runner, runner.run()


def run_b25_comparison() -> dict[str, object]:
    reports = {
        (world, arm): execute_arm(world, arm)[1]
        for world in WORLDS for arm in ARMS
    }
    return {
        "classification": "B25_CONDITIONAL_SOURCE_DISCRIMINATION_CHEAP_ONE_BIT_NULL",
        "reports": reports,
        "total_independent_sim_world_actions": sum(
            x["actual_world_actions"] for x in reports.values()
        ),
        "training_experiences_identical_between_worlds": all(
            reports["NORMAL", arm]["trained_examples"]
            == reports["TWIN", arm]["trained_examples"]
            for arm in ARMS
        ),
        "full_hypothesis_and_cheap_bit_exact_source_parity": all(
            reports[world, "FULL_HYPOTHESIS_S11"]["decision_trace"]
            == reports[world, "CHEAP_HYPOTHESIS_BIT"]["decision_trace"]
            for world in WORLDS
        ),
        "candidate_bank_exogenously_gifted": True,
        "actual_LLM_L2_run": False,
        "physical_Minecraft_or_S17": False,
        "production_S11_acquired": False,
        "security_B22_used": False,
    }
