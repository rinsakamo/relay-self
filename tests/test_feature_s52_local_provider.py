"""S52 no remote egress and actual loopback HTTP request/response contract."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from adapters.mineflayer.local_chat_provider import (
    LocalInferenceUnavailable,
    LoopbackChatProvider,
    LoopbackInferenceConfig,
)
from relay_self.relay_engine import (
    BoundedChoice,
    BoundedChoiceRequest,
    CognitionDatum,
    CognitionMode,
    DecisionStatus,
    OpenCognitionRequest,
)
from relay_self.provenance import Provenance


@pytest.mark.parametrize("url", (
    "https://example.org/v1/chat/completions",
    "http://192.168.1.3/v1/chat/completions",
    "http://127.0.0.1:1234/private",
    "http://localhost:1234/v1/chat/completions?redirect=https://evil.com",
))
def test_provider_rejects_nonlocal_or_noncanonical_endpoint(url):
    with pytest.raises(LocalInferenceUnavailable):
        LoopbackInferenceConfig(model="Gemma", endpoint=url)


def test_missing_typed_request_does_not_contact_provider():
    provider = LoopbackChatProvider(LoopbackInferenceConfig(model="test"))
    with pytest.raises(LocalInferenceUnavailable):
        provider(None, mode=CognitionMode.BOUNDED)


def test_budget_and_model_are_explicit():
    with pytest.raises(LocalInferenceUnavailable):
        LoopbackInferenceConfig(model="", max_tokens=2)
    with pytest.raises(LocalInferenceUnavailable):
        LoopbackInferenceConfig(model="test", max_tokens=10000)


def test_actual_loopback_http_choice_and_open_without_provider_authority():
    recorded = []

    class FakeTransport(BaseHTTPRequestHandler):
        def log_message(self, *args):
            return

        def do_POST(self):
            size = int(self.headers["Content-Length"])
            assert size <= 16384
            request = json.loads(self.rfile.read(size))
            recorded.append((self.path, request))
            body = json.dumps({
                "choices": [{
                    "message": {"content": "MOVE_AWAY"},
                    "finish_reason": "stop",
                }],
                "usage": {
                    "prompt_tokens": 21,
                    "completion_tokens": 3,
                    "total_tokens": 24,
                },
            }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeTransport)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        cfg = LoopbackInferenceConfig(
            model="synthetic-test-server-not-a-model",
            endpoint=f"http://127.0.0.1:{server.server_port}/v1/chat/completions",
            timeout_s=3, max_tokens=32,
        )
        provider = LoopbackChatProvider(cfg)
        provenance = Provenance("native", "world:1")
        request = BoundedChoiceRequest(
            request_id="bounded-probe",
            instruction="Choose exact candidate",
            intent_id="escape-threat", focus="zombie",
            choices=(
                BoundedChoice("WAIT", "do nothing"),
                BoundedChoice("MOVE_AWAY", "move backward"),
            ),
            context=(CognitionDatum.from_value(
                "distance", 2.0, provenance,
            ),),
        )
        decision = provider(request, mode=CognitionMode.BOUNDED)
        assert decision.status is DecisionStatus.RESOLVED
        assert decision.choice_id == "MOVE_AWAY"
        assert decision.call_facts.total_tokens == 24
        assert decision.call_facts.requested_max_output_tokens == 32
        assert recorded[-1][0] == "/v1/chat/completions"
        sent = json.loads(recorded[-1][1]["messages"][1]["content"])
        assert sent["context"][0]["reference"] == "world:1"
        # OPEN output is only transient untrusted expression, not a World fact.
        open_result = provider(OpenCognitionRequest(
            request_id="open-probe", instruction="say something",
            intent_id=None, focus=None, context=(),
        ), mode=CognitionMode.OPEN)
        assert open_result.text == "MOVE_AWAY"
        assert open_result.provenance.source == "local-llm"
        assert len(recorded) == 2
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
