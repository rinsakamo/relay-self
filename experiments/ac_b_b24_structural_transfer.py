"""B24: ACTUAL offline World actions and structural prediction on NEW relevant cues.

A generic degree-2 GF(2) Gaussian solver is a *non-LLM L2-like surrogate*.
An equally supplied cheap finite-difference rule learner shares its bias.
An adversarial counterworld has EXACT SAME 11 original training outcomes
but reverses ALL five genuinely new relevant heldout cue labels.

Never interpret successful toy transfer as actual L2/LLM reasoning, real
Minecraft source evidence, or production S11 acquisition.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations, product

from experiments.ac_b_b11_governed_habit import empty_repertoire
from relay_self.habit import (
    CueFeature,
    HabitCue,
    HabitRepertoire,
    HabitRule,
    HabitSelectionStatus,
    select_habit,
)
from relay_self.provenance import Provenance

Cue4 = tuple[int, int, int, int]
FIELDS = ("a", "b", "c", "d")
PAIRS = tuple(combinations(range(4), 2))
ANCHORS: tuple[Cue4, ...] = tuple(
    cue for cue in product((0, 1), repeat=4) if sum(cue) <= 2
)
HELDOUT: tuple[Cue4, ...] = tuple(
    cue for cue in product((0, 1), repeat=4) if sum(cue) >= 3
)
ARMS = ("STRUCTURAL_S11", "CHEAP_DEG2", "FLAT_TAG")
WORLDS = ("NORMAL", "TWIN")


class InvalidStructuralExperience(ValueError):
    """No valid source experience or bounded unambiguous relational solution."""


def validate_cue(cue: object) -> Cue4:
    if not isinstance(cue, tuple) or len(cue) != 4 or any(
        type(v) is not int or v not in (0, 1) for v in cue
    ):
        raise InvalidStructuralExperience("four original binary relevant cues required")
    return cue


@dataclass(frozen=True, slots=True)
class WorldAction:
    event_id: str
    source_session: str
    cue: Cue4
    action: int
    succeeded: bool


@dataclass(slots=True)
class StructuralWorld:
    session: str
    twin: bool
    _issued: dict[str, WorldAction] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.session or type(self.twin) is not bool:
            raise InvalidStructuralExperience("exact offline World session and law required")

    @staticmethod
    def _goal(cue: Cue4, twin: bool) -> int:
        a, b, c, d = validate_cue(cue)
        base = a ^ b ^ c ^ d ^ (a & b)
        if not twin:
            return base
        triple = (
            (a & b & c) ^ (a & b & d) ^ (a & c & d) ^ (b & c & d)
        )
        return base ^ triple ^ (a & b & c & d)

    def act(self, cue: Cue4, action: int) -> WorldAction:
        cue = validate_cue(cue)
        if type(action) is not int or action not in (0, 1):
            raise InvalidStructuralExperience("executed Action must be binary")
        event_id = f"{self.session}:actual-event:{len(self._issued) + 1}"
        result = WorldAction(
            event_id, self.session, cue, action,
            action == self._goal(cue, self.twin),
        )
        self._issued[event_id] = result
        return result

    def observed(self, receipt: WorldAction) -> bool:
        return (
            isinstance(receipt, WorldAction)
            and self._issued.get(receipt.event_id) is receipt
            and receipt.source_session == self.session
        )

    @property
    def actions_executed(self) -> int:
        return len(self._issued)


@dataclass(frozen=True, slots=True)
class Experience:
    phase: str
    cue: Cue4
    original_action: WorldAction
    trial_id: str


@dataclass(frozen=True, slots=True)
class Episode:
    phase: str
    cue: Cue4
    trial_id: str
    first_action: int
    attempts: tuple[int, ...]
    original_event_ids: tuple[str, ...]
    first_correct: bool
    confirmed_success: bool
    used_cached_L1: bool


def _terms(cue: Cue4) -> tuple[int, ...]:
    cue = validate_cue(cue)
    return (1, *cue, *(cue[i] & cue[j] for i, j in PAIRS))


def infer_degree2_gaussian(examples: tuple[tuple[Cue4, int], ...]) -> tuple[int, ...]:
    """General 11-variable GF2 elimination, not a canned explicit XOR truth."""
    if len(examples) != 11 or {cue for cue, _ in examples} != set(ANCHORS):
        raise InvalidStructuralExperience("all 11 distinct source-tested anchors required")
    rows: list[list[int]] = []
    for cue, result in examples:
        if type(result) is not int or result not in (0, 1):
            raise InvalidStructuralExperience("completed observed binary winner required")
        rows.append(list((*_terms(cue), result)))
    n = 11
    rank = 0
    for col in range(n):
        pivot = next((r for r in range(rank, n) if rows[r][col]), None)
        if pivot is None:
            raise InvalidStructuralExperience("underdetermined degree2 coefficients")
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        for r in range(n):
            if r != rank and rows[r][col]:
                rows[r] = [u ^ v for u, v in zip(rows[r], rows[rank])]
        rank += 1
    solution = tuple(row[-1] for row in rows)
    if any(
        apply_degree2(solution, cue) != result for cue, result in examples
    ):
        raise InvalidStructuralExperience("inconsistent observed constraints")
    return solution


def infer_degree2_cheap(examples: tuple[tuple[Cue4, int], ...]) -> tuple[int, ...]:
    """Strong cheap comparator: exact finite differences of the same degree2 family."""
    if len(examples) != 11 or {cue for cue, _ in examples} != set(ANCHORS):
        raise InvalidStructuralExperience("all 11 distinct source-tested anchors required")
    source = dict(examples)
    if len(source) != 11 or any(type(v) is not int or v not in (0, 1) for v in source.values()):
        raise InvalidStructuralExperience("unique observed binary sources required")
    zero = (0, 0, 0, 0)
    singles = tuple(
        tuple(int(k == i) for k in range(4)) for i in range(4)
    )
    constant = source[zero]
    first = tuple(source[x] ^ constant for x in singles)
    second = tuple(
        source[tuple(int(k in (i, j)) for k in range(4))]
        ^ first[i] ^ first[j] ^ constant
        for i, j in PAIRS
    )
    result = (constant, *first, *second)
    if any(apply_degree2(result, cue) != answer for cue, answer in examples):
        raise InvalidStructuralExperience("nonrepresentable training sources")
    return result


def apply_degree2(coefficients: tuple[int, ...], cue: Cue4) -> int:
    if len(coefficients) != 11 or any(
        type(v) is not int or v not in (0, 1) for v in coefficients
    ):
        raise InvalidStructuralExperience("complete 11-bit structural model required")
    return sum(c * v for c, v in zip(coefficients, _terms(cue))) % 2


def _habit_cue(cue: Cue4, trial_id: str) -> HabitCue:
    return HabitCue(
        cue_id=f"b24-{trial_id}-" + "".join(map(str, cue)),
        features=tuple(CueFeature(name, v) for name, v in zip(FIELDS, cue))
        + (CueFeature("nuisance", trial_id),),
        provenance=Provenance("b24.actual-heldout-cue", trial_id),
    )


@dataclass(slots=True)
class StructuralAgent:
    arm: str
    world: StructuralWorld
    memory: tuple[Experience, ...] = ()
    episodes: list[Episode] = field(default_factory=list)
    owner: HabitRepertoire = field(default_factory=empty_repertoire)
    lookup: dict[Cue4, int] = field(default_factory=dict)
    model: tuple[int, ...] | None = None
    historical_owners: list[HabitRepertoire] = field(default_factory=list)
    source_rule_updates: int = 0
    new_relevant_predictions: int = 0
    L1_reuses: int = 0

    def __post_init__(self) -> None:
        if self.arm not in ARMS or not isinstance(self.world, StructuralWorld):
            raise InvalidStructuralExperience("exact structural experiment arm required")

    def _known_action(self, cue: Cue4, trial_id: str) -> int | None:
        if self.arm != "STRUCTURAL_S11":
            return self.lookup.get(cue)
        item = select_habit(self.owner, _habit_cue(cue, trial_id))
        if item.status is HabitSelectionStatus.NO_MATCH:
            return None
        if item.status is not HabitSelectionStatus.SELECTED or (
            item.selected_candidate_ref not in ("action:0", "action:1")
        ):
            raise InvalidStructuralExperience("native S11 choice ambiguous")
        return int(item.selected_candidate_ref.split(":")[-1])

    def _remember(self, phase: str, cue: Cue4, trial: str, observed: WorldAction) -> None:
        if not self.world.observed(observed) or observed.cue != cue:
            raise InvalidStructuralExperience("cannot remember invented external Action")
        if any(x.original_action.event_id == observed.event_id for x in self.memory):
            raise InvalidStructuralExperience("original Action already remembered")
        self.memory = self.memory + (Experience(phase, cue, observed, trial),)

    def _retain(self, cue: Cue4, outcome: WorldAction) -> None:
        if (
            not self.world.observed(outcome)
            or not outcome.succeeded
            or not self.memory
            or self.memory[-1].original_action is not outcome
            or outcome.cue != cue
        ):
            raise InvalidStructuralExperience("success must be latest real Memory")
        if self.arm != "STRUCTURAL_S11":
            self.lookup[cue] = outcome.action
            self.source_rule_updates += 1
            return
        old = self.owner
        required = tuple(CueFeature(name, v) for name, v in zip(FIELDS, cue))
        existed = tuple(r for r in old.rules if r.cue_requirements == required)
        if len(existed) > 1:
            raise InvalidStructuralExperience("ambiguous retained cue rule")
        if existed and existed[0].candidate_ref == f"action:{outcome.action}":
            return
        rule = HabitRule(
            habit_id=f"b24-learned-{''.join(map(str, cue))}-r{old.revision+1}",
            cue_requirements=required,
            candidate_ref=f"action:{outcome.action}",
            priority=10,
            provenance=Provenance("b24.original-success-memory", outcome.event_id),
        )
        self.historical_owners.append(old)
        self.owner = HabitRepertoire(
            repertoire_id=old.repertoire_id,
            revision=old.revision + 1,
            rules=tuple(r for r in old.rules if r.cue_requirements != required)
            + (rule,),
            provenance=old.provenance,
        )
        self.source_rule_updates += 1

    def encounter(self, cue: Cue4, phase: str, trial_id: str) -> Episode:
        validate_cue(cue)
        if phase not in ("TRAIN", "NOVEL", "REPLAY"):
            raise InvalidStructuralExperience("unregistered experiment phase")
        known = self._known_action(cue, trial_id)
        reuse = known is not None
        if reuse:
            self.L1_reuses += 1
        if known is None:
            if phase == "TRAIN":
                action = 0
            elif self.model is not None and self.arm != "FLAT_TAG":
                action = apply_degree2(self.model, cue)
                self.new_relevant_predictions += 1
            else:
                action = 0
        else:
            action = known
        first = self.world.act(cue, action)
        self._remember(phase, cue, trial_id, first)
        actual = [first]
        if not first.succeeded:
            second = self.world.act(cue, 1 - action)
            self._remember(phase, cue, trial_id, second)
            actual.append(second)
            if not second.succeeded:
                raise InvalidStructuralExperience("actual alternate failed")
        successful = actual[-1]
        self._retain(cue, successful)
        episode = Episode(
            phase=phase, cue=cue, trial_id=trial_id, first_action=action,
            attempts=tuple(x.action for x in actual),
            original_event_ids=tuple(x.event_id for x in actual),
            first_correct=first.succeeded,
            confirmed_success=successful.succeeded,
            used_cached_L1=reuse,
        )
        self.episodes.append(episode)
        return episode

    def completed_training_examples(self) -> tuple[tuple[Cue4, int], ...]:
        if len(tuple(e for e in self.episodes if e.phase == "TRAIN")) != 11:
            raise InvalidStructuralExperience("all 11 actual training encounters required")
        examples = []
        for cue in ANCHORS:
            matching = tuple(
                entry for entry in self.episodes if entry.phase == "TRAIN"
                and entry.cue == cue and entry.confirmed_success
            )
            if len(matching) != 1:
                raise InvalidStructuralExperience("training cue missing/duplicate")
            last = next(
                (m.original_action for m in reversed(self.memory)
                 if m.phase == "TRAIN" and m.cue == cue and m.original_action.succeeded),
                None,
            )
            if last is None or not self.world.observed(last):
                raise InvalidStructuralExperience("no real training-success Memory")
            if last.event_id not in matching[0].original_event_ids:
                raise InvalidStructuralExperience("source Memory is not training encounter")
            examples.append((cue, last.action))
        return tuple(examples)

    def learn_structure(self) -> tuple[int, ...] | None:
        examples = self.completed_training_examples()
        if self.arm == "STRUCTURAL_S11":
            self.model = infer_degree2_gaussian(examples)
        elif self.arm == "CHEAP_DEG2":
            self.model = infer_degree2_cheap(examples)
        else:
            self.model = None
        return self.model


def execute_arm(world_kind: str, arm: str) -> tuple[StructuralAgent, dict[str, object]]:
    if world_kind not in WORLDS or arm not in ARMS:
        raise InvalidStructuralExperience("only fixed model/counterworld arms")
    world = StructuralWorld(f"b24-{world_kind.lower()}-{arm.lower()}", world_kind == "TWIN")
    agent = StructuralAgent(
        arm, world, owner=empty_repertoire(
            f"b24-{world_kind.lower()}-{arm.lower()}-repertoire"
        ),
    )
    for index, cue in enumerate(ANCHORS):
        agent.encounter(cue, "TRAIN", f"training-{index}")
    if len(agent.memory) != 16 or world.actions_executed != 16:
        raise InvalidStructuralExperience("original training World budget mismatch")
    training = agent.completed_training_examples()
    learned = agent.learn_structure()
    if learned is not None and any(
        apply_degree2(learned, cue) != answer for cue, answer in training
    ):
        raise InvalidStructuralExperience("learned rule contradicts original experiences")
    for index, cue in enumerate(HELDOUT):
        agent.encounter(cue, "NOVEL", f"novel-{index}")
    for index, cue in enumerate(HELDOUT):
        agent.encounter(cue, "REPLAY", f"replay-{index}")
    if len(agent.memory) != world.actions_executed or any(
        not world.observed(row.original_action)
        for row in agent.memory
    ):
        raise InvalidStructuralExperience("stored memory lacks real World Actions")
    novel = tuple(row for row in agent.episodes if row.phase == "NOVEL")
    replay = tuple(row for row in agent.episodes if row.phase == "REPLAY")
    return agent, {
        "world_kind": world_kind,
        "arm": arm,
        "actual_source_actions": world.actions_executed,
        "training_source_actions": sum(
            len(e.attempts) for e in agent.episodes if e.phase == "TRAIN"
        ),
        "novel_first_correct": sum(e.first_correct for e in novel),
        "novel_source_actions": sum(len(e.attempts) for e in novel),
        "novel_predictions": agent.new_relevant_predictions,
        "replay_source_actions": sum(len(e.attempts) for e in replay),
        "confirmed_successful_encounters": sum(
            e.confirmed_success for e in agent.episodes
        ),
        "total_encounters": len(agent.episodes),
        "original_memory_events": len(agent.memory),
        "S11_revision": agent.owner.revision,
        "S11_rules": len(agent.owner.rules),
        "cached_reuse": agent.L1_reuses,
        "novel_first_actions": tuple(e.first_action for e in novel),
        "novel_first_results": tuple(e.first_correct for e in novel),
        "first_actions_replayed": tuple(e.first_action for e in replay),
        "learned_coefficients": learned,
        "training_examples": training,
        "decision_trace": tuple(
            (e.phase, e.cue, e.first_action, e.attempts, e.first_correct)
            for e in agent.episodes
        ),
    }


def run_b24_comparison() -> dict[str, object]:
    raw = {
        (kind, arm): execute_arm(kind, arm)[1]
        for kind in WORLDS for arm in ARMS
    }
    return {
        "classification": "B24_CONDITIONAL_NOVEL_CUE_TRANSFER_AND_UNDERDETERMINATION",
        "reports": raw,
        "total_separate_sim_world_actions": sum(
            r["actual_source_actions"] for r in raw.values()
        ),
        "identical_training_outcomes_across_worlds": all(
            raw["NORMAL", arm]["training_examples"]
            == raw["TWIN", arm]["training_examples"]
            for arm in ARMS
        ),
        "native_S11_and_cheap_degree2_exact_match_both_worlds": all(
            raw[kind, "STRUCTURAL_S11"]["decision_trace"]
            == raw[kind, "CHEAP_DEG2"]["decision_trace"]
            for kind in WORLDS
        ),
        "no_actual_LLM_L2": True,
        "no_real_Minecraft": True,
        "no_production_S11_owner": True,
        "B22_security_sibling_not_used": True,
    }
