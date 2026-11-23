"""I Unified original B exploration CPU/GPU contract: synthetic only."""
import asyncio
from dataclasses import replace

import pytest

from adapters.llama_cpp.relay_engine import LlamaCppRelayProvider
from relay_self.i_unified_b_exploration_dev import (
    IUnifiedExplorationHold,
    issue_i_unified_question_once,
    prepare_i_unified_exploration_turn,
    verify_i_unified_exploration_turn,
)
from relay_self.persistent_cognition import load_persistent_cognition
from relay_self.relay_engine import ProviderDecision
from test_bd1b_coverage_adoption_turn_dev import CHOICES, arguments
from test_bd1b_issuer_readback_dev import snapshot
from test_bd1b_owner_present_dev import _configured
from test_bd1b_post_gpu_source_dev import attach


def _args(case, sid="A"):
    return arguments(case, sid)


def _check(case, receipt):
    return verify_i_unified_exploration_turn(
        receipt=receipt, **{k: v for k, v in _args(case).items()
                           if k != "self_id"},
    )


@pytest.mark.parametrize("sid", ("A", "B"))
def test_b_original_current_to_b_registered_l1_turn_is_readonly(
    tmp_path, monkeypatch, sid,
):
    case = _configured(tmp_path, monkeypatch, need=True)
    before = snapshot(case)
    receipt = prepare_i_unified_exploration_turn(**_args(case, sid))
    _check(case, receipt)
    owner = case[1].owners[sid]
    assert owner is receipt.original_owner is case[1].cognitive_work.owners[sid]
    assert receipt.context.current.schema is not None
    assert len(receipt.context.current.signals) == 1
    assert receipt.original_turn.request.choices == CHOICES
    assert receipt.original_turn.inquiry.question_ref == receipt.original_turn.request.focus
    assert receipt.question_adopted is False
    assert receipt.memory_writer is False
    assert receipt.physical_issue_authorized is False
    assert snapshot(case) == before


def test_b_original_missing_exploration_never_mints_question(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=False)
    before = snapshot(case)
    with pytest.raises(IUnifiedExplorationHold):
        prepare_i_unified_exploration_turn(**_args(case))
    assert snapshot(case) == before


@pytest.mark.parametrize("alteration", (
    "foreign_owner", "foreign_self", "forged_source", "forged_need",
    "reversed_choices", "fake_question", "old_generation", "paper",
    "native", "registry", "intent", "fenced",
))
def test_b_original_gateway_refuses_stale_or_foreign(
    tmp_path, monkeypatch, alteration,
):
    case = _configured(tmp_path, monkeypatch, need=True)
    receipt = prepare_i_unified_exploration_turn(**_args(case))
    bridge = case[1]
    before = snapshot(case)
    try:
        if alteration == "foreign_owner":
            receipt = replace(receipt, original_owner=bridge.owners["B"])
        elif alteration == "foreign_self":
            receipt = replace(receipt, self_id="B")
        elif alteration == "forged_source":
            receipt = replace(
                receipt, context=replace(
                    receipt.context,
                    current=replace(
                        receipt.context.current,
                        source=replace(receipt.context.current.source, resident_epoch=999),
                    ),
                ),
            )
        elif alteration == "forged_need":
            receipt = replace(
                receipt, original_turn=replace(
                    receipt.original_turn,
                    inquiry=replace(receipt.original_turn.inquiry, need_signal_ref="forged"),
                ),
            )
        elif alteration == "reversed_choices":
            receipt = replace(
                receipt, original_turn=replace(
                    receipt.original_turn,
                    request=replace(
                        receipt.original_turn.request,
                        choices=tuple(reversed(receipt.original_turn.request.choices)),
                    ),
                ),
            )
        elif alteration == "fake_question":
            receipt = replace(
                receipt, original_turn=replace(
                    receipt.original_turn,
                    inquiry=replace(receipt.original_turn.inquiry, question_ref="not-candidate"),
                ),
            )
        elif alteration == "old_generation":
            bridge.cognitive_work._states["A"].epoch += 1
        elif alteration == "paper":
            bridge.paper._session_id = "new-paper"
        elif alteration == "native":
            bridge.owners["A"].current_worldbody_observation = replace(
                bridge.owners["A"].current_worldbody_observation,
            )
        elif alteration == "registry":
            bridge.owners["A"].pattern_registry = replace(
                bridge.owners["A"].pattern_registry,
                revision=bridge.owners["A"].pattern_registry.revision + 1,
            )
        elif alteration == "intent":
            from relay_self.provenance import Provenance
    
            bridge.owners["A"].intent.commit(
                "new-intent", objective="test", at_ns=100, provenance=Provenance("test", "i"),
            )
        else:
            bridge.cognitive_work.fence_self("A")
    except IUnifiedExplorationHold:
        # Forged typed receipts fail in __post_init__, before any verifier call.
        assert alteration in (
            "foreign_owner", "foreign_self", "forged_source",
            "forged_need", "reversed_choices", "fake_question",
        )
        assert snapshot(case) == before
        return
    with pytest.raises((IUnifiedExplorationHold, RuntimeError, ValueError)):
        _check(case, receipt)
    if alteration in (
        "foreign_owner", "foreign_self", "forged_source", "forged_need",
        "reversed_choices", "fake_question",
    ):
        assert snapshot(case) == before


@pytest.mark.parametrize("decision,selection", (
    (ProviderDecision.resolved("1"), "ADOPT"),
    (ProviderDecision.resolved("2"), "HOLD"),
    (ProviderDecision.resolved("3"), "DECLINE"),
    (ProviderDecision.unresolved(reason="no-decision"), "UNRESOLVED"),
))
def test_b_original_question_issuer_only_owner_writes(
    tmp_path, monkeypatch, decision, selection,
):
    case = _configured(tmp_path, monkeypatch, need=True)
    receipt = prepare_i_unified_exploration_turn(**_args(case))
    before = snapshot(case)
    monkeypatch.setattr(
        LlamaCppRelayProvider, "__call__",
        lambda self, request, mode: decision,
    )
    lane = attach(case[1], monkeypatch)
    try:
        issued = asyncio.run(issue_i_unified_question_once(
            receipt=receipt, lane=lane,
            **{k: v for k, v in _args(case).items() if k != "self_id"},
        ))
        assert issued.selection == selection == issued.readback.selection
        assert issued.ticket.self_id == "A"
        assert issued.ticket.action_issue_authorized is False
        assert issued.ticket.work_ref == receipt.original_turn.work_ref
        if selection != "ADOPT":
            assert snapshot(case) == before
        else:
            owner = receipt.original_owner
            assert owner.retained.exploration_continuity.questions[-1].question_ref == (
                receipt.original_turn.inquiry.question_ref
            )
            assert load_persistent_cognition(owner.files.cognition_file) == owner.retained
        with pytest.raises((RuntimeError, ValueError)):
            asyncio.run(issue_i_unified_question_once(
                receipt=receipt, lane=lane,
                **{k: v for k, v in _args(case).items() if k != "self_id"},
            ))
    finally:
        lane._pool.shutdown(wait=True)
