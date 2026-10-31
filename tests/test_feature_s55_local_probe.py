"""S55 qualification harness contract; test HTTP responder is NOT a model."""
from __future__ import annotations

import hashlib
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from adapters.mineflayer.local_chat_provider import LocalInferenceUnavailable
from adapters.mineflayer.s55_local_model_probe import (
    InvalidLocalQualification,
    hash_gguf,
    qualify,
)


def test_gguf_hash_does_not_qualify_runtime_model(tmp_path):
    fake = tmp_path / "fake-not-real-model.gguf"
    fake.write_bytes(b"dummy-data-NOT-a-real-GGUF")
    expected = hashlib.sha256(fake.read_bytes()).hexdigest()
    a = hash_gguf(fake, expected)
    assert a["file_sha256"] == expected
    assert a["matched_expected_hash"] is True
    assert a["loaded_by_backend"] is False
    with pytest.raises(InvalidLocalQualification):
        hash_gguf(fake, "0" * 64)
    with pytest.raises(InvalidLocalQualification):
        hash_gguf(None, "0" * 64)


def test_nonlocal_http_rejected_before_any_inference():
    with pytest.raises(LocalInferenceUnavailable):
        qualify(
            model="test",
            endpoint="https://example.com/v1/chat/completions",
        )


def test_dummy_local_http_is_labeled_unverified_not_real_model():
    class FakeResponder(BaseHTTPRequestHandler):
        def log_message(self, *args):
            return

        def do_POST(self):
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            assert data["model"] == "mock-not-a-real-llm"
            body = json.dumps({
                "choices": [{
                    "message": {"content": "MOVE_AWAY"},
                    "finish_reason": "stop",
                }],
                "usage": {
                    "prompt_tokens": 13,
                    "completion_tokens": 2,
                    "total_tokens": 15,
                },
            }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeResponder)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        out = qualify(
            model="mock-not-a-real-llm",
            endpoint=f"http://127.0.0.1:{server.server_port}/v1/chat/completions",
            max_tokens=32, timeout_s=3,
        )
        assert out["model_calls"] == 1
        assert out["candidate_choice"] == "MOVE_AWAY"
        assert out["prompt_tokens"] == 13
        assert out["completion_tokens"] == 2
        assert out["status"] == "PASS"
        assert out["classification"] == "LOOPBACK_INFERENCE_RESPONSE_BACKEND_ID_UNVERIFIED"
        assert out["model_actually_loaded_attested"] is False
        assert out["gpu_used_attested"] is False
        assert out["action_authorized"] is False
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
