"""Stage24g no-real-World offline checks for original HTTP, GPU/PID and WAL gates."""
from __future__ import annotations

import hashlib
import json
import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from adapters.llama_cpp.relay_engine import (
    LlamaCppProviderError,
    LlamaCppRelayProvider,
)
from experiments import stage24g_model_gate_dev as model_gate
from experiments.p0d_real_resident_presence_dev import (
    RealResidentPresenceRefusal,
    _require_stage24g_systemone_capture,
)


class _Response:
    status = 200

    def __init__(self, raw: bytes):
        self.raw = raw

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.raw


def _provider(tmp_path):
    path = tmp_path / "raw"
    path.mkdir()
    return LlamaCppRelayProvider(
        endpoint="http://127.0.0.1:8000/v1/chat/completions",
        systemone_endpoint="http://127.0.0.1:8000/v1/systemone",
        model="gemma-local", systemone_raw_dir=path,
    ), path


def test_stage24g_exact_one_post_original_request_response_and_sha(tmp_path):
    provider, evidence = _provider(tmp_path)
    response = b'{ "answers": {"decision": {"choice": "1"}} }'
    requests = []

    def original_post(req, **kwargs):
        requests.append((req.full_url, req.data, kwargs))
        return _Response(response)

    with patch("urllib.request.urlopen", side_effect=original_post):
        got = provider._call(
            {"model": "gemma-local", "questions": {"decision": {}}},
            endpoint=provider.systemone_endpoint,
        )
    assert got["answers"]["decision"]["choice"] == "1"
    assert len(requests) == 1
    assert requests[0][1] == (evidence / "systemone-request-body.bin").read_bytes()
    assert response == (evidence / "systemone-response-body.bin").read_bytes()
    manifest = json.loads((evidence / "systemone-http-evidence.json").read_bytes())
    assert manifest["http_status"] == 200
    assert manifest["request_body_sha256"] == hashlib.sha256(requests[0][1]).hexdigest()
    assert manifest["response_body_sha256"] == hashlib.sha256(response).hexdigest()
    # Reuse of a consumed capture must fail *before* another POST.
    with patch("urllib.request.urlopen", side_effect=AssertionError("second POST")):
        with pytest.raises(LlamaCppProviderError, match="evidence write failed"):
            provider._call({"model": "gemma-local"}, endpoint=provider.systemone_endpoint)


def test_stage24g_response_audit_rejects_modified_original_bytes(tmp_path):
    evidence = tmp_path / "stage24g-systemone-http"
    evidence.mkdir()
    provider = LlamaCppRelayProvider(
        endpoint="http://127.0.0.1:8000/v1/chat/completions",
        systemone_endpoint="http://127.0.0.1:8000/v1/systemone",
        model="gemma-local", systemone_raw_dir=evidence,
    )
    with patch("urllib.request.urlopen", return_value=_Response(b'{"answers":{}}')):
        provider._call({"model": "gemma-local"}, endpoint=provider.systemone_endpoint)
    assert _require_stage24g_systemone_capture(tmp_path)["model_http_status_attested"] == 200
    (evidence / "systemone-response-body.bin").write_bytes(b'{"forged":true}')
    with pytest.raises(RealResidentPresenceRefusal, match="digest mismatch"):
        _require_stage24g_systemone_capture(tmp_path)


def test_stage24g_no_response_bytes_ever_fabricated_on_network_failure(tmp_path):
    provider, evidence = _provider(tmp_path)
    with patch("urllib.request.urlopen", side_effect=TimeoutError("no response")):
        with pytest.raises(LlamaCppProviderError):
            provider._call({"model": "gemma-local"}, endpoint=provider.systemone_endpoint)
    assert (evidence / "systemone-request-body.bin").is_file()
    assert not (evidence / "systemone-response-body.bin").exists()
    assert not (evidence / "systemone-http-evidence.json").exists()


def test_stage24g_gate_uses_pid_maps_gpu_catalog_and_one_idle_slot(tmp_path, monkeypatch):
    gguf = tmp_path / "gemma.gguf"
    gguf.write_bytes(b"GGUF_TEST_FIXTURE")
    monkeypatch.setattr(
        model_gate, "PINNED_STAGE24G_GGUF_SHA256",
        hashlib.sha256(gguf.read_bytes()).hexdigest(),
    )
    pid = 41234
    proc = tmp_path / "proc"
    owned = proc / str(pid)
    owned.mkdir(parents=True)
    (owned / "cmdline").write_bytes(
        b"/tmp/llama-server\x00--model\x00" + str(gguf).encode() + b"\x00"
    )
    (owned / "maps").write_text(
        f"7f000000-7f010000 r--p 0 00:00 0 {gguf}\n"
    )
    (owned / "fd").mkdir()
    (owned / "fd" / "4").symlink_to("socket:[4321]")
    (proc / "net").mkdir()
    (proc / "net/tcp").write_text(
        "sl local_address rem_address st tx_queue rx_queue tr tm->when retrnsmt uid timeout inode\n"
        "0: 0100007F:1F40 00000000:0000 0A 0:0 0:0 0 1000 0 4321\n"
    )

    monkeypatch.setattr(model_gate, "_PROC_ROOT", proc)
    def run(args, **kwargs):
        return SimpleNamespace(stdout=(
            f"{pid}\n" if "--query-compute-apps=pid" in args
            else "NVIDIA GeForce RTX 3060\n"
        ))
    monkeypatch.setattr(model_gate.subprocess, "run", run)
    monkeypatch.setattr(model_gate, "_read_model_catalog", lambda *args: "c" * 64)
    monkeypatch.setattr(
        model_gate.LlamaCppSingleSlotWitness, "require_idle",
        lambda self: SimpleNamespace(slot_id=0, n_slots=1),
    )
    result = model_gate.verify_stage24g_model_gate(
        gguf_path=gguf, llama_pid=pid, model_alias="gemma-local",
        llama_endpoint="http://127.0.0.1:8000/v1/chat/completions",
        systemone_endpoint="http://127.0.0.1:8000/v1/systemone",
    )
    assert result.llama_pid == pid
    assert result.slot_count == 1
    assert result.gpu_name == "NVIDIA GeForce RTX 3060"
    assert result.gguf_sha256 == hashlib.sha256(gguf.read_bytes()).hexdigest()


def test_stage24g_rejects_foreign_or_wrong_gguf_before_pid_gpu(tmp_path):
    path = tmp_path / "fixture.gguf"
    path.write_bytes(b"NOT_ACTUAL_GEMMA")
    with pytest.raises(model_gate.Stage24gModelGateError, match="GGUF bytes"):
        model_gate.verify_stage24g_model_gate(
            gguf_path=path, llama_pid=os.getpid(), model_alias="model",
            llama_endpoint="http://127.0.0.1:8000/v1/chat/completions",
            systemone_endpoint="http://127.0.0.1:8000/v1/systemone",
        )
