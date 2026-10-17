"""Offline negative controls for the engineering-only process owner."""
import argparse
import asyncio
import json
import re
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest

from adapters.mineflayer import v6_world_qualification as q
from adapters.mineflayer.v6_original_capture import V6OriginalCapture


def test_incomplete_ci_and_wrong_remote_head_reject(monkeypatch):
    for value in (
        {"headRefOid": "other", "statusCheckRollup": []},
        {"headRefOid": "head", "statusCheckRollup": []},
        {"headRefOid": "head", "statusCheckRollup": [{"status": "IN_PROGRESS", "conclusion": ""}]},
        {"headRefOid": "head", "statusCheckRollup": [{"status": "COMPLETED", "conclusion": "FAILURE"}]},
    ):
        monkeypatch.setattr(q.subprocess, "run", lambda *a, **kw: SimpleNamespace(stdout=json.dumps(value)))
        with pytest.raises(q.QualificationBlocked):
            q.remote_ci(545, "head")


def test_server_stream_exact_startup_bytes_before_native_session(tmp_path):
    async def scenario():
        capture = V6OriginalCapture(tmp_path / "originals", slot="WORLD_START_A", nonce="a"*32)
        owner = q.OwnedStreams(capture, tmp_path)
        reader = asyncio.StreamReader()
        raw = b'[12:00:01] [Server thread/INFO]: startup  two spaces\n'
        reader.feed_data(raw)
        reader.feed_eof()
        owner.server = SimpleNamespace(stdout=reader)
        await owner.server_reader()
        assert capture.session is None
        capture.close()
        owner.console.close()
        owner.node_stdin.close()
        assert (tmp_path / "originals/server_stdout_original.log").read_bytes() == raw
    asyncio.run(scenario())



@pytest.mark.parametrize("phase,reply", [
    (0, "[22:20:30] [Server thread/INFO]: Running function relayself_v6:install\n"),
    (1, "[22:20:30] [Server thread/INFO]: Running function relayself_v6_start:install\n"),
])
def test_observed_1218_function_dispatch_readback_is_not_effect_success(tmp_path, phase, reply):
    # Offline frozen response shape seen at the consumed World attempt.
    # The original runner incorrectly waited for "Executed N command".
    async def scenario():
        cap = V6OriginalCapture(
            tmp_path / "originals", session="offline-only", slot="WORLD_START_A",
            nonce="e" * 32,
        )
        owner = q.OwnedStreams(cap, tmp_path)
        owner.server = SimpleNamespace(returncode=None)
        owner.server_lines.append(reply)
        found = await owner.wait_log(q.INSTALL_DISPATCH_REPLIES[phase])
        assert found == reply
        assert re.search(q.INSTALL_DISPATCH_REPLIES[phase], found)
        assert "Executed 1 command" not in found
        assert cap._phase == 0  # no issuer attempt or scoreboard effect inferred
        cap.close()
        owner.console.close()
        owner.node_stdin.close()
    asyncio.run(scenario())


@pytest.mark.parametrize("invalid", [
    "[INFO]: Executed 1 command\n",  # old invented response
    "[INFO]: Running function relayself_v6:install_impostor\n",
    "[INFO]: Running function relayself_v6_start:install\n",  # wrong pack
])
def test_wrong_install_dispatch_reply_does_not_match(invalid):
    assert re.search(q.INSTALL_DISPATCH_REPLIES[0], invalid) is None


@pytest.mark.parametrize("error", [
    "[INFO]: Unknown function relayself_v6:install\n",
    "[ERROR]: Failed to load datapack\n",
    "[INFO]: Unknown command\n",
])
def test_server_command_parser_error_fails_closed_without_world(tmp_path, error):
    async def scenario():
        cap = V6OriginalCapture(
            tmp_path / "originals", session="offline-only", slot="WORLD_START_A",
            nonce="f" * 32,
        )
        owner = q.OwnedStreams(cap, tmp_path)
        owner.server = SimpleNamespace(returncode=None)
        owner.server_lines.append(error)
        with pytest.raises(q.QualificationBlocked, match="original server error"):
            await owner.wait_log(q.INSTALL_DISPATCH_REPLIES[0], timeout=0.1)
        cap.close()
        owner.console.close()
        owner.node_stdin.close()
    asyncio.run(scenario())


def test_action_and_nonqualification_console_denied_before_write(tmp_path):
    async def scenario():
        capture = V6OriginalCapture(tmp_path / "originals", slot="WORLD_START_A", nonce="b"*32)
        owner = q.OwnedStreams(capture, tmp_path)
        owner.server = SimpleNamespace(stdin=BytesIO())
        owner.node = SimpleNamespace(stdin=BytesIO())
        with pytest.raises(q.QualificationBlocked):
            await owner.issue("reset", "scoreboard players set #attempt rs_v6_tick 0", "x")
        with pytest.raises(q.QualificationBlocked):
            await owner.node_send('{"type":"set_control","control":"forward","state":true}\n')
        assert owner.server.stdin.getvalue() == owner.node.stdin.getvalue() == b''
        capture.close()
        owner.console.close()
        owner.node_stdin.close()
    asyncio.run(scenario())


def test_consumed_grant_cannot_launch_any_child(tmp_path, monkeypatch):
    async def scenario():
        grant = tmp_path / "consumed"
        grant.write_text("old terminal\n")
        args = argparse.Namespace(output=tmp_path, grant=grant, slot="WORLD_START_A", nonce="c"*32, s_head="x")
        calls = []
        async def forbidden(*a, **kw):
            calls.append(a)
            raise AssertionError("child launch")
        monkeypatch.setattr(q.asyncio, "create_subprocess_exec", forbidden)
        report = {}
        with pytest.raises(FileExistsError):
            await q.execute(args, tmp_path, report)
        assert calls == []
        assert grant.read_text() == "old terminal\n"
        assert report["capture"]["classification"] == "S_V6_ORIGINAL_STREAMS_PARTIAL_NOT_QUALIFIED"
    asyncio.run(scenario())


def test_failed_first_java_call_consumes_and_never_falls_back(tmp_path, monkeypatch):
    async def scenario():
        args = argparse.Namespace(output=tmp_path, grant=tmp_path / "grant", slot="WORLD_START_A",
                                  nonce="d"*32, s_head="x", jar=tmp_path / "jar")
        calls = []
        async def failed(*a, **kw):
            calls.append(a)
            raise OSError("first and only spawn failure")
        monkeypatch.setattr(q.asyncio, "create_subprocess_exec", failed)
        report = {}
        with pytest.raises(OSError):
            await q.execute(args, tmp_path, report)
        assert len(calls) == 1 and calls[0][0] == "java"
        assert args.grant.exists()
        assert report["grant_consumed_conservatively"]
        assert report["java_launch_calls"] == 1
        assert not report["native_stop_ack"]
    asyncio.run(scenario())


def test_frozen_pack_producer_blobs_remain_exact():
    root = Path(__file__).resolve().parents[1]
    for head, file in ((q.START_HEAD, "v6_start_marker.py"), (q.FOOD_HEAD, "v6_atomic_fixture.py")):
        raw = q.subprocess.run(["git", "-C", str(root), "show", head + ":adapters/mineflayer/" + file],
                               capture_output=True, check=True).stdout
        assert raw == (root / "adapters/mineflayer" / file).read_bytes()
