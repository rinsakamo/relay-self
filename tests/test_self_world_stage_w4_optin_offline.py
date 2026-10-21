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
    audit_original_s49_cleanup_claim_offline,
    reconcile_w4_s49_optin_offline,
    replay_original_s49_cleanup_stdout_offline,
    review_s49_cleanup_finalization_candidate,
    review_w4_s49_phase_b_optin_offline,
    seal_w4_s49_optin_offline,
)
from adapters.mineflayer.self_world_stage_w4_preflight import W4PreworldBlocked
from adapters.mineflayer.self_world_stage_w4_window import W4WindowEvent
from relay_self.action import ActionState
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


def _w4_s49_report_claim():
    """Only untrusted local report contents; never an actual S49 evidence run."""
    sid = "session-1"
    steps = [
        {
            "event_seq": seq, "probe_seq": probe, "entity_id": seq,
            "selected": "WAIT" if i == 0 else "MOVE_AWAY",
            "issued": i != 0, "distance_m": 10.0 if i == 0 else 2.0,
        }
        for i, (seq, probe) in enumerate(((1, 2), (3, 4), (5, 6)))
    ]
    source_pairs = [
        {
            "event_seq": step["event_seq"],
            "event_kind": "entities",
            "event_entities": [{
                "name": "zombie", "id": step["entity_id"],
                "d": step["distance_m"],
            }],
            "probe_seq": step["probe_seq"],
            "probe_entities": [{
                "name": "zombie", "id": step["entity_id"],
                "d": step["distance_m"],
            }],
        }
        for step in steps
    ]
    actions = [
        {
            "action": f"s49-native-move-{step['event_seq']}",
            "terminal": ActionState.OUTCOME.value, "source": sid,
            "event_seq": step["event_seq"], "probe_seq": step["probe_seq"],
            "movement_m": 0.2,
        }
        for step in steps[1:]
    ]
    return {
        "milestone": "S49", "stage": "CLOSED", "status": "PASS",
        "session_id": sid, "node_exit": 0, "server_exit": 0,
        "decisions": steps, "actual_native_actions": actions,
        "source_pair_trace": source_pairs,
        "classification": "REAL_ONE_SESSION_L0_WAIT_TWO_AUTHORIZED_MOVES_QUALIFIED",
        "w3_node_stdout_capture": {
            "schema": "relay-self-w3-node-stdout-v0",
            "scope": "NODE_BRIDGE_STDOUT_JSONL_BYTES_NOT_MINECRAFT_TCP",
            "session_id": sid, "status": "COMPLETE_NODE_STDOUT",
            "eof_observed": True, "shutdown_ack_count": 1,
            "process_exit_code": 0, "seal_reason": "clean_shutdown",
            "capture_fault": None,
            "minecraft_tcp_packets_attested": False,
            "external_source_independence_attested": False,
            "s10_commit_permitted": False, "physical_wait_permitted": False,
            "science_qualified": False,
        },
    }



def _s49_stage_r_report_claim():
    """Stage R's unchanged producer summary schema; JSON only, no S10."""
    report = _w4_s49_report_claim()
    sid = report["session_id"]
    decisions = report["decisions"]
    first_action = report["actual_native_actions"][0]["action"]
    # Stage R requires the terminal AFTER-native observation before the
    # later event request, and that event before its correlated probe.
    decisions[2]["event_seq"] = 10
    decisions[2]["probe_seq"] = 11
    report["source_pair_trace"][2].update(event_seq=10, probe_seq=11)
    report["actual_native_actions"][1].update(
        action="s49-native-move-10", event_seq=10, probe_seq=11,
    )
    report["stage_r_dev_enabled"] = True
    report["classification"] = "DEV_ONLY_S49_SINGLE_WRITER_HOLD_REV2"
    report["learning_in_world"] = True
    report["stage_r_decision_revisions"] = [
        {
            "event_seq": step["event_seq"],
            "retained_revision": 2 if i == 2 else 1,
            "retained_value": 4,
            "selected": step["selected"],
        }
        for i, step in enumerate(decisions)
    ]
    report["stage_r_owner"] = {
        "kind": "stage_r_dev_single_writer",
        "classification": "DEV_ONLY_NOT_SCIENCE",
        "original_session_id": sid,
        "initial_revision": 1, "current_revision": 2,
        "current_value": 4,
        "joint_l0_s14_owner_identity": True,
        "operator_s10_grants": 1,
        "s10_hold_commits": 1,
        "original_action_closures": 2,
        "pending_unsealed_or_unknown": False,
        "grant_independent_external_attestation": False,
        "hold_reward_or_policy_gain": False,
        "additional_action_issuer": False,
        "commit_source": {
            "terminal_action_id": first_action,
            "terminal_after_native_seq": 7,
            "next_source_probe_seq": decisions[2]["probe_seq"],
            "next_source_request_id": (
                f"s49-actual:{sid}:event-{decisions[2]['event_seq']}"
            ),
            "feedback_id": "synthetic-hold-feedback",
            "s10_authority_id": (
                f"s49-dev-operator-s10-once:{sid}:{first_action}"
            ),
            "s10_authority_source": "s49-dev-learning-owner",
            "s10_commit_revision": 2,
        },
    }
    return report


