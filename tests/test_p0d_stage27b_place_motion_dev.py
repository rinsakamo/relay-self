"""Stage27b source-qualified, non-issuing native PLACE geometry tests.

Model HTTP and native WorldBody are synthetic fixtures, not real Paper/Gemma.
"""
from __future__ import annotations

import asyncio
import math
from dataclasses import replace
from unittest.mock import patch

import pytest

from adapters.mineflayer.python_protocol import MineflayerPosition
from relay_self.p0d_stage27b_place_motion_dev import (
    Stage27PlaceResolutionRefusal,
    resolve_stage27_place_motion,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.skill_invocation import SkillBudget
from test_p0d_real_preset_checkpoint_dev import native_probe, source_recovered
from test_p0d_resident_llama_slot_owner_dev import (
    ResidentFixture,
    _SyntheticLlamaServer,
)
from test_p0d_stage26_gemma_l1_dev import _attach_and_audit
from test_p0d_stage27_owned_move_intent_dev import _handoff, _one_a_choice


async def qualified_a(f, lane):
    prepared, ticket, witness, refreshed = await _one_a_choice(f, lane)
    handoff = _handoff(f, lane, prepared, ticket, witness, refreshed)
    return prepared, handoff, refreshed


def _resolve(f, prepared, handoff, observed, **overrides):
    args = dict(
        prepared=prepared, handoff=handoff, observation=observed,
        owner=f.owners[f.names[0]], physical=f.physical,
        world_epoch=prepared.world_epoch,
    )
    args.update(overrides)
    return resolve_stage27_place_motion(**args)


def test_stage27b_world_east_uses_native_target_yaw_not_relative_forward(tmp_path):
    http = _SyntheticLlamaServer()
    http.choice_id = "1"
    endpoint = http.start()
    f = ResidentFixture(tmp_path, 2, cognitive_work=True)
    lane = _attach_and_audit(f, endpoint, tmp_path)

    async def scenario():
        prepared, handoff, fresh = await qualified_a(f, lane)
        peer = f.owners[f.names[1]]
        peer_before = (peer.intent.events, tuple(peer.skills.items()),
                       PhysicalActionJournal.restore(
                           peer.files.physical_wal_file, self_id=peer.self_id,
                       ).digest)
        actual = _resolve(f, prepared, handoff, fresh)
        assert actual.self_id == f.names[0]
        assert actual.invocation_ref == handoff.invocation_ref
        assert actual.parameter_preset_ref == handoff.preset_ref
        assert actual.world_epoch == prepared.world_epoch
        assert actual.native_probe_seq == fresh.seq
        assert actual.native_probe_request_id == fresh.request_id
        assert actual.observation_status == "OUTSIDE"
        assert actual.horizontal_distance_m == pytest.approx(1.0)
        assert actual.gap_to_arrival_envelope_m == pytest.approx(0.4)
        assert actual.preset_max_distance_m == pytest.approx(2.0)
        assert actual.full_envelope_reachable_within_distance_budget
        assert actual.desired_mineflayer_yaw_rad == pytest.approx(-math.pi / 2)
        assert actual.next_step == (
            "NATIVE_LOOK_AND_BOUNDED_MOVE_RESOLUTION_REQUIRED_NOT_ISSUABLE"
        )
        assert not actual.clearance_observed
        assert not actual.facing_aligned_observed
        assert not actual.action_granted
        assert not actual.native_effect_issued
        assert not actual.world_goal_succeeded
        assert (peer.intent.events, tuple(peer.skills.items()),
                PhysicalActionJournal.restore(
                    peer.files.physical_wal_file, self_id=peer.self_id,
                ).digest) == peer_before
        for sid in f.names:
            assert not f.owners[sid].supervisor.open_actions
            PhysicalActionJournal.restore(
                f.owners[sid].files.physical_wal_file, self_id=sid,
            ).require_clear()
        assert len(http.calls) == 1  # no hidden model retry
        for sid in f.names:
            await f.bridge.logout(sid)

    try:
        asyncio.run(scenario())
    finally:
        f.stop_paper()
        http.stop()


def test_stage27b_already_in_target_envelope_does_not_move(tmp_path):
    http = _SyntheticLlamaServer()
    http.choice_id = "1"
    endpoint = http.start()
    f = ResidentFixture(tmp_path, 2, cognitive_work=True)
    lane = _attach_and_audit(f, endpoint, tmp_path)

    async def scenario():
        prepared, handoff, _ = await qualified_a(f, lane)
        sid = f.names[0]
        here = native_probe(sid, 12, session=handoff.native_session_id, x=2.0)
        plan = _resolve(f, prepared, handoff, here)
        assert plan.observation_status == "CONDITION_OBSERVED"
        assert plan.preset_max_distance_m == pytest.approx(2.0)
        assert plan.full_envelope_reachable_within_distance_budget
        assert plan.desired_mineflayer_yaw_rad is None
        assert plan.next_step == (
            "TARGET_GEOMETRY_OBSERVED_AWAIT_INDEPENDENT_GOAL_EVALUATION"
        )
        assert not plan.world_goal_succeeded
        for name in f.names:
            await f.bridge.logout(name)

    try:
        asyncio.run(scenario())
    finally:
        f.stop_paper()
        http.stop()


@pytest.mark.parametrize("fault", [
    "foreign-owner", "wrong-epoch", "stale-seq", "old-native",
    "changed-invocation", "wrong-intent", "wrong-skill",
    "foreign-choice", "already-issued", "wrong-target", "vertical-mismatch",
])
def test_stage27b_fails_closed_on_stale_or_different_goal_geometry(
    tmp_path, fault,
):
    http = _SyntheticLlamaServer()
    http.choice_id = "1"
    endpoint = http.start()
    f = ResidentFixture(tmp_path, 2, cognitive_work=True)
    lane = _attach_and_audit(f, endpoint, tmp_path)

    async def scenario():
        prepared, handoff, fresh = await qualified_a(f, lane)
        sid = f.names[0]
        kwargs = {}
        if fault == "foreign-owner":
            kwargs["owner"] = f.owners[f.names[1]]
        elif fault == "wrong-epoch":
            kwargs["world_epoch"] = prepared.world_epoch + 1
        elif fault == "stale-seq":
            fresh = native_probe(sid, handoff.rechecked_native_seq - 1,
                                 session=handoff.native_session_id)
        elif fault == "old-native":
            fresh = native_probe(
                sid, 12, session=prepared.original_native_session,
            )
        elif fault == "changed-invocation":
            handoff = replace(handoff, invocation_ref="foreign-invocation")
        elif fault == "wrong-intent":
            handoff = replace(handoff, intent_id="foreign-intent")
        elif fault == "wrong-skill":
            handoff = replace(handoff, skill_execution_id="foreign-skill")
        elif fault == "foreign-choice":
            handoff = replace(handoff, decision_number="3")
        elif fault == "already-issued":
            handoff = replace(handoff, physical_action_issued=True)
        elif fault == "wrong-target":
            handoff = replace(handoff, target_ref="foreign-target")
        elif fault == "vertical-mismatch":
            fresh = replace(
                fresh, snapshot=replace(
                    fresh.snapshot, position=MineflayerPosition(1.0, 66.0, 2.0),
                ),
            )
        with pytest.raises(Stage27PlaceResolutionRefusal):
            _resolve(f, prepared, handoff, fresh, **kwargs)
        for name in f.names:
            assert not f.owners[name].supervisor.open_actions
            PhysicalActionJournal.restore(
                f.owners[name].files.physical_wal_file, self_id=name,
            ).require_clear()
            await f.bridge.logout(name)

    try:
        asyncio.run(scenario())
    finally:
        f.stop_paper()
        http.stop()


def test_stage27b_refuses_after_original_actor_logout(tmp_path):
    http = _SyntheticLlamaServer()
    http.choice_id = "1"
    endpoint = http.start()
    f = ResidentFixture(tmp_path, 2, cognitive_work=True)
    lane = _attach_and_audit(f, endpoint, tmp_path)

    async def scenario():
        prepared, handoff, fresh = await qualified_a(f, lane)
        await f.bridge.logout(f.names[0])
        with pytest.raises(Stage27PlaceResolutionRefusal):
            _resolve(f, prepared, handoff, fresh)
        await f.bridge.logout(f.names[1])

    try:
        asyncio.run(scenario())
    finally:
        f.stop_paper()
        http.stop()


def test_too_short_frozen_budget_still_allows_partial_target_plan(tmp_path):
    """Goal achievement is not required to be possible in one bounded pulse."""
    http = _SyntheticLlamaServer()
    http.choice_id = "1"
    endpoint = http.start()
    f = ResidentFixture(tmp_path, 2, cognitive_work=True)
    lane = _attach_and_audit(f, endpoint, tmp_path)

    def source_with_short_budget(sid):
        staged = source_recovered(sid)
        registry = staged.semantic.pattern_registry
        (entry,) = registry.accepted_presets
        preset = replace(
            entry.preset, budget=SkillBudget(1, 1500, 0.1, 4),
        )
        owned = replace(entry, preset=preset, receipt=replace(
            entry.receipt, preset_ref=preset.preset_ref,
        ))
        revised = replace(registry, accepted_presets=(owned,))
        return replace(
            staged,
            retained=replace(staged.retained, pattern_registry=revised),
            semantic=replace(staged.semantic, pattern_registry=revised),
        )

    async def scenario():
        # The synthetic restored Self actually holds this short immutable
        # accepted Preset BEFORE L1; neither the model nor L0 alters it.
        with patch(
            "test_p0d_stage26_gemma_l1_dev.source_recovered",
            side_effect=source_with_short_budget,
        ):
            prepared, handoff, fresh = await qualified_a(f, lane)
        plan = _resolve(f, prepared, handoff, fresh)
        assert plan.preset_max_distance_m == pytest.approx(0.1)
        assert plan.gap_to_arrival_envelope_m == pytest.approx(0.4)
        assert not plan.full_envelope_reachable_within_distance_budget
        assert plan.next_step.endswith("NOT_ISSUABLE")
        assert plan.invocation_ref == handoff.invocation_ref
        assert len(http.calls) == 1
        for sid in f.names:
            PhysicalActionJournal.restore(
                f.owners[sid].files.physical_wal_file, self_id=sid,
            ).require_clear()
            await f.bridge.logout(sid)

    try:
        asyncio.run(scenario())
    finally:
        f.stop_paper()
        http.stop()
