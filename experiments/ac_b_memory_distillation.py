"""AC-B offline evidence retrieval and conditional Habit candidate apparatus.

This module owns no production state, action permission, or WorldModel.
It deliberately does not import S10/S11/S17 unmerged Draft sources.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, replace
from enum import Enum
from hashlib import sha256


class EvidenceError(ValueError):
    """Invalid or unqualified World evidence; fail closed."""


class RetrievalStatus(str, Enum):
    FOUND = "FOUND"
    UNKNOWN = "UNKNOWN"
    CONFLICT = "CONFLICT"


class EdgeKind(str, Enum):
    ASSOCIATED_WITH = "ASSOCIATED_WITH"
    OBSERVED_TRANSITION = "OBSERVED_TRANSITION"
    CAUSAL_HYPOTHESIS = "CAUSAL_HYPOTHESIS"
    HABIT_CANDIDATE = "HABIT_CANDIDATE"


@dataclass(frozen=True)
class Cue:
    a: int
    b: int
    weather: int

    def __post_init__(self) -> None:
        if type(self.a) is not int or self.a not in (0, 1):
            raise EvidenceError("a must be a binary integer")
        if type(self.b) is not int or self.b not in (0, 1):
            raise EvidenceError("b must be a binary integer")
        if type(self.weather) is not int or self.weather < 0:
            raise EvidenceError("weather must be a nonnegative integer")


@dataclass(frozen=True)
class Episode:
    episode_id: str
    session: str
    revision: int
    sequence: int
    cue: Cue
    action: int
    success: bool
    kind: str
    outcome_ref: str
    evidence_digest: str


@dataclass(frozen=True)
class TypedEdge:
    origin: str
    target: str
    kind: EdgeKind


@dataclass(frozen=True)
class Retrieval:
    status: RetrievalStatus
    episode_ids: tuple[str, ...]
    query_work: int
    build_work: int


class DeterministicWorld:
    """An offline World witness; hidden regime is never an argument to the learner."""

    def __init__(self, session: str = "session-b") -> None:
        if not session or session.strip() != session:
            raise EvidenceError("invalid World session")
        self.session = session
        self.revision = 0
        self._regime = 0
        self._ledger: dict[str, Episode] = {}
        self._sequence = 0

    def change_rule(self, *, announce: bool) -> None:
        self._regime ^= 1
        if announce:
            self.revision += 1

    def act(self, cue: Cue, action: int) -> Episode:
        """Independently reset each fixture trial; one actual observed Action receipt."""
        if not isinstance(cue, Cue) or type(action) is not int or action not in (0, 1):
            raise EvidenceError("invalid simulated Action")
        self._sequence += 1
        episode_id = f"{self.session}:event:{self._sequence}"
        success = action == (cue.a ^ cue.b ^ self._regime)
        payload = (episode_id, self.session, self.revision, self._sequence,
                   cue.a, cue.b, cue.weather, action, success, "OBSERVED")
        digest = sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()
        episode = Episode(
            episode_id=episode_id, session=self.session,
            revision=self.revision, sequence=self._sequence, cue=cue,
            action=action, success=success, kind="OBSERVED",
            outcome_ref=f"offline-world:{episode_id}:outcome",
            evidence_digest=digest,
        )
        self._ledger[episode_id] = episode
        return episode

    def verify(self, episode: Episode) -> None:
        if not isinstance(episode, Episode):
            raise EvidenceError("not an Episode")
        if (
            episode.kind != "OBSERVED"
            or self._ledger.get(episode.episode_id) != episode
            or not episode.outcome_ref.startswith("offline-world:")
        ):
            raise EvidenceError("outcome is not exactly source-qualified")

    @property
    def action_count(self) -> int:
        return self._sequence


class MemoryView:
    """Experiment-local derived index; no mutation of the Memory owner."""

    def __init__(
        self, world: DeterministicWorld, episodes: tuple[Episode, ...],
        *, session: str, revision: int,
        edges: tuple[TypedEdge, ...] = (),
    ) -> None:
        if not isinstance(world, DeterministicWorld):
            raise EvidenceError("missing source witness")
        self.session, self.revision = session, revision
        seen: set[str] = set()
        self.episodes = tuple(sorted(episodes, key=lambda e: e.episode_id))
        self.by_id: dict[str, Episode] = {}
        self.by_tag: dict[tuple[int, int], list[Episode]] = {}
        for ep in self.episodes:
            world.verify(ep)
            if ep.session != session or ep.revision != revision:
                raise EvidenceError("wrong session or stale revision")
            if ep.episode_id in seen:
                raise EvidenceError("duplicate Episode identity")
            seen.add(ep.episode_id)
            self.by_id[ep.episode_id] = ep
            self.by_tag.setdefault((ep.cue.a, ep.cue.b), []).append(ep)
        self.edges = edges
        for edge in edges:
            if not isinstance(edge, TypedEdge) or not isinstance(edge.kind, EdgeKind):
                raise EvidenceError("untyped edge")
            if edge.origin not in self.by_id or edge.target not in self.by_id:
                raise EvidenceError("edge crosses evidence boundary")
            if edge.origin == edge.target:
                raise EvidenceError("self-edge is not evidence")
            if edge.kind is EdgeKind.OBSERVED_TRANSITION:
                origin, target = self.by_id[edge.origin], self.by_id[edge.target]
                if origin.sequence >= target.sequence:
                    raise EvidenceError("transition not in observed order")
        self.index_build_work = len(self.episodes)
        self.edge_build_work = len(edges)

    def search(self, a: int, b: int, mode: str) -> Retrieval:
        if type(a) is not int or type(b) is not int or a not in (0, 1) or b not in (0, 1) or mode not in (
            "full_scan", "tags", "tags_typed_graph",
        ):
            raise EvidenceError("invalid query")
        if mode == "full_scan":
            selected = [ep for ep in self.episodes if (ep.cue.a, ep.cue.b) == (a, b)]
            query_work = len(self.episodes)
            build_work = 0
        else:
            selected = self.by_tag.get((a, b), ())
            query_work = 1 + len(selected)
            build_work = self.index_build_work
            if mode == "tags_typed_graph":
                # Graph can *only* decorate already admissible tag hits. It
                # cannot promote CAUSAL_HYPOTHESIS to OBSERVED.
                relevant = {ep.episode_id for ep in selected}
                query_work += sum(
                    edge.origin in relevant or edge.target in relevant
                    for edge in self.edges
                )
                build_work += self.edge_build_work
        flags: dict[tuple[int, int, int], set[bool]] = {}
        for ep in selected:
            flags.setdefault((ep.cue.a, ep.cue.b, ep.action), set()).add(ep.success)
        conflict = any(len(values) != 1 for values in flags.values())
        status = (
            RetrievalStatus.CONFLICT if conflict else
            RetrievalStatus.FOUND if selected else RetrievalStatus.UNKNOWN
        )
        return Retrieval(status, tuple(sorted(ep.episode_id for ep in selected)),
                         query_work, build_work)


@dataclass(frozen=True)
class HabitCandidate:
    """Read-only, non-authoritative S11-compatible cue -> action proposal."""

    session: str
    revision: int
    mapping: tuple[tuple[int, int, int], ...]
    training_ids: tuple[str, ...]
    validation_ids: tuple[str, ...]
    quarantined: bool = False

    def select(self, *, session: str, revision: int, cue: Cue) -> int | None:
        if self.quarantined or session != self.session or revision != self.revision:
            return None
        return next(
            (action for a, b, action in self.mapping if (cue.a, cue.b) == (a, b)),
            None,
        )

    def reconsider_after_outcome(
        self, world: DeterministicWorld, episode: Episode,
    ) -> HabitCandidate:
        world.verify(episode)
        expected = self.select(
            session=episode.session, revision=episode.revision, cue=episode.cue
        )
        if expected is None or expected != episode.action or not episode.success:
            return replace(self, quarantined=True)
        return self


def _derive_paired_success(
    world: DeterministicWorld, items: tuple[Episode, ...],
    *, session: str, revision: int, weather: int,
) -> dict[tuple[int, int], int]:
    pairs: dict[tuple[int, int], dict[int, Episode]] = {}
    if len(items) != 8:
        raise EvidenceError("need exactly eight independent World outcomes")
    seen: set[str] = set()
    for ep in items:
        world.verify(ep)
        if (
            ep.episode_id in seen or ep.session != session
            or ep.revision != revision or ep.cue.weather != weather
        ):
            raise EvidenceError("duplicate, wrong source, stale or split leakage")
        seen.add(ep.episode_id)
        group = pairs.setdefault((ep.cue.a, ep.cue.b), {})
        if ep.action in group:
            raise EvidenceError("duplicate action for one cue")
        group[ep.action] = ep
    if set(pairs) != {(0, 0), (0, 1), (1, 0), (1, 1)}:
        raise EvidenceError("training cue coverage incomplete")
    results = {}
    for key, actions in pairs.items():
        if set(actions) != {0, 1} or sum(ep.success for ep in actions.values()) != 1:
            raise EvidenceError("both Actions must be observed; unique success required")
        results[key] = next(action for action, ep in actions.items() if ep.success)
    return results


def distill(
    world: DeterministicWorld, training: tuple[Episode, ...],
    validation: tuple[Episode, ...], *, session: str, revision: int,
    training_weather: int = 0, validation_weather: int = 1,
) -> HabitCandidate:
    """Train and separately qualify; no result from heldout is an input."""
    if set(ep.episode_id for ep in training) & set(ep.episode_id for ep in validation):
        raise EvidenceError("training and validation overlap")
    trained = _derive_paired_success(
        world, training, session=session, revision=revision, weather=training_weather
    )
    qualified = _derive_paired_success(
        world, validation, session=session, revision=revision, weather=validation_weather
    )
    if trained != qualified:
        raise EvidenceError("World outcomes disagree across splits")
    return HabitCandidate(
        session=session, revision=revision,
        mapping=tuple((a, b, trained[(a, b)]) for a in (0, 1) for b in (0, 1)),
        training_ids=tuple(sorted(ep.episode_id for ep in training)),
        validation_ids=tuple(sorted(ep.episode_id for ep in validation)),
    )


def cheap_rule(training: tuple[Episode, ...]) -> tuple[str, int] | None:
    """Strong cheap comparator: four declared hypotheses, no hidden regime access."""
    expected: dict[tuple[int, int], int] = {}
    for ep in training:
        key = (ep.cue.a, ep.cue.b)
        if ep.success:
            if key in expected and expected[key] != ep.action:
                return None
            expected[key] = ep.action
    if len(expected) != 4:
        return None
    candidates = (
        ("constant", 0, lambda a, b: 0),
        ("constant", 1, lambda a, b: 1),
        ("xor", 0, lambda a, b: a ^ b),
        ("xor", 1, lambda a, b: a ^ b ^ 1),
    )
    matches = [(family, bias) for family, bias, fn in candidates if all(
        fn(a, b) == action for (a, b), action in expected.items()
    )]
    return matches[0] if len(matches) == 1 else None


def apply_cheap(rule: tuple[str, int] | None, cue: Cue) -> int | None:
    if rule is None:
        return None
    family, bias = rule
    return bias if family == "constant" else cue.a ^ cue.b ^ bias


def observe_split(world: DeterministicWorld, weather: int) -> tuple[Episode, ...]:
    return tuple(
        world.act(Cue(a, b, weather), action)
        for a in (0, 1) for b in (0, 1) for action in (0, 1)
    )


def run_fixture() -> dict[str, object]:
    world = DeterministicWorld()
    train = observe_split(world, 0)
    valid = observe_split(world, 1)
    candidate = distill(world, train, valid, session=world.session, revision=0)
    rule = cheap_rule(train)
    edges = tuple(
        TypedEdge(train[i].episode_id, train[i + 1].episode_id,
                  EdgeKind.ASSOCIATED_WITH)
        for i in range(0, 8, 2)
    )
    view = MemoryView(world, train + valid, session=world.session,
                      revision=0, edges=edges)
    totals = {}
    for mode in ("full_scan", "tags", "tags_typed_graph"):
        answers = [view.search(a, b, mode) for a in (0, 1) for b in (0, 1)]
        totals[mode] = {
            "statuses": [answer.status.value for answer in answers],
            "ids": [answer.episode_ids for answer in answers],
            "query_work": sum(answer.query_work for answer in answers),
            "build_work": answers[0].build_work,
        }
    scores = {"no_retention": 0, "exact_case": 0, "cheap_rule": 0,
              "habit": 0, "expensive_probe": 0}
    probes = 0
    for a in (0, 1):
        for b in (0, 1):
            cue = Cue(a, b, 2)  # full cue unobserved in train or validation
            choices = {
                "no_retention": 0,
                "exact_case": None,  # no exact (a,b,weather=2) earlier
                "cheap_rule": apply_cheap(rule, cue),
                "habit": candidate.select(
                    session=world.session, revision=world.revision, cue=cue
                ),
            }
            # Simulated high-cost controller explicitly probes real World outcomes.
            first = world.act(cue, 0)
            probes += 1
            if first.success:
                choices["expensive_probe"] = 0
            else:
                second = world.act(cue, 1)
                probes += 1
                choices["expensive_probe"] = 1 if second.success else None
            for name, action in choices.items():
                if action is not None:
                    ep = world.act(cue, action)
                    scores[name] += int(ep.success)
    world.change_rule(announce=True)
    stale_abstentions = sum(
        candidate.select(session=world.session, revision=world.revision,
                         cue=Cue(a, b, 3)) is None
        for a in (0, 1) for b in (0, 1)
    )
    recovery_start = world.action_count
    new_train = observe_split(world, 0)
    new_valid = observe_split(world, 1)
    refreshed = distill(world, new_train, new_valid, session=world.session,
                        revision=world.revision)
    recovery_actions = world.action_count - recovery_start
    recovery_success = sum(
        world.act(Cue(a, b, 3), refreshed.select(
            session=world.session, revision=world.revision, cue=Cue(a, b, 3)
        )).success
        for a in (0, 1) for b in (0, 1)
    )
    return {
        "classification": "INDEX_ONLY_GAIN",
        "retrieval": totals,
        "heldout_4": scores,
        "expensive_extra_probes": probes,
        "stale_abstentions_4": stale_abstentions,
        "shift_recovery_training_validation_actions": recovery_actions,
        "shift_recovered_heldout_4": recovery_success,
        "unseen_full_cue": True,
        "graph_incremental_gain": False,
        "habit_incremental_gain_over_cheap_rule": False,
    }


if __name__ == "__main__":
    print(json.dumps(run_fixture(), indent=2, sort_keys=True))