def _w4_s49_closed_claim():
    return {
        "schema": "W4_S49_OPTIN_COMPOSITION_OFFLINE_CLOSED_V0",
        "session_id": "session-1",
        "local_shutdown_completed": True,
        "node_exit_code": 0,
        "evidence_scope": "SYNTHETIC_DEV_ONLY",
        "live_owner_attested": False, "external_custody_qualified": False,
        "physical_run_permitted": False, "s10_permission": False,
        "science_qualified": False,
    }


def _local_w3_synthetic_archive(tmp_path):
    # No process launch: build exactly the W3 local capture format and
    # let the existing independent W3 decoder verify saved raw JSONL.
    from adapters.mineflayer.self_world_stage_w3_capture import W3RawNodeStdoutCapture
    from test_self_world_stage_w3_capture import _fixture_lines

    capture = W3RawNodeStdoutCapture(tmp_path)
    for raw in _fixture_lines():
        frame = json.loads(raw)
        capture.append_before_decode(raw)
        capture.after_decoder(
            session_id=frame["session_id"], seq=frame["seq"],
            message_type=frame["type"],
        )
    capture.mark_eof()
    result = capture.seal(exit_code=0, reason="clean_shutdown")
    assert result["status"] == "COMPLETE_NODE_STDOUT"
    return result


def test_s49_report_only_claim_cannot_enter_phase_b_offline_review(tmp_path):
    report = _w4_s49_report_claim()
    claim = audit_original_s49_cleanup_claim_offline(report=report)
    assert claim["producer_claimed_stop_ack"] == 1
    assert claim["reported_decisions"] == 3
    assert claim["reported_actions"] == 2
    assert claim["reported_correlated_pairs"] == 3
    assert report["actual_native_actions"][0]["terminal"] == "outcome"
    assert not claim["raw_stdout_independently_replayed"]
    # No raw files: plausible producer report alone is not replay.
    with pytest.raises(W4PreworldBlocked):
        review_w4_s49_phase_b_optin_offline(
            selected_mode="W4_S49_SYNTHETIC_OFFLINE_REVIEW",
            explicit_opt_in=True, closed_composition=_w4_s49_closed_claim(),
            report=report, archive_root=tmp_path,
        )


def test_w3_raw_file_and_s49_report_replayed_for_offline_only(tmp_path):
    report = _w4_s49_report_claim()
    report["w3_node_stdout_capture"] = _local_w3_synthetic_archive(tmp_path)
    verified = replay_original_s49_cleanup_stdout_offline(
        report=report, archive_root=tmp_path,
    )
    assert verified["raw_stdout_independently_replayed"]
    assert verified["node_stdout_frame_count"] == 3
    assert verified["evidence_scope"] == "LOCAL_W3_RAW_REPLAY_NOT_EXTERNAL_CUSTODY"
    assert not verified["external_custody_qualified"]
    result = review_w4_s49_phase_b_optin_offline(
        selected_mode="W4_S49_SYNTHETIC_OFFLINE_REVIEW",
        explicit_opt_in=True, closed_composition=_w4_s49_closed_claim(),
        report=report, archive_root=tmp_path,
    )
    assert not result["original_s49_qualify_wired"]
    assert not result["live_original_owner_permitted"]
    assert result["scope"] == "SYNTHETIC_LOCAL_W3_RAW_REPLAY_NO_EXTERNAL_CUSTODY"
    assert not result["physical_run_permitted"]
    assert result["next_gate"] == "W4_EXTERNAL_TRUST_NO_GO_PREWORLD_BLOCKED"


@pytest.mark.parametrize("fault", (
    "report_sha", "report_frame_count", "raw_extra_bytes",
    "receipt_missing", "archive_symlink", "foreign_session",
))
def test_w3_raw_local_replay_rejects_producer_mismatch(tmp_path, fault):
    report = _w4_s49_report_claim()
    report["w3_node_stdout_capture"] = _local_w3_synthetic_archive(tmp_path)
    root = tmp_path
    if fault == "report_sha":
        report["w3_node_stdout_capture"]["stdout_sha256"] = "0" * 64
    elif fault == "report_frame_count":
        report["w3_node_stdout_capture"]["frame_count"] = 99
    elif fault == "raw_extra_bytes":
        file = tmp_path / "w3-node-stdout.raw.jsonl"
        file.write_bytes(file.read_bytes() + b"forged\\n")
    elif fault == "receipt_missing":
        (tmp_path / "w3-node-stdout-receipt.json").unlink()
    elif fault == "archive_symlink":
        root = tmp_path / "linked"
        root.symlink_to(tmp_path, target_is_directory=True)
    elif fault == "foreign_session":
        report["session_id"] = "foreign"
    with pytest.raises(W4PreworldBlocked):
        replay_original_s49_cleanup_stdout_offline(
            report=report, archive_root=root,
        )


