"""#860 Stage21: source-shaped actual HTTP llama.cpp requests + /slots probes.

HTTP is a controlled synthetic server, NOT a real Gemma GPU backend.
Original cognition, physical issuer and original native process adapters are
reused; only the model endpoint is substituted by a deterministic HTTP stub.
"""
from __future__ import annotations

import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from adapters.llama_cpp.relay_engine import LlamaCppRelayProvider
from relay_self.owned_resident_physical_bridge_dev import (
    OwnedResidentPhysicalBridge,
)
from relay_self.relay_engine import (
    BoundedChoice,
    BoundedChoiceRequest,
    CognitionMode,
    OpenCognitionRequest,
    ProviderDecision,
    ProviderExpression,
)
from relay_self.resident_llama_inference_lane_dev import (
    LlamaCppSingleSlotWitness,
    ResidentGpuLaneError,
    ResidentLlamaInferenceLane,
)
from relay_self.world_only_owned_checkpoint_dev import (
    WorldOnlyOwnedPaperCheckpoint,
)
from relay_self.world_resident_lifecycle_dev import Presence
from test_p0d_resident_physical_issuer_dev import ResidentFixture, _memory


class _SyntheticLlamaServer:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.active = 0
        self.maximum_active = 0
        self.entered = threading.Event()
        self.release = threading.Event()
        self.release.set()
        self.leave_busy = False
        self.extra_slots = False
        self.respond_500 = False
        self.calls: list[str] = []
        self.probes = 0
        self.srv: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None

    def start(self) -> str:
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                del fmt, args

            def do_GET(self):
                if self.path != "/slots":
                    self.send_error(404)
                    return
                with owner.lock:
                    owner.probes += 1
                    busy = owner.active > 0
                    slots = [{"id": 0, "id_task": 23 if busy else -1,
                              "is_processing": busy}]
                    if owner.extra_slots:
                        slots.append({"id": 1, "is_processing": False})
                self._write(200, slots)

            def do_POST(self):
                if self.path != "/v1/chat/completions":
                    self.send_error(404)
                    return
                length = int(self.headers.get("Content-Length", 0))
                payload = json.loads(self.rfile.read(length))
                with owner.lock:
                    owner.active += 1
                    owner.maximum_active = max(
                        owner.maximum_active, owner.active,
                    )
                    owner.calls.append(payload.get("model", "unknown"))
                owner.entered.set()
                owner.release.wait(timeout=8.0)
                with owner.lock:
                    if not owner.leave_busy:
                        owner.active -= 1
                    error = owner.respond_500
                if error:
                    self._write(500, {"error": "synthetic transport failure"})
                    return
                response = (
                    '{"status":"resolved","choice_id":"A"}'
                    if "response_format" in payload
                    else "Cognition is a tentative inference, not physical truth."
                )
                self._write(200, {
                    "choices": [{
                        "message": {"content": response},
                        "finish_reason": "stop",
                    }],
                    "usage": {"prompt_tokens": 10,
                              "completion_tokens": 14, "total_tokens": 24},
                })

            def _write(self, status: int, body: object) -> None:
                data = json.dumps(body).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                try:
                    self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(
            target=self.srv.serve_forever, daemon=True,
        )
        self.thread.start()
        return f"http://127.0.0.1:{self.srv.server_address[1]}/v1/chat/completions"

    def stop(self) -> None:
        self.release.set()
        if self.srv is not None:
            self.srv.shutdown()
            self.srv.server_close()
        if self.thread is not None:
            self.thread.join(timeout=3)


def _request(ref: str) -> OpenCognitionRequest:
    return OpenCognitionRequest(
        request_id=ref, instruction="Observe the new World.",
        intent_id=None, focus="synthetic-only", context=(),
    )


def _bounded(ref: str) -> BoundedChoiceRequest:
    return BoundedChoiceRequest(
        request_id=ref, instruction="Choose one.", intent_id=None,
        focus=None,
        choices=(BoundedChoice("A", "first"), BoundedChoice("B", "second")),
        context=(), think_allowed=False,
    )


def _attach(f: ResidentFixture, endpoint: str) -> ResidentLlamaInferenceLane:
    assert f.cognitive is not None
    provider = LlamaCppRelayProvider(
        endpoint=endpoint, model="fake-gemma", timeout=4.0,
    )
    probe = LlamaCppSingleSlotWitness(
        provider=provider, backend_ref="owned-llama-test-server",
    )
    lane = ResidentLlamaInferenceLane(
        provider=provider, cognitive_work=f.cognitive, witness=probe,
    )
    # Construct bridge using the actual optional integration constructor;
    # nothing from the old unbound test bridge has logged in.
    f.bridge = OwnedResidentPhysicalBridge(
        lifecycle=f.lifecycle, physical=f.physical,
        paper=f.paper, configs=f.configs, owners=f.owners,
        launch=f.bridge.launch, cognitive_work=f.cognitive,
        inference_lane=lane,
    )
    return lane


