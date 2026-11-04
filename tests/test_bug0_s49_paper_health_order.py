"""Paper async say-vs-data source-order regression, no World or ATTACK."""
from __future__ import annotations

import asyncio

import pytest

from adapters.mineflayer import s49_attack_server_health as health


NONCE = "abcdefghijklmnopqrst"


class BufferedPaperSource:
    def __init__(self, log_path, value=20.0):
        self.pending = []
        self.log_path = log_path
        self.value = value
        self.stdin = self

    async def drain(self):
        # Model Paper's observed callback scheduling: a single batch can
        # publish /data synchronously ahead of chat (/say) markers, whereas
        # each separately awaited command is published in issuance order.
        commands = list(self.pending)
        self.pending.clear()
        if len(commands) > 1:
            commands.sort(key=lambda s: 0 if s.startswith("data ") else 1)
        with self.log_path.open("a", encoding="utf-8") as out:
            for command in commands:
                if command.startswith("say "):
                    out.write(
                        "[Not Secure] [Server] " + command[len("say "):] + "\n"
                    )
                elif command.startswith("data get entity"):
                    out.write(
                        f"Zombie has the following entity data: {self.value}f\n"
                    )
                else:
                    raise AssertionError("unexpected command")


def test_sequential_paper_health_readback_brackets_native_source(
    tmp_path, monkeypatch,
):
    path = tmp_path / "paper.log"
    path.touch()
    server = BufferedPaperSource(path)
    monkeypatch.setattr(health, "_command", lambda srv, cmd: srv.pending.append(cmd))
    before = asyncio.run(health.sample_tagged_zombie_health(
        server, path, stage="before", nonce=NONCE,
        paper_source_sequential=True,
    ))
    assert before.health == 20.0
    assert "RSELF_HEALTH_" in before.marker_start
    assert before.native_line.endswith("20.0f")
    server.value = 19.06
    after = asyncio.run(health.sample_tagged_zombie_health(
        server, path, stage="after", nonce=NONCE,
        paper_source_sequential=True,
    ))
    assert after.health == pytest.approx(19.06)
    assert after.log_line_number > before.log_line_number
    assert len(path.read_text().splitlines()) == 6


def test_batched_paper_chat_reorder_still_fails_closed(
    tmp_path, monkeypatch,
):
    path = tmp_path / "paper.log"
    path.touch()
    server = BufferedPaperSource(path)
    monkeypatch.setattr(health, "_command", lambda srv, cmd: srv.pending.append(cmd))
    with pytest.raises(health.ServerHealthReadbackRejected):
        asyncio.run(health.sample_tagged_zombie_health(
            server, path, stage="before", nonce=NONCE,
        ))
    assert server.pending == []


def test_invalid_paper_order_mode_never_emits_native_commands(tmp_path, monkeypatch):
    path = tmp_path / "paper.log"
    path.touch()
    server = BufferedPaperSource(path)
    monkeypatch.setattr(health, "_command", lambda srv, cmd: srv.pending.append(cmd))
    with pytest.raises(health.ServerHealthReadbackRejected):
        asyncio.run(health.sample_tagged_zombie_health(
            server, path, stage="before", nonce=NONCE,
            paper_source_sequential="yes",
        ))
    assert not server.pending