@pytest.mark.parametrize("fault", (
    "node_missing", "node_nonzero", "node_bool", "node_cleanup_error",
    "server_missing", "server_nonzero", "server_cleanup_error",
    "status_blocked", "stage_not_closed", "capture_missing",
    "ack_missing", "ack_duplicate", "eof_missing", "bad_capture_status",
    "capture_other_session", "capture_node_nonzero", "capture_error",
    "fake_tcp_attested", "s10_promoted", "science_promoted",
))
def test_s49_cleanup_report_vetoes_all_unreliable_status_claims(fault):
    report = _w4_s49_report_claim()
    capture = report["w3_node_stdout_capture"]
    if fault == "node_missing":
        report.pop("node_exit")
    elif fault == "node_nonzero":
        report["node_exit"] = 1
    elif fault == "node_bool":
        report["node_exit"] = False
    elif fault == "node_cleanup_error":
        report["node_cleanup_error"] = "timeout"
    elif fault == "server_missing":
        report.pop("server_exit")
    elif fault == "server_nonzero":
        report["server_exit"] = -9
    elif fault == "server_cleanup_error":
        report["server_cleanup_error"] = "cancelled"
    elif fault == "status_blocked":
        report["status"] = "BLOCKED"
    elif fault == "stage_not_closed":
        report["stage"] = "UNATTENDED_NATIVE_EVENT_LOOP"
    elif fault == "capture_missing":
        report.pop("w3_node_stdout_capture")
    elif fault == "ack_missing":
        capture["shutdown_ack_count"] = 0
    elif fault == "ack_duplicate":
        capture["shutdown_ack_count"] = 2
    elif fault == "eof_missing":
        capture["eof_observed"] = False
    elif fault == "bad_capture_status":
        capture["status"] = "INCOMPLETE_UNQUALIFIED"
    elif fault == "capture_other_session":
        capture["session_id"] = "foreign"
    elif fault == "capture_node_nonzero":
        capture["process_exit_code"] = 1
    elif fault == "capture_error":
        capture["capture_fault"] = "bad_frame"
    elif fault == "fake_tcp_attested":
        capture["minecraft_tcp_packets_attested"] = True
    elif fault == "s10_promoted":
        capture["s10_commit_permitted"] = True
    elif fault == "science_promoted":
        capture["science_qualified"] = True
    with pytest.raises(W4PreworldBlocked):
        audit_original_s49_cleanup_claim_offline(report=report)


@pytest.mark.parametrize("fault", (
    "default_mode", "live_mode", "no_optin", "wrong_session",
    "open_session", "nonzero_exit", "fake_live_scope",
    "claim_fake_live_scope", "missing_claim", "wrong_classification",
    "unbound_stage_r_classification",
    "node_terminate_error", "stage_world_cleanup_error", "temp_cleanup_error",
    "stage_r_cleanup_error", "error_key", "false_stage_r_dev",
    "capture_scope_exaggerated",
))
def test_phase_b_mode_gate_blocks_implicit_or_live_wiring(tmp_path, fault):
    selected_mode = "W4_S49_SYNTHETIC_OFFLINE_REVIEW"
    explicit_opt_in = True
    closed = _w4_s49_closed_claim()
    report = _w4_s49_report_claim()
    report["w3_node_stdout_capture"] = _local_w3_synthetic_archive(tmp_path)
    if fault == "default_mode":
        selected_mode = "S49"
    elif fault == "live_mode":
        selected_mode = "W4_S49_LIVE"
    elif fault == "no_optin":
        explicit_opt_in = False
    elif fault == "wrong_session":
        report["session_id"] = "foreign"
    elif fault == "open_session":
        closed["local_shutdown_completed"] = False
    elif fault == "nonzero_exit":
        closed["node_exit_code"] = 1
    elif fault == "fake_live_scope":
        closed["physical_run_permitted"] = True
    elif fault == "claim_fake_live_scope":
        report["w3_node_stdout_capture"]["external_source_independence_attested"] = True
    elif fault == "missing_claim":
        report.pop("w3_node_stdout_capture")
    elif fault == "wrong_classification":
        report["classification"] = "PENDING_REAL_NATIVE_EVIDENCE"
    elif fault == "unbound_stage_r_classification":
        report["classification"] = "DEV_ONLY_S49_SINGLE_WRITER_HOLD_REV2"
    elif fault in {
        "node_terminate_error", "stage_world_cleanup_error",
        "temp_cleanup_error", "stage_r_cleanup_error",
    }:
        report[fault] = "synthetic failure"
    elif fault == "error_key":
        report["error"] = ""
    elif fault == "false_stage_r_dev":
        report["stage_r_dev_enabled"] = "false"
    elif fault == "capture_scope_exaggerated":
        report["w3_node_stdout_capture"]["minecraft_tcp_packets_attested"] = True
    with pytest.raises(W4PreworldBlocked):
        review_w4_s49_phase_b_optin_offline(
            selected_mode=selected_mode, explicit_opt_in=explicit_opt_in,
            closed_composition=closed, report=report, archive_root=tmp_path,
        )


def _s49_cleanup_candidate_fixture():
    return {
        "milestone": "S49", "status": "PASS", "stage": "CLOSED",
        "session_id": "fixture-session", "node_exit": 0,
        "server_exit": 0,
        "classification": "REAL_ONE_SESSION_L0_WAIT_TWO_AUTHORIZED_MOVES_QUALIFIED",
    }


def test_s49_finalization_candidate_clean_normal_s49_without_claimed_ack():
    report = _s49_cleanup_candidate_fixture()
    original = dict(report)
    result = review_s49_cleanup_finalization_candidate(
        report=report, provisional_rc=0,
    )
    assert result["candidate_final_status"] == "PASS"
    assert result["candidate_rc"] == 0
    assert result["candidate_final_classification"] == report["classification"]
    assert result["candidate_classification_scope"] == "UNTRUSTED_PRODUCER_REPORT_ONLY"
    assert result["reported_cleanup_consistent"]
    assert not result["raw_stdout_independently_replayed"]
    assert not result["external_custody_qualified"]
    assert report == original
    assert not result["original_qualify_modified"]
    assert not result["physical_run_permitted"]


