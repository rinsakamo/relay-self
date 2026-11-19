"""Stage27j 5m WALK->SNEAK: synthetic physical sources ONLY, no real World."""
from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from experiments.p0d_stage27_real_place_move_dev import (
    Stage27RealWorldRefusal,
    run_stage27_real_world,
)
from relay_self.p0d_stage27h_bounded_l0_move_dev import Stage27hLoopRefusal
from relay_self.p0d_stage27i_precision_gait_dev import (
    Stage27iGaitRefusal,
    choose_stage27i_gait,
)
from relay_self.p0d_stage27j_long_move_profile_dev import (
    STAGE27J_MAX_ACTIONS,
    STAGE27J_MAX_DISTANCE_M,
    STAGE27J_MAX_DURATION_MS,
    STAGE27J_MAX_OBSERVATIONS,
    STAGE27J_PRESET_ID,
    STAGE27J_TARGET_DISTANCE_M,
    stage27j_can_reserve_action,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.skill_invocation import SkillBudget
from test_p0d_stage27i_precision_gait_dev import (
    PrecisionPlaceNative,
    _case,
    _issue,
)


def test_stage27j_original_one_skill_reaches_5m_with_slow_approach(tmp_path):
    async def scenario(f, lane, server, pre, handoff, former, current, loop):
        owner, peer = f.owners[f.names[0]], f.owners[f.names[1]]
        assert loop.invocation.budget == SkillBudget(
            STAGE27J_MAX_ACTIONS, STAGE27J_MAX_DURATION_MS,
            STAGE27J_MAX_DISTANCE_M, STAGE27J_MAX_OBSERVATIONS,
        )
        assert handoff.preset_ref == loop.invocation.parameter_preset_ref
        target = loop.invocation.target.contract
        assert target is not None and target.anchor is not None
        assert target.condition.max_horizontal_m == 0.15
        assert target.anchor.x - current.snapshot.position.x == pytest.approx(
            STAGE27J_TARGET_DISTANCE_M,
        )
        peer_before = (
            peer.intent.events, tuple(peer.skills.items()), peer.retained,
            PhysicalActionJournal.restore(
                peer.files.physical_wal_file, self_id=peer.self_id,
            ).digest,
        )
        calls = len(server.calls)
        native = PrecisionPlaceNative(handoff.native_session_id)
        modes, ids = [], []
        for i in range(STAGE27J_MAX_ACTIONS + 1):
            step = loop.pre_action(current, now_ns=150 + 500000000 * i)
            if step.status != "L0_CONTINUE_MOVE":
                break
            decision = choose_stage27i_gait(
                loop, step, current, long_stage27j=True,
            )
            modes.append(decision.gait_mode)
            receipt = await _issue(
                f, pre, handoff, loop, former, current, native,
                decision.gait_mode,
            )
            assert receipt.gait_mode == decision.gait_mode
            ids.append(receipt.action_id)
            post = loop.observe_terminal_action(
                receipt, source_probe=current, now_ns=200 + 500000000 * i,
            )
            assert post.observation_count <= STAGE27J_MAX_OBSERVATIONS
            former = receipt.settled_probe
            if post.status != "L0_CONTINUE_MOVE":
                break
            current = replace(
                former, seq=former.seq + 1,
                request_id=f"stage27j-next-{i}",
            )
        assert modes[:7] == ["WALK"] * 7
        assert modes[7:] == ["SNEAK"] * (len(modes) - 7)
        assert len(modes) >= 9 and len(modes) <= STAGE27J_MAX_ACTIONS
        assert native.move_modes == modes
        assert len(ids) == len(set(ids)) == loop.action_count
        assert post.status == "L0_TARGET_REACHED_YIELD_EVALUATION"
        assert loop.cumulative_distance_m == pytest.approx(
            7 * 0.65 + (len(modes) - 7) * 0.18,
        )
        assert loop.cumulative_distance_m <= STAGE27J_MAX_DISTANCE_M
        assert len(server.calls) == calls
        journal = PhysicalActionJournal.restore(
            owner.files.physical_wal_file, self_id=owner.self_id,
        )
        assert len(journal.records) == loop.action_count
        assert not journal.unresolved
        assert [row["gait_mode"] for row in journal.records] == modes
        assert all(row["status"] == "NATIVE_PLACE_MOVE_SETTLED"
                   for row in journal.records)
        assert (
            peer.intent.events, tuple(peer.skills.items()), peer.retained,
            PhysicalActionJournal.restore(
                peer.files.physical_wal_file, self_id=peer.self_id,
            ).digest,
        ) == peer_before
        assert owner.intent.current_intent is not None
        assert any(skill.state.value == "started" for skill in owner.skills.values())

    _case(
        tmp_path, scenario, preset_id=STAGE27J_PRESET_ID,
        precision=False, long_stage27j=True,
    )


def test_stage27j_refuses_stage27i_gait_reinterpretation(tmp_path):
    async def scenario(f, lane, server, pre, handoff, former, current, loop):
        step = loop.pre_action(current, now_ns=150)
        with pytest.raises(Stage27iGaitRefusal, match="bound"):
            choose_stage27i_gait(loop, step, current)
        assert not f.owners[f.names[0]].supervisor.recorded_actions
    _case(
        tmp_path, scenario, preset_id=STAGE27J_PRESET_ID,
        precision=False, long_stage27j=True,
    )


def test_stage27j_rejects_12_action_budget_without_long_preset(tmp_path):
    # The older Stage27h/27i authorizer must not silently inherit 12 Actions.
    async def scenario(f, lane, server, pre, handoff, former, current, loop):
        assert loop.invocation.budget.max_actions == 4
        with pytest.raises(Stage27iGaitRefusal):
            choose_stage27i_gait(
                loop, loop.pre_action(current, now_ns=150),
                current, long_stage27j=True,
            )
        assert not f.owners[f.names[0]].supervisor.recorded_actions
    _case(tmp_path, scenario)


def test_stage27j_rejects_stale_native_source_without_action(tmp_path):
    async def scenario(f, lane, server, pre, handoff, former, current, loop):
        step = loop.pre_action(current, now_ns=150)
        with pytest.raises(Stage27iGaitRefusal, match="ready L0"):
            choose_stage27i_gait(
                loop, step, replace(current, seq=current.seq + 1),
                long_stage27j=True,
            )
        assert not f.owners[f.names[0]].supervisor.recorded_actions
    _case(
        tmp_path, scenario, preset_id=STAGE27J_PRESET_ID,
        precision=False, long_stage27j=True,
    )


def test_stage27j_runner_isolated_flag_and_real_world_not_started():
    async def scenario(stage27j=True, stage27i=False, stage27h=False):
        with patch(
            "experiments.p0d_stage27_real_place_move_dev."
            "run_real_two_self_preset_checkpoint",
            new_callable=AsyncMock,
        ) as runner:
            await run_stage27_real_world(
                paper_jar=Path("/not/actually/paper.jar"),
                paper_sha256="synthetic",
                plugin_jar=Path("/not/actually/plugin.jar"),
                plugin_sha256="synthetic",
                scratch_parent=Path("/no/world"),
                accepted_eula=True,
                real_world_dev_grant=True,
                gemma_l1_endpoint="http://127.0.0.1:18881/v1/chat/completions",
                gemma_l1_model="synthetic-stub",
                stage27j_long_move=stage27j,
                stage27i_precision_gait=stage27i,
                stage27h_l0_move_loop=stage27h,
            )
            return runner
    runner = asyncio.run(scenario())
    assert runner.await_count == 1
    kwargs = runner.await_args.kwargs
    assert kwargs["_stage27j_long_target"] is True
    assert kwargs["_stage27i_precision_target"] is False
    assert kwargs["_stage27h_multi_preset"] is True

    for other in ("stage27i", "stage27h"):
        with pytest.raises(Stage27RealWorldRefusal):
            asyncio.run(scenario(
                stage27j=True, stage27i=(other == "stage27i"),
                stage27h=(other == "stage27h"),
            ))


def test_stage27j_12_actions_refused_for_non_long_accepted_preset(tmp_path):
    # Budget and target flag do not grant the older Stage27i Preset 12
    # Actions. This must fail at the original loop admission gate.
    async def should_never_issue(*_args):
        raise AssertionError("unexpected physical issue")
    with pytest.raises(Stage27hLoopRefusal, match="bounded multi-Action"):
        _case(
            tmp_path, should_never_issue,
            preset_id="OperatorPrecisionWalkSneakAt075",
            precision=False,
            long_stage27j=True,
        )


@pytest.mark.parametrize(
    "gait,already_m,now_ms,allowed",
    [
        ("WALK", 5.25, 0, True),       # 5.25 + 0.75 = 6.00
        ("WALK", 5.26, 0, False),      # no one-pulse space
        ("SNEAK", 5.75, 0, True),      # 5.75 + 0.25 = 6.00
        ("SNEAK", 5.76, 0, False),
        ("WALK", 0.0, 39999, True),   # 5s margin still reserved
        ("WALK", 0.0, 40000, False),
        ("WALK", 0.0, 45000, False),
    ],
)
def test_stage27j_preissue_distance_and_time_envelope(
    gait, already_m, now_ms, allowed,
):
    assert stage27j_can_reserve_action(
        gait_mode=gait, cumulative_m=already_m,
        max_distance_m=6.0,
        now_ns=now_ms * 1_000_000,
        deadline_ns=45_000_000_000,
    ) is allowed


def test_stage27j_no_action_when_not_enough_shared_time(tmp_path):
    async def scenario(f, lane, server, pre, handoff, former, current, loop):
        step = loop.pre_action(current, now_ns=150)
        assert step.status == "L0_CONTINUE_MOVE"
        result = loop.reserve_stage27j_motor_budget(
            source_probe=current, gait_mode="WALK",
            now_ns=loop.original_deadline_ns - 4_999_999_999,
        )
        assert result is not None
        assert result.status == "L0_BUDGET_EXHAUSTED_YIELD_EVALUATION"
        assert loop.action_count == 0
        assert loop._stage27j_pending_distance_m is None
        assert not f.owners[f.names[0]].supervisor.recorded_actions
    _case(
        tmp_path, scenario, preset_id=STAGE27J_PRESET_ID,
        precision=False, long_stage27j=True,
    )


def test_stage27j_unexpected_over_envelope_action_fails_closed(tmp_path):
    class UnplannedFastNative(PrecisionPlaceNative):
        async def send_set_control(self, action_id, *, control, state):
            await super().send_set_control(
                action_id, control=control, state=state,
            )
            if control == "forward" and state:
                self.x += 0.20

    async def scenario(f, lane, server, pre, handoff, former, current, loop):
        step = loop.pre_action(current, now_ns=150)
        assert step.status == "L0_CONTINUE_MOVE"
        decision = choose_stage27i_gait(
            loop, step, current, long_stage27j=True,
        )
        native = UnplannedFastNative(handoff.native_session_id)
        receipt = await _issue(
            f, pre, handoff, loop, former, current, native,
            decision.gait_mode,
        )
        assert receipt.displacement_m > 0.75
        with pytest.raises(Stage27hLoopRefusal, match="preissue reserve"):
            loop.observe_terminal_action(
                receipt, source_probe=current, now_ns=1000,
            )
        # The already-issued Action retains canonical terminal WAL evidence,
        # but L0 refuses any next Action and cannot silently refund the cap.
        journal = PhysicalActionJournal.restore(
            f.owners[f.names[0]].files.physical_wal_file,
            self_id=f.names[0],
        )
        assert len(journal.records) == 1 and not journal.unresolved
        assert loop._stage27j_pending_distance_m == 0.75
    _case(
        tmp_path, scenario, preset_id=STAGE27J_PRESET_ID,
        precision=False, long_stage27j=True,
    )
