"""R2-3b: original first-reJOIN Inquiry/Need and 3Self CURRENT compatibility.

The original B post-reJOIN path publishes CPU Present + Inquiry only; it
does NOT register a post-reJOIN BoundedChoiceRequest with L1 choices.
No World, Gemma, GPU, issuer, Memory or Physical action in these tests.
"""
from dataclasses import FrozenInstanceError, replace

import pytest

from relay_self.r2_3b_original_rejoin_l1_source_compare_dev import (
    R23BOriginalL1SourceComparison,
    R23BOriginalL1SourceHold,
    compare_r23b_original_rejoin_inquiry_context,
    r23b_original_rejoin_inquiry_is_live,
)
from relay_self.resident_cognitive_work_owner_dev import ResidentCognitiveWorkError
from test_b_np1b_fresh_native_update_dev import files
from test_b_np1b_normal_present_poll_dev import pair as pair


def _bind(pair):
    f = pair[0]
    f.bridge.bind_normal_rejoin_present_cpu(
        initial_receipts=pair[1], historical_composite=pair[3],
    )
    return f


def _owner_state(f):
    return {
        sid: (
            owner.retained, owner.intent.events, owner.pattern_registry,
            dict(owner.skills), frozenset(owner.pending_questions),
            owner.supervisor.open_actions,
        )
        for sid, owner in f.owners.items()
    }


@pytest.mark.parametrize("sid", ("A", "B"))
def test_r23b_original_owner_source_inquiry_context_matches_without_l1_request(pair, sid):
    f = _bind(pair)
    initial_poll = f.bridge.poll_normal_present_cpu()
    baseline_files, baseline_owner = files(f), _owner_state(f)
    result = f.cognitive.read_rejoined_l1_source_compatibility_cpu(
        bridge=f.bridge, self_id=sid,
    )
    independently = compare_r23b_original_rejoin_inquiry_context(
        bridge=f.bridge, self_id=sid,
    )
    assert type(result) is R23BOriginalL1SourceComparison
    assert result == independently
    assert result.original_owner is f.owners[sid]
    assert result.original_owner is f.cognitive.owners[sid]
    present = initial_poll.a_present if sid == "A" else initial_poll.b_present
    inquiry = initial_poll.a_inquiry if sid == "A" else initial_poll.b_inquiry
    assert result.current.source == present.source
    assert result.current.schema == present.schema
    assert result.current.source_revision_refs == inquiry.source_revision_refs
    assert result.current.need_refs == (inquiry.need_signal_ref,)
    assert result.current.attention_refs == present.present.attention_refs
    assert result.original_inquiry == inquiry
    assert len(result.current.source_revision_refs) == 3
    assert result.source_pair_revision == initial_poll.source_pair_revision
    if sid == "A":
        assert result.current.source.native_session_id != pair[4]
    else:
        assert result.current.source.native_session_id == pair[1][1].native_session_id
    assert r23b_original_rejoin_inquiry_is_live(result, bridge=f.bridge)
    assert result.original_l1_request_id is None
    assert result.original_choice_ids == ()
    assert result.l1_request_registered is False
    assert result.model_invoked is False
    assert result.l1_input_switched is False
    assert result.intent_committed is False
    assert result.memory_written is False
    assert result.physical_action_issued is False
    assert files(f) == baseline_files
    assert _owner_state(f) == baseline_owner
    assert not f.bridge.physical.active_action_ids
    with pytest.raises((FrozenInstanceError, AttributeError)):
        result.model_invoked = True


