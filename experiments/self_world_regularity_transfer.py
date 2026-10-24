"""DEV/OFFLINE: bounded, non-retained SelfWorld regularity-transfer candidate.

This is a read-only experimental *hypothesis*, not a new WorldModel,
Memory owner, Action issuer, learned law or physical/source qualification.
Only positive, typed observations can support or falsify the candidate.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from enum import Enum

from relay_self.prediction import (
    PredictionState,
    PredictionStatus,
    StateVariable,
    TransitionRule,
    predict_transition,
)
from relay_self.provenance import Provenance
from relay_self.self_world import InvalidSelfWorldData, SelfWorldView, WorldObservation


class TransferStatus(str, Enum):
    MATCH = "match"
    MISMATCH = "mismatch"
    UNDETERMINED = "undetermined"


@dataclass(frozen=True, slots=True)
class ObservedPair:
    before: SelfWorldView
    after: SelfWorldView
    entity_ref: str


@dataclass(frozen=True, slots=True)
class LabelPersistenceCandidate:
    """Compressed hypothesis for one label, with exact native source pointers."""

    self_id: str
    session_id: str
    label: str
    max_native_seq_gap: int
    regions: tuple[tuple[int, int], ...]
    target_refs: tuple[str, ...]
    source_pairs: tuple[tuple[str, str], ...]

    @property
    def digest(self) -> str:
        fields = repr((
            self.self_id, self.session_id, self.label,
            self.max_native_seq_gap, self.regions, self.target_refs,
            self.source_pairs,
        ))
        return hashlib.sha256(fields.encode("utf-8")).hexdigest()

    def as_prediction_rule(self) -> TransitionRule:
        """Reuse existing PRD; a proposed rule is not an authoritative law."""
        return TransitionRule(
            rule_id=f"dev-label-persistence-{self.digest[:20]}",
            preconditions=(StateVariable("entity_label", self.label),),
            assignments=(StateVariable("entity_label", self.label),),
            provenance=Provenance(
                "relay_self.dev.self_world_regularity", self.digest,
            ),
        )


@dataclass(frozen=True, slots=True)
class TransferComparison:
    status: TransferStatus
    cheap_repeat_status: TransferStatus
    predicted_label: str | None
    observed_label: str | None
    holdout_source_pairs: tuple[str, str] | None
    # A non-independent, cheap 'repeat current label' rule is an explicit baseline.
    # No outcome gain or cognitive cost claim is made from this comparison.


@dataclass(frozen=True, slots=True)
class _PositivePair:
    self_id: str
    session_id: str
    target_ref: str
    label_before: str
    label_after: str
    region: tuple[int, int]
    sources: tuple[str, str]
    before_provenance: Provenance


def _positive_pair(pair: ObservedPair, max_gap: int) -> _PositivePair | None:
    """Return only *positive* exterior label observations; missing != absent."""
    if not isinstance(pair, ObservedPair):
        raise InvalidSelfWorldData("typed observed pair required")
    a, b = pair.before, pair.after
    if not isinstance(a, SelfWorldView) or not isinstance(b, SelfWorldView):
        raise InvalidSelfWorldData("pair requires two typed SelfWorld views")
    if (not isinstance(pair.entity_ref, str)
            or not pair.entity_ref.startswith("entity-")):
        raise InvalidSelfWorldData("target must be exterior entity identity")
    if (
        a.self_id != b.self_id
        or a.session_id != b.session_id
        or a.epoch_id == b.epoch_id
    ):
        raise InvalidSelfWorldData("foreign Self/session or duplicate epoch")
    prior, later = a.observation, b.observation
    if (not isinstance(prior, WorldObservation)
            or not isinstance(later, WorldObservation)):
        return None
    if (
        prior.observer_id != a.self_id
        or later.observer_id != b.self_id
        or prior.session_id != a.session_id
        or later.session_id != b.session_id
        or prior.provenance.source != "mineflayer"
        or later.provenance.source != "mineflayer"
        or prior.provenance.reference != f"{prior.session_id}:{prior.native_seq}"
        or later.provenance.reference != f"{later.session_id}:{later.native_seq}"
    ):
        raise InvalidSelfWorldData("invalid native source lineage")
    if (
        later.native_seq <= prior.native_seq
        or later.native_seq - prior.native_seq > max_gap
    ):
        return None
    if (
        prior.observed_at_ns is not None
        and later.observed_at_ns is not None
        and later.observed_at_ns < prior.observed_at_ns
    ):
        raise InvalidSelfWorldData("nonmonotonic observation timestamp")
    left = next((e for e in prior.entities if e.entity_ref == pair.entity_ref), None)
    right = next((e for e in later.entities if e.entity_ref == pair.entity_ref), None)
    if (
        left is None or right is None
        or left.label is None or right.label is None
        or left.position is None
    ):
        return None
    region = (
        math.floor(left.position[0] / 16),
        math.floor(left.position[2] / 16),
    )
    return _PositivePair(
        a.self_id, a.session_id, pair.entity_ref, left.label, right.label,
        region, (prior.source_ref, later.source_ref), prior.provenance,
    )


def induce_label_persistence(
    training: tuple[ObservedPair, ...],
    *,
    label: str,
    max_native_seq_gap: int,
) -> LabelPersistenceCandidate | None:
    """Propose a location-invariant label *persistence* hypothesis.

    Requires two distinct sites and two distinct positive entities, all
    consistent. Returns None for insufficient/contradictory/unknown evidence.
    Caller must authenticate native observations independently.
    """
    if not isinstance(training, tuple) or not training:
        raise InvalidSelfWorldData("explicit nonempty training cohort required")
    if not isinstance(label, str) or not label or label.strip() != label:
        raise InvalidSelfWorldData("explicit label required")
    if type(max_native_seq_gap) is not int or max_native_seq_gap <= 0:
        raise InvalidSelfWorldData("positive bounded sequence gap required")
    positives: list[_PositivePair] = []
    for sample in training:
        qualified = _positive_pair(sample, max_native_seq_gap)
        if qualified is None:
            return None
        positives.append(qualified)
    owner = positives[0].self_id, positives[0].session_id
    if any((p.self_id, p.session_id) != owner for p in positives):
        raise InvalidSelfWorldData("training cannot combine Self or sessions")
    if any(p.label_before != label or p.label_after != label for p in positives):
        return None
    regions = tuple(p.region for p in positives)
    targets = tuple(p.target_ref for p in positives)
    sources = tuple(p.sources for p in positives)
    if (
        len(positives) < 2 or len(set(regions)) < 2
        or len(set(targets)) != len(targets)
        or len({src for pair in sources for src in pair}) != 2 * len(sources)
    ):
        return None
    return LabelPersistenceCandidate(
        owner[0], owner[1], label, max_native_seq_gap,
        regions, targets, sources,
    )


def evaluate_unseen_region(
    candidate: LabelPersistenceCandidate,
    holdout: ObservedPair,
) -> TransferComparison:
    """Evaluate *one* positive holdout; never infer absence from missing data.

    PRD's prediction is compared to an explicitly cheap current-label repeat.
    The candidate cannot change World, Action, Memory, BLF or S10.
    """
    if not isinstance(candidate, LabelPersistenceCandidate):
        raise InvalidSelfWorldData("candidate required")
    p = _positive_pair(holdout, candidate.max_native_seq_gap)
    empty = TransferComparison(
        TransferStatus.UNDETERMINED, TransferStatus.UNDETERMINED,
        None, None, None,
    )
    if p is None:
        return empty
    if (p.self_id, p.session_id) != (candidate.self_id, candidate.session_id):
        raise InvalidSelfWorldData("foreign holdout Self/session")
    if (
        p.region in candidate.regions
        or p.target_ref in candidate.target_refs
        or any(ref in {x for pair in candidate.source_pairs for x in pair}
               for ref in p.sources)
    ):
        raise InvalidSelfWorldData("holdout must be unseen and non-replayed")
    if p.label_before != candidate.label:
        return TransferComparison(
            TransferStatus.UNDETERMINED, TransferStatus.UNDETERMINED,
            None, p.label_after, p.sources,
        )
    rule = candidate.as_prediction_rule()
    source = PredictionState(
        state_id=(
            "dev-holdout-"
            + hashlib.sha256(repr(p.sources).encode()).hexdigest()[:20]
        ),
        variables=(StateVariable("entity_label", p.label_before),),
        provenance=p.before_provenance,
        source_refs=(p.sources[0], f"target:{p.target_ref}"),
        source_provenance=(p.before_provenance,),
    )
    predicted = predict_transition(source, rule)
    if predicted.status is not PredictionStatus.PREDICTED:
        return empty
    assert predicted.predicted_state is not None
    value = predicted.predicted_state.variable("entity_label")
    if value is None:
        return empty
    label = value.value
    status = (
        TransferStatus.MATCH if label == p.label_after
        else TransferStatus.MISMATCH
    )
    cheap_status = (
        TransferStatus.MATCH if p.label_before == p.label_after
        else TransferStatus.MISMATCH
    )
    return TransferComparison(status, cheap_status, label, p.label_after, p.sources)
