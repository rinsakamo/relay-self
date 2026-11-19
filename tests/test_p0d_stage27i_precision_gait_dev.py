"""Stage27i CPU precision gait: synthetic native and HTTP only, NO real World."""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from adapters.mineflayer.python_protocol import MineflayerEffectResult
from experiments.p0d_stage27_real_place_move_dev import (
    Stage27RealWorldRefusal,
    _native_place_wire_readback,
    run_stage27_real_world,
    stage27i_real_a_motor_hook,
)
from relay_self.p0d_stage26_gemma_l1_dev import prepare_restored_preset_l1
from relay_self.p0d_stage27b_place_motion_dev import resolve_stage27_place_motion
from relay_self.p0d_stage27c_l0_place_proposal_dev import (
    propose_stage27c_original_place_move,
)
from relay_self.p0d_stage27h_bounded_l0_move_dev import Stage27hBoundedMoveLoop
from relay_self.p0d_stage27i_precision_gait_dev import (
    STAGE27I_ARRIVAL_M,
    STAGE27I_PRESET_ID,
    Stage27iGaitRefusal,
    choose_stage27i_gait,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_action_port import PhysicalCapability
from relay_self.provenance import Provenance
from relay_self.skill_invocation import SkillBudget
from test_p0d_real_preset_checkpoint_dev import native_probe, source_recovered
from test_p0d_resident_llama_slot_owner_dev import (
    ResidentFixture,
    _SyntheticLlamaServer,
)
from test_p0d_stage26_gemma_l1_dev import _attach_and_audit
from test_p0d_stage27b_place_motion_dev import qualified_a
from test_p0d_stage27c_place_move_wal_issuer_dev import (
    ScriptedPlaceNative,
    _args,
)


class PrecisionPlaceNative(ScriptedPlaceNative):
    """Source-shaped two-velocity fixture; no actual Minecraft physics."""

    def __init__(self, native):
        super().__init__(native)
        self.sneak_active = False
        self.move_modes: list[str] = []

    async def send_set_control(self, action_id, *, control, state):
        if control == "sneak":
            self.gate(self.started.session_id, "set_control", action_id)
            assert state is True and not self.sneak_active
            self.sneak_active = True
            self.sent_commands.append((action_id, control, state))
            self.seq += 1
            self.events.append(MineflayerEffectResult(
                self.started.session_id, self.seq, action_id,
                "set_control", "applied", None,
            ))
            return
        assert control == "forward" and state is True
        previous = self.x
        await super().send_set_control(action_id, control=control, state=state)
        self.x = previous + (0.18 if self.sneak_active else 0.65)
        self.move_modes.append("SNEAK" if self.sneak_active else "WALK")

    async def send_clear_controls(self, action_id):
        await super().send_clear_controls(action_id)
        self.sneak_active = False


def _case(tmp_path, scenario, *, preset_id=STAGE27I_PRESET_ID, precision=True):
    server = _SyntheticLlamaServer()
    server.choice_id = "1"
    endpoint = server.start()
    fixture = ResidentFixture(
        tmp_path, 2, cognitive_work=True, allow_resident_move=True,
    )
    lane = _attach_and_audit(fixture, endpoint, tmp_path)
    budget = SkillBudget(4, 15000, 2.0, 256)

    def original(self_id="A"):
        return source_recovered(self_id, budget=budget, preset_id=preset_id)

    def prepare(*args, **kwargs):
        return prepare_restored_preset_l1(
            *args, **kwargs, stage27i_precision_target=precision,
        )

    async def inner():
        pre, handoff, former = await qualified_a(fixture, lane)
        owner = fixture.owners[fixture.names[0]]
        loop = Stage27hBoundedMoveLoop(
            pre, handoff, owner=owner, physical=fixture.physical,
            world_epoch=pre.world_epoch, start_ns=100,
        )
        current = native_probe(
            fixture.names[0], former.seq + 1,
            session=handoff.native_session_id,
        )
        return await scenario(fixture, lane, server, pre, handoff, former,
                              current, loop)

    try:
        with (
            patch("test_p0d_stage26_gemma_l1_dev.source_recovered",
                  side_effect=original),
            patch("test_p0d_stage27_owned_move_intent_dev."
                  "prepare_restored_preset_l1", side_effect=prepare),
        ):
            return asyncio.run(inner())
    finally:
        fixture.stop_paper()
        server.stop()


async def _issue(f, pre, handoff, loop, former, current, native, gait_mode):
    owner = f.owners[f.names[0]]
    plan = resolve_stage27_place_motion(
        pre, handoff, current, owner=owner,
        physical=f.physical, world_epoch=pre.world_epoch,
    )
    l0 = propose_stage27c_original_place_move(
        pre, handoff, plan, current, owner=owner,
        physical=f.physical, world_epoch=pre.world_epoch,
        capability=PhysicalCapability(
            "MOVE", 1, "locomotion", "DESTINATION", True,
        ),
        at_ns=200 + loop.action_count * 20,
        provenance=Provenance("stage27i-synthetic", current.provenance.reference),
    )
    native.seq = current.seq
    native.tick = 1213 + current.seq * 9
    native.x = current.snapshot.position.x
    native.gate = lambda session, effect, action: f.physical.require_native_effect(
        self_id=f.names[0], native_session_id=session,
        effect=effect, action_id=action,
    )
    args = _args(f, pre, handoff, plan, l0, former, current)
    args["at_ns"] = 1000 + loop.action_count * 20
    args["allow_prior_terminal_place_actions"] = loop.action_count > 0
    args["settlement_probe_limit"] = loop.reserve_settling_observations(
        source_probe=current,
    )
    args["precision_gait"] = gait_mode
    return await f.physical.issue_place_move(native, **args)


def test_precision_gait_1_5m_three_actions_and_original_wal(tmp_path):
    async def scenario(f, lane, server, pre, handoff, former, current, loop):
        native = PrecisionPlaceNative(handoff.native_session_id)
        peer = f.owners[f.names[1]]
        before_peer = (
            peer.intent.events, dict(peer.skills),
            PhysicalActionJournal.restore(
                peer.files.physical_wal_file, self_id=peer.self_id,
            ).digest,
        )
        initial_http_count = len(server.calls)
        modes, gaps, ids = [], [], []
        for i in range(4):
            step = loop.pre_action(current, now_ns=150 + 1000 * i)
            if step.status != "L0_CONTINUE_MOVE":
                break
            gait = choose_stage27i_gait(loop, step, current)
            modes.append(gait.gait_mode)
            assert gait.preset_ref == handoff.preset_ref
            assert gait.arrival_radius_m == STAGE27I_ARRIVAL_M
            assert gait.native_seq == current.seq
            receipt = await _issue(
                f, pre, handoff, loop, former, current, native,
                gait.gait_mode,
            )
            assert receipt.gait_mode == gait.gait_mode
            assert (receipt.gait_control_ack is not None) == (
                gait.gait_mode == "SNEAK"
            )
            ids.append(receipt.action_id)
            post = loop.observe_terminal_action(
                receipt, source_probe=current, now_ns=200 + 1000 * i,
            )
            assert post.observation_count <= 256
            gaps.append(post.target_gap_m)
            former = receipt.settled_probe
            if post.status != "L0_CONTINUE_MOVE":
                break
            current = replace(
                former, seq=former.seq + 1,
                request_id=f"stage27i-next-{i}",
            )
        assert modes == ["WALK", "WALK", "SNEAK"]
        assert native.move_modes == modes
        assert len(ids) == len(set(ids)) == 3
        assert post.status == "L0_TARGET_REACHED_YIELD_EVALUATION"
        assert gaps[-1] == pytest.approx(0.0)
        assert loop.action_count == 3
        assert loop.cumulative_distance_m == pytest.approx(1.48)
        assert len(server.calls) == initial_http_count
        journal = PhysicalActionJournal.restore(
            f.owners[f.names[0]].files.physical_wal_file,
            self_id=f.names[0],
        )
        assert len(journal.records) == 3 and not journal.unresolved
        assert [r["gait_mode"] for r in journal.records] == modes
        assert journal.records[0]["gait_ack_seq"] is None
        assert journal.records[1]["gait_ack_seq"] is None
        assert journal.records[2]["gait_ack_seq"] is not None
        assert journal.records[2]["effect_seqs"][0] < (
            journal.records[2]["gait_ack_seq"]
        ) < journal.records[2]["effect_seqs"][1]
        assert (
            peer.intent.events, dict(peer.skills),
            PhysicalActionJournal.restore(
                peer.files.physical_wal_file, self_id=peer.self_id,
            ).digest,
        ) == before_peer
    _case(tmp_path, scenario)


@pytest.mark.parametrize("preset_id,precision", [
    ("OperatorNearProbe", True),
    (STAGE27I_PRESET_ID, False),
])
def test_gait_fails_before_physical_action_without_precise_bound_preset(
    tmp_path, preset_id, precision,
):
    async def scenario(f, lane, server, pre, handoff, former, current, loop):
        step = loop.pre_action(current, now_ns=150)
        assert step.status == "L0_CONTINUE_MOVE"
        with pytest.raises(Stage27iGaitRefusal):
            choose_stage27i_gait(loop, step, current)
        assert not f.owners[f.names[0]].supervisor.recorded_actions
    _case(tmp_path, scenario, preset_id=preset_id, precision=precision)


def test_precision_gait_rejects_stale_pre_action_source(tmp_path):
    async def scenario(f, lane, server, pre, handoff, former, current, loop):
        step = loop.pre_action(current, now_ns=150)
        with pytest.raises(Stage27iGaitRefusal, match="ready L0"):
            choose_stage27i_gait(
                loop, step, replace(current, seq=current.seq + 1),
            )
        assert not f.owners[f.names[0]].supervisor.recorded_actions
    _case(tmp_path, scenario)


def test_native_readback_requires_exact_sneak_before_forward(tmp_path):
    rows = [
        {"session_id": "native-A", "type": "observation",
         "kind": "probe", "seq": 9, "request_id": "first"},
        *[
            {"session_id": "native-A", "type": "effect_result",
             "seq": seq, "action_id": f"action-A-{name}",
             "effect": effect, "result": "applied"}
            for seq, name, effect in (
                (10, "look", "look"), (11, "sneak", "set_control"),
                (12, "start", "set_control"), (13, "stop", "clear_controls"),
            )
        ],
        *[
            {"session_id": "native-A", "type": "observation",
             "kind": "probe", "seq": seq, "request_id": str(seq)}
            for seq in (14, 15, 16)
        ],
    ]
    source = tmp_path / "native.jsonl"
    source.write_text("".join(json.dumps(x) + "\n" for x in rows))
    kwargs = dict(
        session_id="native-A", parent="action-A", new_probe_seq=9,
        ack_seqs=(10, 12, 13), stop_probe_seqs=(14, 15, 16),
    )
    assert _native_place_wire_readback(
        source, **kwargs, sneak_ack_seq=11,
    )["precision_sneak_effect_attested"]
    with pytest.raises(Stage27RealWorldRefusal):
        _native_place_wire_readback(source, **kwargs)


def test_stage27i_new_runner_mode_exclusive_before_world(tmp_path):
    args = dict(
        paper_jar=tmp_path / "paper.jar", paper_sha256="0" * 64,
        plugin_jar=tmp_path / "plugin.jar", plugin_sha256="0" * 64,
        scratch_parent=tmp_path, accepted_eula=True,
        real_world_dev_grant=True,
        gemma_l1_endpoint="http://127.0.0.1:18081/v1/chat/completions",
        gemma_l1_model="stage26-gemma",
    )
    with patch(
        "experiments.p0d_stage27_real_place_move_dev."
        "run_real_two_self_preset_checkpoint", new_callable=AsyncMock,
    ) as original:
        original.return_value = Path(tmp_path / "report.json")
        asyncio.run(run_stage27_real_world(
            **args, stage27i_precision_gait=True,
        ))
        assert original.await_args.kwargs["_stage27h_multi_preset"] is True
        assert original.await_args.kwargs["_stage27i_precision_target"] is True
        assert original.await_args.kwargs["_stage27_motor_hook"] is (
            stage27i_real_a_motor_hook
        )
        original.reset_mock()
        with pytest.raises(Stage27RealWorldRefusal):
            asyncio.run(run_stage27_real_world(
                **args, stage27i_precision_gait=True,
                stage27h_l0_move_loop=True,
            ))
        original.assert_not_awaited()
