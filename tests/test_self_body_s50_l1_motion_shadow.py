"""S49/Body route B -> experience-conditioned L1 attention contrast only."""
from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

import test_postmain_s42_world_contrast as s42
from adapters.mineflayer.self_body_s50_l1_motion_shadow import (
    L1AttentionCandidate,
    L1MotionContrast,
    L1MotionShadowRejected,
    compare_l1_motion_attention_shadow,
)
from adapters.mineflayer.self_body_s50_live_next_epoch import LiveNextEpochLease
from relay_self.world_conditioned_choice import (
    WorldChoiceKind,
    select_world_conditioned_choice,
)
from test_s50_live_paper_window import capture
from test_self_body_s50_live_next_epoch import next_source, prior_body


def real_type_pair():
    # S42's retained fixture runs its own asynchronous S19 original, so it
    # MUST finish before this route B coroutine starts its event loop.
    retained, _, far_native, _, _ = s42._pair()
    original_s_choice = select_world_conditioned_choice(
        far_native, retained,
        expected_session_id=far_native.observation.session_id,
        expected_entity_id=far_native.entity_id,
    )

    async def run():
        lease = LiveNextEpochLease(prior_body(), capture())
        await lease.observe_original_l0_probe(next_source())
        readout = lease.take_once()
        native = readout.current_body.observation
        choice = replace(
            original_s_choice, session_id=readout.current_body.session_id,
            probe_seq=native.native_seq, request_id=native.request_id,
            provenance=native.source_provenance,
            selection=WorldChoiceKind.WAIT,
        )
        return readout, choice
    return asyncio.run(run())


def test_prior_movement_changes_attention_not_action_and_matches_one_bit_cheap():
    readout, choice = real_type_pair()
    result = compare_l1_motion_attention_shadow(readout, choice)
    assert result.current_native_source_ref == readout.current_body.observation.source_ref
    assert result.current_s_choice is WorldChoiceKind.WAIT
    assert result.previous_motion_ticks == (251, 252)
    assert result.without_experience is L1AttentionCandidate.ABSTAIN_NO_PRIOR
    assert result.with_experience is L1AttentionCandidate.RECHECK_SETTLING
    assert result.attention_candidate_differs
    assert result.cheap_same_information is result.with_experience
    assert result.contrast is L1MotionContrast.CHEAP_EQUIVALENT
    assert not result.learned_l1_policy
    assert not result.cognitive_priority_committed
    assert result.original_s_choice_kept
    assert result.current_native_present_unchanged
    assert not result.paper_input_is_full_tick
    assert not result.effective_clear_tick_attested
    assert not result.goal_admitted
    assert result.l10_training_episodes == 0
    assert result.s10_updates == result.s11_grants == result.p1_wait_admitted == 0
    assert result.new_native_probes == result.extra_actions == result.model_calls == 0


def test_no_sampled_motion_makes_only_nonphysical_unproven_attention():
    readout, choice = real_type_pair()
    quiet_ticks = tuple(replace(t, displacement_m=0.0) for t in readout.prior_window.ticks)
    source = replace(readout, prior_window=replace(readout.prior_window, ticks=quiet_ticks))
    result = compare_l1_motion_attention_shadow(source, choice)
    assert result.with_experience is L1AttentionCandidate.NO_SAMPLED_MOTION
    assert result.contrast is L1MotionContrast.NO_CHANGE
    assert result.attention_candidate_differs is False
    assert result.with_experience is result.cheap_same_information
    assert not result.goal_admitted


@pytest.mark.parametrize("attack", [
    "untyped_readout", "untyped_choice", "foreign_session",
    "foreign_probe", "foreign_provenance", "altered_world_source",
    "altered_world_identity", "wrong_action", "repeated_native",
    "false_goals", "false_rest", "claim_final_paper", "claim_node_complete",
    "prior_no_ticks", "noncontiguous", "not_wait", "action_grant",
])
def test_source_and_authority_fences_fail_closed(attack):
    readout, choice = real_type_pair()
    if attack == "untyped_readout":
        readout = {"session": "fake"}
    elif attack == "untyped_choice":
        choice = {"selection": "WAIT"}
    elif attack == "foreign_session":
        choice = replace(choice, session_id="foreign")
    elif attack == "foreign_probe":
        choice = replace(choice, probe_seq=choice.probe_seq + 1)
    elif attack == "foreign_provenance":
        from relay_self.provenance import Provenance
        choice = replace(choice, provenance=Provenance("operator", "fake"))
    elif attack == "altered_world_source":
        exterior = replace(
            readout.current_world.observation,
            native_seq=readout.current_world.observation.native_seq + 1,
        )
        readout = replace(readout, current_world=replace(
            readout.current_world, observation=exterior,
        ))
    elif attack == "altered_world_identity":
        readout = replace(readout, current_world=replace(
            readout.current_world, self_body=prior_body(),
        ))
    elif attack == "wrong_action":
        readout = replace(readout, prior_action_id="other-action")
    elif attack == "repeated_native":
        readout = replace(
            readout, prior_native_ref=readout.current_body.observation.source_ref,
        )
    elif attack == "false_goals":
        readout = replace(readout, prior_window=replace(
            readout.prior_window, goal_admitted=True,
        ))
    elif attack == "false_rest":
        readout = replace(readout, prior_window=replace(
            readout.prior_window, physical_stability_attested=True,
        ))
    elif attack == "claim_final_paper":
        readout = replace(readout, prior_window=replace(
            readout.prior_window, final_source_verified=True,
        ))
    elif attack == "claim_node_complete":
        readout = replace(readout, prior_window=replace(
            readout.prior_window, node_trace_complete=True,
        ))
    elif attack == "prior_no_ticks":
        readout = replace(readout, prior_window=replace(
            readout.prior_window, ticks=(),
        ))
    elif attack == "noncontiguous":
        rows = readout.prior_window.ticks
        readout = replace(readout, prior_window=replace(
            readout.prior_window, ticks=(
                rows[0], replace(rows[1], world_tick=999), *rows[2:],
            ),
        ))
    elif attack == "not_wait":
        choice = replace(choice, selection=WorldChoiceKind.MOVE_AWAY)
    else:
        choice = replace(choice, action_authorized=True)
    with pytest.raises(L1MotionShadowRejected):
        compare_l1_motion_attention_shadow(readout, choice)


def test_host_shadow_opt_in_default_off_and_requires_live_route_b(tmp_path, monkeypatch):
    import inspect

    from adapters.mineflayer import self_body_s50_world_dev as host

    signature = inspect.signature(host.qualify)
    assert signature.parameters["l1_motion_shadow_dev"].default is False
    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    out = tmp_path / "report.json"
    assert asyncio.run(host.qualify(
        out, tmp_path / "server.log", l1_motion_shadow_dev=True,
    )) != 0
    assert "requires existing route B" in out.read_text()
