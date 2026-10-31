"""S57 owned local backend test harness: mock files do NOT prove model use."""
from __future__ import annotations

import asyncio
import hashlib
import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from adapters.mineflayer.s57_owned_llama_backend import (
    OwnedBackendRejected,
    OwnedBackendSpec,
    backend_environment,
    backend_ready,
    preflight_available_port,
    run_owned_world,
)


def _fake_local_files(tmp_path):
    binary = tmp_path / "FAKE_NOT_LLAMA_SERVER"
    binary.write_bytes(b"test-only-no-real-server")
    binary.chmod(0o755)
    gguf = tmp_path / "FAKE_NOT_GGUF.gguf"
    gguf.write_bytes(b"test-only-not-valid-model-weights")
    shab = hashlib.sha256(binary.read_bytes()).hexdigest()
    shag = hashlib.sha256(gguf.read_bytes()).hexdigest()
    return binary, gguf, shab, shag


def test_exact_owned_binary_and_model_sha_are_separate_from_loaded_attestation(
    tmp_path,
):
    binary, model, shab, shag = _fake_local_files(tmp_path)
    spec = OwnedBackendSpec(
        binary, model, shab, shag,
        "test-model-alias", port=12345, gpu_layers=12,
        ctx_size=4352,
    )
    assert spec.validate_files() == (shab, shag)
    argv = spec.argv()
    assert "--model" in argv and "--alias" in argv
    assert "--host" in argv and "127.0.0.1" in argv
    assert "--port" in argv and "12345" in argv
    assert "--parallel" in argv and "1" in argv
    assert "--n-gpu-layers" in argv and "12" in argv
    assert "--ctx-size" in argv and "4352" in argv
    pub = spec.public_config()
    assert pub["binary_file_path_published"] is False
    assert pub["model_file_path_published"] is False
    assert "FAKE_NOT_GGUF" not in json.dumps(pub)


def test_wrong_hash_must_fail_before_any_process_launch(tmp_path):
    binary, model, shab, shag = _fake_local_files(tmp_path)
    with pytest.raises(OwnedBackendRejected):
        OwnedBackendSpec(
            binary, model, shab, shag, "bad alias spaces",
        )
    spec = OwnedBackendSpec(binary, model, "0" * 64, shag, "model")
    with pytest.raises(OwnedBackendRejected):
        spec.validate_files()
    spec = OwnedBackendSpec(binary, model, shab, "f" * 64, "model")
    with pytest.raises(ValueError):
        spec.validate_files()


def test_external_host_and_inherited_secrets_cannot_be_in_backend_argv(
    tmp_path, monkeypatch,
):
    binary, model, shab, shag = _fake_local_files(tmp_path)
    spec = OwnedBackendSpec(binary, model, shab, shag, "alias")
    assert "0.0.0.0" not in spec.argv()
    monkeypatch.setenv("LLAMA_ARG_MODEL", "different-model")
    monkeypatch.setenv("OPENAI_API_KEY", "private-token")
    monkeypatch.setenv("HTTP_PROXY", "http://untrusted:1234")
    env = backend_environment()
    assert "LLAMA_ARG_MODEL" not in env
    assert "OPENAI_API_KEY" not in env
    assert "HTTP_PROXY" not in env


def test_occupied_loopback_port_is_rejected():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as owner:
        owner.bind(("127.0.0.1", 0))
        port = owner.getsockname()[1]
        if port >= 1025:
            with pytest.raises(OwnedBackendRejected):
                preflight_available_port(port)


def test_no_explicit_owned_backend_opt_in_fails_before_io(tmp_path, monkeypatch):
    monkeypatch.delenv("S57_ALLOW_OWNED_BACKEND", raising=False)
    binary, model, shab, shag = _fake_local_files(tmp_path)
    spec = OwnedBackendSpec(binary, model, shab, shag, "synthetic-only")
    receipt_path = tmp_path / "receipt.json"
    result = asyncio.run(run_owned_world(
        spec, report_file=receipt_path,
        server_log=tmp_path / "native-server.log",
        backend_log=tmp_path / "s57-private-backend.log",
        timeout_s=1,
    ))
    receipt = json.loads(receipt_path.read_text())
    assert result == 2 and receipt["status"] == "BLOCKED"
    assert receipt["owned_backend_started"] is False
    assert receipt["backend_model_loaded_independently_attested"] is False
    assert receipt["native_world_actual_model_overlap_pass"] is False
    assert not (tmp_path / "s57-private-backend.log").exists()


def test_github_host_cannot_claim_local_backend_even_with_opt_in(
    tmp_path, monkeypatch,
):
    monkeypatch.setenv("S57_ALLOW_OWNED_BACKEND", "1")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    binary, model, shab, shag = _fake_local_files(tmp_path)
    spec = OwnedBackendSpec(binary, model, shab, shag, "synthetic-only")
    report_file = tmp_path / "receipt.json"
    result = asyncio.run(run_owned_world(
        spec, report_file=report_file,
        server_log=tmp_path / "native-server.log",
        backend_log=tmp_path / "backend.log",
        timeout_s=1,
    ))
    receipt = json.loads(report_file.read_text())
    assert result == 2
    assert receipt["status"] == "BLOCKED"
    assert receipt["owned_backend_started"] is False


def test_fake_local_health_probe_never_counts_as_model_attestation():
    """Unit health transport test, NOT a model execution or GPU test."""
    class HealthHandler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            return

        def do_GET(self):
            body = b'{"status":"ok"}'
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    class FakeProcess:
        def poll(self):
            return None

    server = ThreadingHTTPServer(("127.0.0.1", 0), HealthHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        backend_ready(server.server_port, FakeProcess(), timeout_s=2)
        assert True  # Healthy test socket alone is not GGUF attestation.
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)


def test_untrusted_local_health_redirect_is_rejected_without_following():
    class Redirect(BaseHTTPRequestHandler):
        def log_message(self, *args):
            return

        def do_GET(self):
            self.send_response(302)
            self.send_header("Location", "https://example.invalid/leave-localhost")
            self.end_headers()

    class FakeProcess:
        def poll(self):
            return None

    server = ThreadingHTTPServer(("127.0.0.1", 0), Redirect)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        with pytest.raises(OwnedBackendRejected):
            backend_ready(server.server_port, FakeProcess(), timeout_s=1)
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)