@pytest.mark.parametrize("attack,reason", (
    ("node_nonzero", "NODE_EXIT_NOT_ZERO"),
    ("node_missing", "NODE_EXIT_NOT_ZERO"),
    ("node_bool", "NODE_EXIT_NOT_ZERO"),
    ("node_cleanup_exception", "NODE_CLEANUP_ERROR"),
    ("node_cleanup_blank", "NODE_CLEANUP_ERROR"),
    ("java_nonzero", "JAVA_EXIT_NOT_ZERO"),
    ("java_missing", "JAVA_EXIT_NOT_ZERO"),
    ("java_cleanup_exception", "JAVA_CLEANUP_ERROR"),
    ("premature_stage", "PREMATURE_PASS"),
    ("premature_rc", "PREMATURE_PASS"),
    ("w3_capture_missing_ack", "W3_CAPTURE_INCOMPLETE"),
    ("w3_capture_wrong_session", "W3_CAPTURE_INCOMPLETE"),
    ("qualified_label_missing", "PROVISIONAL_CLASSIFICATION_INVALID"),
    ("unrecognized_label", "PROVISIONAL_CLASSIFICATION_INVALID"),
    ("dev_label_without_stage_r", "PROVISIONAL_CLASSIFICATION_INVALID"),
    ("stage_r_standard_label", "PROVISIONAL_CLASSIFICATION_INVALID"),
    ("node_terminate_error", "NODE_TERMINATE_ERROR"),
    ("stage_r_cleanup_error", "STAGE_R_CLEANUP_ERROR"),
    ("stage_world_cleanup_error", "STAGE_WORLD_CLEANUP_ERROR"),
    ("temp_cleanup_error", "TEMP_CLEANUP_ERROR"),
    ("existing_error_field", "PREEXISTING_PRODUCER_ERROR"),
    ("w3_scope_exaggerated", "W3_CAPTURE_INCOMPLETE"),
))
def test_s49_finalization_candidate_vetoes_false_pass(attack, reason):
    report = _s49_cleanup_candidate_fixture()
    rc = 0
    if attack == "node_nonzero":
        report["node_exit"] = 1
    elif attack == "node_missing":
        report.pop("node_exit")
    elif attack == "node_bool":
        report["node_exit"] = False
    elif attack == "node_cleanup_exception":
        report["node_cleanup_error"] = "timeout"
    elif attack == "node_cleanup_blank":
        report["node_cleanup_error"] = ""
    elif attack == "java_nonzero":
        report["server_exit"] = -9
    elif attack == "java_missing":
        report.pop("server_exit")
    elif attack == "java_cleanup_exception":
        report["server_cleanup_error"] = "interrupted"
    elif attack == "premature_stage":
        report["stage"] = "UNATTENDED_NATIVE_EVENT_LOOP"
    elif attack == "premature_rc":
        rc = 1
    elif attack == "qualified_label_missing":
        report.pop("classification")
    elif attack == "unrecognized_label":
        report["classification"] = "PENDING_REAL_NATIVE_EVIDENCE"
    elif attack == "dev_label_without_stage_r":
        report["classification"] = "DEV_ONLY_S49_SINGLE_WRITER_HOLD_REV2"
    elif attack == "stage_r_standard_label":
        report["stage_r_dev_enabled"] = True
    elif attack in (
        "node_terminate_error", "stage_r_cleanup_error",
        "stage_world_cleanup_error", "temp_cleanup_error",
    ):
        report[attack] = ""
    elif attack == "existing_error_field":
        report["error"] = ""
    elif attack == "w3_scope_exaggerated":
        report["w3_node_stdout_capture"] = {
            **_w4_s49_report_claim()["w3_node_stdout_capture"],
            "minecraft_tcp_packets_attested": True,
        }
    elif attack in {"w3_capture_missing_ack", "w3_capture_wrong_session"}:
        report["w3_node_stdout_capture"] = {
            "status": "COMPLETE_NODE_STDOUT",
            "session_id": (
                "foreign" if attack == "w3_capture_wrong_session"
                else report["session_id"]
            ),
            "eof_observed": True,
            "shutdown_ack_count": (
                0 if attack == "w3_capture_missing_ack" else 1
            ),
            "process_exit_code": 0,
            "capture_fault": None,
        }
    initial = json.loads(json.dumps(report))
    result = review_s49_cleanup_finalization_candidate(
        report=report, provisional_rc=rc,
    )
    assert report == initial
    assert result["candidate_final_status"] == "FAIL"
    assert result["candidate_rc"] == 1
    assert result["candidate_final_classification"] == "S49_SESSION_NOT_QUALIFIED"
    assert result["candidate_classification_scope"] == "UNTRUSTED_PRODUCER_REPORT_ONLY"
    assert reason in result["veto_reasons"]
    assert not result["physical_run_permitted"]


@pytest.mark.parametrize("status,rc", (("FAIL", 1), ("BLOCKED", 2)))
def test_s49_candidate_never_upgrades_prior_nonpass(status, rc):
    report = _s49_cleanup_candidate_fixture()
    report["status"] = status
    result = review_s49_cleanup_finalization_candidate(
        report=report, provisional_rc=rc,
    )
    assert result["candidate_final_status"] == status
    assert result["candidate_rc"] == rc
    assert result["candidate_final_classification"] == "S49_SESSION_NOT_QUALIFIED"
    assert not result["reported_cleanup_consistent"]


