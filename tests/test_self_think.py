"""Self product's optional S60-A/B1 L2 advisory over completed native S49 source.

Local HTTP mock only. No real llama-server, Java/Minecraft, GPU or Action.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from adapters.mineflayer import self_demo
from adapters.mineflayer.self_think import (
    MODEL_SOURCE,
    bounded_native_commentary,
    native_advisory_prompt,
)
from test_self_demo import _native_report


def completed_native_trace():
    return self_demo.project_native_report(_native_report())


class OneShotLocalModel:
    def __init__(self, *, status: int = 200, wrong_model: bool = False):
        self.server = None
        self.status = status
        self.wrong_model = wrong_model
        self.posts = []
        self.writers = []
        self.requests = 0

    async def __aenter__(self):
        self.server = await asyncio.start_server(self.handle, "127.0.0.1", 0)
        self.port = self.server.sockets[0].getsockname()[1]
        return self

    async def __aexit__(self, *_):
        # Python 3.12 Server.wait_closed() also waits for live clients.
        # Close accepted client sockets FIRST or fixture teardown deadlocks.
        self.server.close()
        for writer in self.writers:
            writer.close()
        await asyncio.gather(
            *(writer.wait_closed() for writer in self.writers),
            return_exceptions=True,
        )
        await self.server.wait_closed()

    async def handle(self, reader, writer):
        self.writers.append(writer)
        header = await reader.readuntil(b"\r\n\r\n")
        content_len = int(next(
            part.split(b":", 1)[1] for part in header.split(b"\r\n")
            if part.lower().startswith(b"content-length:")
        ))
        content = json.loads(await reader.readexactly(content_len))
        self.posts.append(content)
        self.requests += 1
        body = json.dumps({
            "model": "foreign-model" if self.wrong_model else "self-demo-test-model",
            "choices": [
                {"index": 0, "finish_reason": "stop",
                 "message": {"role": "assistant",
                             "content": "Three observations and two bounded movements; "
                                        "this does not prove objective success."}},
            ],
            "usage": {"prompt_tokens": 25, "completion_tokens": 13, "total_tokens": 38},
        }).encode()
        writer.write(
            f"HTTP/1.1 {self.status} Test\r\n".encode()
            + b"Content-Type: application/json\r\n"
            + f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n".encode()
            + body
        )
        await writer.drain()


def test_native_prompt_only_uses_observed_world_projection():
    session, prompt, seq = native_advisory_prompt(completed_native_trace())
    assert session == "real-native-session-test-record"
    assert seq == 22
    assert "zombie distance 10.0 m" in prompt
    assert "MOVE_AWAY" in prompt
    assert "0.627" in prompt
    assert "No goal-success" in prompt
    assert "synthetic" not in prompt.lower()
    assert "commands" in prompt


@pytest.mark.parametrize("which", [
    "fake_source", "wrong_decision", "fake_goal", "no_world", "bad_seq",
    "different_session", "no_action",
])
def test_forged_world_trace_cannot_be_sent_to_l2(which: str):
    rows = [dict(x) for x in completed_native_trace()]
    if which == "fake_source":
        rows[1]["source_type"] = "SYNTHETIC_SMOKE_ONLY"
    elif which == "wrong_decision":
        rows[2]["selected"] = "FLEE"
    elif which == "fake_goal":
        rows[5]["goal_success_attested"] = True
    elif which == "no_world":
        rows = list(self_demo.smoke_trace())
    elif which == "bad_seq":
        rows[6]["probe_seq"] = 5
    elif which == "different_session":
        rows[8]["world_source_session"] = "foreign"
    else:
        rows[-1]["native_terminal_actions"] = 0
    with pytest.raises(ValueError):
        native_advisory_prompt(tuple(rows))


def test_one_real_local_http_advisory_never_authorizes_action_or_habit():
    async def scenario():
        async with OneShotLocalModel() as model:
            got = await bounded_native_commentary(
                completed_native_trace(), model="self-demo-test-model",
                port=model.port, timeout_s=2.0, max_tokens=80,
            )
            assert model.requests == 1
            assert len(model.posts) == 1
            body = model.posts[0]
            assert body["stream"] is False
            assert body["max_tokens"] == 80
            assert body["temperature"] == 0
            assert body["model"] == "self-demo-test-model"
            assert body["messages"][0]["role"] == "system"
            assert got["status"] == "ADVISORY_ONLY"
            assert got["kind"] == "l2_commentary"
            assert got["source_type"] == MODEL_SOURCE
            assert "Three observations" in got["text_untrusted_advisory"]
            assert got["authorized_actions"] == 0
            assert got["used_as_action"] is False
            assert got["learning_feedback_created"] is False
            assert got["habit_updated"] is False
            assert got["backend_stop_ack"] is False
            assert got["gpu_release_claimed"] is False
            assert not got["provider_identity_cryptographically_verified"]
            assert "BACKEND_COMPLETION_OBSERVED" in got["transport_events"]

    asyncio.run(scenario())


@pytest.mark.parametrize("status,wrong_model", [(503, False), (200, True)])
def test_model_failure_keeps_native_world_authority_untouched(status, wrong_model):
    async def scenario():
        async with OneShotLocalModel(status=status, wrong_model=wrong_model) as model:
            got = await bounded_native_commentary(
                completed_native_trace(), model="self-demo-test-model",
                port=model.port, timeout_s=1.0,
            )
            assert model.requests == 1
            assert got["status"] == "UNCONFIRMED"
            assert got["text_untrusted_advisory"] is None
            assert got["authorized_actions"] == 0
            assert got["learning_feedback_created"] is False
            assert got["backend_stop_ack"] is False

    asyncio.run(scenario())


def test_think_cannot_run_without_native_world(capsys):
    assert self_demo.main(["--smoke", "--think"]) == 2
    assert json.loads(capsys.readouterr().out)["reason"] == "L2_REQUIRES_REAL_NATIVE_SOURCE"
    assert self_demo.main(["--think"]) == 2


def test_invalid_model_config_blocks_before_world_resources(
    capsys, monkeypatch, tmp_path: Path,
):
    monkeypatch.setattr(self_demo.shutil, "which", lambda _: "/unused/tool")
    args = [
        "--run-disposable", "--confirm", self_demo.CONFIRM,
        "--output-dir", str(tmp_path), "--think",
        "--model-alias", "test-model",
        "--model-port", "0",
    ]
    assert self_demo.main(args) == 2
    assert json.loads(capsys.readouterr().out)["reason"] == (
        "INVALID_EXPLICIT_L2_LOOPBACK_CONFIG"
    )


def test_product_cli_projects_one_advisory_after_native_and_saves_memory(
    capsys, tmp_path: Path, monkeypatch,
):
    async def scenario():
        async with OneShotLocalModel() as model:
            async def synthetic_native_world(report_path, server_log):
                # The real S49 owner is replaced only inside THIS test.
                report_path.write_text(json.dumps(_native_report()), encoding="utf-8")
                server_log.write_text("synthetic; no server started", encoding="utf-8")
                return 0

            monkeypatch.setattr(self_demo, "_run_disposable", synthetic_native_world)
            monkeypatch.setattr(self_demo.shutil, "which", lambda _: "/mock/java-or-node")
            args = [
                "--run-disposable", "--confirm", self_demo.CONFIRM,
                "--output-dir", str(tmp_path), "--think",
                "--model-alias", "self-demo-test-model",
                "--model-port", str(model.port), "--model-timeout", "2",
            ]
            result = await asyncio.to_thread(self_demo.main, args)
            assert result == 0
            assert model.requests == 1
            trace = [
                json.loads(row) for row in
                (tmp_path / "self_trace.jsonl").read_text().splitlines()
            ]
            assert [row["kind"] for row in trace].count("l2_commentary") == 1
            assert trace[-2]["kind"] == "l2_commentary"
            assert trace[-2]["used_as_action"] is False
            assert trace[-1]["kind"] == "observed_memory"
            assert trace[-1]["retained_episodes"] == 2
            from relay_self.persistent_cognition import load_persistent_cognition

            snapshot = load_persistent_cognition(tmp_path / "observed_memory.json")
            assert len(snapshot.memories) == 2
            assert all(
                json.loads(m.content)["goal_success_attested"] is False
                for m in snapshot.memories
            )

    asyncio.run(scenario())
    assert len(capsys.readouterr().out.splitlines()) >= 12


def test_existing_real_report_readonly_reflection_with_no_minecraft(
    capsys, tmp_path: Path, monkeypatch,
) -> None:
    async def scenario():
        async with OneShotLocalModel() as model:
            previous = tmp_path / "native_report.json"
            previous.write_text(json.dumps(_native_report()), encoding="utf-8")
            original = previous.read_bytes()
            destination = tmp_path / "reflections"
            destination.mkdir()

            async def forbidden_native(*_args, **_kwargs):
                raise AssertionError("real Minecraft must never be launched")

            monkeypatch.setattr(self_demo, "_run_disposable", forbidden_native)
            monkeypatch.setattr(
                self_demo.shutil, "which",
                lambda _: (_ for _ in ()).throw(AssertionError("no java/node check")),
            )
            args = [
                "--reflect-report", str(previous),
                "--think", "--output-dir", str(destination),
                "--model-alias", "self-demo-test-model",
                "--model-port", str(model.port), "--model-timeout", "2",
            ]
            rc = await asyncio.to_thread(self_demo.main, args)
            assert rc == 0
            assert model.requests == 1
            assert previous.read_bytes() == original
            rows = [
                json.loads(line) for line in
                (destination / "l2_reflection.jsonl").read_text().splitlines()
            ]
            assert [x["kind"] for x in rows] == ["source", "l2_commentary", "summary"]
            assert rows[0]["origin"] == "OPERATOR_PROVIDED_REPORT_NOT_INDEPENDENTLY_ATTESTED"
            assert rows[1]["status"] == "ADVISORY_ONLY"
            assert rows[1]["used_as_action"] is False
            assert rows[-1]["replayed_actions"] == 0
            assert rows[-1]["minecraft_launched"] is False
            assert rows[-1]["learning_updates"] == 0
            assert sorted(x.name for x in destination.iterdir()) == ["l2_reflection.jsonl"]

    asyncio.run(asyncio.wait_for(scenario(), timeout=6))
    assert len(capsys.readouterr().out.splitlines()) == 3


def test_reflection_requires_both_model_consent_and_existing_report(
    capsys, tmp_path: Path,
):
    file = tmp_path / "native_report.json"
    file.write_text(json.dumps(_native_report()), encoding="utf-8")
    assert self_demo.main([
        "--reflect-report", str(file), "--output-dir", str(tmp_path),
    ]) == 2
    assert json.loads(capsys.readouterr().out)["reason"] == (
        "REFLECTION_REQUIRES_EXPLICIT_THINK"
    )
    assert self_demo.main([
        "--reflect-report", str(file), "--think", "--output-dir", str(tmp_path),
        "--model-alias", "bad model", "--model-port", "12345",
    ]) == 2
    assert json.loads(capsys.readouterr().out)["reason"] == (
        "INVALID_EXPLICIT_L2_LOOPBACK_CONFIG"
    )


def test_reflection_fails_closed_for_invalid_source_and_existing_output(
    capsys, tmp_path: Path,
):
    valid = tmp_path / "native_report.json"
    valid.write_text(json.dumps(_native_report()), encoding="utf-8")
    broken = tmp_path / "broken.json"
    broken.write_text(json.dumps({**_native_report(), "status": "FAIL"}), encoding="utf-8")
    output = tmp_path / "reflections"
    output.mkdir()
    opts = [
        "--think", "--output-dir", str(output),
        "--model-alias", "test-model", "--model-port", "12345",
    ]
    assert self_demo.main(["--reflect-report", str(broken), *opts]) == 2
    assert json.loads(capsys.readouterr().out)["reason"] == "INVALID_NATIVE_SOURCE_REPORT"
    (output / "l2_reflection.jsonl").write_text("keep original evidence", encoding="utf-8")
    assert self_demo.main(["--reflect-report", str(valid), *opts]) == 2
    assert json.loads(capsys.readouterr().out)["reason"] == "REFLECTION_OUTPUT_EXISTS"
    assert (output / "l2_reflection.jsonl").read_text() == "keep original evidence"


def test_reflection_no_model_returns_unknown_without_changing_world(
    capsys, tmp_path: Path,
):
    import socket

    native = tmp_path / "native_report.json"
    native.write_text(json.dumps(_native_report()), encoding="utf-8")
    output = tmp_path / "reflections"
    output.mkdir()
    # Explicit unused loopback port; only a rejected HTTP request is permitted.
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    if port <= 1024:
        pytest.skip("eligible unused TCP port unavailable")
    assert self_demo.main([
        "--reflect-report", str(native), "--think",
        "--output-dir", str(output),
        "--model-alias", "not-running", "--model-port", str(port),
        "--model-timeout", "0.5",
    ]) == 0
    rows = [
        json.loads(line) for line in
        (output / "l2_reflection.jsonl").read_text().splitlines()
    ]
    assert rows[1]["status"] == "UNCONFIRMED"
    assert rows[1]["authorized_actions"] == 0
    assert rows[-1]["replayed_actions"] == 0
