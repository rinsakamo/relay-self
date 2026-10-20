"""One W4 DEV owner: real decoder, original collector, host and S16, fake I/O."""
from __future__ import annotations

import asyncio
import json
import math
import time
from dataclasses import asdict, replace
from types import SimpleNamespace

import pytest

from adapters.mineflayer.normal_action import (
    NormalActionAuthorization,
    NormalActionStage,
    NormalSessionActionExecutor,
    NormalWorldL0,
    observe_closed_native_actions,
)
from adapters.mineflayer.s31a_real_server_ci import (
    _command,
    _correlated_observe,
    _ready_server,
)
from adapters.mineflayer.s34_native_world_cognition_ci import (
    _native_epoch_two,
    _native_threat,
)
from adapters.mineflayer.self_world_stage_w4_lease import W4DevNativeObservationPort
from adapters.mineflayer.self_world_stage_w4_logtap import (
    capture_w4_collector_cursor,
    marker_as_w4_window_event,
    wait_for_w4_collector_marker,
)
from adapters.mineflayer.self_world_stage_w4_optin_offline import (
    reconcile_w4_s49_optin_offline,
    seal_w4_s49_optin_offline,
)
from adapters.mineflayer.self_world_stage_w4_preflight import W4PreworldBlocked
from adapters.mineflayer.self_world_stage_w4_window import W4WindowEvent
from relay_self.action_supervision import ActionSupervisor
from relay_self.execution_binding import ExecutionBinding, resolve_execution_binding
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.reactive_l0 import L0ActionGrant
from test_self_world_stage_w4_lease import launch, preworld
from test_self_world_stage_w4_prehost import _offline_lines, _wire
from test_self_world_stage_w4_window import TOKEN


def _action_frames(session_id, post, action_id):
    import test_action_feedback_qualification as s17

    def native(seq, dx):
        # Prepare typed orientation in the RAW synthetic native producer frame,
        # before the unchanged decoder/S16 sees it; never patch old outcomes.
        position = replace(
            post.snapshot.position, x=post.snapshot.position.x + dx,
        )
        original_target = post.snapshot.nearby_entities[0]
        native_distance = math.dist(
            (position.x, position.y, position.z),
            (original_target.position.x, original_target.position.y,
             original_target.position.z),
        )
        # Derive the native synthetic registry distance from *this* source
        # frame's position+target, not from a previously captured result.
        target = replace(original_target, distance=native_distance)
        oriented = replace(
            post, seq=seq, request_id=None,
            snapshot=replace(
                post.snapshot, position=position, nearby_entities=(target,),
            ),
        )
        record = json.loads(_wire(oriented, seq))
        record.pop("request_id", None)  # Original S16 uses uncorrelated probes.
        return (json.dumps(record) + "\n").encode()

    def effect(seq, name, aid):
        record = asdict(s17.effect(seq, aid, name))
        record.update(type="effect_result", session_id=session_id)
        return (json.dumps(record) + "\n").encode()

    return (
        native(6, 0.),
        effect(7, "set_control", action_id),
        effect(8, "clear_controls", action_id + "-s15-clear"),
        native(9, 0.2),
    )