@pytest.mark.parametrize("status,rc", (("PASS", True), ("FAIL", 0), ("BLOCKED", 1)))
def test_s49_candidate_rejects_type_or_status_inconsistency(status, rc):
    report = _s49_cleanup_candidate_fixture()
    report["status"] = status
    with pytest.raises(W4PreworldBlocked):
        review_s49_cleanup_finalization_candidate(
            report=report, provisional_rc=rc,
        )


@pytest.mark.parametrize("failure", ("exit_7", "shutdown_exception"))
def test_original_s49_qualify_fake_node_cleanup_failure(monkeypatch, tmp_path, failure):
    """Original protected S49 false-PASS witness; no real Minecraft process."""
    from types import SimpleNamespace as NS

    import adapters.mineflayer.s49_normal_session_real_ci as s49
    from adapters.mineflayer.execution import WorldConsequenceStatus
    from relay_self.action import ActionState
    from relay_self.world_conditioned_choice import WorldChoiceKind

    sid = "fake-only-s49-native-session"
    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    monkeypatch.setattr(s49, "_fetch_official_server", lambda path: {})
    monkeypatch.setattr(s49, "_write_config", lambda root: None)
    monkeypatch.setattr(s49, "_command", lambda *args: None)
    monkeypatch.setattr(s49, "capture_native_action_evidence", lambda c: {})
    monkeypatch.setattr(s49, "ExecutionBinding", lambda **kwargs: kwargs)
    monkeypatch.setattr(s49, "resolve_execution_binding", lambda *a, **kw: object())
    monkeypatch.setattr(s49, "_native_threat", lambda *a, **kw: NS(distance_m=2))
    monkeypatch.setattr(
        s49, "_native_epoch_two",
        lambda *a, **kw: (
            {"plan": NS(selected=NS(candidate_id="MOVE_AWAY")),
             "admission": NS(status=NS(value="admitted")),
             "control": object(), "route": object(),
             "policies": [object(), object()]},
            NS(cognition_requested=False),
        ),
    )
    monkeypatch.setattr(
        s49.s19, "_epoch_one",
        lambda: (None, NS(new_state=NS(
            target_id="risk_weight", revision=1, value=4,
        )), None, None, None, None),
    )

    class FakeStdin:
        async def drain(self):
            return None

    server = NS(stdin=FakeStdin(), returncode=0)

    async def ready(*args):
        return server, None, None

    async def stop(*args):
        server.returncode = 0

    monkeypatch.setattr(s49, "_ready_server", ready)
    monkeypatch.setattr(s49, "_shutdown_server", stop)

    class FakeNodeSession:
        started = NS(session_id=sid)

        async def shutdown(self, *, timeout_s):
            assert timeout_s == 10
            if failure == "shutdown_exception":
                raise OSError("synthetic-node-shutdown-exception")
            return 7

        async def terminate(self):
            return 7

    async def new_session():
        return FakeNodeSession()

    monkeypatch.setattr(s49, "_new_session", new_session)

    async def read_probe(session, request_id):
        seq = int(request_id.rsplit("-", 1)[1])
        return NS(
            seq=seq + 1, request_id=request_id,
            snapshot=NS(nearby_entities=(NS(
                name="zombie", entity_id=seq,
                distance=10.0 if seq == 1 else 2.0,
            ),)),
        )

    monkeypatch.setattr(s49, "_correlated_observe", read_probe)

    class FakeExecutor:
        def __init__(self, session, intent):
            self.supervisor = NS(
                open_actions=(),
                get=lambda aid: NS(state=ActionState.OUTCOME),
            )

        async def execute(self, session, step, bound, probe, *auth):
            return NS(
                terminal=NS(state=ActionState.OUTCOME, action_id=step.action_request_id),
                consequence=NS(
                    status=WorldConsequenceStatus.EXECUTED,
                    movement_distance=0.2, session_id=sid,
                ),
            )

    monkeypatch.setattr(s49, "NormalSessionActionExecutor", FakeExecutor)

    class FakeL0:
        events = 3
        action_requests = 2

        def __init__(self, *a, **kw):
            pass

        async def run_session(
            self, source, *, probe, grant, on_action_request, max_frames,
        ):
            assert max_frames == 320
            result = []
            for i, event_seq in enumerate((1, 3, 5)):
                entity = NS(name="zombie", entity_id=event_seq, distance=2.0)
                frame = NS(
                    seq=event_seq, kind="entities",
                    snapshot=NS(nearby_entities=(entity,)),
                )
                reading = await probe(frame)
                choice = NS(
                    selection=WorldChoiceKind.WAIT if i == 0
                    else WorldChoiceKind.MOVE_AWAY,
                    probe_seq=reading.seq, entity_id=event_seq,
                    distance_m=10 if i == 0 else 2,
                )
                aid = f"s49-native-move-{event_seq}" if i else None
                step = NS(
                    event_seq=event_seq, choice=choice,
                    asks_for_action=i != 0, action_request_id=aid,
                )
                if i:
                    assert grant(choice, event_seq).action_id == aid
                    await on_action_request(step)
                result.append(step)
            return tuple(result)

    monkeypatch.setattr(s49, "NormalWorldL0", FakeL0)
    out = tmp_path / "original-s49-fake.json"
    original_rc = asyncio.run(s49.qualify(out, tmp_path / "fake-java.log"))
    report = json.loads(out.read_text(encoding="utf-8"))
    assert len(report["decisions"]) == 3
    assert len(report["actual_native_actions"]) == 2
    # Parse the *unchanged S49 original* serializer, not only a hand-built
    # W4 report fixture: the canonical terminal wire value is "outcome".
    assert [a["terminal"] for a in report["actual_native_actions"]] == [
        ActionState.OUTCOME.value, ActionState.OUTCOME.value,
    ]
    from adapters.mineflayer.self_world_stage_w4_optin_offline import (
        audit_original_s49_action_trace_claim_offline,
    )
    trace_verdict = audit_original_s49_action_trace_claim_offline(report=report)
    assert trace_verdict["reported_decisions"] == 3
    assert trace_verdict["reported_actions"] == 2
    from adapters.mineflayer.self_world_stage_w4_optin_offline import (
        audit_original_s49_event_probe_pairs_offline,
    )
    pair_verdict = audit_original_s49_event_probe_pairs_offline(report=report)
    assert pair_verdict["reported_correlated_pairs"] == 3
    assert not pair_verdict["physical_run_permitted"]
    assert not trace_verdict["physical_run_permitted"]
    # Document the EXISTING defect; once original S49 is corrected, invert
    # this expected witness to require original FAIL. Never call it qualified.
    assert original_rc == 0
    assert report["status"] == "PASS"
    if failure == "exit_7":
        assert report["node_exit"] == 7
    else:
        assert "synthetic-node-shutdown-exception" in report["node_cleanup_error"]
    prospective = review_s49_cleanup_finalization_candidate(
        report=report, provisional_rc=original_rc,
    )
    assert prospective["candidate_final_status"] == "FAIL"
    assert prospective["candidate_rc"] == 1
    assert prospective["candidate_final_classification"] == "S49_SESSION_NOT_QUALIFIED"
    assert report["classification"] == "REAL_ONE_SESSION_L0_WAIT_TWO_AUTHORIZED_MOVES_QUALIFIED"
    assert not prospective["reported_cleanup_consistent"]
    assert not prospective["physical_run_permitted"]


