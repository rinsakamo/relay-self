"""R2-3a first reJOIN Context comparison: original A/B source, CPU-only tests.

The existing pair fixture runs synthetic original process adapters/Paper records.
No real World, GPU, L1 request, physical action or Memory write occurs here.
"""
from dataclasses import FrozenInstanceError, replace

import pytest

from relay_self.b_np1b_continuing_b_composite_dev import ContinuingCompositeSourceReceipt
from relay_self.b_np1b_rejoin_composite_source_dev import RejoinedCompositeSourceReceipt
from relay_self.r2_3_rejoin_composite_context_dev import (
    R23CompositeContextHold,
    R23RejoinedContextComparison,
    R23RejoinedCurrent,
    r23_rejoined_context_is_live,
    read_r23_original_rejoin_context,
)
from relay_self.three_self_present import EpistemicStatus
from test_b_np1b_fresh_native_update_dev import files
from test_b_np1b_normal_present_poll_dev import pair as pair


def _args(pair, sid="A"):
    f, initials, _, historical, *_ = pair
    return dict(
        bridge=f.bridge, self_id=sid, initial_receipts=initials,
        historical_composite=historical,
    )


def _snapshot(f):
    return {
        sid: (
            owner.retained, owner.intent.events, owner.pattern_registry,
            dict(owner.skills), frozenset(owner.pending_questions),
        )
        for sid, owner in f.owners.items()
    }


@pytest.mark.parametrize("sid", ("A", "B"))
def test_r23_first_rejoin_uses_original_a_b_owners_and_all_three_sources(
    pair, sid,
):
    f = pair[0]
    resident = f.cognitive
    args = _args(pair, sid)
    before_files, before_state = files(f), _snapshot(f)
    original = resident.read_present_cpu(**args)
    report = resident.read_rejoined_context_shadow_cpu(**args)
    independently = read_r23_original_rejoin_context(**args)
    assert type(report) is R23RejoinedContextComparison
    assert report == independently
    assert report.original_owner is f.owners[sid]
    assert report.original_owner is resident.owners[sid]
    assert type(report.current) is R23RejoinedCurrent
    current = report.current
    assert current.source == original.source
    assert current.schema == original.schema
    assert current.signals == original.present.signals
    assert current.owner_epoch == resident.current_scope(sid)[0]
    assert current.source_revision_refs == original.present.three_self.source_revision_refs
    assert len(current.source_revision_refs) == 3
    assert current.source_revision_refs[2] == (
        "composite:rejoin:" + current.source.composite_receipt.composite_revision
    )
    assert current.coverage is EpistemicStatus.UNKNOWN
    assert current.need_refs == original.present.need_refs
    if sid == "A":
        assert type(current.source.composite_receipt) is RejoinedCompositeSourceReceipt
        assert current.source.native_session_id != pair[4]
    else:
        assert type(current.source.composite_receipt) is ContinuingCompositeSourceReceipt
        assert current.source.native_session_id == pair[1][1].native_session_id
    assert r23_rejoined_context_is_live(
        report, bridge=f.bridge, initial_receipts=pair[1],
        historical_composite=pair[3],
    )
    assert report.model_invoked is False
    assert report.l1_input_switched is False
    assert report.memory_adopted is False
    assert report.physical_authorized is False
    assert files(f) == before_files
    assert _snapshot(f) == before_state
    with pytest.raises((FrozenInstanceError, AttributeError)):
        report.l1_input_switched = True


@pytest.mark.parametrize("failure", (
    "foreign_owner", "foreign_self", "paper_changed", "native_changed",
    "epoch_changed", "registry_changed", "wrong_history", "second_cut",
))
def test_r23_rejoin_composite_read_rejects_stale_or_foreign_original(
    pair, failure,
):
    f = pair[0]
    args = _args(pair)
    if failure == "foreign_owner":
        f.bridge.owners["A"] = f.bridge.owners["B"]
    elif failure == "foreign_self":
        args["self_id"] = "foreign"
    elif failure == "paper_changed":
        with f.paper._log_path.open("a") as stream:
            stream.write("R23_STALE_ORIGINAL_PAPER_LOG\n")
    elif failure == "native_changed":
        obs = f.owners["A"].current_worldbody_observation
        f.owners["A"].current_worldbody_observation = replace(obs)
    elif failure == "epoch_changed":
        f.cognitive._states["A"].epoch += 1
    elif failure == "registry_changed":
        owner = f.owners["A"]
        owner.pattern_registry = replace(
            owner.pattern_registry, revision=owner.pattern_registry.revision + 1,
        )
    elif failure == "wrong_history":
        args["historical_composite"] = replace(
            pair[3], paper_log_sha256="0" * 64,
        )
    else:
        f.cognitive._normal_second_rejoin_cut = object()
    originals = files(f)
    with pytest.raises(R23CompositeContextHold):
        f.cognitive.read_rejoined_context_shadow_cpu(**args)
    assert files(f) == originals


def test_r23_cached_first_rejoin_context_invalidates_on_paper_advance(pair):
    f = pair[0]
    report = f.cognitive.read_rejoined_context_shadow_cpu(**_args(pair))
    assert r23_rejoined_context_is_live(
        report, bridge=f.bridge, initial_receipts=pair[1],
        historical_composite=pair[3],
    )
    with f.paper._log_path.open("a") as stream:
        stream.write("NEW_PAPER_LINE_AFTER_R23_READ\n")
    assert not r23_rejoined_context_is_live(
        report, bridge=f.bridge, initial_receipts=pair[1],
        historical_composite=pair[3],
    )


@pytest.mark.parametrize("field", (
    "revision", "coverage", "signal", "source",
))
def test_r23_typed_current_cannot_promote_foreign_claims_to_schema(
    pair, field,
):
    f = pair[0]
    current = f.cognitive.read_rejoined_context_shadow_cpu(
        **_args(pair),
    ).current
    if field == "revision":
        change = {"source_revision_refs": (
            *current.source_revision_refs[:2], "composite:rejoin:foreign",
        )}
    elif field == "coverage":
        change = {"coverage": EpistemicStatus.OBSERVED}
    elif field == "signal":
        change = {"signals": ("unqualified-body-claim",)}
    else:
        change = {"source": replace(
            current.source, native_probe_seq=current.source.native_probe_seq + 1,
        )}
    with pytest.raises(R23CompositeContextHold):
        replace(current, **change)


def test_r23_rejoin_external_paper_change_during_second_read_fails_closed(
    pair, monkeypatch,
):
    f = pair[0]
    resident = f.cognitive
    original = resident.read_present_cpu
    calls = 0

    def change_between_original_reads(**kwargs):
        nonlocal calls
        reading = original(**kwargs)
        calls += 1
        if calls == 2:
            with f.paper._log_path.open("a") as stream:
                stream.write("R23_RACE_PAPER_ADVANCED\n")
        return reading

    monkeypatch.setattr(resident, "read_present_cpu", change_between_original_reads)
    with pytest.raises(R23CompositeContextHold):
        resident.read_rejoined_context_shadow_cpu(**_args(pair))
    assert calls == 2


@pytest.mark.parametrize("invalid", (None, "original-stage28", object()))
def test_r23_untyped_cached_context_never_is_live(pair, invalid):
    assert not r23_rejoined_context_is_live(
        invalid, bridge=pair[0].bridge, initial_receipts=pair[1],
        historical_composite=pair[3],
    )