async def _one_original_owner(
    monkeypatch, tmp_path, *, broken=None, tamper=None, close_tamper=None,
):
    import test_postmain_s42_world_contrast as s42

    # S42's deterministic S19 fixture internally runs asyncio.run(); isolate
    # fixture construction from this already-running joint asyncio event loop.
    retained, _near, _far, _, _ = await asyncio.to_thread(s42._pair)
    pre, post, basic = _offline_lines()
    # This new fake source uses the ORIGINAL S49 event-seq naming rule:
    # entity event 4 -> correlated request event-4 -> native move/binding 4.
    # Never rewrite a previously captured original/frozen receipt.
    post = replace(post, request_id=f"s49-actual:{pre.session_id}:event-4")
    action_id = "s49-native-move-4"
    incoming = basic[:5] + (_wire(post, 5),) + _action_frames(
        pre.session_id, post, action_id,
    )
    # Supply only startup + PREWORLD native frames initially. If a future
    # World observation is read before the collector barrier, fake stdout
    # reaches EOF and the original lease fails closed instead of silently
    # consuming a pre-buffered postworld result.
    session, owner, native_process, _ = await launch(
        monkeypatch, lines=incoming[:4],
    )
    receipt, ledger = await preworld(session, owner, pre)
    assert not native_process.stdout.lines
    commands = receipt.candidate_commands
    before = ledger.captured_frames[-1]

    stream = asyncio.StreamReader()
    stream.feed_data(b"[00:00] [Server thread/INFO]: Done (1s)! For help\n")
    writes = []
    class Sink:
        def write(self, raw):
            writes.append(raw)
            if raw == (commands.confirm_command + "\n").encode():
                stream.feed_data((
                    "[19:00] [Server thread/INFO]: "
                    + commands.expected_log_suffix + "\n"
                ).encode())
        async def drain(self):
            return None

    server = SimpleNamespace(stdin=Sink(), stdout=stream, returncode=None, pid=4242)

    async def synthetic_java(*args, **kwargs):
        assert args[0] == "java"
        return server

    # Do not leave any launch that could fall through to a real subprocess.
    monkeypatch.setattr(asyncio, "create_subprocess_exec", synthetic_java)
    original_server, collector, _ = await _ready_server(
        tmp_path, tmp_path / "fixture-only.jar", tmp_path / "collector.log",
    )
    events = []
    def record(name, content, *, server_event=False):
        previous = events[-1].monotonic_ns if events else 0
        events.append(W4WindowEvent(
            name, len(events) + 1, max(time.monotonic_ns(), previous + 1),
            "existing_world_experimenter" if server_event else "sole_native_reader",
            content, 4242 if server_event else None,
        ))

    trace = None
    closures = []
    original_receipts = []
    try:
        record("native_before_probe", before.provenance.reference)
        cursor = capture_w4_collector_cursor(tmp_path / "collector.log")
        session.advance(owner=owner, phase="WORLD_WINDOW", binding="w4-fixture-window")
        for name, command, digest in (
            ("summon", commands.summon_command, commands.summon_sha256),
            ("confirm", commands.confirm_command, commands.confirm_sha256),
        ):
            _command(original_server, command)
            record(f"server_{name}_write", digest, server_event=True)
            await original_server.stdin.drain()
            record(f"server_{name}_drain", digest, server_event=True)
        marker = await wait_for_w4_collector_marker(
            cursor, commands, timeout_s=0.3, poll_s=0.001,
        )
        events.append(marker_as_w4_window_event(
            marker, order=len(events) + 1, server_pid=4242,
        ))
        session.world_marker(owner=owner, marker=marker)
        # Only this synthetic producer releases the later entity/probe/S16
        # bytes. This is a fixture ordering barrier, NOT evidence of actual
        # Minecraft source custody or server tick chronology.
        assert not native_process.stdout.lines
        native_process.stdout.lines.extend(incoming[4:])
        op = session.advance(owner=owner, phase="HOST", binding="w4-fixture-host")

        intent = IntentCommitment()
        intent.commit(
            "escape-threat", objective="escape near zombie", at_ns=1,
            provenance=Provenance("fixture-operator", "intent"),
        )
        executor = NormalSessionActionExecutor(pre.session_id, intent)
        host = NormalWorldL0(
            pre.session_id, "escape-threat", retained, max_events=1,
            max_action_requests=1,
        )
        port = W4DevNativeObservationPort(session, owner=owner)
        holder = []

        def probe(_event):
            async def original_correlated():
                after = await _correlated_observe(session, post.request_id)
                session._bridge._handoff.after_world(
                    after, owner=owner, request_id=post.request_id,
                )
                holder.append(after)
                record("native_after_probe", after.provenance.reference)
                return after
            session.bind_probe(owner=owner, request_id=post.request_id)
            return session.delegate(
                owner=owner, operation=session._operation,
                invoke=original_correlated,
            )

        def grant(choice, event_seq):
            if broken == "missing_grant":
                return None
            return L0ActionGrant(
                "fixture-l0", action_id, "escape-threat", pre.session_id,
                event_seq, choice.probe_seq, choice.entity_id, True,
                Provenance("fixture-operator", "l0"),
            )

        async def on_action(step):
            native = _native_threat(
                holder[-1], holder[-1].request_id,
                expected_entity_id=step.choice.entity_id,
            )
            values, _ = _native_epoch_two(
                ActionSupervisor(), intent, retained, retained,
                expected_revision=1, native=native,
            )
            binding = ExecutionBinding(
                "s49-binding-4", "MOVE_AWAY", "escape-threat",
                "fixture-skill", "escape-movement", action_id,
                "MOVE_BACKWARD", Provenance("fixture-operator", "binding"),
            )
            bound = resolve_execution_binding(
                values["admission"], values["control"], values["route"],
                intent, values["policies"][-2], binding,
                provenance=Provenance("fixture-operator", "admitted"),
            )
            def authorize(stage):
                if broken == "missing_issue" and stage is NormalActionStage.ISSUE:
                    return None
                return NormalActionAuthorization(
                    stage, "fixture-" + stage.value, "escape-threat",
                    pre.session_id, action_id, step.event_seq,
                    holder[-1].seq, step.choice.entity_id, True,
                    Provenance("fixture-operator", stage.value),
                )
            session.advance(
                owner=owner, phase="ACTION_READ", binding=action_id,
                supervisor=executor.supervisor,
            )
            original_receipts.append(await executor.execute(
                session, step, bound, holder[-1],
                authorize(NormalActionStage.PROPOSE),
                authorize(NormalActionStage.ISSUE),
            ))
            session.advance(owner=owner, phase="HOST", binding="w4-host-return")

        async def original_host():
            return await host.run_session(
                port, probe=probe, grant=grant,
                on_action_request=on_action, max_frames=10,
            )

        with observe_closed_native_actions(closures.append):
            trace = await asyncio.wait_for(
                session.delegate(owner=owner, operation=op, invoke=original_host),
                timeout=10,
            )
        if broken in {"missing_issue", "missing_grant"}:
            raise AssertionError("missing independent authority should have rejected")

        assert len(original_receipts) == len(closures) == 1
        assert original_receipts[0].terminal is closures[0].terminal
        assert original_receipts[0].consequence is closures[0].consequence
        assert original_receipts[0].consequence.error is None
        assert original_receipts[0].terminal.state.value == "outcome"
        assert host.retained is retained
        assert [f.seq for f in ledger.captured_frames] == [2, 3]
        assert len(writes) == 2
        assert writes == [
            (commands.summon_command + "\n").encode(),
            (commands.confirm_command + "\n").encode(),
        ]
        checked_ledger = ledger
        checked_events = tuple(events)
        checked_closure = closures[0]
        if tamper == "foreign_ledger":
            checked_ledger = replace(ledger, session_id="foreign")
        elif tamper == "missing_marker":
            session._marker = False
        elif tamper == "source_rewrite":
            checked_events = (*events[:-1], replace(events[-1], content="forged"))
        elif tamper == "missing_closure":
            checked_closure = None
        elif tamper == "pending_read":
            session._pending = object()
        elif tamper == "identity_mismatch":
            checked_closure = replace(
                checked_closure,
                original_probe=replace(holder[-1], request_id="foreign"),
            )
        result = reconcile_w4_s49_optin_offline(
            session=session, ledger=checked_ledger, before=before,
            after=holder[-1], host_trace=trace, events=checked_events,
            expected_session=pre.session_id,
            before_request_id=pre.request_id,
            after_request_id=post.request_id,
            slot=1, one_time_token=TOKEN, original_closed=checked_closure,
        )
        assert result["original_s16_closed"]
        assert result["window"]["observed_zombie_id"] == trace[0].choice.entity_id
        assert result["evidence_scope"] == "SYNTHETIC_DEV_ONLY"
        assert not result["live_owner_attested"]
        assert not result["physical_run_permitted"]
        assert not result["s10_permission"]
        assert native_process.stdout.reads == list(incoming)
        # A composition readback before clean shutdown is NOT a final seal.
        with pytest.raises(W4PreworldBlocked):
            seal_w4_s49_optin_offline(session=session, composition=result)
        session.advance(owner=owner, phase="QUIESCE", binding="stop-host")
        session.advance(owner=owner, phase="SHUTDOWN", binding="exit")
        assert await session.shutdown() == 0
        assert session.phase == "CLOSED"
        if close_tamper == "all_close_negatives":
            # One full original pipeline, then six *read-only* verdicts
            # against independently restored local closeout mutations.
            # No second Java/Node fixture or S16 execution is necessary.
            for attack in (
                "node_nonzero", "false_shutdown", "pending_read",
                "audit_abort", "promoted_scope", "wrong_session",
            ):
                if attack == "node_nonzero":
                    native_process.returncode = 1
                elif attack == "false_shutdown":
                    session._shutdown_completed = False
                elif attack == "pending_read":
                    session._pending = object()
                elif attack == "audit_abort":
                    session._record("ABORT", detail="fixture-only-mutation")
                elif attack == "promoted_scope":
                    result["live_owner_attested"] = True
                elif attack == "wrong_session":
                    result["session_id"] = "foreign"
                with pytest.raises(W4PreworldBlocked):
                    seal_w4_s49_optin_offline(
                        session=session, composition=result,
                    )
                if attack == "node_nonzero":
                    native_process.returncode = 0
                elif attack == "false_shutdown":
                    session._shutdown_completed = True
                elif attack == "pending_read":
                    session._pending = None
                elif attack == "audit_abort":
                    assert session._audit.pop().event == "ABORT"
                elif attack == "promoted_scope":
                    result["live_owner_attested"] = False
                elif attack == "wrong_session":
                    result["session_id"] = pre.session_id
        sealed = seal_w4_s49_optin_offline(session=session, composition=result)
        assert sealed["local_shutdown_completed"]
        assert sealed["node_exit_code"] == 0
        assert not sealed["live_owner_attested"]
        assert not sealed["physical_run_permitted"]
        return sealed
    finally:
        stream.feed_eof()
        await collector


