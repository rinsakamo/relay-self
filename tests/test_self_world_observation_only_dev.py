"""Observation-only W4 DEV interface: no Java/Node/World launched."""
from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import replace

import pytest

from adapters.mineflayer.python_protocol import (
    MineflayerStreamDecoder,
    encode_observe,
    encode_shutdown,
)
from adapters.mineflayer.self_world_observation_only_dev import (
    ObservationOnlyDevBlocked,
    ObservationOnlyDevSession,
    review_observation_only_dev_offline,
)
from test_mineflayer_process_session import FakeProcess
from test_self_world_stage_w4_prehost import _offline_lines


def _valid_review():
    _pre, _post, raws = _offline_lines()
    decoder = MineflayerStreamDecoder()
    decoded = [decoder.decode(raw.decode("utf-8")) for raw in raws]
    marker = b"[21:00:00] [Server thread/INFO]: The time is 1234\n"
    return dict(
        started=decoded[0], spawn=decoded[1],
        before=decoded[3], after=decoded[5],
        before_request=decoded[3].request_id,
        after_request=decoded[5].request_id,
        raw_marker_line=marker, marker_sha256=hashlib.sha256(marker).hexdigest(),
        marker_after_before=True, after_marker=True,
    )


def test_read_only_review_accepts_source_lineage_but_never_promotes_dev():
    result = review_observation_only_dev_offline(**_valid_review())
    assert result.spawn_seq == 1
    assert result.before_seq == 3 and result.after_seq == 5
    assert result.marker_local_game_time == 1234
    assert result.scope == "SYNTHETIC_OR_LOCAL_CONSOLE_NOT_EXTERNAL_CUSTODY"
    assert result.action_count == result.outcome_count == result.s10_update_count == 0
    assert not result.physical_run_permitted
    assert not result.qualification_approved and not result.science_qualified


@pytest.mark.parametrize("attack", (
    "foreign_session", "replay_seq", "wrong_spawn_kind",
    "wrong_before_request", "same_requests", "wrong_after_kind",
    "same_source", "wrong_marker_hash", "forged_marker", "partial_marker",
    "before_marker_unverified", "after_marker_unverified",
))
def test_read_only_review_rejects_unbound_source_or_marker(attack):
    params = _valid_review()
    if attack == "foreign_session":
        params["after"] = replace(params["after"], session_id="foreign")
    elif attack == "replay_seq":
        params["after"] = replace(params["after"], seq=params["before"].seq)
    elif attack == "wrong_spawn_kind":
        params["spawn"] = replace(params["spawn"], kind="probe")
    elif attack == "wrong_before_request":
        params["before_request"] = "another-request"
    elif attack == "same_requests":
        params["after_request"] = params["before_request"]
    elif attack == "wrong_after_kind":
        params["after"] = replace(params["after"], kind="entities", request_id=None)
    elif attack == "same_source":
        # Provenance is a derived read-only property (session_id, seq).
        # A collision can only be constructed through its source fields.
        params["after"] = replace(params["after"], seq=params["before"].seq)
        assert params["after"].provenance == params["before"].provenance
    elif attack == "wrong_marker_hash":
        params["marker_sha256"] = "0" * 64
    elif attack == "forged_marker":
        params["raw_marker_line"] = b"[21:00:00] [Server thread/INFO]: fake 1234\n"
        params["marker_sha256"] = hashlib.sha256(params["raw_marker_line"]).hexdigest()
    elif attack == "partial_marker":
        params["raw_marker_line"] = params["raw_marker_line"].rstrip(b"\n")
        params["marker_sha256"] = hashlib.sha256(params["raw_marker_line"]).hexdigest()
    elif attack == "before_marker_unverified":
        params["marker_after_before"] = False
    elif attack == "after_marker_unverified":
        params["after_marker"] = False
    with pytest.raises(ObservationOnlyDevBlocked):
        review_observation_only_dev_offline(**params)


def test_observation_only_process_session_blocks_inherited_action_commands():
    async def run():
        process = FakeProcess([])
        session = ObservationOnlyDevSession(process)
        for attempt in (
            lambda: session.send_set_control("action-1", control="back", state=True),
            lambda: session.send_clear_controls("action-1"),
            lambda: session.send_look("action-1", yaw=0, pitch=0),
            lambda: session.send_attack_entity("action-1", entity_id=1),
            lambda: session.send_consume_held("action-1"),
            lambda: session.send_equip_item("action-1", item_name="bread"),
            lambda: session._send('{"type":"effect","effect":"clear_controls"}\n'),
            lambda: session._send('{"type":"observe"}\n'),
            lambda: session._send('{"type":"observe","request_id":"r1","extra":true}\n'),
        ):
            with pytest.raises(ObservationOnlyDevBlocked):
                await attempt()
        assert process.stdin.writes == []
        await session.send_observe("probe-one")
        assert process.stdin.writes == [encode_observe("probe-one").encode()]
        rc = await session.shutdown()
        assert rc == 0 and process.stdin.writes[-1] == encode_shutdown().encode()
        assert len(process.stdin.writes) == 2
    asyncio.run(run())


