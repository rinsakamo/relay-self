"""Stage-3 saved-W4 projection comparisons. Synthetic source bytes only."""
from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError, replace

import pytest

from adapters.mineflayer.self_world_cognitive_w4_compare import (
    W4CognitiveComparisonBlocked,
    prepare_w4_cognitive_context_comparison,
)
from adapters.mineflayer.self_world_observation_only_cognition import (
    W4CognitionInputBlocked,
)
from adapters.mineflayer.self_world_observation_only_epoch_replay import (
    W4OfflineEpochBlocked,
    replay_w4_saved_self_world_epochs,
)
from relay_self.cognition_view import CognitionTier
from relay_self.relay_engine import ProviderDecision, RelayEngine
from relay_self.self_world import WorldOrigin
from test_self_world_observation_only_epoch_replay import _case, _pin


def _replay(tmp_path, *, target_before=False, later="zombie", gap=8):
    root = tmp_path / "synthetic"
    report = _case(root, target_before=target_before, later_kind=later)
    pins = _pin(root, report)
    original_hashes = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.iterdir() if p.is_file()
    }
    result = replay_w4_saved_self_world_epochs(
        **pins, max_native_seq_gap=gap,
    )
    return root, original_hashes, result


def _read(request):
    return {v.key: json.loads(v.value_json) for v in request.context}


@pytest.mark.parametrize("tier,ceiling", [
    (CognitionTier.L0, 4),
    (CognitionTier.L1, 16),
    (CognitionTier.L2, 32),
])
@pytest.mark.parametrize("later,expected", [
    ("zombie", "match"),
    ("skeleton", "mismatch"),
    ("missing", "undetermined"),
])
def test_two_epoch_saved_source_context_vs_fixed_baseline(
    tmp_path, tier, ceiling, later, expected,
):
    root, original, replay = _replay(
        tmp_path, target_before=True, later=later,
    )
    pair = prepare_w4_cognitive_context_comparison(
        replay, tier=tier, max_world_facts=32,
    )
    assert pair.baseline.review_status == expected
    assert pair.source_head == replay.source_head
    assert pair.report_sha256 == replay.report_sha256
    assert pair.run_id == replay.run_id
    assert pair.prior_view.tier is pair.following_view.tier is tier
    assert pair.prior_view.world_source_ref == replay.prior.observation.source_ref
    assert pair.following_view.world_source_ref == replay.following.observation.source_ref
    assert pair.prior_view.body_status == pair.following_view.body_status == "UNKNOWN"
    assert pair.prior_view.body_facts == pair.following_view.body_facts == ()
    assert pair.prior_view.world_status == "UNVERIFIED_FRESHNESS"
    assert pair.following_view.world_status == "UNVERIFIED_FRESHNESS"
    assert pair.prior_view.world_revision is pair.following_view.world_revision is None
    assert pair.following_view.coverage_truncated is not None
    assert len(pair.prior_view.world_facts) <= ceiling
    assert len(pair.following_view.world_facts) <= ceiling
    assert all(
        f.origin is WorldOrigin.OBSERVED
        for f in pair.following_view.world_facts
    )
    for old, new in (
        (pair.baseline.prior_bounded, pair.prior_bounded),
        (pair.baseline.following_bounded, pair.following_bounded),
        (pair.baseline.prior_open, pair.prior_open),
        (pair.baseline.following_open, pair.following_open),
    ):
        assert new.context[:len(old.context)] == old.context
        assert new.instruction == old.instruction
        assert new.request_id == old.request_id
        assert len(new.context) == len(old.context) + 3
        context = _read(new)
        assert context["self_cognitive_source"]["world_revision"] is None
        assert context["self_cognitive_source"]["body_status"] == "UNKNOWN"
        assert context["self_cognitive_body"] == []
        assert not hasattr(new, "issue_action")
    assert pair.following_context_bytes_projected > pair.following_context_bytes_baseline
    assert pair.prior_context_bytes_projected > pair.prior_context_bytes_baseline
    if later == "missing":
        assert pair.following_view.world_facts == ()
        assert _read(pair.following_bounded)["self_cognitive_world"] == []
        assert pair.baseline.review_status == "undetermined"
    assert all(getattr(pair, key) == 0 for key in (
        "model_calls", "physical_actions", "outcomes",
        "memory_writes", "s10_updates",
    ))
    assert not pair.source_world_qualified and not pair.science_qualified
    with pytest.raises(FrozenInstanceError):
        pair.tier = CognitionTier.L0
    assert original == {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.iterdir() if p.is_file()
    }