def test_s49_finalization_candidate_stage_r_classification_is_dev_only():
    report = _s49_stage_r_report_claim()
    verdict = review_s49_cleanup_finalization_candidate(
        report=report, provisional_rc=0,
    )
    assert verdict["candidate_final_status"] == "PASS"
    assert verdict["candidate_final_classification"] == report["classification"]
    assert verdict["candidate_classification_scope"] == "UNTRUSTED_PRODUCER_REPORT_ONLY"
    assert not verdict["science_qualified"]
    from adapters.mineflayer.self_world_stage_w4_optin_offline import (
        audit_original_s49_stage_r_owner_claim_offline,
    )
    owner_claim = audit_original_s49_stage_r_owner_claim_offline(report=report)
    assert owner_claim["reported_hold_commits"] == 1
    assert not owner_claim["s10_permission"]
    assert not owner_claim["external_custody_qualified"]


def test_s49_nonpass_with_stale_qualified_label_always_demotes():
    report = _s49_cleanup_candidate_fixture()
    report["status"] = "FAIL"
    verdict = review_s49_cleanup_finalization_candidate(
        report=report, provisional_rc=1,
    )
    assert report["classification"].endswith("_QUALIFIED")
    assert verdict["candidate_final_classification"] == "S49_SESSION_NOT_QUALIFIED"
    assert verdict["candidate_rc"] == 1


@pytest.mark.parametrize("status", ([], {}, 123, True))
def test_s49_candidate_rejects_malformed_status_as_blocked(status):
    report = _s49_cleanup_candidate_fixture()
    report["status"] = status
    with pytest.raises(W4PreworldBlocked):
        review_s49_cleanup_finalization_candidate(
            report=report, provisional_rc=0,
        )


@pytest.mark.parametrize("stage_r", ("true", 1, None, [], {}))
def test_s49_candidate_rejects_non_boolean_stage_r_optin(stage_r):
    report = _s49_cleanup_candidate_fixture()
    report["stage_r_dev_enabled"] = stage_r
    with pytest.raises(W4PreworldBlocked):
        review_s49_cleanup_finalization_candidate(
            report=report, provisional_rc=0,
        )


@pytest.mark.parametrize("fault", (
    "node_terminate_error", "stage_r_cleanup_error",
    "stage_world_cleanup_error", "temp_cleanup_error",
))
def test_direct_s49_report_claim_rejects_secondary_cleanup_even_clean_exit(fault):
    report = _w4_s49_report_claim()
    report[fault] = ""
    with pytest.raises(W4PreworldBlocked):
        audit_original_s49_cleanup_claim_offline(report=report)

