"""Synthetic DEV-only negatives for bounded World regularity transfer."""

from dataclasses import replace

import pytest

from experiments.self_world_regularity_transfer import (
    ObservedPair,
    TransferStatus,
    evaluate_unseen_region,
    induce_label_persistence,
)
from relay_self.provenance import Provenance
from relay_self.self_world import (
    InvalidSelfWorldData,
    WorldEntityObservation,
    WorldObservation,
    compose_self_world_view,
)


def _view(
    seq: int,
    *,
    self_id: str = "self-a",
    session: str = "session-a",
    target: str = "entity-1",
    label: str | None = "zombie",
    x: float = 2.0,
    present: bool = True,
    provenance: Provenance | None = None,
):
    entities = (
        (WorldEntityObservation(target, label, (x, 64.0, 0.0), 2.0),)
        if present else ()
    )
    return compose_self_world_view(
        self_id=self_id,
        session_id=session,
        epoch_id=f"epoch-{seq}",
        observation=WorldObservation(
            observer_id=self_id,
            session_id=session,
            native_seq=seq,
            request_id=f"probe-{seq}",
            entities=entities,
            coverage_scope="bounded-nearby",
            coverage_radius_m=16.0,
            coverage_cap=5,
            coverage_candidates=len(entities),
            coverage_truncated=False,
            provenance=provenance or Provenance("mineflayer", f"{session}:{seq}"),
        ),
    )


def _pair(
    seq: int,
    *,
    self_id: str = "self-a",
    session: str = "session-a",
    target: str = "entity-1",
    x: float = 2.0,
    initial: str | None = "zombie",
    final: str | None = "zombie",
    present_after: bool = True,
):
    return ObservedPair(
        _view(seq, self_id=self_id, session=session, target=target, x=x, label=initial),
        _view(
            seq + 1, self_id=self_id, session=session, target=target, x=x,
            label=final, present=present_after,
        ),
        target,
    )


def _training():
    return (
        _pair(1, target="entity-one", x=2.0),
        _pair(4, target="entity-two", x=34.0),
    )


def _candidate():
    result = induce_label_persistence(
        _training(), label="zombie", max_native_seq_gap=2,
    )
    assert result is not None
    return result


def test_compress_two_positive_sites_into_prd_rule():
    c = _candidate()
    assert c.regions == ((0, 0), (2, 0))
    assert len(c.source_pairs) == 2
    assert c.as_prediction_rule().assignments[0].value == "zombie"
    assert (
        c.as_prediction_rule().provenance.source
        == "relay_self.dev.self_world_regularity"
    )


def test_heldout_other_region_matches_but_cheap_repeat_matches_too():
    result = evaluate_unseen_region(
        _candidate(), _pair(7, target="entity-three", x=66.0)
    )
    assert result.status is TransferStatus.MATCH
    assert result.cheap_repeat_status is TransferStatus.MATCH
    assert result.predicted_label == result.observed_label == "zombie"


def test_heldout_distribution_shift_is_mismatch_not_learning_update():
    result = evaluate_unseen_region(
        _candidate(), _pair(7, target="entity-three", x=66.0, final="skeleton"),
    )
    assert result.status is TransferStatus.MISMATCH
    assert result.cheap_repeat_status is TransferStatus.MISMATCH


@pytest.mark.parametrize("missing", ["missing_entity", "missing_label"])
def test_later_unknown_never_becomes_absent_or_match(missing):
    holdout = _pair(
        7, target="entity-three", x=66.0,
        present_after=missing != "missing_entity",
        final=None if missing == "missing_label" else "zombie",
    )
    out = evaluate_unseen_region(_candidate(), holdout)
    assert out.status is TransferStatus.UNDETERMINED
    assert out.observed_label is None
    assert out.predicted_label is None


def test_training_requires_two_locations_two_entities():
    a = _training()[0]
    assert induce_label_persistence((a,), label="zombie", max_native_seq_gap=2) is None
    b = _pair(4, target="entity-two", x=3.0)
    assert (
        induce_label_persistence((a, b), label="zombie", max_native_seq_gap=2)
        is None
    )
    c = _pair(4, target="entity-one", x=34.0)
    assert (
        induce_label_persistence((a, c), label="zombie", max_native_seq_gap=2)
        is None
    )


def test_training_mismatch_never_yields_rule():
    bad = _pair(4, target="entity-two", x=34.0, final="skeleton")
    assert induce_label_persistence(
        (_training()[0], bad), label="zombie", max_native_seq_gap=2,
    ) is None


def test_training_missing_positive_property_never_yields_rule():
    bad = _pair(4, target="entity-two", x=34.0, present_after=False)
    assert induce_label_persistence(
        (_training()[0], bad), label="zombie", max_native_seq_gap=2,
    ) is None


@pytest.mark.parametrize("bad_pair", [
    _pair(4, self_id="self-b", target="entity-two", x=34.0),
    _pair(4, session="session-b", target="entity-two", x=34.0),
])
def test_cross_owner_training_fails_closed(bad_pair):
    with pytest.raises(InvalidSelfWorldData):
        induce_label_persistence(
            (_training()[0], bad_pair),
            label="zombie", max_native_seq_gap=2,
        )


def test_cross_owner_holdout_fails_closed():
    foreign = _pair(7, self_id="self-b", target="entity-three", x=66.0)
    with pytest.raises(InvalidSelfWorldData):
        evaluate_unseen_region(_candidate(), foreign)


def test_reused_training_source_or_region_is_not_holdout():
    with pytest.raises(InvalidSelfWorldData):
        evaluate_unseen_region(_candidate(), _training()[0])
    with pytest.raises(InvalidSelfWorldData):
        evaluate_unseen_region(_candidate(), _pair(7, target="entity-three", x=2.0))


def test_bad_provenance_is_rejected_even_when_labels_match():
    pair = _pair(7, target="entity-three", x=66.0)
    world = pair.before.observation
    assert world is not None
    altered = replace(
        pair.before, observation=replace(
            world, provenance=Provenance("synthetic", "fake"),
        ),
    )
    with pytest.raises(InvalidSelfWorldData):
        evaluate_unseen_region(_candidate(), replace(pair, before=altered))


def test_stale_or_beyond_gap_is_unknown():
    pair = _pair(7, target="entity-three", x=66.0)
    later = _view(10, target="entity-three", x=66.0)
    result = evaluate_unseen_region(_candidate(), replace(pair, after=later))
    assert result.status is TransferStatus.UNDETERMINED


def test_unknown_training_label_cannot_be_positive_support():
    t = _training()
    unknown = _pair(4, target="entity-two", x=34.0, initial=None)
    assert induce_label_persistence(
        (t[0], unknown), label="zombie", max_native_seq_gap=2,
    ) is None


def test_no_transfer_without_matching_prior_label():
    out = evaluate_unseen_region(
        _candidate(), _pair(7, target="entity-three", x=66.0, initial="skeleton"),
    )
    assert out.status is TransferStatus.UNDETERMINED
    assert out.predicted_label is None