@pytest.mark.parametrize("failure", (
    "unbound", "foreign_owner", "foreign_self", "native_session",
    "resident_epoch", "paper_drift", "composite_drift", "registry_drift",
    "second_rejoin", "missing_inquiry",
))
def test_r23b_unregistered_or_stale_original_rejoin_source_holds(
    pair, monkeypatch, failure,
):
    f = pair[0]
    if failure != "unbound":
        _bind(pair)
    sid = "A"
    if failure == "foreign_owner":
        f.bridge.owners["A"] = f.bridge.owners["B"]
    elif failure == "foreign_self":
        sid = "foreign"
    elif failure == "native_session":
        native = f.bridge.sessions["A"]
        native._started = replace(native.started, session_id="foreign-native")
    elif failure == "resident_epoch":
        f.cognitive._states["A"].epoch += 1
    elif failure == "paper_drift":
        # Log growth may yield a freshly qualified source; corrupt the attested
        # Paper ACK rather than treating benign new history as a failure.
        log = f.paper._log_path.read_text()
        assert "P0D_TICK_ACK nonce=88888888" in log
        f.paper._log_path.write_text(log.replace(
            "P0D_TICK_ACK nonce=88888888",
            "P0D_TICK_ACK nonce=00000000", 1,
        ))
    elif failure == "composite_drift":
        cut = f.cognitive._normal_rejoin_source_cut
        f.cognitive._normal_rejoin_source_cut = replace(
            cut, historical_composite=replace(
                cut.historical_composite, paper_log_sha256="0" * 64,
            ),
        )
    elif failure == "registry_drift":
        owner = f.owners["A"]
        owner.pattern_registry = replace(
            owner.pattern_registry, revision=owner.pattern_registry.revision + 1,
        )
    elif failure == "second_rejoin":
        f.cognitive._normal_second_rejoin_cut = object()
    elif failure == "missing_inquiry":
        original = f.cognitive.read_coverage_inquiry_cpu
        monkeypatch.setattr(
            f.cognitive, "read_coverage_inquiry_cpu",
            lambda **kwargs: None if kwargs["self_id"] == "A"
            else original(**kwargs),
        )
    before_files = files(f)
    with pytest.raises((R23BOriginalL1SourceHold, ResidentCognitiveWorkError)):
        f.cognitive.read_rejoined_l1_source_compatibility_cpu(
            bridge=f.bridge, self_id=sid,
        )
    assert files(f) == before_files


def test_r23b_no_existing_l1_request_or_candidates_can_be_forged(pair):
    f = _bind(pair)
    report = f.cognitive.read_rejoined_l1_source_compatibility_cpu(
        bridge=f.bridge, self_id="A",
    )
    with pytest.raises(R23BOriginalL1SourceHold):
        replace(report, original_l1_request_id="forged-request")
    with pytest.raises(R23BOriginalL1SourceHold):
        replace(report, original_choice_ids=("1", "2"))
    with pytest.raises(R23BOriginalL1SourceHold):
        replace(report, l1_request_registered=True)
    with pytest.raises(R23BOriginalL1SourceHold):
        replace(report, intent_committed=True)


def test_r23b_inquiry_need_ref_mismatch_cannot_be_called_compatible(pair, monkeypatch):
    f = _bind(pair)
    original = f.cognitive.read_coverage_inquiry_cpu

    def tampered(**kwargs):
        inquiry = original(**kwargs)
        return (replace(inquiry, need_signal_ref="foreign-need")
                if kwargs["self_id"] == "A" else inquiry)

    monkeypatch.setattr(f.cognitive, "read_coverage_inquiry_cpu", tampered)
    with pytest.raises(R23BOriginalL1SourceHold):
        f.cognitive.read_rejoined_l1_source_compatibility_cpu(
            bridge=f.bridge, self_id="A",
        )


def test_r23b_cached_report_invalidates_on_paper_change(pair):
    f = _bind(pair)
    report = f.cognitive.read_rejoined_l1_source_compatibility_cpu(
        bridge=f.bridge, self_id="B",
    )
    assert r23b_original_rejoin_inquiry_is_live(report, bridge=f.bridge)
    with f.paper._log_path.open("a") as stream:
        stream.write("R23B_EXTERNAL_NEW_PAPER\n")
    assert not r23b_original_rejoin_inquiry_is_live(report, bridge=f.bridge)


def test_r23b_paper_race_between_original_reads_holds(pair, monkeypatch):
    f = _bind(pair)
    original = f.cognitive.poll_normal_present_cpu
    calls = 0

    def race(**kwargs):
        nonlocal calls
        result = original(**kwargs)
        calls += 1
        if calls == 1:
            with f.paper._log_path.open("a") as stream:
                stream.write("R23B_READ_RACE\n")
        return result

    monkeypatch.setattr(f.cognitive, "poll_normal_present_cpu", race)
    with pytest.raises(R23BOriginalL1SourceHold):
        f.cognitive.read_rejoined_l1_source_compatibility_cpu(
            bridge=f.bridge, self_id="A",
        )
    assert calls >= 1


@pytest.mark.parametrize("value", (None, object(), "unregistered-l1"))
def test_r23b_unknown_report_cannot_be_live(pair, value):
    f = _bind(pair)
    assert not r23b_original_rejoin_inquiry_is_live(value, bridge=f.bridge)