@pytest.mark.parametrize("count", [2, 10, 100])
def test_serial_shared_gpu_one_actor_logout_and_other_actor_continues(
    tmp_path, count,
):
    fake = _SyntheticLlamaServer()
    endpoint = fake.start()
    f = ResidentFixture(tmp_path, count, cognitive_work=True)
    lane = _attach(f, endpoint)

    async def scenario():
        for sid in f.names:
            await f.bridge.login(sid)
        a = f.names[-1]
        b = f.names[0]
        token = lane.submit(
            a, work_ref="owned-open-L2",
            request=_request("llama-L2-A"), mode=CognitionMode.OPEN,
        )
        result = await lane.await_result(token)
        assert isinstance(result, ProviderExpression)
        assert "tentative inference" in result.text
        lane.adopt_memory(token, _memory(a, "adopted-llama"))
        assert _memory(a, "adopted-llama") in f.owners[a].retained.memories
        old_native = f.bridge.sessions[a].started.session_id
        await f.bridge.logout(a)
        assert f.lifecycle.view(a).status is Presence.OFFLINE
        assert lane.retired_clean(a)
        with pytest.raises(ResidentGpuLaneError, match="late"):
            lane.result(token)
        with pytest.raises(ResidentGpuLaneError, match="adoptable"):
            lane.adopt_memory(token, _memory(a, "stale-llama"))
        assert f.lifecycle.view(b).status is Presence.ONLINE
        with f.physical.lease(
            self_id=b, native_session_id=f.bridge.sessions[b].started.session_id,
            action_id="peer-eat-while-A-gpu-logged-off", effect_family="EAT",
        ):
            f.bridge.sessions[b].send_test_effect(
                "consume_held", "peer-eat-while-A-gpu-logged-off",
            )
        f.owners[b].retain_memory(_memory(b, "peer-keeps-learning"))
        await f.bridge.login(a)
        assert f.bridge.sessions[a].started.session_id != old_native
        with pytest.raises(ResidentGpuLaneError, match="late"):
            lane.result(token)
        if a != b:
            t_b = lane.submit(
                b, work_ref="owned-L1-selection",
                request=_bounded("llama-L1-B"), mode=CognitionMode.BOUNDED,
            )
            outcome = await lane.await_result(t_b)
            assert isinstance(outcome, ProviderDecision)
            assert outcome.choice_id == "A"
        for sid in f.names:
            await f.bridge.logout(sid)
        assert all(lane.retired_clean(sid) for sid in f.names)
        assert not lane.require_world_idle().is_processing
        assert f.bridge.world_only_quiescence().all_gpu_epochs_retired

    try:
        asyncio.run(scenario())
        assert fake.maximum_active == 1
        assert fake.probes >= 4
    finally:
        f.stop_paper()
        fake.stop()


def test_self_logout_waits_for_backend_not_just_python_future_cancel(tmp_path):
    fake = _SyntheticLlamaServer()
    fake.release.clear()
    endpoint = fake.start()
    f = ResidentFixture(tmp_path, 2, cognitive_work=True)
    lane = _attach(f, endpoint)

    async def scenario():
        for sid in f.names:
            await f.bridge.login(sid)
        tok = lane.submit(
            "S000", work_ref="slow-llm",
            request=_request("slow-open"), mode=CognitionMode.OPEN,
        )
        assert await asyncio.to_thread(fake.entered.wait, 3.0)
        # Physical Action and cognition fences close before backend wait.
        f.bridge.quarantine("S000")
        with pytest.raises(ResidentGpuLaneError, match="still active"):
            await lane.retire_self("S000", timeout_s=0.02)
        assert f.lifecycle.view("S000").status is Presence.QUARANTINED
        assert f.physical.resident_states["S000"] == "QUARANTINED"
        assert f.lifecycle.view("S001").status is Presence.ONLINE
        with f.physical.lease(
            self_id="S001",
            native_session_id=f.bridge.sessions["S001"].started.session_id,
            action_id="peer-physical-while-gpu-running", effect_family="EAT",
        ):
            pass
        f.owners["S001"].retain_memory(_memory("S001", "peer-while-gpu"))
        with pytest.raises(
            ResidentGpuLaneError, match="terminal|late",
        ):
            lane.result(tok)
        fake.release.set()
        # The original provider request must actually conclude before the
        # actor can be retired; the old result still has no authority.
        await f.bridge.logout("S000")
        assert lane.retired_clean("S000")
        with pytest.raises(ResidentGpuLaneError, match="late"):
            lane.result(tok)
        await f.bridge.logout("S001")

    try:
        asyncio.run(scenario())
    finally:
        fake.release.set()
        f.stop_paper()
        fake.stop()