def test_combined_original_reader_collector_host_and_s16_one_fixture(monkeypatch, tmp_path):
    receipt = asyncio.run(_one_original_owner(monkeypatch, tmp_path))
    assert receipt["preworld_captured_sequences"] == [2, 3]
    assert receipt["preworld_unsolicited_sequences"] == [2]
    assert receipt["native_delivered_frames"] == 10
    assert receipt["host_decisions"] == 1
    assert receipt["original_s16_stage_s_join"] is not None


@pytest.mark.parametrize("fault", ("missing_issue", "missing_grant"))
def test_same_fake_collector_cannot_supply_original_action_grant(monkeypatch, tmp_path, fault):
    from adapters.mineflayer.normal_action import NormalActionRejected
    from relay_self.reactive_l0 import ReactiveL0Rejected

    with pytest.raises((NormalActionRejected, ReactiveL0Rejected)):
        asyncio.run(_one_original_owner(monkeypatch, tmp_path, broken=fault))


@pytest.mark.parametrize("attack", (
    "foreign_ledger", "missing_marker", "source_rewrite", "missing_closure",
    "pending_read", "identity_mismatch",
))
def test_joint_readback_vetoes_independent_witness_substitution(monkeypatch, tmp_path, attack):
    # Full decoder/collector/host/S16 path first; tamper one distinct seal
    # only at joint readback. No unqualified IO before the rejection.
    with pytest.raises(W4PreworldBlocked):
        asyncio.run(_one_original_owner(monkeypatch, tmp_path, tamper=attack))


def test_final_seal_rejects_dirty_or_forged_shutdown(monkeypatch, tmp_path):
    # Preserve all six independent veto assertions in one closed session;
    # original S49/S16/collector setup should not be repeated six times.
    sealed = asyncio.run(_one_original_owner(
        monkeypatch, tmp_path, close_tamper="all_close_negatives",
    ))
    assert sealed["local_shutdown_completed"]
