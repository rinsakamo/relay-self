"""Stage27h: multi-Action MOVE is a bounded CPU L0 loop, no extra L1 call.

All Paper/native/model shapes in this suite are synthetic. A real World
trial requires separate original-host one-shot execution and qualification.
"""
from __future__ import annotations

import asyncio
from dataclasses import replace
from unittest.mock import patch

import pytest

from adapters.mineflayer.python_protocol import MineflayerPosition
from relay_self.p0d_stage27h_bounded_l0_move_dev import (
    Stage27hBoundedMoveLoop,
    Stage27hLoopRefusal,
)
from relay_self.p0d_stage27b_place_motion_dev import resolve_stage27_place_motion
from relay_self.p0d_stage27c_l0_place_proposal_dev import propose_stage27c_original_place_move
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_action_port import PhysicalCapability
from relay_self.provenance import Provenance
from relay_self.skill import SkillState
from relay_self.skill_invocation import SkillBudget
from test_p0d_real_preset_checkpoint_dev import native_probe, source_recovered
from test_p0d_resident_llama_slot_owner_dev import (
    ResidentFixture,
    _SyntheticLlamaServer,
)
from test_p0d_stage26_gemma_l1_dev import _attach_and_audit
from test_p0d_stage27c_place_move_wal_issuer_dev import (
    ScriptedPlaceNative,
    _args,
    selected_original,
)


class SlowPlaceNative(ScriptedPlaceNative):
    """A source-shaped original native emitter: each pulse advances 0.2m."""

    async def send_set_control(self, action_id, *, control, state):
        await super().send_set_control(action_id, control=control, state=state)
        self.x -= 0.6


def _fixture(tmp_path, case):
    server = _SyntheticLlamaServer()
    server.choice_id = "1"
    endpoint = server.start()
    f = ResidentFixture(tmp_path, 2, cognitive_work=True, allow_resident_move=True)
    lane = _attach_and_audit(f, endpoint, tmp_path)
    budget = SkillBudget(4, 15000, 2.0, 16)
    original = source_recovered

    def multi(self_id="A"):
        return original(self_id, budget=budget)

    try:
        with patch("test_p0d_stage26_gemma_l1_dev.source_recovered", side_effect=multi):
            return asyncio.run(case(f, lane, server))
    finally:
        f.stop_paper()
        server.stop()


async def _start(f, lane):
    pre, handoff, _, _, former, current = await selected_original(f, lane)
    owner = f.owners[f.names[0]]
    loop = Stage27hBoundedMoveLoop(
        pre, handoff, owner=owner,
        physical=f.physical, world_epoch=pre.world_epoch, start_ns=100,
    )
    return pre, handoff, former, current, loop


async def _issue(f, pre, handoff, loop, previous, observed, native):
    owner = f.owners[f.names[0]]
    plan = resolve_stage27_place_motion(
        pre, handoff, observed, owner=owner,
        physical=f.physical, world_epoch=pre.world_epoch,
    )
    l0 = propose_stage27c_original_place_move(
        pre, handoff, plan, observed, owner=owner,
        physical=f.physical, world_epoch=pre.world_epoch,
        capability=PhysicalCapability("MOVE", 1, "locomotion", "DESTINATION", True),
        at_ns=200 + loop.action_count * 20,
        provenance=Provenance("stage27h-synthetic", observed.provenance.reference),
    )
    native.seq = observed.seq
    native.tick = 1213 + observed.seq * 9
    native.x = observed.snapshot.position.x
    native.gate = lambda session, effect, action: f.physical.require_native_effect(
        self_id=f.names[0], native_session_id=session,
        effect=effect, action_id=action,
    )
    kwargs = _args(f, pre, handoff, plan, l0, previous, observed)
    kwargs["at_ns"] = 1000 + loop.action_count * 20
    receipt = await f.physical.issue_place_move(native, **kwargs)
    return receipt


