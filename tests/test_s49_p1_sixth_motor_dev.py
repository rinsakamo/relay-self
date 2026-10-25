"""DEV-only sixth original host motor timing: opt-in negative controls."""
from __future__ import annotations

import asyncio
import hashlib
import inspect

import pytest

from adapters.mineflayer import s49_normal_session_real_ci as original
from adapters.mineflayer.s49_paper_world_first_dev import CONFIRM, run


@pytest.mark.parametrize("next_mode,fifth_mode,sixth_mode", [
    ("MOVE_AWAY", "WAIT", "MOVE_AWAY"),
    (None, "WAIT", "MOVE_AWAY"),
    ("MOVE_AWAY", None, "MOVE_AWAY"),
    ("MOVE_AWAY", "WAIT", "WAIT"),
])
def test_sixth_requires_explicit_owner_and_separate_dev_gate(
    tmp_path, monkeypatch, next_mode, fifth_mode, sixth_mode,
):
    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.setenv("S49_NEXT_EPOCH_DEV_ONLY", "1")
    monkeypatch.setenv("S49_FIFTH_EPOCH_DEV_ONLY", "1")
    monkeypatch.delenv("S49_SIXTH_EPOCH_DEV_ONLY", raising=False)
    monkeypatch.delenv("NODE_OPTIONS", raising=False)

    def no_java(*args, **kwargs):
        raise AssertionError("missing DEV sixth gate attempted Minecraft")
    monkeypatch.setattr(original, "_fetch_official_server", no_java)
    report = tmp_path / "original.json"
    rc = asyncio.run(original.qualify(
        report, tmp_path / "java.log",
        dev_next_epoch=next_mode,
        dev_fifth_epoch=fifth_mode,
        dev_sixth_epoch=sixth_mode,
    ))
    assert rc == 2
    assert report.is_file()
    import json
    actual = json.loads(report.read_text())
    assert actual["status"] == "BLOCKED"
    assert actual["actual_native_actions"] == []


@pytest.mark.parametrize("next_on,fifth_on,gait_on", [
    (False, False, False),
    (True, False, False),
    (True, True, False),
])
def test_physical_model_motor_rejected_without_complete_prior_epochs(
    tmp_path, next_on, fifth_on, gait_on,
):
    paper, observer = tmp_path / "paper.jar", tmp_path / "obs.jar"
    paper.write_bytes(b"offline")
    observer.write_bytes(b"offline-observer")
    output = tmp_path / "output"
    rc = asyncio.run(run(
        output, paper, hashlib.sha256(paper.read_bytes()).hexdigest(),
        observer, hashlib.sha256(observer.read_bytes()).hexdigest(),
        confirmation=CONFIRM, fresh_target_distance=2,
        actual_next_epoch=next_on, actual_fifth_epoch=fifth_on,
        compare_fifth_gait=gait_on, actual_sixth_motor=True,
    ))
    assert rc == 2
    assert not output.exists()


def test_s49_default_stays_three_decisions_and_original_executor_source_pinned():
    code = inspect.getsource(original.qualify)
    assert "dev_sixth_epoch: str | None = None" in code
    assert "S49_SIXTH_EPOCH_DEV_ONLY" in code
    assert "else 4 if dev_next_epoch is not None else 3" in code
    assert "max_events=(6 if dev_sixth_epoch is not None" in code
    assert "dev_original_sixth_epoch" in code
