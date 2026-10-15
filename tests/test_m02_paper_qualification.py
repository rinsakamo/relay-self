"""Offline boundaries of S-owned M0.2 Paper one-shot qualification source."""
from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path

import pytest

from adapters.mineflayer.m02_paper_dev import s51_paper_qualification as q
from adapters.mineflayer.m02_paper_dev import s51_paper_physics_dev as dev
from relay_self.action import ActionState
from relay_self.action_supervision import ActionSupervisor


def _assets(tmp_path, monkeypatch):
    root = tmp_path / "assets"
    root.mkdir()
    d = {
        "paper-1.21.8.jar": b"paper fake binary offline",
        "relay-metabolism-paper-dev.jar": b"plugin fake binary offline",
        "config.yml": b"dev-enabled: true\ntarget-player: RelaySelf\n",
        "server.properties": (
            b"server-ip=127.0.0.1\nonline-mode=false\ngamemode=survival\n"),
    }
    for name, value in d.items():
        (root / name).write_bytes(value)
    monkeypatch.setattr(dev, "PAPER_PREWORLD_ASSET_PINS", {
        k: hashlib.sha256(v).hexdigest() for k, v in d.items()})
    monkeypatch.setattr(q, "ASSET_NAMES", frozenset(d))
    return root


def test_user_grant_has_nondev_authorized_source():
    supervisor = ActionSupervisor()
    issued = q._issue(supervisor, "m02-action-once", "eat",
                      "m02-intent", "controlled qualification", time_base=30)
    assert issued.state is ActionState.ISSUED
    assert q.GRANT != dev.M02_CONFIRM
    assert "QUALIFICATION" in q.GRANT


def test_four_assets_fail_closed_and_do_not_launch_world(tmp_path, monkeypatch):
    root = _assets(tmp_path, monkeypatch)
    assert q.check_assets(root) == dev.PAPER_PREWORLD_ASSET_PINS
    for p in root.iterdir():
        before = p.read_bytes()
        if p.name == "paper-1.21.8.jar":
            p.write_bytes(before + b"mutated")
            with pytest.raises(q.QualificationBlocked):
                q.check_assets(root)
            p.write_bytes(before)


def test_symlink_or_unsafe_output_cannot_start(tmp_path, monkeypatch):
    root = _assets(tmp_path, monkeypatch)
    actual = root / "server.properties"
    original = actual.read_bytes()
    actual.unlink()
    actual.symlink_to(root / "config.yml")
    with pytest.raises(q.QualificationBlocked):
        q.check_assets(root)
    actual.unlink()
    actual.write_bytes(original)

    async def forbidden(*_args, **_kw):
        pytest.fail("physical Java started in offline test")
    monkeypatch.setattr(q, "_ready_server", forbidden)
    with pytest.raises(q.QualificationBlocked, match="confirmation"):
        asyncio.run(q.run(
            asset_root=root, output_root=tmp_path / "never",
            confirm="UNAUTHORIZED"))
    assert not (tmp_path / "never").exists()
    with pytest.raises(q.QualificationBlocked, match="existing World"):
        (tmp_path / "taken").mkdir()
        asyncio.run(q.run(
            asset_root=root, output_root=tmp_path / "taken",
            confirm=q.CONFIRM))


def test_native_stop_must_match_single_session_and_seq(tmp_path):
    path = tmp_path / "source.jsonl"
    import json
    lines = [
        {"type": "observation", "session_id": "a", "seq": i}
        for i in range(10)
    ]
    lines[8]["type"] = "shutdown_ack"
    lines[9]["type"] = "connection_end"
    path.write_text("".join(json.dumps(x)+"\n" for x in lines))
    assert q._terminal_native(path, "a")["native_stop_ack_seq"] == 8
    lines[7]["session_id"] = "other"
    path.write_text("".join(json.dumps(x)+"\n" for x in lines))
    with pytest.raises(q.QualificationBlocked):
        q._terminal_native(path, "a")
