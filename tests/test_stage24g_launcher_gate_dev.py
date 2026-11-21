"""Stage24g launcher is inert until model/Paper/GPU gates qualify."""
from __future__ import annotations

import sys
from pathlib import Path

from experiments import stage24g_pinned_assets_launch_dev as launch
from experiments.stage24g_model_gate_dev import Stage24gModelGateReceipt


def _args(tmp_path, *, pid: bool):
    values = [
        "stage24g_pinned_assets_launch_dev",
        "--paper-jar", str(tmp_path / "paper.jar"),
        "--plugin-jar", str(tmp_path / "plugin.jar"),
        "--scratch-parent", str(tmp_path),
        "--eula-accepted", "--execute-once",
        "--real-world-dev-grant", "--grant-real-llm",
        "--llama-endpoint", "http://127.0.0.1:8000/v1/chat/completions",
        "--systemone-endpoint", "http://127.0.0.1:8000/v1/systemone",
        "--model", "stage24g-gemma",
    ]
    if pid:
        values.extend(["--gguf-path", str(tmp_path / "gemma.gguf"),
                       "--llama-pid", "14021"])
    return values


def _assets(tmp_path, monkeypatch):
    checked = launch.Stage24gPinnedAssetReceipt(
        tmp_path / "paper.jar", tmp_path / "plugin.jar", tmp_path,
        "a" * 64, "b" * 64,
    )
    monkeypatch.setattr(launch, "check_stage24g_pinned_assets", lambda **kw: checked)
    monkeypatch.setattr(launch, "_verify_local_runtime", lambda *args: None)


def test_stage24g_missing_gpu_pid_never_creates_world_or_calls_model(tmp_path, monkeypatch):
    _assets(tmp_path, monkeypatch)
    monkeypatch.setattr(sys, "argv", _args(tmp_path, pid=False))
    def fail(*args, **kwargs):
        raise AssertionError("GPU gate not admitted")
    monkeypatch.setattr(launch, "verify_stage24g_model_gate", fail)
    monkeypatch.setattr(launch, "run_real_resident_presence", fail)
    assert launch.main() == 2


def test_stage24g_passed_gate_calls_original_runner_once(tmp_path, monkeypatch):
    _assets(tmp_path, monkeypatch)
    monkeypatch.setattr(sys, "argv", _args(tmp_path, pid=True))
    receipt = Stage24gModelGateReceipt(
        14021, "stage24g-gemma", str(tmp_path / "gemma.gguf"),
        "c" * 64, "NVIDIA RTX 3060", "d" * 64, "e" * 64,
        0, 1, "f" * 64,
    )
    calls = []
    def gate(**kwargs):
        calls.append(("model", kwargs))
        return receipt
    async def world(**kwargs):
        calls.append(("world", kwargs))
        return Path("/safe/fictional/offline-result.json")
    monkeypatch.setattr(launch, "verify_stage24g_model_gate", gate)
    monkeypatch.setattr(launch, "run_real_resident_presence", world)
    assert launch.main() == 0
    assert [kind for kind, _ in calls] == ["model", "world"]
    assert calls[1][1]["stage24g_model_receipt"] is receipt
    assert calls[1][1]["world_only"] is True
    assert calls[1][1]["b_autonomous_l1_dev"] is True
    assert calls[1][1]["b_selected_move_dev"] is False