def test_zero_positive_source_does_not_imply_absence_or_safe(tmp_path):
    _, _, replay = _replay(tmp_path, target_before=False)
    pair = prepare_w4_cognitive_context_comparison(
        replay, tier=CognitionTier.L2,
    )
    assert pair.prior_view.world_facts == ()
    assert pair.baseline.prior_selected == 0
    assert pair.following_view.world_facts  # positive following source
    assert not hasattr(pair.prior_view, "safe")
    assert "REQUEST_FRESH_WORLD_OBSERVATION" not in (
        pair.prior_view.information_options
    )  # source exists but is spatially bounded
    assert pair.prior_view.coverage_truncated is False


def test_stub_cognition_can_choose_differently_from_same_saved_world(tmp_path):
    _, _, replay = _replay(tmp_path, target_before=True, later="zombie")
    pair = prepare_w4_cognitive_context_comparison(
        replay, tier=CognitionTier.L1,
    )
    calls = []

    def provider(request, *, mode):
        keys = _read(request)
        calls.append((request.request_id, mode))
        # Only a deliberately synthetic context-sensitive policy; it does
        # not validate improvements over the existing W4 richer context.
        new = keys.get("self_cognitive_world", [])
        choice = (
            "INSPECT_SOURCE" if any(
                fact["key"] == "world.entity_ref"
                and fact["origin"] == "observed"
                for fact in new
            )
            else "DEFER_RECHECK"
        )
        return ProviderDecision.resolved(choice, reason="synthetic only")

    engine = RelayEngine(provider)
    original = engine(pair.baseline.following_bounded)
    projected = engine(pair.following_bounded)
    assert original.choice_id == "DEFER_RECHECK"
    assert projected.choice_id == "INSPECT_SOURCE"
    assert original.provider_call_count == projected.provider_call_count == 1
    assert pair.model_calls == pair.physical_actions == pair.s10_updates == 0
    assert len(calls) == 2
    assert pair.following_bounded.choices == pair.baseline.following_bounded.choices


def test_input_preparation_never_executes_model_or_world(tmp_path, monkeypatch):
    _, _, replay = _replay(tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("input preparation invoked LLM, World or Action")

    monkeypatch.setattr(RelayEngine, "__call__", forbidden)
    monkeypatch.setattr(RelayEngine, "open", forbidden)
    pair = prepare_w4_cognitive_context_comparison(
        replay, tier=CognitionTier.L0,
    )
    assert pair.model_calls == pair.physical_actions == 0


def test_reject_counterfeit_or_cross_owner_w4_source(tmp_path):
    _, _, replay = _replay(tmp_path, target_before=True)
    for change in (
        replace(replay, physical_action_count=1),
        replace(replay, world_qualification=True),
        replace(replay, following=replace(replay.following, self_id="B")),
        replace(replay, following=replace(replay.following, self_body=object())),
        replace(replay, source_head="bogus"),
        replace(replay, prediction_review=replace(
            replay.prediction_review, reason_code="invented-reward",
        )),
    ):
        with pytest.raises((W4CognitionInputBlocked, W4CognitiveComparisonBlocked)):
            prepare_w4_cognitive_context_comparison(
                change, tier=CognitionTier.L1,
            )
    with pytest.raises(W4CognitiveComparisonBlocked, match="tier"):
        prepare_w4_cognitive_context_comparison(
            replay, tier="L2",
        )
    with pytest.raises(ValueError, match="budgets"):
        prepare_w4_cognitive_context_comparison(
            replay, tier=CognitionTier.L1, max_world_facts=33,
        )


def test_missing_or_tampered_pinned_report_is_not_replayable(tmp_path):
    root = tmp_path / "source"
    report = _case(root, target_before=True)
    kwargs = _pin(root, report)
    (root / "report.json").write_bytes(b"{}\n")
    with pytest.raises(W4OfflineEpochBlocked):
        replay_w4_saved_self_world_epochs(**kwargs)
