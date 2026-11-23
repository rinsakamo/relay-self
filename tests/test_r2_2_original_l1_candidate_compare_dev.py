"""R2-2 DEV: compare *existing* Original B L1 choice and R2-1 Context.

The original I/B turn is generated outside the audited comparison. A/B,
paper/source/Owner/choice drifts remain CPU-only; no model, Native or World.
"""
from dataclasses import FrozenInstanceError, replace

import pytest

from relay_self.i_unified_b_exploration_dev import (
    prepare_i_unified_exploration_turn,
)
from relay_self.r2_2_original_l1_candidate_compare_dev import (
    R22CandidateContextComparison,
    R22CandidateContextHold,
    compare_r2_2_original_l1_candidate_context,
)
from test_bd1b_coverage_adoption_turn_dev import arguments
from test_bd1b_issuer_readback_dev import snapshot
from test_bd1b_owner_present_dev import _configured
from test_bd1b_owner_source_dev import _files


def _compare(case, receipt, **overrides):
    kw = {
        k: v for k, v in arguments(case, receipt.self_id).items() if k != "self_id"
    }
    kw.update(overrides)
    return compare_r2_2_original_l1_candidate_context(receipt=receipt, **kw)


@pytest.mark.parametrize("sid", ("A", "B"))
def test_r2_2_existing_original_l1_request_aligned_without_new_owner_or_effects(
    tmp_path, monkeypatch, sid,
):
    case = _configured(tmp_path, monkeypatch, need=True)
    bridge = case[1]
    receipt = prepare_i_unified_exploration_turn(**arguments(case, sid))
    original = receipt.original_turn
    original_request = original.request
    initial_files, initial_state = _files(bridge), snapshot(case)

    result = _compare(case, receipt)

    assert type(result) is R22CandidateContextComparison
    assert result.original_request_id == original_request.request_id
    assert result.original_question_ref == original_request.focus
    assert result.original_choice_ids == ("1", "2", "3")
    assert result.original_need_signal_ref == original.inquiry.need_signal_ref
    assert result.current_source_revision_refs == original.inquiry.source_revision_refs
    assert result.current_owner_epoch == 1
    assert bridge.cognitive_work.owners[sid] is original.owner
    assert original.request is original_request
    assert result.original_request_unchanged is True
    assert result.context_matches_original_l1_source is True
    assert result.model_invoked is False
    assert result.l1_input_switched is False
    assert result.question_adopted is False
    assert result.memory_written is False
    assert result.action_issue_authorized is False
    assert snapshot(case) == initial_state
    assert _files(bridge) == initial_files
    with pytest.raises((FrozenInstanceError, AttributeError)):
        result.l1_input_switched = True


@pytest.mark.parametrize("failure", (
    "paper", "owner", "owner_epoch", "world", "registry", "intent", "source",
    "turn_unregistered", "gpu_connected",
))
def test_r2_2_refuses_retired_or_foreign_original_l1_candidate(
    tmp_path, monkeypatch, failure,
):
    case = _configured(tmp_path, monkeypatch, need=True)
    bridge = case[1]
    receipt = prepare_i_unified_exploration_turn(**arguments(case))
    kwargs = {}
    if failure == "paper":
        bridge.paper._session_id = "replaced-paper"
    elif failure == "owner":
        bridge.owners["A"] = bridge.owners["B"]
    elif failure == "owner_epoch":
        bridge.cognitive_work._states["A"].epoch += 1
    elif failure == "world":
        kwargs["world"] = replace(case[3], epoch=case[3].epoch + 1)
    elif failure == "registry":
        old = bridge.owners["A"].pattern_registry
        bridge.owners["A"].pattern_registry = replace(old, revision=old.revision + 1)
    elif failure == "intent":
        from relay_self.provenance import Provenance

        bridge.owners["A"].intent.commit(
            "new-original-intent", objective="change", at_ns=1,
            provenance=Provenance("cpu-test", "intent-drift"),
        )
    elif failure == "source":
        obs = bridge.owners["A"].current_worldbody_observation
        bridge.owners["A"].current_worldbody_observation = replace(obs)
    elif failure == "turn_unregistered":
        del bridge.cognitive_work._coverage_adoption_turns[receipt.original_turn.work_ref]
    else:
        bridge.inference_lane = object()

    before = _files(bridge)
    with pytest.raises(R22CandidateContextHold):
        _compare(case, receipt, **kwargs)
    assert _files(bridge) == before


@pytest.mark.parametrize("change", ("choices", "request_id", "need", "focus"))
def test_r2_2_tampered_request_cannot_replace_original_issued_choices(
    tmp_path, monkeypatch, change,
):
    case = _configured(tmp_path, monkeypatch, need=True)
    receipt = prepare_i_unified_exploration_turn(**arguments(case))
    original_turn = receipt.original_turn
    if change == "choices":
        forged = replace(original_turn, request=replace(
            original_turn.request, choices=tuple(reversed(original_turn.request.choices)),
        ))
    elif change == "request_id":
        forged = replace(original_turn, request=replace(
            original_turn.request, request_id="replaced-original-request",
        ))
    elif change == "need":
        forged = replace(original_turn, inquiry=replace(
            original_turn.inquiry, need_signal_ref="forged-need",
        ))
    else:
        forged = replace(original_turn, request=replace(
            original_turn.request, focus="forged-question",
        ))
    before = _files(case[1])
    try:
        replaced = replace(receipt, original_turn=forged)
    except (ValueError, RuntimeError):
        assert _files(case[1]) == before
        return
    with pytest.raises(R22CandidateContextHold):
        _compare(case, replaced)
    assert _files(case[1]) == before


def test_r2_2_forged_context_from_other_original_self_fails_closed(
    tmp_path, monkeypatch,
):
    case = _configured(tmp_path, monkeypatch, need=True)
    a = prepare_i_unified_exploration_turn(**arguments(case))
    b = prepare_i_unified_exploration_turn(**arguments(case, "B"))
    resident = case[1].cognitive_work
    real = resident.read_context_shadow_cpu

    def foreign(**kwargs):
        return real(**{**kwargs, "self_id": "B"})

    monkeypatch.setattr(resident, "read_context_shadow_cpu", foreign)
    with pytest.raises(R22CandidateContextHold):
        _compare(case, a)
    assert b.original_turn.request.request_id != a.original_turn.request.request_id


def test_r2_2_paper_race_between_original_request_and_shadow_recheck(
    tmp_path, monkeypatch,
):
    import relay_self.r2_2_original_l1_candidate_compare_dev as module

    case = _configured(tmp_path, monkeypatch, need=True)
    receipt = prepare_i_unified_exploration_turn(**arguments(case))
    original_verify = module.verify_i_unified_exploration_turn
    seen = 0

    def advance_paper_after_first_read(**kwargs):
        nonlocal seen
        original_verify(**kwargs)
        seen += 1
        if seen == 2:
            case[1].paper._session_id = "outside-resident-lock-paper-drift"

    monkeypatch.setattr(module, "verify_i_unified_exploration_turn",
                        advance_paper_after_first_read)
    with pytest.raises(R22CandidateContextHold):
        _compare(case, receipt)
    assert seen == 2


@pytest.mark.parametrize("invalid", (None, object(), "not-original-turn"))
def test_r2_2_no_untyped_or_new_candidate_can_be_compared(invalid):
    with pytest.raises(R22CandidateContextHold):
        compare_r2_2_original_l1_candidate_context(
            bridge=None, boot=None, world=None, links=None, receipt=invalid,
        )