@pytest.mark.parametrize("fault", (
    "missing_decisions", "missing_actions", "short_decisions",
    "extra_action", "wrong_wait", "wait_issued", "move_unissued",
    "duplicate_entity", "duplicate_event_seq", "decreasing_probe",
    "foreign_action_source", "action_seq_mismatch", "action_probe_mismatch",
    "action_id_mismatch", "action_not_outcome", "missing_movement",
    "tiny_movement", "nan_movement", "bool_movement", "foreign_action_type",
    "uppercase_enum_name",
))
def test_w4_s49_action_trace_negative_claims_fail_closed(fault):
    report = _w4_s49_report_claim()
    decisions = report["decisions"]
    actions = report["actual_native_actions"]
    if fault == "missing_decisions":
        report.pop("decisions")
    elif fault == "missing_actions":
        report.pop("actual_native_actions")
    elif fault == "short_decisions":
        decisions.pop()
    elif fault == "extra_action":
        actions.append(dict(actions[-1]))
    elif fault == "wrong_wait":
        decisions[0]["selected"] = "MOVE_AWAY"
    elif fault == "wait_issued":
        decisions[0]["issued"] = True
    elif fault == "move_unissued":
        decisions[1]["issued"] = False
    elif fault == "duplicate_entity":
        decisions[2]["entity_id"] = decisions[1]["entity_id"]
    elif fault == "duplicate_event_seq":
        decisions[2]["event_seq"] = decisions[1]["event_seq"]
    elif fault == "decreasing_probe":
        decisions[2]["probe_seq"] = 0
    elif fault == "foreign_action_source":
        actions[0]["source"] = "foreign"
    elif fault == "action_seq_mismatch":
        actions[0]["event_seq"] += 1
    elif fault == "action_probe_mismatch":
        actions[0]["probe_seq"] += 1
    elif fault == "action_id_mismatch":
        actions[0]["action"] = "forged"
    elif fault == "action_not_outcome":
        actions[0]["terminal"] = ActionState.UNKNOWN.value
    elif fault == "uppercase_enum_name":
        actions[0]["terminal"] = "OUTCOME"
    elif fault == "missing_movement":
        actions[0].pop("movement_m")
    elif fault == "tiny_movement":
        actions[0]["movement_m"] = 0.049
    elif fault == "nan_movement":
        actions[0]["movement_m"] = float("nan")
    elif fault == "bool_movement":
        actions[0]["movement_m"] = True
    elif fault == "foreign_action_type":
        report["actual_native_actions"] = {}
    with pytest.raises(W4PreworldBlocked):
        audit_original_s49_cleanup_claim_offline(report=report)


@pytest.mark.parametrize("fault", (
    "missing_owner", "missing_revisions", "no_learning", "wrong_rev",
    "wrong_event", "wrong_selection", "wrong_value", "wrong_kind",
    "wrong_classification", "foreign_session", "wrong_initial",
    "wrong_current", "fake_value_gain", "split_l0_s14",
    "no_s10_grant", "duplicated_s10", "missing_closure",
    "pending", "external_attestation", "reward_gain", "second_issuer",
    "missing_commit", "other_action", "terminal_seq_equal",
    "late_source_probe", "foreign_source_request", "missing_feedback",
    "foreign_authority", "foreign_authority_source", "wrong_commit_rev",
    "terminal_not_before_next_event",
))
def test_s49_stage_r_producer_claim_fail_closed_offline(fault):
    report = _s49_stage_r_report_claim()
    owner = report["stage_r_owner"]
    commit = owner["commit_source"]
    revisions = report["stage_r_decision_revisions"]
    if fault == "missing_owner":
        report.pop("stage_r_owner")
    elif fault == "missing_revisions":
        report.pop("stage_r_decision_revisions")
    elif fault == "no_learning":
        report["learning_in_world"] = False
    elif fault == "wrong_rev":
        revisions[2]["retained_revision"] = 1
    elif fault == "wrong_event":
        revisions[1]["event_seq"] += 1
    elif fault == "wrong_selection":
        revisions[2]["selected"] = "WAIT"
    elif fault == "wrong_value":
        revisions[1]["retained_value"] = 5
    elif fault == "wrong_kind":
        owner["kind"] = "second_writer"
    elif fault == "wrong_classification":
        owner["classification"] = "SCIENCE_QUALIFIED"
    elif fault == "foreign_session":
        owner["original_session_id"] = "foreign"
    elif fault == "wrong_initial":
        owner["initial_revision"] = 0
    elif fault == "wrong_current":
        owner["current_revision"] = 1
    elif fault == "fake_value_gain":
        owner["current_value"] = 5
    elif fault == "split_l0_s14":
        owner["joint_l0_s14_owner_identity"] = False
    elif fault == "no_s10_grant":
        owner["operator_s10_grants"] = 0
    elif fault == "duplicated_s10":
        owner["s10_hold_commits"] = 2
    elif fault == "missing_closure":
        owner["original_action_closures"] = 1
    elif fault == "pending":
        owner["pending_unsealed_or_unknown"] = True
    elif fault == "external_attestation":
        owner["grant_independent_external_attestation"] = True
    elif fault == "reward_gain":
        owner["hold_reward_or_policy_gain"] = True
    elif fault == "second_issuer":
        owner["additional_action_issuer"] = True
    elif fault == "missing_commit":
        owner["commit_source"] = None
    elif fault == "other_action":
        commit["terminal_action_id"] = "foreign-action"
    elif fault == "terminal_seq_equal":
        commit["terminal_after_native_seq"] = report["decisions"][1]["probe_seq"]
    elif fault == "terminal_not_before_next_event":
        commit["terminal_after_native_seq"] = report["decisions"][2]["event_seq"]
    elif fault == "late_source_probe":
        commit["next_source_probe_seq"] = report["decisions"][1]["probe_seq"]
    elif fault == "foreign_source_request":
        commit["next_source_request_id"] = "foreign"
    elif fault == "missing_feedback":
        commit["feedback_id"] = ""
    elif fault == "foreign_authority":
        commit["s10_authority_id"] = "forged"
    elif fault == "foreign_authority_source":
        commit["s10_authority_source"] = "selfworld-w4"
    elif fault == "wrong_commit_rev":
        commit["s10_commit_revision"] = 1
    verdict = review_s49_cleanup_finalization_candidate(
        report=report, provisional_rc=0,
    )
    assert verdict["candidate_final_status"] == "FAIL"
    assert verdict["candidate_rc"] == 1
    assert verdict["candidate_final_classification"] == "S49_SESSION_NOT_QUALIFIED"
    assert "STAGE_R_OWNER_CLAIM_INCOMPLETE" in verdict["veto_reasons"]


