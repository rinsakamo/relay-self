"""Stage27j 5m WALK->SNEAK: synthetic physical sources ONLY, no real World."""
from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from experiments.p0d_stage27_real_place_move_dev import (
    Stage27RealWorldRefusal,
    _stage27h_capture_prepared,
    run_stage27_real_world,
)
from relay_self.p0d_stage27h_bounded_l0_move_dev import Stage27hLoopRefusal
from relay_self.p0d_stage27i_precision_gait_dev import (
    Stage27iGaitRefusal,
    choose_stage27i_gait,
)
from relay_self.p0d_stage27j_long_move_profile_dev import (
    STAGE27J_ACTION_IO_WATCHDOG_S,
    STAGE27J_MAX_ACTIONS,
    STAGE27J_MAX_DISTANCE_M,
    STAGE27J_MAX_DURATION_MS,
    STAGE27J_MAX_OBSERVATIONS,
    STAGE27J_PRESET_ID,
    STAGE27J_TARGET_DISTANCE_M,
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



def test_stage27j_elapsed_budget_before_action_issues_nothing(tmp_path):
    async def scenario(f, lane, server, pre, handoff, former, current, loop):
        step = loop.pre_action(
            current,
            now_ns=loop.start_ns + STAGE27J_MAX_DURATION_MS * 1_000_000,
        )
        assert step.status == "L0_BUDGET_EXHAUSTED_YIELD_EVALUATION"
        assert step.action_count == 0
        assert not f.owners[f.names[0]].supervisor.recorded_actions
        journal = PhysicalActionJournal.restore(
            f.owners[f.names[0]].files.physical_wal_file,
            self_id=f.names[0],
        )
        assert not journal.records and not journal.unresolved
        assert loop.terminal_status == step.status
    _case(
        tmp_path, scenario, preset_id=STAGE27J_PRESET_ID,
        precision=False, long_stage27j=True,
    )


def test_stage27j_action_crosses_soft_time_budget_settles_then_yields(tmp_path):
    async def scenario(f, lane, server, pre, handoff, former, current, loop):
        step = loop.pre_action(current, now_ns=loop.start_ns + 1000)
        assert step.status == "L0_CONTINUE_MOVE"
        native = PrecisionPlaceNative(handoff.native_session_id)
        decision = choose_stage27i_gait(
            loop, step, current, long_stage27j=True,
        )
        receipt = await _issue(
            f, pre, handoff, loop, former, current, native,
            decision.gait_mode,
        )
        assert receipt.start_ack.result == "applied"
        assert receipt.stop_ack.result == "applied"
        assert receipt.journal_status == "NATIVE_PLACE_MOVE_SETTLED"
        post = loop.observe_terminal_action(
            receipt, source_probe=current,
            now_ns=loop.start_ns + (STAGE27J_MAX_DURATION_MS + 250) * 1_000_000,
        )
        assert post.status == "L0_BUDGET_EXHAUSTED_YIELD_EVALUATION"
        assert post.action_count == 1
        assert post.cumulative_distance_m == pytest.approx(0.65)
        assert STAGE27J_ACTION_IO_WATCHDOG_S > 0
        journal = PhysicalActionJournal.restore(
            f.owners[f.names[0]].files.physical_wal_file,
            self_id=f.names[0],
        )
        assert len(journal.records) == 1
        assert journal.records[0]["status"] == "NATIVE_PLACE_MOVE_SETTLED"
        assert not journal.unresolved
        assert len(server.calls) == 1
        assert loop.terminal_status == post.status
    _case(
        tmp_path, scenario, preset_id=STAGE27J_PRESET_ID,
        precision=False, long_stage27j=True,
    )


def test_stage27j_actual_pulse_above_old_reserve_is_not_fabricated_hold(tmp_path):
    class UnplannedFastNative(PrecisionPlaceNative):
        async def send_set_control(self, action_id, *, control, state):
            await super().send_set_control(
                action_id, control=control, state=state,
            )
            if control == "forward" and state:
                self.x += 0.20

    async def scenario(f, lane, server, pre, handoff, former, current, loop):
        step = loop.pre_action(current, now_ns=150)
        decision = choose_stage27i_gait(
            loop, step, current, long_stage27j=True,
        )
        native = UnplannedFastNative(handoff.native_session_id)
        receipt = await _issue(
            f, pre, handoff, loop, former, current, native,
            decision.gait_mode,
        )
        assert receipt.displacement_m == pytest.approx(0.85)
        post = loop.observe_terminal_action(
            receipt, source_probe=current, now_ns=1000,
        )
        assert post.status == "L0_CONTINUE_MOVE"
        assert post.cumulative_distance_m == pytest.approx(0.85)
        journal = PhysicalActionJournal.restore(
            f.owners[f.names[0]].files.physical_wal_file,
            self_id=f.names[0],
        )
        assert len(journal.records) == 1 and not journal.unresolved
    _case(
        tmp_path, scenario, preset_id=STAGE27J_PRESET_ID,
        precision=False, long_stage27j=True,
    )


def test_stage27j_cumulative_distance_overrun_is_soft_terminal(tmp_path):
    class UnexpectedImpulseNative(PrecisionPlaceNative):
        def __init__(self, native):
            super().__init__(native)
            self.forward_count = 0

        async def send_set_control(self, action_id, *, control, state):
            await super().send_set_control(
                action_id, control=control, state=state,
            )
            if control == "forward" and state:
                self.forward_count += 1
                if self.forward_count == 8:
                    self.x += 2.0

    async def scenario(f, lane, server, pre, handoff, former, current, loop):
        native = UnexpectedImpulseNative(handoff.native_session_id)
        receipts = []
        for i in range(12):
            step = loop.pre_action(current, now_ns=150 + 1_000_000_000 * i)
            if step.status != "L0_CONTINUE_MOVE":
                break
            decision = choose_stage27i_gait(
                loop, step, current, long_stage27j=True,
            )
            receipt = await _issue(
                f, pre, handoff, loop, former, current, native,
                decision.gait_mode,
            )
            receipts.append(receipt)
            post = loop.observe_terminal_action(
                receipt, source_probe=current,
                now_ns=200 + 1_000_000_000 * i,
            )
            if post.status != "L0_CONTINUE_MOVE":
                break
            former = receipt.settled_probe
            current = replace(
                former, seq=former.seq + 1,
                request_id=f"stage27j-soft-distance-{i}",
            )
        assert len(receipts) == 8
        assert receipts[-1].journal_status == "NATIVE_PLACE_MOVE_SETTLED"
        assert post.cumulative_distance_m > STAGE27J_MAX_DISTANCE_M
        assert post.status == "L0_BUDGET_EXHAUSTED_YIELD_EVALUATION"
        journal = PhysicalActionJournal.restore(
            f.owners[f.names[0]].files.physical_wal_file,
            self_id=f.names[0],
        )
        assert len(journal.records) == 8 and not journal.unresolved
        assert all(row["status"] == "NATIVE_PLACE_MOVE_SETTLED"
                   for row in journal.records)
        assert not post.skill_succeeded and not post.goal_succeeded
    _case(
        tmp_path, scenario, preset_id=STAGE27J_PRESET_ID,
        precision=False, long_stage27j=True,
    )


def test_stage27j_no_forward_start_ack_remains_unresolved_hold(tmp_path):
    # A failed native forward START is an ambiguous physical outcome, NOT
    # cognitive Budget exhaustion and NOT a fabricated no-forward terminal.
    class NoForwardStartNative(PrecisionPlaceNative):
        async def send_set_control(self, action_id, *, control, state):
            if control == "forward" and state:
                raise RuntimeError("synthetic native START unavailable")
            return await super().send_set_control(
                action_id, control=control, state=state,
            )

    async def scenario(f, lane, server, pre, handoff, former, current, loop):
        step = loop.pre_action(current, now_ns=150)
        assert step.status == "L0_CONTINUE_MOVE"
        decision = choose_stage27i_gait(
            loop, step, current, long_stage27j=True,
        )
        native = NoForwardStartNative(handoff.native_session_id)
        with pytest.raises(RuntimeError, match="START unavailable"):
            await _issue(
                f, pre, handoff, loop, former, current, native,
                decision.gait_mode,
            )
        assert not any(
            command[1] == "forward" for command in native.sent_commands
        )
        assert sum(
            command[1] == "clear_controls" for command in native.sent_commands
        ) == 1
        journal = PhysicalActionJournal.restore(
            f.owners[f.names[0]].files.physical_wal_file,
            self_id=f.names[0],
        )
        assert journal.unresolved
        assert loop.action_count == 0
        # Do not reinterpret uncertain PREPARED as a Budget terminal.
        with pytest.raises(Stage27hLoopRefusal):
            loop.pre_action(
                replace(current, seq=current.seq + 100),
                now_ns=loop.start_ns + STAGE27J_MAX_DURATION_MS * 1_000_000,
            )
    _case(
        tmp_path, scenario, preset_id=STAGE27J_PRESET_ID,
        precision=False, long_stage27j=True,
    )


def test_stage27j_original_prepared_evidence_all_twelve_actions(tmp_path):
    """Exercise the real pre-native callback on all 12 source-shaped children.

    Regression: the real Paper run settled four WALK Actions, then refused
    Action index 4 *after* fsyncing its fifth PREPARED row. This test checks
    that fifth, ninth and twelfth snapshots before any current native effect.
    It does not constitute an additional real World attempt.
    """
    class TwelveActionNative(PrecisionPlaceNative):
        async def send_set_control(self, action_id, *, control, state):
            previous = self.x
            await super().send_set_control(
                action_id, control=control, state=state,
            )
            if control == "forward" and state and not self.sneak_active:
                self.x = previous + 0.42

    async def scenario(f, lane, server, pre, handoff, former, current, loop):
        owner = f.owners[f.names[0]]
        peer = f.owners[f.names[1]]
        before_peer = (
            peer.intent.events, tuple(peer.skills.items()), peer.retained,
            PhysicalActionJournal.restore(
                peer.files.physical_wal_file, self_id=peer.self_id,
            ).digest,
        )
        evidence = tmp_path / "stage27j-prepared-snapshots"
        evidence.mkdir()
        native = TwelveActionNative(handoff.native_session_id)
        snapshots = []
        original_l1_calls = len(server.calls)
        for i in range(STAGE27J_MAX_ACTIONS):
            step = loop.pre_action(
                current, now_ns=150 + i * 500_000_000,
            )
            assert step.status == "L0_CONTINUE_MOVE"
            gait = choose_stage27i_gait(
                loop, step, current, long_stage27j=True,
            )

            def capture(journal, action):
                assert journal.unresolved
                assert len(journal.records) == i + 1
                assert journal.records[-1]["status"] == "PREPARED_UNRESOLVED"
                assert all(
                    command[0] != action + "-look"
                    for command in native.sent_commands
                )
                frozen = _stage27h_capture_prepared(
                    journal, evidence, action_id=action,
                    action_index=i, long_stage27j=True,
                )
                assert frozen["before_any_native_effect"] is True
                snapshots.append(frozen)

            receipt = await _issue(
                f, pre, handoff, loop, former, current, native,
                gait.gait_mode, pre_native_evidence=capture,
            )
            assert receipt.journal_status == "NATIVE_PLACE_MOVE_SETTLED"
            assert len(snapshots) == i + 1
            feedback = loop.observe_terminal_action(
                receipt, source_probe=current,
                now_ns=200 + i * 500_000_000,
            )
            former = receipt.settled_probe
            if i < STAGE27J_MAX_ACTIONS - 1:
                assert feedback.status == "L0_CONTINUE_MOVE"
                current = replace(
                    former, seq=former.seq + 1,
                    request_id=f"stage27j-prepared-step-{i + 1}",
                )
        assert feedback.status == "L0_BUDGET_EXHAUSTED_YIELD_EVALUATION"
        assert loop.action_count == STAGE27J_MAX_ACTIONS
        assert len(snapshots) == STAGE27J_MAX_ACTIONS
        assert [row["action_number"] for row in snapshots] == list(
            range(1, STAGE27J_MAX_ACTIONS + 1)
        )
        assert all(
            (evidence / f"stage27h-A-PREPARED-{k}.json").is_file()
            for k in range(1, STAGE27J_MAX_ACTIONS + 1)
        )
        for k in (5, 9, 12):
            original = PhysicalActionJournal.restore(
                evidence / f"stage27h-A-PREPARED-{k}.json",
                self_id=owner.self_id,
            )
            assert len(original.records) == k
            assert original.unresolved
            assert original.records[-1]["status"] == "PREPARED_UNRESOLVED"
            assert all(
                row["status"] == "NATIVE_PLACE_MOVE_SETTLED"
                for row in original.records[:-1]
            )
            assert original.digest == snapshots[k - 1]["journal_digest"]
        terminal = PhysicalActionJournal.restore(
            owner.files.physical_wal_file, self_id=owner.self_id,
        )
        assert len(terminal.records) == STAGE27J_MAX_ACTIONS
        assert not terminal.unresolved
        assert all(
            row["status"] == "NATIVE_PLACE_MOVE_SETTLED"
            for row in terminal.records
        )
        assert len(server.calls) == original_l1_calls
        assert (
            peer.intent.events, tuple(peer.skills.items()), peer.retained,
            PhysicalActionJournal.restore(
                peer.files.physical_wal_file, self_id=peer.self_id,
            ).digest,
        ) == before_peer

        # Failing boundary controls: an older Stage27h/i evidence cap cannot
        # adopt child 5, and child 13 must never be accepted for Stage27j.
        fifth = PhysicalActionJournal.restore(
            evidence / "stage27h-A-PREPARED-5.json", self_id=owner.self_id,
        )
        with pytest.raises(Stage27RealWorldRefusal, match="PREPARED invalid"):
            _stage27h_capture_prepared(
                fifth, tmp_path, action_id=fifth.records[-1]["action_id"],
                action_index=4,
            )
        twelfth = PhysicalActionJournal.restore(
            evidence / "stage27h-A-PREPARED-12.json", self_id=owner.self_id,
        )
        with pytest.raises(Stage27RealWorldRefusal, match="PREPARED invalid"):
            _stage27h_capture_prepared(
                twelfth, tmp_path,
                action_id=twelfth.records[-1]["action_id"],
                action_index=12, long_stage27j=True,
            )
        with pytest.raises(Stage27RealWorldRefusal, match="PREPARED invalid"):
            _stage27h_capture_prepared(
                fifth, tmp_path, action_id="forged-action",
                action_index=4, long_stage27j=True,
            )
        with pytest.raises(Stage27RealWorldRefusal, match="PREPARED invalid"):
            _stage27h_capture_prepared(
                fifth, tmp_path,
                action_id=fifth.records[-1]["action_id"],
                action_index=4, long_stage27j=1,
            )
        with pytest.raises(FileExistsError):
            _stage27h_capture_prepared(
                fifth, evidence,
                action_id=fifth.records[-1]["action_id"],
                action_index=4, long_stage27j=True,
            )

    _case(
        tmp_path, scenario, preset_id=STAGE27J_PRESET_ID,
        precision=False, long_stage27j=True,
    )
