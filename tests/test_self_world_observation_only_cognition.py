"""Two-epoch W4 SelfWorld cognition inputs; synthetic sources ONLY."""
from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, replace

import pytest

from adapters.mineflayer.self_world_observation_only_cognition import (
    W4CognitionInputBlocked,
    prepare_w4_offline_cognition_inputs,
)
from adapters.mineflayer.self_world_observation_only_epoch_replay import (
    replay_w4_saved_self_world_epochs,
)
from relay_self.relay_engine import (
    CognitionMode,
    DecisionStatus,
    ProviderDecision,
    ProviderExpression,
    RelayEngine,
)
from relay_self.provenance import Provenance
from test_self_world_observation_only_epoch_replay import _case, _pin


def _prepare(tmp_path, *, target_before=False, later="zombie", gap=8):
    root = tmp_path / "synthetic"
    report = _case(root, target_before=target_before, later_kind=later)
    replay = replay_w4_saved_self_world_epochs(**_pin(root, report))
    return replay, prepare_w4_offline_cognition_inputs(
        replay, max_native_seq_gap=gap,
    )


def _context(req):
    return {row.key: json.loads(row.value_json) for row in req.context}


def test_empty_real_shaped_source_has_empty_but_observed_probe_context(tmp_path):
    replay, prepared = _prepare(tmp_path)
    assert replay.prior.observation.native_seq == 3
    assert replay.following.observation.native_seq == 5
    assert prepared.prior_selected == prepared.following_selected == 0
    assert prepared.review_status is None
    for request in (
        prepared.prior_bounded, prepared.following_bounded,
        prepared.prior_open, prepared.following_open,
    ):
        fields = _context(request)
        assert fields["self_world_observer"]["status"] == "observed"
        assert fields["self_world_observed"] == []
        assert "self_world_prediction_review" not in fields
        assert "self_world_retained_preference" not in fields
        assert request.intent_id is None
    assert all(getattr(prepared, name) == 0 for name in (
        "model_calls", "action_count", "outcome_count", "s10_update_count",
        "memory_writes",
    ))
    assert not prepared.world_qualified and not prepared.science_qualified
    with pytest.raises(FrozenInstanceError):
        prepared.prior_selected = 2


@pytest.mark.parametrize("later,expected", [
    ("zombie", "match"),
    ("skeleton", "mismatch"),
    ("missing", "undetermined"),
])
def test_source_positive_case_changes_next_epoch_context_not_world(later, expected, tmp_path):
    replay, prepared = _prepare(tmp_path, target_before=True, later=later)
    before = _context(prepared.prior_bounded)
    after = _context(prepared.following_bounded)
    assert len(before["self_world_observed"]) == 1
    assert prepared.prior_selected == 1
    assert prepared.following_selected == (0 if later == "missing" else 1)
    assert "self_world_prediction_review" not in before
    assert prepared.review_status == expected
    assert after["self_world_prediction_review"]["status"] == expected
    assert after["self_world_prediction_review"]["action_success"] is None
    assert _context(prepared.following_open) == after
    assert before["self_world_observer"]["source_ref"] != (
        after["self_world_observer"]["source_ref"]
    )
    if later == "missing":
        assert after["self_world_observed"] == []
        assert after["self_world_prediction_review"]["observed_value"] is None
    assert not prepared.world_qualified


def test_source_gap_does_not_mint_mismatch_or_reward(tmp_path):
    root = tmp_path / "gap"
    report = _case(root, target_before=True, later_kind="skeleton")
    replay = replay_w4_saved_self_world_epochs(
        **_pin(root, report), max_native_seq_gap=1,
    )
    prepared = prepare_w4_offline_cognition_inputs(replay, max_native_seq_gap=1)
    assert prepared.review_status == "undetermined"
    assert _context(prepared.following_bounded)[
        "self_world_prediction_review"
    ]["reason"] == "source_gap_beyond_explicit_bound"
    with pytest.raises(W4CognitionInputBlocked):
        prepare_w4_offline_cognition_inputs(replay, max_native_seq_gap=8)


def test_existing_bounded_think_and_open_consume_only_prepared_input(tmp_path):
    # Synthetic deterministic policy is an input-dependency demo, not actual
    # policy learning, L1 HABIT execution, Action routing, or model success.
    _, prepared = _prepare(tmp_path, target_before=True, later="zombie")
    calls = []

    def provider(request, *, mode):
        fields = _context(request)
        calls.append((request.request_id, mode))
        assert fields["self_world_observer"]["status"] == "observed"
        assert "self_world_retained_preference" not in fields
        if mode is CognitionMode.OPEN:
            return ProviderExpression(
                "hypothesis only", Provenance("synthetic", "offline-expression"),
            )
        if mode is CognitionMode.BOUNDED:
            return ProviderDecision(
                DecisionStatus.UNRESOLVED, None, "synthetic requests THINK",
            )
        assert mode is CognitionMode.THINK
        assert fields["self_world_prediction_review"]["status"] == "match"
        return ProviderDecision(
            DecisionStatus.RESOLVED, "INSPECT_SOURCE", "synthetic only",
        )

    engine = RelayEngine(provider)
    decision = engine(prepared.following_bounded)
    generated = engine.open(prepared.following_open)
    assert decision.choice_id == "INSPECT_SOURCE"
    assert decision.provider_call_count == 2
    assert generated.text == "hypothesis only"
    assert [mode for _, mode in calls] == [
        CognitionMode.BOUNDED, CognitionMode.THINK, CognitionMode.OPEN,
    ]
    assert prepared.model_calls == 0 and prepared.action_count == 0


@pytest.mark.parametrize("attack", [
    "foreign_self", "replay_seq", "counterfeit_attention", "counterfeit_review",
    "fake_action", "fake_world_qualified", "missing_source", "wrong_epoch",
    "fake_memory", "changed_scope", "bad_native_gap", "bad_run_id",
])
def test_forged_epoch_or_authority_is_rejected(tmp_path, attack):
    replay, _ = _prepare(tmp_path, target_before=True)
    if attack == "foreign_self":
        replay = replace(
            replay, following=replace(replay.following, self_id="foreign"),
        )
    elif attack == "replay_seq":
        obs = replace(
            replay.following.observation,
            native_seq=replay.prior.observation.native_seq,
        )
        replay = replace(replay, following=replace(replay.following, observation=obs))
    elif attack == "counterfeit_attention":
        replay = replace(
            replay, following_attention=replay.prior_attention,
        )
    elif attack == "counterfeit_review":
        replay = replace(replay, prediction_review=replace(
            replay.prediction_review, reason_code="reward_GRANTED",
        ))
    elif attack == "fake_action":
        replay = replace(replay, physical_action_count=1)
    elif attack == "fake_world_qualified":
        replay = replace(replay, world_qualification=True)
    elif attack == "missing_source":
        replay = replace(replay, following=replace(replay.following, observation=None))
    elif attack == "wrong_epoch":
        replay = replace(replay, following=replace(replay.following, epoch_id="other"))
    elif attack == "fake_memory":
        replay = replace(
            replay, retained_memory_written=True,
        )
    elif attack == "changed_scope":
        replay = replace(replay, source_scope="EXTERNAL_ATTESTED_WORLD")
    elif attack == "bad_native_gap":
        with pytest.raises(W4CognitionInputBlocked):
            prepare_w4_offline_cognition_inputs(replay, max_native_seq_gap=0)
        return
    else:
        replay = replace(replay, run_id="different")
    with pytest.raises((W4CognitionInputBlocked, ValueError)):
        prepare_w4_offline_cognition_inputs(replay)