def test_l0_reaches_target_after_two_short_actions_without_second_llm(tmp_path):
    async def scenario(f, lane, server):
        pre, handoff, previous, observed, loop = await _start(f, lane)
        owner, peer = f.owners[f.names[0]], f.owners[f.names[1]]
        peer_before = (peer.intent.events, dict(peer.skills),
                       PhysicalActionJournal.restore(
                           peer.files.physical_wal_file, self_id=peer.self_id,
                       ).digest)
        native = SlowPlaceNative(handoff.native_session_id)
        model_calls = len(server.calls)
        action_ids = []
        statuses = []
        for idx in range(4):
            ready = loop.pre_action(observed, now_ns=150 + idx * 1000)
            if ready.status != "L0_CONTINUE_MOVE":
                statuses.append(ready.status)
                break
            receipt = await _issue(
                f, pre, handoff, loop, previous, observed, native,
            )
            action_ids.append(receipt.action_id)
            done = loop.observe_terminal_action(
                receipt, source_probe=observed, now_ns=200 + idx * 1000,
            )
            statuses.append(done.status)
            previous = receipt.settled_probe
            if done.status != "L0_CONTINUE_MOVE":
                break
            # Real native readback would be requested after the previous STOP.
            observed = replace(
                previous, seq=previous.seq + 1,
                request_id=f"stage27h-preflight-{idx}",
            )
        assert action_ids
        assert len(action_ids) == 2
        assert len(set(action_ids)) == 2
        assert statuses == [
            "L0_CONTINUE_MOVE", "L0_TARGET_REACHED_YIELD_EVALUATION",
        ]
        assert len(server.calls) == model_calls  # no L1/GPU in L0 loop
        assert owner.intent.current_intent is not None
        assert owner.skills[handoff.skill_execution_id].state is SkillState.STARTED
        journal = PhysicalActionJournal.restore(
            owner.files.physical_wal_file, self_id=owner.self_id,
        )
        assert len(journal.records) == 2
        assert [r["action_id"] for r in journal.records] == action_ids
        assert all(r["status"] == "NATIVE_PLACE_MOVE_SETTLED" for r in journal.records)
        assert (peer.intent.events, dict(peer.skills),
                PhysicalActionJournal.restore(
                    peer.files.physical_wal_file, self_id=peer.self_id,
                ).digest) == peer_before

    _fixture(tmp_path, scenario)


@pytest.mark.parametrize("mode", ["already-there", "no-progress", "budget", "old-session"])
def test_l0_stops_before_issuing_or_reissuing_unqualified_move(tmp_path, mode):
    async def scenario(f, lane, server):
        pre, handoff, previous, observed, loop = await _start(f, lane)
        if mode == "already-there":
            target = pre.original_target.arrival_contract.anchor
            assert target is not None
            observed = replace(
                observed, snapshot=replace(
                    observed.snapshot,
                    position=MineflayerPosition(target.x, target.y, target.z),
                ),
            )
            step = loop.pre_action(observed, now_ns=150)
            assert step.status == "L0_TARGET_REACHED_YIELD_EVALUATION"
            assert loop.action_count == 0
        elif mode == "old-session":
            observed = replace(observed, session_id="foreign-native")
            with pytest.raises(Stage27hLoopRefusal):
                loop.pre_action(observed, now_ns=150)
        else:
            loop.pre_action(observed, now_ns=150)
            native = ScriptedPlaceNative(
                handoff.native_session_id, blocked=mode == "no-progress",
            )
            receipt = await _issue(f, pre, handoff, loop, previous, observed, native)
            if mode == "budget":
                loop.cumulative_distance_m = 1.9
            result = loop.observe_terminal_action(
                receipt, source_probe=observed, now_ns=180,
            )
            assert result.status == (
                "L0_NO_PROGRESS_YIELD_EVALUATION"
                if mode == "no-progress"
                else "L0_CUMULATIVE_OVERSHOOT_YIELD_EVALUATION"
            )
            assert loop.action_count == 1
            with pytest.raises(Stage27hLoopRefusal):
                loop.pre_action(receipt.settled_probe, now_ns=200)

    _fixture(tmp_path, scenario)