def test_observation_only_dev_does_not_spawn_any_process_in_offline_review(monkeypatch):
    async def forbidden(*args, **kwargs):
        raise AssertionError("observation-only review must never start Java/Node")
    monkeypatch.setattr(asyncio, "create_subprocess_exec", forbidden)
    result = review_observation_only_dev_offline(**_valid_review())
    assert not result.physical_run_permitted


def test_observation_only_synthetic_owner_loop_has_two_probes_no_action(monkeypatch):
    from adapters.mineflayer.self_world_observation_only_dev import (
        run_observation_only_synthetic_dev,
    )

    _pre, _post, raws = _offline_lines()
    async def forbidden_spawn(*args, **kwargs):
        raise AssertionError("synthetic observation loop cannot spawn Java or Node")
    monkeypatch.setattr(asyncio, "create_subprocess_exec", forbidden_spawn)
    result = asyncio.run(run_observation_only_synthetic_dev(
        raw_frames=tuple(raws), before_request=_pre.request_id,
        after_request=_post.request_id,
        marker_line=b"[21:00:00] [Server thread/INFO]: The time is 1234\n",
    ))
    assert result["schema"] == "W4_OBSERVATION_ONLY_SYNTHETIC_DEV_V1"
    assert result["source_frames"] == 6
    assert result["commands"] == ["observe", "observe", "shutdown"]
    assert result["local_shutdown_completed"] and result["node_exit_code"] == 0
    assert result["readback"]["action_count"] == 0
    assert result["readback"]["outcome_count"] == 0
    assert result["readback"]["s10_update_count"] == 0
    assert result["world_marker_synthetic"]
    assert not result["action_issued"] and not result["physical_run_permitted"]


@pytest.mark.parametrize("attack", (
    "missing_frame", "extra_frame", "partial_frame",
    "foreign_session", "duplicate_seq", "different_request",
    "bad_marker", "same_requests",
))
def test_observation_only_synthetic_owner_loop_rejects_corruption(monkeypatch, attack):
    from adapters.mineflayer.process_session import MineflayerProcessEnded
    from adapters.mineflayer.python_protocol import MineflayerAdapterProtocolError
    from adapters.mineflayer.s31a_real_server_ci import S31AQualificationError
    from adapters.mineflayer.self_world_observation_only_dev import (
        run_observation_only_synthetic_dev,
    )

    pre, post, raws = _offline_lines()
    frames = list(raws)
    params = dict(
        before_request=pre.request_id, after_request=post.request_id,
        marker_line=b"[21:00:00] [Server thread/INFO]: The time is 1234\n",
    )
    if attack == "missing_frame":
        frames.pop()
    elif attack == "extra_frame":
        frames.append(frames[-1])
    elif attack == "partial_frame":
        frames[3] = frames[3].rstrip(b"\n")
    elif attack in {"foreign_session", "duplicate_seq", "different_request"}:
        index = 5 if attack == "different_request" else 3
        obj = json.loads(frames[index])
        if attack == "foreign_session":
            obj["session_id"] = "different-session"
        elif attack == "duplicate_seq":
            obj["seq"] = 2
        else:
            obj["request_id"] = "different-probe"
        frames[index] = (json.dumps(obj) + "\n").encode()
    elif attack == "bad_marker":
        params["marker_line"] = b"fake marker\n"
    else:
        params["after_request"] = params["before_request"]
    async def forbidden_spawn(*args, **kwargs):
        raise AssertionError("offline negative must not launch a child")
    monkeypatch.setattr(asyncio, "create_subprocess_exec", forbidden_spawn)
    with pytest.raises((
        ObservationOnlyDevBlocked, MineflayerProcessEnded,
        MineflayerAdapterProtocolError, S31AQualificationError,
    )):
        asyncio.run(run_observation_only_synthetic_dev(
            raw_frames=tuple(frames), **params,
        ))


def test_observation_only_provenance_is_derived_not_mutable_field():
    """Keep the source-lineage negative tied to the real protocol dataclass."""
    params = _valid_review()
    before, after = params["before"], params["after"]
    assert before.provenance.reference == f"{before.session_id}:{before.seq}"
    assert after.provenance.reference == f"{after.session_id}:{after.seq}"
    assert before.provenance != after.provenance
    # replace() cannot directly override provenance: it is not a dataclass field.
    with pytest.raises(TypeError, match="unexpected keyword argument 'provenance'"):
        replace(after, provenance=before.provenance)


