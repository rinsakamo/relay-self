"""S53 actually overlapping L0 callback while slow synchronous L2 runs."""
import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from adapters.mineflayer.local_chat_provider import (
    LoopbackChatProvider,
    LoopbackInferenceConfig,
)
from relay_self.concurrent_cognition import (
    ConcurrentCognitionRejected,
    ConcurrentL0L2,
)
from relay_self.interruption_fence import (
    CognitionContext,
    InterruptEvidence,
    InterruptStage,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    BoundedChoice,
    BoundedChoiceRequest,
    CognitionMode,
)


def test_l0_runs_before_blocked_l2_and_discards_stale_result():
    async def scenario():
        gate = threading.Event()
        provider_started = threading.Event()
        owner = ConcurrentL0L2()
        before = CognitionContext("actual-session", 7, 1, 4)
        ticket = owner.begin_l2(
            "slow-think", before,
            lambda: (provider_started.set(), gate.wait(timeout=5), "outdated")[2],
        )
        assert ticket.work_id == "slow-think"
        for _ in range(100):
            if provider_started.is_set():
                break
            await asyncio.sleep(0.01)
        assert provider_started.is_set()
        ran = []
        async def urgent():
            ran.append("L0")
        now = CognitionContext("actual-session", 8, 1, 4)
        receipt = await asyncio.wait_for(owner.urgent_l0(now, urgent), timeout=1)
        assert ran == ["L0"] and not gate.is_set()
        assert receipt.l0_completed and not receipt.backend_stopped
        gate.set()
        assert await asyncio.wait_for(owner.collect_l2(now), timeout=2) is None
        assert owner.pending_backend_stop
        with pytest.raises(ConcurrentCognitionRejected):
            owner.begin_l2("second", now, lambda: "new")
        owner.acknowledge_backend_stop(
            InterruptEvidence("slow-think", InterruptStage.BACKEND_STOP_ACK,
                              Provenance("backend", "independent-stopped")),
        )
        # A completed but discarded provider no longer has Action authority.
        owner.retire_after_stop()
        assert not owner.pending_backend_stop
        second = owner.begin_l2("second", now, lambda: "new")
        assert second.work_id == "second"
        assert await owner.collect_l2(now) == "new"
    asyncio.run(scenario())


def test_cannot_claim_urgent_without_l2_work():
    async def scenario():
        owner = ConcurrentL0L2()
        async def noop():
            pass
        with pytest.raises(ConcurrentCognitionRejected):
            await owner.urgent_l0(CognitionContext("s", 1, 0, 0), noop)
    asyncio.run(scenario())


def test_real_http_waiting_l2_does_not_block_urgent_l0():
    """Real loopback socket; the responder is a fake transport, NOT an LLM."""
    hit = threading.Event()
    release = threading.Event()
    count = []

    class BlockedOpenAICompatibleServer(BaseHTTPRequestHandler):
        def log_message(self, *args):
            return

        def do_POST(self):
            length = int(self.headers["Content-Length"])
            payload = json.loads(self.rfile.read(length))
            count.append(payload["model"])
            hit.set()
            release.wait(timeout=8)
            body = json.dumps({
                "choices": [{
                    "message": {"content": "MOVE_AWAY"},
                    "finish_reason": "stop",
                }],
                "usage": {"prompt_tokens": 8, "completion_tokens": 1,
                          "total_tokens": 9},
            }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), BlockedOpenAICompatibleServer)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    async def scenario():
        owner = ConcurrentL0L2()
        before = CognitionContext("real-socket-session", 20, 1, 1)
        now = CognitionContext("real-socket-session", 21, 1, 1)
        provider = LoopbackChatProvider(LoopbackInferenceConfig(
            model="fake-http-transport-only",
            endpoint=f"http://127.0.0.1:{server.server_port}/v1/chat/completions",
            timeout_s=9.0, max_tokens=10,
        ))
        request = BoundedChoiceRequest(
            "l2-transport", "choose", "escape", "zombie",
            (BoundedChoice("WAIT", "wait"),
             BoundedChoice("MOVE_AWAY", "move")),
            (),
        )
        owner.begin_l2(
            "model-http", before,
            lambda: provider(request, mode=CognitionMode.BOUNDED),
        )
        for _ in range(100):
            if hit.is_set():
                break
            await asyncio.sleep(0.01)
        assert hit.is_set()
        l0 = []
        async def urgent():
            l0.append("urgent-reactive-choice")
        receipt = await asyncio.wait_for(owner.urgent_l0(now, urgent), timeout=1)
        assert l0 == ["urgent-reactive-choice"]
        assert not release.is_set()
        assert not receipt.backend_stopped and not receipt.gpu_released
        release.set()
        assert await asyncio.wait_for(owner.collect_l2(now), timeout=3) is None
        with pytest.raises(ConcurrentCognitionRejected):
            owner.retire_after_stop()
        # The fake test server completion does not provide a GPU/runner ACK.
        assert owner.pending_backend_stop
        assert count == ["fake-http-transport-only"]
    try:
        asyncio.run(scenario())
    finally:
        release.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
