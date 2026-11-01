"""MP10 synthetic typed-body contract; no real World is created by these tests."""
from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from adapters.mineflayer.self_body_s50_l1_mp9_selector import (
    freeze_from_paper_lock,
    train_mp8_only,
)
from adapters.mineflayer.self_body_s50_l1_mp10_revision import (
    MP10Rejected,
    propose_from_typed_next_epoch,
)
from adapters.mineflayer.self_body_s50_live_next_epoch import LiveNextEpochLease
from test_s50_live_paper_window import capture
from test_self_body_s50_live_next_epoch import next_source, prior_body


def typed_source():
    async def run():
        lease = LiveNextEpochLease(prior_body(), capture())
        await lease.observe_original_l0_probe(next_source())
        return lease.take_once()
    return asyncio.run(run())


def ticket_for(readout, *, mode="NORMAL"):
    window = readout.prior_window
    return freeze_from_paper_lock(
        train_mp8_only(), {
            "status": "REAL_PAPER_PRE_ACTION_SURFACE_LOCK",
            "mode": "GRASS_BLOCK_5X5_READONLY" if mode == "NORMAL" else "PACKED_ICE_5X5",
            "target_material": "GRASS_BLOCK" if mode == "NORMAL" else "PACKED_ICE",
            "original_material": "GRASS_BLOCK", "blocks_verified": "25",
            "on_ground": "true",
            "world": window.paper_world_uuid,
            "subject_uuid": window.subject_uuid,
        }, mode=mode,
    )


def test_real_typed_next_epoch_view_can_propose_without_l0_change():
    readout = typed_source()
    ticket = ticket_for(readout)
    c = propose_from_typed_next_epoch(readout, ticket, train_mp8_only(),
                                      trigger_threshold_m=0.0)
    assert c.session_id == readout.current_body.session_id
    assert c.native_observation_ref == readout.current_body.observation.source_ref
    assert c.action_id == readout.prior_action_id
    assert c.world_uuid == readout.prior_window.paper_world_uuid
    assert c.observed_pair_count == 7
    assert c.old_mae_m >= 0
    assert 0 <= c.proposed_slope <= 2
    assert c.status in ("REVISE_CANDIDATE_IN_SAMPLE_ONLY",
                        "ABSTAIN_INSUFFICIENT_MOTION",
                        "ABSTAIN_NO_EFFECTIVE_COEFFICIENT_CHANGE",
                        "ABSTAIN_NO_IN_SAMPLE_MAE_GAIN")
    assert c.future_heldout_mae_m == "NOT_OBSERVED"
    assert c.durable_learning_admissions == 0
    assert not c.current_l0_action_modified


def test_small_error_keeps_prior_or_abstains_without_promoting_memory():
    r = typed_source()
    t = ticket_for(r)
    c = propose_from_typed_next_epoch(r, t, train_mp8_only(),
                                      trigger_threshold_m=0.1)
    assert c.status in ("KEEP_NO_MATERIAL_ERROR", "ABSTAIN_INSUFFICIENT_MOTION")
    assert c.proposed_slope == c.previous_slope


@pytest.mark.parametrize("case", [
    "foreign_world", "foreign_subject", "foreign_action", "different_native_session",
    "replayed_typed_epoch", "not_native_body", "claimed_final_paper",
    "paper_not_provisional", "foreign_model", "ticket_mutation",
    "nonfinite_samples", "out_of_order_ticks", "nonzero_learning",
])
def test_forged_or_unqualified_source_never_returns_revision(case):
    r = typed_source()
    t = ticket_for(r)
    p = train_mp8_only()
    w = r.prior_window
    if case == "foreign_world":
        t = replace(t, world_uuid="foreign")
    if case == "foreign_subject":
        t = replace(t, subject_uuid="other")
    if case == "foreign_action":
        r = replace(r, prior_action_id="foreign")
    if case == "different_native_session":
        r = replace(r, current_body=replace(r.current_body, session_id="foreign"))
    if case == "replayed_typed_epoch":
        r = replace(r, current_world=replace(r.current_world, self_body=prior_body()))
    if case == "not_native_body":
        r = replace(r, current_body={})
    if case == "claimed_final_paper":
        r = replace(r, paper_source_finalized=True)
    if case == "paper_not_provisional":
        r = replace(r, prior_window=replace(w, provisional=False))
    if case == "foreign_model":
        p = replace(p, normal_slope=0.123)
    if case == "ticket_mutation":
        t = replace(t, selected_slope=0.4)
    if case == "nonfinite_samples":
        samples = list(w.ticks)
        samples[0] = replace(samples[0], displacement_m=float("nan"))
        r = replace(r, prior_window=replace(w, ticks=tuple(samples)))
    if case == "out_of_order_ticks":
        samples = list(w.ticks)
        samples[2] = replace(samples[2], world_tick=samples[1].world_tick)
        r = replace(r, prior_window=replace(w, ticks=tuple(samples)))
    if case == "nonzero_learning":
        r = replace(r, learning_updates=1)
    with pytest.raises(MP10Rejected):
        propose_from_typed_next_epoch(r, t, p)


def test_inappropriate_thresholds_fail_closed():
    r = typed_source()
    t = ticket_for(r)
    for value in (None, 0.3, float("nan"), "0.01", -0.2):
        with pytest.raises(MP10Rejected):
            propose_from_typed_next_epoch(r, t, train_mp8_only(),
                                          trigger_threshold_m=value)

def test_exact_same_slope_should_abstain_even_when_threshold_zero():
    r = typed_source()
    prior = train_mp8_only()
    slope = prior.normal_slope
    current = 0.1
    seq = []
    for tick in r.prior_window.ticks:
        seq.append(replace(tick, displacement_m=float(current)))
        current *= slope
    r = replace(r, prior_window=replace(r.prior_window, ticks=tuple(seq)))
    c = propose_from_typed_next_epoch(
        r, ticket_for(r), prior, trigger_threshold_m=0.0,
    )
    assert c.status == "ABSTAIN_NO_EFFECTIVE_COEFFICIENT_CHANGE"
    assert c.proposed_slope == c.previous_slope
    assert c.durable_learning_admissions == 0


def test_7_pairs_with_real_improvement_generate_only_in_sample_candidate():
    r = typed_source()
    seq = []
    current = 0.1
    for tick in r.prior_window.ticks:
        seq.append(replace(tick, displacement_m=float(current)))
    r = replace(r, prior_window=replace(r.prior_window, ticks=tuple(seq)))
    c = propose_from_typed_next_epoch(
        r, ticket_for(r), train_mp8_only(), trigger_threshold_m=0.002,
    )
    assert c.status == "REVISE_CANDIDATE_IN_SAMPLE_ONLY"
    assert c.proposed_slope == pytest.approx(1.0)
    assert c.proposed_in_sample_mae_m < c.old_mae_m
    assert c.future_heldout_mae_m == "NOT_OBSERVED"