@pytest.mark.parametrize("fault", (
    "ok", "missing_ack", "duplicate_ack", "wrong_session", "seq_gap",
))
def test_observation_only_stop_requires_raw_ack_eof_reap(tmp_path, fault):
    """The original W3 capture/decoder owns all shutdown frames and EOF."""
    from test_mineflayer_process_session import started_line

    def frame(kind, seq, sid="session-1"):
        payload = {"type": kind, "session_id": sid, "seq": seq}
        if kind == "connection_end":
            payload["reason"] = "test bridge clean end"
        return (json.dumps(payload) + "\n").encode()

    lines = [started_line()]
    if fault == "ok":
        lines += [frame("shutdown_ack", 1), frame("connection_end", 2)]
    elif fault == "duplicate_ack":
        lines += [frame("shutdown_ack", 1), frame("shutdown_ack", 2)]
    elif fault == "wrong_session":
        lines += [frame("shutdown_ack", 1, "foreign")]
    elif fault == "seq_gap":
        lines += [frame("shutdown_ack", 4)]
    process = FakeProcess(lines)

    async def run():
        session = ObservationOnlyDevSession(
            process, raw_capture_root=tmp_path,
        )
        await session.receive()  # Original adapter_started, seq 0.
        if fault == "ok":
            receipt = await session.shutdown_with_stdout_receipt()
            assert receipt["status"] == "COMPLETE_NODE_STDOUT"
            assert receipt["shutdown_ack_count"] == 1
            assert receipt["eof_observed"] is True
            assert receipt["process_exit_code"] == 0
            assert receipt["seal_reason"] == "clean_shutdown"
            assert receipt["frame_count"] == 3
        else:
            with pytest.raises((
                ObservationOnlyDevBlocked, ValueError,
            )):
                await session.shutdown_with_stdout_receipt()
            assert session.raw_capture_receipt["status"] != "COMPLETE_NODE_STDOUT"
        assert process.stdin.writes == [b'{"type":"shutdown"}\n']
        assert process.wait_count >= 1
        assert (tmp_path / "w3-node-stdout.raw.jsonl").exists()
    asyncio.run(run())


def test_observation_only_stop_without_byte_capture_fails_before_send():
    from test_mineflayer_process_session import started_line

    process = FakeProcess([started_line()])
    async def run():
        session = ObservationOnlyDevSession(process)
        await session.receive()
        with pytest.raises(ObservationOnlyDevBlocked, match="raw stdout capture"):
            await session.shutdown_with_stdout_receipt()
        assert process.stdin.writes == []
        assert process.wait_count == 0
    asyncio.run(run())


@pytest.mark.parametrize("fault", (
    "ok", "missing", "partial", "forged", "duplicate", "replaced_inode",
))
def test_observation_only_raw_java_marker_uses_existing_collector_file(tmp_path, fault):
    from adapters.mineflayer.self_world_observation_only_dev import (
        wait_for_observation_raw_world_marker,
    )
    from adapters.mineflayer.self_world_stage_w4_logtap import (
        capture_w4_collector_cursor,
    )
    from adapters.mineflayer.self_world_stage_w4_preflight import W4PreworldBlocked

    raw_path = tmp_path / "original-sole-collector.raw"
    preface = b"[21:00:00] [Server thread/INFO]: Done (1s)! For help\n"
    raw_path.write_bytes(preface)
    cursor = capture_w4_collector_cursor(raw_path)
    marker = b"[21:00:01] [Server thread/INFO]: The time is 1234\n"
    payloads = {
        "ok": marker,
        "missing": b"[21:00:01] [Server thread/INFO]: unrelated\n",
        "partial": marker.rstrip(b"\n"),
        "forged": b"[21:00:01] [Fake thread/INFO]: The time is 1234\n",
        "duplicate": marker + marker,
        "replaced_inode": marker,
    }
    if fault == "replaced_inode":
        raw_path.unlink()
        raw_path.write_bytes(preface + payloads[fault])
    else:
        with raw_path.open("ab") as sink:
            sink.write(payloads[fault])

    async def run():
        if fault == "ok":
            result = await wait_for_observation_raw_world_marker(cursor, timeout_s=0.03)
            assert result.local_game_time == 1234
            assert result.raw_start_byte == len(preface)
            assert result.raw_end_byte == len(preface) + len(marker)
            assert result.raw_sha256 == hashlib.sha256(marker).hexdigest()
            assert result.local_collector_only and not result.external_world_attested
        else:
            with pytest.raises((ObservationOnlyDevBlocked, W4PreworldBlocked)):
                await wait_for_observation_raw_world_marker(cursor, timeout_s=0.03)
    asyncio.run(run())


def test_observation_only_native_receive_overlap_denied_without_second_reader():
    from test_mineflayer_process_session import started_line

    process = FakeProcess([])
    entered = asyncio.Event()
    release = asyncio.Event()
    line = started_line()

    class HeldStdout:
        reads = 0

        async def readline(self):
            self.reads += 1
            entered.set()
            await release.wait()
            return line

    stdout = HeldStdout()
    process.stdout = stdout

    async def run():
        session = ObservationOnlyDevSession(process)
        first = asyncio.create_task(session.receive())
        await entered.wait()
        with pytest.raises(ObservationOnlyDevBlocked, match="concurrent"):
            await session.receive()
        assert stdout.reads == 1
        release.set()
        started = await first
        assert started.seq == 0 and started.session_id == "session-1"
    asyncio.run(run())
