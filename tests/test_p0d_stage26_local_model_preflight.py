"""Stage26 owned llama.cpp pre-World evidence tests; no actual GPU or Paper.

All Linux /proc, Windows WDDM snapshots and HTTP are synthetic sources.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from experiments.p0d_stage26_local_model_preflight import (
    Stage26ModelPreflightHold,
    _argv_value,
    inspect_stage26_model_source,
)


class FakeSlotResponse:
    status = 200

    def __init__(self, slots) -> None:
        self.payload = json.dumps(slots).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def read(self, limit):
        return self.payload[:limit]


def fixture_sources(tmp_path: Path):
    proc = tmp_path / "fake-proc"
    (proc / "42" / "fd").mkdir(parents=True)
    (proc / "net").mkdir(parents=True)
    exe = tmp_path / "owned" / "llama-server"
    gguf = tmp_path / "owned" / "gemma-Q4_K_M.gguf"
    exe.parent.mkdir()
    exe.write_bytes(b"llama-server-build11066")
    gguf.write_bytes(b"model-file-synthetic")
    (proc / "42" / "exe").symlink_to(exe)
    (proc / "42" / "fd" / "3").symlink_to("socket:[789]")
    (proc / "42" / "cmdline").write_bytes(
        b"/owned/llama-server\x00-m\x00"
        + str(gguf).encode()
        + b"\x00-np1\x00-c8192\x00-ngl999\x00"
    )
    (proc / "net" / "tcp").write_text(
        "sl local_address rem_address st tx_queue rx_queue tr tm->when "
        "retrnsmt uid timeout inode\n"
        "0: 0100007F:1F90 00000000:0000 0A 00000000:00000000 "
        "00:00000000 00000000 1000 0 789\n"
    )
    baseline = tmp_path / "windows-wddm-gpu-readback.txt"
    baseline.write_text(
        "GPU used 696MiB; explorer.exe C+G; ChatGPT.exe C+G; "
        "NVIDIA Overlay C+G; GUI presence is not inference competition\n"
    )
    kwargs = {
        "pid": 42, "endpoint": "http://127.0.0.1:8080/v1/chat/completions",
        "executable": exe, "executable_sha256": hashlib.sha256(
            exe.read_bytes()
        ).hexdigest(),
        "gguf": gguf, "gguf_sha256": hashlib.sha256(
            gguf.read_bytes()
        ).hexdigest(),
        "proc_root": proc, "windows_gpu_snapshot": baseline,
    }
    return kwargs


def test_stage26_verified_owner_and_idle_slot_not_confused_with_wddm_desktop(
    tmp_path,
):
    args = fixture_sources(tmp_path)
    with patch("urllib.request.urlopen", return_value=FakeSlotResponse([
        {"id": 0, "is_processing": False},
    ])) as request:
        result = inspect_stage26_model_source(**args)
    assert request.call_count == 1
    assert result.linux_pid == 42
    assert result.owned_listener_inode == "789"
    assert result.slots_id == 0
    assert not result.slots_processing
    assert result.gguf_sha256 == args["gguf_sha256"]
    assert result.n_parallel == 1
    assert result.context_size == 8192
    assert result.gpu_layers == 999
    assert result.windows_gpu_snapshot_sha256
    assert result.classification == (
        "OWNED_MODEL_SLOT_IDLE_DEV_NOT_FULL_GPU_ATTESTATION"
    )
    # The source inspector CANNOT certify global GPU ownership or even model
    # VRAM fit, independent of Windows C+G desktop processes being present.
    assert not result.gpu_wide_exclusivity_attested
    assert not result.gpu_capacity_attested
    assert not result.external_client_absence_attested
    assert not result.physical_action_authorized
    assert not result.world_trial_consumed


@pytest.mark.parametrize("mode", [
    "foreign-pid-socket",
    "public-listener",
    "missing-process-exe",
    "model-changed",
    "binary-changed",
    "model-argv-changed",
    "multiple-parallel",
    "wrong-context",
    "cpu-only",
    "busy-slot",
    "two-slots",
    "foreign-endpoint",
])
def test_stage26_fails_closed_when_original_owner_is_not_source_qualified(
    tmp_path, mode,
):
    args = fixture_sources(tmp_path)
    proc = args["proc_root"]
    slots = [{"id": 0, "is_processing": False}]
    if mode == "foreign-pid-socket":
        (proc / "42" / "fd" / "3").unlink()
    elif mode == "public-listener":
        tcp = proc / "net" / "tcp"
        tcp.write_text(tcp.read_text().replace("0100007F", "00000000"))
    elif mode == "missing-process-exe":
        (proc / "42" / "exe").unlink()
    elif mode == "model-changed":
        args["gguf"].write_bytes(b"unexpected-model")
    elif mode == "binary-changed":
        args["executable"].write_bytes(b"changed-llama-server")
    elif mode == "model-argv-changed":
        cmd = proc / "42" / "cmdline"
        cmd.write_bytes(cmd.read_bytes().replace(b"gemma-Q4_K_M.gguf", b"wrong.gguf"))
    elif mode == "multiple-parallel":
        cmd = proc / "42" / "cmdline"
        cmd.write_bytes(cmd.read_bytes().replace(b"-np1", b"-np2"))
    elif mode == "wrong-context":
        cmd = proc / "42" / "cmdline"
        cmd.write_bytes(cmd.read_bytes().replace(b"-c8192", b"-c4096"))
    elif mode == "cpu-only":
        cmd = proc / "42" / "cmdline"
        cmd.write_bytes(cmd.read_bytes().replace(b"-ngl999", b"-ngl0"))
    elif mode == "busy-slot":
        slots = [{"id": 0, "is_processing": True}]
    elif mode == "two-slots":
        slots.append({"id": 1, "is_processing": False})
    elif mode == "foreign-endpoint":
        args["endpoint"] = "http://0.0.0.0:8080/v1/chat/completions"
    with patch("urllib.request.urlopen", return_value=FakeSlotResponse(slots)):
        with pytest.raises(Stage26ModelPreflightHold):
            inspect_stage26_model_source(**args)


def test_argv_parser_accepts_short_and_long_but_rejects_duplicates():
    assert _argv_value(("llama", "-np1"), "-np", "--parallel") == "1"
    assert _argv_value(("llama", "--parallel", "1"), "-np", "--parallel") == "1"
    assert _argv_value(("llama", "--parallel=1"), "-np", "--parallel") == "1"
    with pytest.raises(Stage26ModelPreflightHold):
        _argv_value(("llama", "-np1", "--parallel=1"), "-np", "--parallel")
    with pytest.raises(Stage26ModelPreflightHold):
        _argv_value(("llama",), "-np", "--parallel")


def test_preflight_source_does_not_issue_any_model_request(tmp_path):
    args = fixture_sources(tmp_path)
    with patch("urllib.request.urlopen", return_value=FakeSlotResponse([
        {"id": 0, "is_processing": False},
    ])) as request:
        inspect_stage26_model_source(**args)
    actual = request.call_args.args[0]
    assert actual.get_method() == "GET"
    assert actual.full_url.endswith("/slots")
    assert actual.data is None
