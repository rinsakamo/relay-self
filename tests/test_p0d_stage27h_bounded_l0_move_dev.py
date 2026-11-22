"""Stage27h: multi-Action MOVE is a bounded CPU L0 loop, no extra L1 call.

All Paper/native/model shapes in this suite are synthetic. A real World
trial requires separate original-host one-shot execution and qualification.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from adapters.mineflayer.python_protocol import MineflayerPosition, MineflayerTime
from experiments.cognitive_physical_move_issue_dev import (
    PhysicalMoveRefusal,
    _settled,
)
from experiments.cognitive_physical_place_move_issue_dev import Stage27PlaceMoveRefusal
from experiments.p0d_real_preset_checkpoint_dev import (
    RealPresetCheckpointRefusal,
    _preserve_and_validate_stage27h_hook_return,
)
from experiments.p0d_stage27_real_place_move_dev import (
    Stage27RealWorldRefusal,
    _stage27h_all_settling_stdout_readback,
    run_stage27_real_world,
    stage27h_real_a_motor_hook,
)
from relay_self.p0d_stage27b_place_motion_dev import resolve_stage27_place_motion
from relay_self.p0d_stage27c_l0_place_proposal_dev import propose_stage27c_original_place_move
from relay_self.p0d_stage27h_bounded_l0_move_dev import (
    STAGE27H_SETTLING_PROBE_RESERVATION,
    Stage27hBoundedMoveLoop,
    Stage27hLoopRefusal,
)
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
from test_p0d_stage27b_place_motion_dev import qualified_a
from test_p0d_stage27c_place_move_wal_issuer_dev import (
    ScriptedPlaceNative,
    _args,
)


class SlowPlaceNative(ScriptedPlaceNative):
    """A source-shaped original native emitter: each pulse advances 0.2m."""

    async def send_set_control(self, action_id, *, control, state):
        await super().send_set_control(action_id, control=control, state=state)
        self.x -= 0.6


def _fixture(tmp_path, case, budget=None):
    server = _SyntheticLlamaServer()
    server.choice_id = "1"
    endpoint = server.start()
    f = ResidentFixture(tmp_path, 2, cognitive_work=True, allow_resident_move=True)
    lane = _attach_and_audit(f, endpoint, tmp_path)
    budget = budget or SkillBudget(4, 15000, 2.0, 256)
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
    pre, handoff, former = await qualified_a(f, lane)
    current = native_probe(
        f.names[0], former.seq + 1, session=handoff.native_session_id,
    )
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
    kwargs["allow_prior_terminal_place_actions"] = loop.action_count > 0
    kwargs["settlement_probe_limit"] = loop.reserve_settling_observations(
        source_probe=observed,
    )
    receipt = await f.physical.issue_place_move(native, **kwargs)
    return receipt


def test_l0_reaches_target_after_three_short_actions_without_second_llm(tmp_path):
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
        assert len(action_ids) == 3
        assert len(set(action_ids)) == 3
        # Three source-qualified STOP probes per original Action and one
        # distinct pre-motor observation per Action = 12 in total.
        assert loop.observation_count == 3 * (3 + 1)
        assert loop.observation_count <= loop.invocation.budget.max_observations
        assert loop._settlement_reserved == 0
        assert statuses == [
            "L0_CONTINUE_MOVE", "L0_CONTINUE_MOVE",
            "L0_TARGET_REACHED_YIELD_EVALUATION",
        ]
        assert len(server.calls) == model_calls  # no L1/GPU in L0 loop
        assert owner.intent.current_intent is not None
        assert owner.skills[handoff.skill_execution_id].state is SkillState.STARTED
        journal = PhysicalActionJournal.restore(
            owner.files.physical_wal_file, self_id=owner.self_id,
        )
        assert len(journal.records) == 3
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
            first = loop.pre_action(
                observed, now_ns=15_000_000_101 if mode == "budget" else 150,
            )
            if mode == "budget":
                assert first.status == "L0_BUDGET_EXHAUSTED_YIELD_EVALUATION"
                assert loop.action_count == 0
                with pytest.raises(Stage27hLoopRefusal):
                    loop.pre_action(observed, now_ns=15_000_000_102)
                return
            native = ScriptedPlaceNative(
                handoff.native_session_id, blocked=mode == "no-progress",
            )
            receipt = await _issue(f, pre, handoff, loop, previous, observed, native)
            result = loop.observe_terminal_action(
                receipt, source_probe=observed, now_ns=180,
            )
            assert result.status == "L0_NO_PROGRESS_YIELD_EVALUATION"
            assert loop.action_count == 1
            with pytest.raises(Stage27hLoopRefusal):
                loop.pre_action(receipt.settled_probe, now_ns=200)

    _fixture(tmp_path, scenario)


def test_stage27h_uses_explicit_original_multi_preset_only(tmp_path):
    kwargs = dict(
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
    ) as actual:
        actual.return_value = Path(tmp_path / "source-report.json")
        asyncio.run(run_stage27_real_world(
            **kwargs, stage27h_l0_move_loop=True,
        ))
        assert actual.await_args.kwargs["_stage27h_multi_preset"] is True
        assert actual.await_args.kwargs["_stage27_motor_hook"] is (
            stage27h_real_a_motor_hook
        )
        actual.reset_mock()
        asyncio.run(run_stage27_real_world(**kwargs))
        assert actual.await_args.kwargs["_stage27h_multi_preset"] is False
        assert actual.await_args.kwargs["_stage27_motor_hook"] is not (
            stage27h_real_a_motor_hook
        )


def test_l0_tampered_budget_counter_rejected(tmp_path):
    async def scenario(f, lane, server):
        pre, handoff, previous, observed, loop = await _start(f, lane)
        loop.pre_action(observed, now_ns=150)
        native = SlowPlaceNative(handoff.native_session_id)
        receipt = await _issue(f, pre, handoff, loop, previous, observed, native)
        loop.observe_terminal_action(
            receipt, source_probe=observed, now_ns=180,
        )
        loop.cumulative_distance_m = 1.9
        fresh = replace(
            receipt.settled_probe,
            seq=receipt.settled_probe.seq + 1,
            request_id="fresh-after-stop-tamper",
        )
        with pytest.raises(Stage27hLoopRefusal, match="counter altered"):
            loop.pre_action(fresh, now_ns=200)

    _fixture(tmp_path, scenario)


def test_original_physical_issuer_rejects_second_action_without_explicit_l0_gate(tmp_path):
    async def scenario(f, lane, server):
        pre, handoff, previous, observed, loop = await _start(f, lane)
        native = SlowPlaceNative(handoff.native_session_id)
        assert loop.pre_action(observed, now_ns=150).status == "L0_CONTINUE_MOVE"
        first = await _issue(f, pre, handoff, loop, previous, observed, native)
        assert loop.observe_terminal_action(
            first, source_probe=observed, now_ns=200,
        ).status == "L0_CONTINUE_MOVE"
        current = replace(
            first.settled_probe, seq=first.settled_probe.seq + 1,
            request_id="next-motor-original-probe",
        )
        assert loop.pre_action(current, now_ns=250).status == "L0_CONTINUE_MOVE"
        owner = f.owners[f.names[0]]
        plan = resolve_stage27_place_motion(
            pre, handoff, current, owner=owner,
            physical=f.physical, world_epoch=pre.world_epoch,
        )
        proposal = propose_stage27c_original_place_move(
            pre, handoff, plan, current, owner=owner,
            physical=f.physical, world_epoch=pre.world_epoch,
            capability=PhysicalCapability("MOVE", 1, "locomotion", "DESTINATION", True),
            at_ns=300, provenance=Provenance("stage27h-test", "second-source"),
        )
        native.seq = current.seq
        native.tick = 1213 + current.seq * 9
        native.x = current.snapshot.position.x
        args = _args(f, pre, handoff, plan, proposal, first.settled_probe, current)
        args["at_ns"] = 1010
        before_commands = tuple(native.sent_commands)
        with pytest.raises(Stage27PlaceMoveRefusal, match="no longer eligible"):
            await f.physical.issue_place_move(native, **args)
        assert tuple(native.sent_commands) == before_commands
        ledger = PhysicalActionJournal.restore(
            owner.files.physical_wal_file, self_id=owner.self_id,
        )
        ledger.require_clear()
        assert len(ledger.records) == 1
        assert ledger.records[0]["action_id"] == first.action_id

    _fixture(tmp_path, scenario)


def test_stage27h_rejects_mixed_real_runner_modes_before_world(tmp_path):
    kwargs = dict(
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
        with pytest.raises(Stage27RealWorldRefusal, match="sole explicit DEV"):
            asyncio.run(run_stage27_real_world(
                **kwargs, stage27h_l0_move_loop=True,
                stage27g_real_l1_evaluation=True,
            ))
        original.assert_not_awaited()


def test_stage27h_rejects_preset_16_as_insufficient_for_stop_reservations(tmp_path):
    """No World start is required to discover the exact preflight flaw."""
    async def scenario(f, lane, server):
        pre, handoff, former = await qualified_a(f, lane)
        with pytest.raises(Stage27hLoopRefusal, match="bounded multi-Action"):
            Stage27hBoundedMoveLoop(
                pre, handoff, owner=f.owners[f.names[0]], physical=f.physical,
                world_epoch=pre.world_epoch, start_ns=100,
            )
        assert not f.owners[f.names[0]].supervisor.recorded_actions
    _fixture(tmp_path, scenario, budget=SkillBudget(4, 15000, 2.0, 16))


def test_stage27h_stop_quota_reserved_before_any_action(tmp_path):
    async def scenario(f, lane, server):
        pre, handoff, _, observed, loop = await _start(f, lane)
        assert loop.pre_action(observed, now_ns=150).status == "L0_CONTINUE_MOVE"
        available = STAGE27H_SETTLING_PROBE_RESERVATION
        assert available == 60
        original_count = loop.observation_count
        assert original_count == 1
        quota = loop.reserve_settling_observations(source_probe=observed)
        assert quota == available
        assert loop.observation_count == original_count + available
        with pytest.raises(Stage27hLoopRefusal, match="reservation unavailable"):
            loop.reserve_settling_observations(source_probe=observed)
        with pytest.raises(Stage27hLoopRefusal, match="reservation unresolved"):
            loop.pre_action(
                replace(observed, seq=observed.seq + 1,
                        request_id="unsafe-next-preflight"), now_ns=200,
            )
        ledger = PhysicalActionJournal.restore(
            f.owners[f.names[0]].files.physical_wal_file, self_id=f.names[0],
        )
        assert len(ledger.records) == 0
    _fixture(tmp_path, scenario)


def test_stage27h_insufficient_remaining_obs_refuses_reservation_without_effect(tmp_path):
    async def scenario(f, lane, server):
        pre, handoff, _, observed, loop = await _start(f, lane)
        assert loop.pre_action(observed, now_ns=150).status == "L0_CONTINUE_MOVE"
        # Boundary injection represents consumption of previous canonical
        # STOP probes; no new physical command may be issued with only 59 left.
        loop.observation_count = loop.invocation.budget.max_observations - 59
        with pytest.raises(Stage27hLoopRefusal, match="reservation unavailable"):
            loop.reserve_settling_observations(source_probe=observed)
        assert not f.owners[f.names[0]].supervisor.recorded_actions
    _fixture(tmp_path, scenario)


def test_stage27h_rejects_duplicated_stop_probe_without_refunding_budget(tmp_path):
    async def scenario(f, lane, server):
        pre, handoff, previous, observed, loop = await _start(f, lane)
        loop.pre_action(observed, now_ns=150)
        receipt = await _issue(
            f, pre, handoff, loop, previous, observed,
            SlowPlaceNative(handoff.native_session_id),
        )
        assert len(receipt.all_stop_probes) == 3
        forged = replace(
            receipt,
            all_stop_probes=receipt.all_stop_probes + (receipt.all_stop_probes[-1],),
        )
        with pytest.raises(Stage27hLoopRefusal, match="not fully accounted"):
            loop.observe_terminal_action(
                forged, source_probe=observed, now_ns=200,
            )
        assert loop.observation_count == 1 + STAGE27H_SETTLING_PROBE_RESERVATION
        with pytest.raises(Stage27hLoopRefusal, match="reservation unresolved"):
            loop.pre_action(
                replace(receipt.settled_probe,
                        seq=receipt.settled_probe.seq + 1,
                        request_id="blocked-after-forged-receipt"),
                now_ns=230,
            )
    _fixture(tmp_path, scenario)


def test_stage27h_bad_stop_retains_reserved_probes_and_unresolved_wal(tmp_path):
    async def scenario(f, lane, server):
        pre, handoff, previous, observed, loop = await _start(f, lane)
        loop.pre_action(observed, now_ns=150)
        with pytest.raises(PhysicalMoveRefusal, match="failed native child ACK"):
            await _issue(
                f, pre, handoff, loop, previous, observed,
                ScriptedPlaceNative(handoff.native_session_id, bad_stop=True),
            )
        assert loop.observation_count == 1 + STAGE27H_SETTLING_PROBE_RESERVATION
        journal = PhysicalActionJournal.restore(
            f.owners[f.names[0]].files.physical_wal_file, self_id=f.names[0],
        )
        assert journal.unresolved
    _fixture(tmp_path, scenario)


@pytest.mark.parametrize("cap,success", [(16, False), (17, True)])
def test_native_stop_probe_quota_counts_initial_and_every_settling_request(
    cap, success,
):
    """A 16-tick settlement can require 17 probes, so old total=16 is unsafe."""
    from experiments import cognitive_physical_move_issue_dev as source

    calls = []

    async def scripted_native_probe(
        session, *, native, after_seq, timeout_s,
    ):
        n = len(calls)
        if n >= 17:
            raise AssertionError("STOP issuer requested an unbudgeted probe")
        original = native_probe("A", n + 10, session="native-A")
        result = replace(
            original,
            snapshot=replace(
                original.snapshot,
                time=MineflayerTime(100 + n, 0, True),
            ),
        )
        calls.append(result.request_id)
        return result

    async def scenario():
        with patch.object(source, "_probe", side_effect=scripted_native_probe):
            if success:
                first, stable, settled, all_stop = await _settled(
                    object(), native="native-A", stop_seq=2, timeout_s=2.0,
                    max_probe_requests=cap,
                )
                assert len(all_stop) == 17
                assert (first.seq, stable.seq, settled.seq) == (10, 18, 26)
            else:
                with pytest.raises(PhysicalMoveRefusal, match="quota exhausted"):
                    await _settled(
                        object(), native="native-A", stop_seq=2, timeout_s=2.0,
                        max_probe_requests=cap,
                    )

    asyncio.run(scenario())
    assert len(calls) == cap
    assert len(set(calls)) == cap


def test_stage27h_original_stdout_accounts_all_stop_probes_exact_once(tmp_path):
    originals = tuple(native_probe(
        "A", seq, session="native-A",
        request_id=f"settling-{seq}",
    ) for seq in (11, 12, 13))
    raw = tmp_path / "owned-native-A.jsonl"
    events = [
        {"session_id": "native-A", "type": "observation",
         "kind": "probe", "seq": item.seq,
         "request_id": item.request_id}
        for item in originals
    ]
    raw.write_text("".join(json.dumps(x) + "\n" for x in events))
    evidence = _stage27h_all_settling_stdout_readback(
        raw, session_id="native-A", stop_seq=10, probes=originals,
    )
    assert evidence["stop_probe_count"] == 3
    assert evidence["all_stop_probes_exact_once"] is True
    with raw.open("a") as file:
        file.write(json.dumps(events[-1]) + "\n")
    with pytest.raises(Stage27RealWorldRefusal, match="differs"):
        _stage27h_all_settling_stdout_readback(
            raw, session_id="native-A", stop_seq=10, probes=originals,
        )


def _one_action_hook_result():
    """Only synthetic hook summary; not real World/Paper evidence."""
    peer = {
        "intent_event_count": 0, "skill_execution_count": 0,
        "physical_wal_sha256": "synthetic-empty", "physical_wal_action_rows": 0,
        "open_action_count": 0,
    }
    result = {
        "classification": "REAL_STAGE27H_L0_TARGET_REACHED_NATIVE_OBSERVED_DEV",
        "physical_effect_observed": True,
        "stage27_native_action_count": 1,
        "stage27h_l0_action_count": 1,
        "stage27h_l0_feedback": {
            "status": "L0_TARGET_REACHED_YIELD_EVALUATION", "action_count": 1,
            "observation_count": 19, "target_status": "CONDITION_OBSERVED",
        },
        "stage27h_original_action_witnesses": [{
            "action": "stage27c-A-39",
            "l0_feedback": {
                "status": "L0_TARGET_REACHED_YIELD_EVALUATION",
                "action_count": 1, "observation_count": 19,
            },
            "goal_success": False, "skill_success": False,
        }],
        "stage27h_peer_b_before": peer,
        "stage27h_peer_b_after": dict(peer),
        "original_peer_b_before": peer,
        "original_peer_b_after": dict(peer),
        "stage27h_self_a_intent_current": "original-intent-A",
        "stage27h_self_a_skill_state": "started",
        "stage27h_goal_success": False,
        "stage27h_skill_success": False,
    }
    return result


def test_stage27h_parent_contract_one_action_arrival_preserves_original(tmp_path):
    """One MOVE inside original arrival envelope is valid; not multi-MOVE proof."""
    source = _one_action_hook_result()
    receipt = _preserve_and_validate_stage27h_hook_return(
        source, evidence=tmp_path,
    )
    assert receipt["original_hook_contract_valid"] is True
    file = tmp_path / "stage27h-original-motor-hook-return.json"
    assert file.exists()
    assert json.loads(file.read_bytes()) == source
    assert receipt["original_hook_return_sha256"]
    assert receipt["original_hook_frozen_before_parent_aggregation"] is True


def test_stage27h_parent_contract_three_original_actions_is_typed(tmp_path):
    source = _one_action_hook_result()
    source["stage27_native_action_count"] = 3
    source["stage27h_l0_action_count"] = 3
    source["stage27h_l0_feedback"]["action_count"] = 3
    source["stage27h_original_action_witnesses"] = [
        {
            "action": f"stage27c-A-{39+i}",
            "l0_feedback": {
                "action_count": i + 1,
                "status": (
                    "L0_TARGET_REACHED_YIELD_EVALUATION" if i == 2
                    else "L0_CONTINUE_MOVE"
                ),
            },
            "goal_success": False, "skill_success": False,
        } for i in range(3)
    ]
    assert _preserve_and_validate_stage27h_hook_return(
        source, evidence=tmp_path,
    )["original_hook_contract_valid"]


@pytest.mark.parametrize("fault", [
    "missing-physical-key", "physical-nonbool", "false-effect", "wrong-count",
    "peer-mutated", "peer-report-mismatch", "wrong-status", "skill-completed",
    "goal-completed", "duplicate-actions", "missing-feedback",
])
def test_stage27h_post_effect_aggregation_fail_closed_with_durable_evidence(
    tmp_path, fault,
):
    source = _one_action_hook_result()
    if fault == "missing-physical-key":
        del source["physical_effect_observed"]
    elif fault == "physical-nonbool":
        source["physical_effect_observed"] = 1
    elif fault == "false-effect":
        source["physical_effect_observed"] = False
    elif fault == "wrong-count":
        source["stage27_native_action_count"] = 0
    elif fault == "peer-mutated":
        source["stage27h_peer_b_after"]["intent_event_count"] = 1
    elif fault == "peer-report-mismatch":
        source["original_peer_b_after"]["intent_event_count"] = 1
    elif fault == "wrong-status":
        source["classification"] = "REAL_STAGE27H_L0_BUDGET_EXHAUSTED_DEV"
    elif fault == "skill-completed":
        source["stage27h_self_a_skill_state"] = "succeeded"
    elif fault == "goal-completed":
        source["stage27h_goal_success"] = True
    elif fault == "duplicate-actions":
        source["stage27h_l0_action_count"] = 2
        source["stage27_native_action_count"] = 2
        source["stage27h_l0_feedback"]["action_count"] = 2
        source["stage27h_original_action_witnesses"] *= 2
        source["stage27h_original_action_witnesses"][1]["l0_feedback"]["action_count"] = 2
    elif fault == "missing-feedback":
        del source["stage27h_l0_feedback"]
    with pytest.raises(RealPresetCheckpointRefusal, match="motor-hook"):
        _preserve_and_validate_stage27h_hook_return(
            source, evidence=tmp_path,
        )
    # The invalid return is captured *before* parent starts indexing keys
    # and must survive HOLD to explain any prior irreversible Action.
    stored = tmp_path / "stage27h-original-motor-hook-return.json"
    assert stored.is_file()
    assert json.loads(stored.read_bytes()) == source


def test_stage27h_nonselected_motor_return_is_nonissuing(tmp_path):
    peer = {"intent_event_count": 0, "skill_execution_count": 0}
    source = {
        "classification": "REAL_STAGE27_A_MOVE_NOT_SELECTED_NO_PHYSICAL_DEV",
        "physical_effect_observed": False,
        "stage27_native_action_count": 0,
        "original_peer_b_before": peer, "original_peer_b_after": dict(peer),
    }
    evidence = _preserve_and_validate_stage27h_hook_return(
        source, evidence=tmp_path,
    )
    assert evidence["original_hook_contract_valid"]
    assert not source["physical_effect_observed"]


def test_stage27h_parent_result_file_is_write_once_no_replay(tmp_path):
    source = _one_action_hook_result()
    _preserve_and_validate_stage27h_hook_return(source, evidence=tmp_path)
    with pytest.raises(FileExistsError):
        _preserve_and_validate_stage27h_hook_return(source, evidence=tmp_path)