def test_queued_other_self_can_logout_without_cancelling_active_owner(tmp_path):
    fake = _SyntheticLlamaServer()
    fake.release.clear()
    endpoint = fake.start()
    f = ResidentFixture(tmp_path, 2, cognitive_work=True)
    lane = _attach(f, endpoint)

    async def scenario():
        await f.bridge.login("S000")
        await f.bridge.login("S001")
        active = lane.submit(
            "S000", work_ref="active-A",
            request=_request("active-A"), mode=CognitionMode.OPEN,
        )
        assert await asyncio.to_thread(fake.entered.wait, 3.0)
        queued = lane.submit(
            "S001", work_ref="queued-B",
            request=_request("queued-B"), mode=CognitionMode.OPEN,
        )
        # B's job never started: a local Future.cancel is real queued-work
        # cancellation. A continues generating, so global /slots is busy.
        await f.bridge.logout("S001")
        assert lane.retired_clean("S001")
        receipt = lane.verified_retirement("S001")
        assert receipt.queued_cancelled_refs == ("queued-B",)
        assert receipt.backend_idle_checked is False
        assert receipt.vram_released is False
        assert f.lifecycle.view("S001").status is Presence.OFFLINE
        assert fake.active == 1
        assert fake.calls == ["fake-gemma"]
        with pytest.raises(ResidentGpuLaneError):
            lane.result(queued)
        fake.release.set()
        assert isinstance(await lane.await_result(active), ProviderExpression)
        await f.bridge.logout("S000")

    try:
        asyncio.run(scenario())
    finally:
        fake.release.set()
        f.stop_paper()
        fake.stop()


def test_inference_backend_remains_processing_after_http_response_fails_closed(
    tmp_path,
):
    fake = _SyntheticLlamaServer()
    fake.leave_busy = True
    endpoint = fake.start()
    f = ResidentFixture(tmp_path, 2, cognitive_work=True)
    lane = _attach(f, endpoint)

    async def scenario():
        await f.bridge.login("S000")
        await f.bridge.login("S001")
        ticket = lane.submit(
            "S000", work_ref="orphan-llm",
            request=_request("backend-misreported"), mode=CognitionMode.OPEN,
        )
        with pytest.raises(ResidentGpuLaneError, match="idle"):
            await lane.await_result(ticket)
        assert lane.uncertain
        with pytest.raises(ResidentGpuLaneError, match="fenced"):
            lane.submit(
                "S001", work_ref="never-admit-after-busy",
                request=_request("fresh"), mode=CognitionMode.OPEN,
            )
        with pytest.raises(ResidentGpuLaneError, match="not qualified"):
            await f.bridge.logout("S000")
        assert f.lifecycle.view("S000").status is Presence.QUARANTINED
        assert f.physical.resident_states["S000"] == "QUARANTINED"
        assert f.lifecycle.view("S001").status is Presence.ONLINE
        f.owners["S001"].retain_memory(_memory("S001", "world-keeps-going"))

    try:
        asyncio.run(scenario())
    finally:
        f.stop_paper()
        fake.stop()


def test_world_only_after_verified_llama_slot_retirement(tmp_path):
    from relay_self.world_only_owned_checkpoint_dev import (
        verify_world_only_generation,
    )

    fake = _SyntheticLlamaServer()
    endpoint = fake.start()
    f = ResidentFixture(tmp_path, 2, cognitive_work=True)
    lane = _attach(f, endpoint)
    store = tmp_path / "world-after-real-http-slot"
    store.mkdir()

    async def scenario():
        for sid in f.names:
            await f.bridge.login(sid)
        ticket = lane.submit(
            "S000", work_ref="world-only-probe",
            request=_request("last-llm"), mode=CognitionMode.OPEN,
        )
        await lane.await_result(ticket)
        for sid in f.names:
            await f.bridge.logout(sid)
        assert lane.require_world_idle().n_slots == 1

    try:
        asyncio.run(scenario())
        archive = WorldOnlyOwnedPaperCheckpoint(
            lifecycle=f.lifecycle, owned_paper=f.paper, store=store,
            issuer_quiescence=f.bridge.world_only_quiescence,
        ).cycle()
        assert verify_world_only_generation(
            archive.checkpoint_dir,
        )["owner_self_count"] == 0
        assert archive.new_world.epoch == 1
    finally:
        f.stop_paper()
        fake.stop()


def test_slot_witness_rejects_nonexclusive_backend_and_remote_sources(tmp_path):
    fake = _SyntheticLlamaServer()
    endpoint = fake.start()
    try:
        provider = LlamaCppRelayProvider(
            endpoint=endpoint, model="fake-gemma",
        )
        witness = LlamaCppSingleSlotWitness(
            provider=provider, backend_ref="local-fixture",
        )
        fake.extra_slots = True
        with pytest.raises(ResidentGpuLaneError, match="n_parallel"):
            witness.require_idle()
        fake.extra_slots = False
        assert witness.require_idle().n_slots == 1
        remote = LlamaCppRelayProvider(
            endpoint="http://192.0.2.1:9999/v1/chat/completions",
            model="fake-gemma",
        )
        with pytest.raises(ResidentGpuLaneError, match="loopback"):
            LlamaCppSingleSlotWitness(
                provider=remote, backend_ref="remote-no-source",
            )
    finally:
        fake.stop()