@pytest.mark.parametrize("fault", (
    "base_with_owner", "base_with_revisions", "base_with_learning",
))
def test_s49_base_producer_cannot_inherit_stage_r_state(fault):
    report = _w4_s49_report_claim()
    if fault == "base_with_owner":
        report["stage_r_owner"] = {}
    elif fault == "base_with_revisions":
        report["stage_r_decision_revisions"] = []
    elif fault == "base_with_learning":
        report["learning_in_world"] = True
    verdict = review_s49_cleanup_finalization_candidate(
        report=report, provisional_rc=0,
    )
    assert verdict["candidate_final_status"] == "FAIL"
    assert "BASE_S49_HAS_STAGE_R_CLAIMS" in verdict["veto_reasons"]


def test_w4_phase_b_reads_consistent_stage_r_only_as_untrusted_source(tmp_path):
    report = _s49_stage_r_report_claim()
    report["w3_node_stdout_capture"] = _local_w3_synthetic_archive(tmp_path)
    result = review_w4_s49_phase_b_optin_offline(
        selected_mode="W4_S49_SYNTHETIC_OFFLINE_REVIEW",
        explicit_opt_in=True, closed_composition=_w4_s49_closed_claim(),
        report=report, archive_root=tmp_path,
    )
    assert not result["original_s49_qualify_wired"]
    assert not result["s10_permission"]
    assert not result["external_custody_qualified"]
    assert not result["physical_run_permitted"]
    assert not result["science_qualified"]


@pytest.mark.parametrize("fault", (
    "missing_pairs", "empty_pairs", "too_many_pairs",
    "wrong_event_kind", "wrong_event_seq", "wrong_probe_seq",
    "before_event", "no_event_entities", "no_probe_entities",
    "foreign_event_target", "foreign_probe_target",
    "event_duplicate_target", "probe_duplicate_target",
    "wrong_entity_name", "probe_distance_changed",
    "nan_probe_distance", "boolean_probe_distance",
    "negative_probe_distance", "invalid_pair_type",
    "invalid_probe_entities_type",
))
def test_original_s49_event_probe_pair_claim_fail_closed(fault):
    report = _w4_s49_report_claim()
    pairs = report["source_pair_trace"]
    step = report["decisions"][1]
    pair = pairs[1]
    if fault == "missing_pairs":
        del report["source_pair_trace"]
    elif fault == "empty_pairs":
        pairs.clear()
    elif fault == "too_many_pairs":
        pairs.append(dict(pair))
    elif fault == "wrong_event_kind":
        pair["event_kind"] = "effect_result"
    elif fault == "wrong_event_seq":
        pair["event_seq"] += 1
    elif fault == "wrong_probe_seq":
        pair["probe_seq"] += 1
    elif fault == "before_event":
        pair["probe_seq"] = pair["event_seq"]
        step["probe_seq"] = pair["probe_seq"]
        report["actual_native_actions"][0]["probe_seq"] = pair["probe_seq"]
    elif fault == "no_event_entities":
        pair["event_entities"] = []
    elif fault == "no_probe_entities":
        pair["probe_entities"] = []
    elif fault == "foreign_event_target":
        pair["event_entities"][0]["id"] += 1
    elif fault == "foreign_probe_target":
        pair["probe_entities"][0]["id"] += 1
    elif fault == "event_duplicate_target":
        pair["event_entities"].append(dict(pair["event_entities"][0]))
    elif fault == "probe_duplicate_target":
        pair["probe_entities"].append(dict(pair["probe_entities"][0]))
    elif fault == "wrong_entity_name":
        pair["probe_entities"][0]["name"] = "skeleton"
    elif fault == "probe_distance_changed":
        pair["probe_entities"][0]["d"] = 2.5
    elif fault == "nan_probe_distance":
        pair["probe_entities"][0]["d"] = float("nan")
    elif fault == "boolean_probe_distance":
        pair["probe_entities"][0]["d"] = True
    elif fault == "negative_probe_distance":
        pair["probe_entities"][0]["d"] = -1.0
    elif fault == "invalid_pair_type":
        pairs[1] = []
    elif fault == "invalid_probe_entities_type":
        pair["probe_entities"] = {}
    with pytest.raises(W4PreworldBlocked):
        audit_original_s49_cleanup_claim_offline(report=report)


def test_w4_action_report_source_pair_stays_untrusted(tmp_path):
    report = _w4_s49_report_claim()
    report["w3_node_stdout_capture"] = _local_w3_synthetic_archive(tmp_path)
    claim = audit_original_s49_cleanup_claim_offline(report=report)
    assert claim["reported_decisions"] == 3
    assert claim["reported_correlated_pairs"] == 3
    result = review_w4_s49_phase_b_optin_offline(
        selected_mode="W4_S49_SYNTHETIC_OFFLINE_REVIEW",
        explicit_opt_in=True, closed_composition=_w4_s49_closed_claim(),
        report=report, archive_root=tmp_path,
    )
    assert not result["external_custody_qualified"]
    assert not result["physical_run_permitted"]
    assert not result["s10_permission"]
    assert not result["science_qualified"]
