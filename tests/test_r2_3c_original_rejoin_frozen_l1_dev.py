"""R2-3c: first-reJOIN Original Owner frozen Question L1 CPU-only tests.

Uses existing original Bridge/Paper synthetic event fixtures. No real
World/Gemma, no GPU submission, Question adoption, Intent or Physical issue.
"""
from dataclasses import FrozenInstanceError, replace

import pytest

from relay_self.bd1b_coverage_adoption_turn_dev import (
    CHOICES,
    CoverageAdoptionTurnHold,
    validate_coverage_adoption_turn_cpu,
)
from relay_self.r2_3c_original_rejoin_frozen_l1_dev import (
    R23CFrozenOriginalRejoinL1,
    R23COriginalRejoinL1Comparison,
    R23COriginalRejoinRequestHold,
    compare_r23c_registered_l1_context,
    r23c_original_l1_request_is_live,
)
from relay_self.resident_cognitive_work_owner_dev import ResidentCognitiveWorkError
from test_b_np1b_current_composite_source_dev import current as current_fixture
from test_b_np1b_fresh_native_update_dev import files
from test_b_np1b_normal_present_poll_dev import pair as pair
from test_b_np1b_owner_bound_rejoin_dev import rejoined as rejoined
from test_b_np1b_rejoin_present_dev import rejoined_present as rejoined_present


def _bind(pair):
    assert current_fixture is not None and rejoined is not None and rejoined_present is not None
    f = pair[0]
    f.bridge.bind_normal_rejoin_present_cpu(
        initial_receipts=pair[1], historical_composite=pair[3],
    )
    return f


def _state(f):
    return {
        sid: (
            owner.retained, owner.intent.events, owner.pattern_registry,
            dict(owner.skills), tuple(owner.pending_questions),
            owner.supervisor.open_actions,
        )
        for sid, owner in f.owners.items()
    }


@pytest.mark.parametrize("sid", ("A", "B"))
def test_r23c_original_owner_freezes_registered_first_rejoin_question_request(pair, sid):
    f = _bind(pair)
    before_files, before = files(f), _state(f)
    old_keys = set(f.cognitive._coverage_adoption_turns)
    turn = f.cognitive.prepare_rejoined_original_l1_request_cpu(
        bridge=f.bridge, self_id=sid,
    )
    assert type(turn) is R23CFrozenOriginalRejoinL1
    assert f.cognitive._coverage_adoption_turns.get(turn.work_ref) is turn
    assert set(f.cognitive._coverage_adoption_turns) == old_keys | {turn.work_ref}
    assert turn.owner is f.owners[sid]
    assert turn.owner is f.cognitive.owners[sid]
    assert turn.source.original_owner is turn.owner
    assert turn.request.choices is CHOICES
    assert tuple(c.choice_id for c in turn.request.choices) == ("1", "2", "3")
    assert turn.request.focus == turn.source.original_inquiry.question_ref
    assert turn.source.original_inquiry.need_signal_ref in (
        s.envelope.event_id for s in turn.source.current.signals
    )
    assert len(turn.source.current.source_revision_refs) == 3
    original_pair = f.bridge.poll_normal_present_cpu()
    present = original_pair.a_present if sid == "A" else original_pair.b_present
    assert turn.source.current.need_refs == present.present.need_refs
    if sid == "A":
        assert turn.source.current.source.native_session_id != pair[4]
    else:
        assert turn.source.current.source.native_session_id == pair[1][1].native_session_id
    report = f.cognitive.compare_rejoined_original_l1_request_cpu(
        bridge=f.bridge, turn=turn,
    )
    independent = compare_r23c_registered_l1_context(
        bridge=f.bridge, turn=turn,
    )
    assert type(report) is R23COriginalRejoinL1Comparison
    assert independent == report
    assert report.original_owner is f.owners[sid]
    assert report.request_id == turn.request.request_id
    assert report.choice_ids == ("1", "2", "3")
    assert report.question_ref == turn.source.original_inquiry.question_ref
    assert report.need_signal_ref == turn.source.original_inquiry.need_signal_ref
    assert report.schema_revision == turn.source.current.schema.revision
    assert report.source_revision_refs == turn.source.current.source_revision_refs
    assert report.request_sha256 == turn.request_sha256
    assert r23c_original_l1_request_is_live(bridge=f.bridge, turn=turn)
    assert report.model_invoked is False
    assert report.l1_input_switched is False
    assert report.action_issue_authorized is False
    assert turn.model_invoked is False
    assert turn.question_adopted is False
    assert turn.intent_committed is False
    assert turn.memory_written is False
    assert turn.physical_authorized is False
    assert files(f) == before_files
    assert _state(f) == before
    assert not f.bridge.physical.active_action_ids
    with pytest.raises(CoverageAdoptionTurnHold):
        # Original Stage28 issuer must not admit a separately typed reJOIN turn.
        validate_coverage_adoption_turn_cpu(
            bridge=f.bridge, boot=None, world=None, links=None, turn=turn,
        )
    with pytest.raises((FrozenInstanceError, AttributeError)):
        turn.model_invoked = True


@pytest.mark.parametrize("tamper", (
    "focus", "choices", "identity", "context", "request_id", "request_digest",
    "owner", "source", "work_ref", "grant",
))
def test_r23c_forged_original_request_is_rejected(pair, tamper):
    f = _bind(pair)
    turn = f.cognitive.prepare_rejoined_original_l1_request_cpu(
        bridge=f.bridge, self_id="A",
    )
    if tamper == "focus":
        patch = {"request": replace(turn.request, focus="foreign-question")}
    elif tamper == "choices":
        patch = {"request": replace(
            turn.request, choices=tuple(reversed(CHOICES)),
        )}
    elif tamper == "identity":
        patch = {"request": replace(turn.request, identity_context=None)}
    elif tamper == "context":
        patch = {"request": replace(turn.request, context=())}
    elif tamper == "request_id":
        patch = {"request": replace(turn.request, request_id="foreign-request")}
    elif tamper == "request_digest":
        patch = {"request_sha256": "0" * 64}
    elif tamper == "owner":
        patch = {"owner": f.owners["B"]}
    elif tamper == "source":
        patch = {"source": replace(
            turn.source, source_pair_revision="other-composite-source",
        )}
    elif tamper == "work_ref":
        patch = {"work_ref": "foreign-request"}
    else:
        patch = {"physical_authorized": True}
    with pytest.raises(R23COriginalRejoinRequestHold):
        replace(turn, **patch)
    assert r23c_original_l1_request_is_live(bridge=f.bridge, turn=turn)


@pytest.mark.parametrize("failure", (
    "foreign_owner", "foreign_epoch", "native_changed", "paper_advanced",
    "schema_changed", "second_rejoin", "intent_changed", "registration_lost",
    "other_self_changed",
))
def test_r23c_registered_request_fences_original_changes(pair, failure):
    f = _bind(pair)
    turn = f.cognitive.prepare_rejoined_original_l1_request_cpu(
        bridge=f.bridge, self_id="A",
    )
    if failure == "foreign_owner":
        f.bridge.owners["A"] = f.bridge.owners["B"]
    elif failure == "foreign_epoch":
        f.cognitive._states["A"].epoch += 1
    elif failure == "native_changed":
        native = f.bridge.sessions["A"]
        native._started = replace(native.started, session_id="foreign-native")
    elif failure == "paper_advanced":
        with f.paper._log_path.open("a") as stream:
            stream.write("R23C_NEW_PAPER_SOURCE\n")
    elif failure == "schema_changed":
        owner = f.owners["A"]
        owner.pattern_registry = replace(
            owner.pattern_registry, revision=owner.pattern_registry.revision + 1,
        )
    elif failure == "second_rejoin":
        f.cognitive._normal_second_rejoin_cut = object()
    elif failure == "intent_changed":
        from relay_self.intent import IntentCommitment

        f.owners["A"].intent = IntentCommitment()
    elif failure == "registration_lost":
        del f.cognitive._coverage_adoption_turns[turn.work_ref]
    else:
        f.cognitive._states["B"].epoch += 1
    assert not r23c_original_l1_request_is_live(bridge=f.bridge, turn=turn)
    with pytest.raises((R23COriginalRejoinRequestHold, ResidentCognitiveWorkError)):
        f.cognitive.compare_rejoined_original_l1_request_cpu(
            bridge=f.bridge, turn=turn,
        )


def test_r23c_no_original_request_when_gpu_already_attached(pair):
    f = _bind(pair)
    before = set(f.cognitive._coverage_adoption_turns)
    f.bridge.inference_lane = object()
    with pytest.raises(R23COriginalRejoinRequestHold):
        f.cognitive.prepare_rejoined_original_l1_request_cpu(
            bridge=f.bridge, self_id="A",
        )
    assert set(f.cognitive._coverage_adoption_turns) == before


def test_r23c_source_race_before_original_registration_refuses(pair, monkeypatch):
    f = _bind(pair)
    original = f.cognitive.read_rejoined_l1_source_compatibility_cpu
    calls = 0
    old_keys = set(f.cognitive._coverage_adoption_turns)

    def external_change(**kw):
        nonlocal calls
        reading = original(**kw)
        calls += 1
        if calls == 1:
            with f.paper._log_path.open("a") as stream:
                stream.write("R23C_RACE_AFTER_FIRST_READ\n")
        return reading

    monkeypatch.setattr(
        f.cognitive, "read_rejoined_l1_source_compatibility_cpu",
        external_change,
    )
    with pytest.raises(R23COriginalRejoinRequestHold):
        f.cognitive.prepare_rejoined_original_l1_request_cpu(
            bridge=f.bridge, self_id="A",
        )
    assert calls >= 1
    assert set(f.cognitive._coverage_adoption_turns) == old_keys


def test_r23c_absent_or_unregistered_request_is_not_l1_admission(pair):
    f = _bind(pair)
    with pytest.raises(R23COriginalRejoinRequestHold):
        f.cognitive.compare_rejoined_original_l1_request_cpu(
            bridge=f.bridge, turn=None,
        )
    # Existing Original Owner rejects a foreign Self before the R2-3c
    # adapter is entered; this is the expected earlier fail-closed fence.
    with pytest.raises((R23COriginalRejoinRequestHold, ResidentCognitiveWorkError)):
        f.cognitive.prepare_rejoined_original_l1_request_cpu(
            bridge=f.bridge, self_id="foreign",
        )
