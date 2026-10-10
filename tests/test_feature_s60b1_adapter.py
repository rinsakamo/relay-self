"""Event/barrier controlled real loopback HTTP, zero model/World processes."""
import asyncio
import json
from dataclasses import replace

import pytest

import adapters.mineflayer.s60b1_loopback_adapter as transport
from adapters.mineflayer.s60b1_loopback_adapter import (
    LoopbackDisplacementAdapter,
    LoopbackTransportConfig,
    TransportUnconfirmed,
)
from relay_self.best_effort_displacement import BestEffortDisplacement, DisplacementRejected
from relay_self.interruption_fence import CognitionContext, InterruptRejected
from relay_self.provenance import Provenance

CONTEXT = CognitionContext("offline-world", 3, 1, 2)
SOURCE = Provenance("admission", "offline")
PRIVATE = "private prompt /secret/path"


def payload():
    return dict(model="offline-model", messages=[dict(role="user", content=PRIVATE)],
                temperature=0, max_tokens=32, stream=False)


def envelope():
    return dict(model="offline-model", choices=[dict(index=0, finish_reason="stop",
                message=dict(role="assistant", content="transient-output"))],
                usage=dict(prompt_tokens=10, completion_tokens=3, total_tokens=13))


def response(body=None, *, status=200, chunked=False):
    if body is None:
        body = json.dumps(envelope()).encode()
    if chunked:
        framing = b"Transfer-Encoding: chunked\r\n"
        body = f"{len(body):x}\r\n".encode() + body + b"\r\n0\r\n\r\n"
    else:
        framing = f"Content-Length: {len(body)}\r\n".encode()
    return (f"HTTP/1.1 {status} Fixture\r\nContent-Type: application/json\r\n".encode()
            + framing + b"\r\n" + body)


class FakeHTTP:
    def __init__(self):
        self.posts = []
        self.arrived = asyncio.Queue()
        self.responses = []
        self.release = []
        self.finished = []
        self.tasks = set()
        self.writers = set()
        self.errors = []

    async def __aenter__(self):
        self.server = await asyncio.start_server(self.handle, "127.0.0.1", 0)
        self.port = self.server.sockets[0].getsockname()[1]
        return self

    async def handle(self, reader, writer):
        task = asyncio.current_task()
        self.tasks.add(task)
        self.writers.add(writer)
        try:
            head = await reader.readuntil(b"\r\n\r\n")
            assert head.startswith(b"POST /v1/chat/completions HTTP/1.1\r\n")
            length = next(int(x.split(b":")[1]) for x in head.split(b"\r\n")
                          if x.startswith(b"Content-Length:"))
            data = await reader.readexactly(length)
            number = len(self.posts)
            self.posts.append((head, json.loads(data)))
            self.release.append(asyncio.Event())
            self.finished.append(asyncio.Event())
            self.arrived.put_nowait(number)
            # Server keeps working even if caller cancels/closes its socket.
            await self.release[number].wait()
            if self.responses[number] is not None:
                writer.write(self.responses[number])
                try:
                    await writer.drain()
                except (ConnectionError, OSError):
                    pass
            self.finished[number].set()
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            self.errors.append(type(exc).__name__)
        finally:
            writer.close()
            await writer.wait_closed()
            self.writers.discard(writer)
            self.tasks.discard(task)

    async def next_post(self):
        return await asyncio.wait_for(self.arrived.get(), 2)

    async def __aexit__(self, *args):
        self.server.close()
        await self.server.wait_closed()
        for writer in self.writers:
            writer.close()
        remaining = list(self.tasks)
        for task in remaining:
            task.cancel()
        await asyncio.gather(*remaining, return_exceptions=True)
        assert not self.tasks and not self.writers
        assert not self.errors


class IgnoreCancel(LoopbackDisplacementAdapter):
    """Negative-control client: keep reading so complete stale 200 is observable."""
    def cancel(self, request):
        self._local()
        assert self._attempt.request is request
        lease = self._owner._active
        with pytest.raises(InterruptRejected):
            lease.fence.accept_l2_result(lease.ticket, self._owner.context)
        self._record("FIXTURE_CANCEL_IGNORED", self._attempt)


class Rig:
    def __init__(self, server, *, ignore=False, config=None, supplier=None):
        self.now = 0.0
        kind = IgnoreCancel if ignore else LoopbackDisplacementAdapter
        self.adapter = kind(config or LoopbackTransportConfig("offline-model", server.port),
                            supplier or (lambda request: payload()))
        self.owner = BestEffortDisplacement(CONTEXT, "admission", self.adapter.start,
                                           self.adapter.cancel, lambda: self.now)
        self.adapter.bind(self.owner)

    def submit(self, *, priority=1, level="L1", deadline=20, budget=5):
        request = self.owner.admit(self.owner.context, level, priority, deadline, budget, SOURCE)
        self.owner.submit(request)
        return request

    async def terminal(self):
        attempt = self.adapter._attempt
        if attempt.task:
            await asyncio.wait_for(asyncio.shield(attempt.task), 2)
        assert attempt.future.done()

    def events(self):
        return [r.event for r in self.owner.receipts]

    def assert_sanitized(self):
        text = repr(self.owner.receipts) + repr(self.adapter.receipts)
        assert "private" not in text and "/secret" not in text and "transient-output" not in text
        assert not {"BACKEND_IDLE", "STOP_ACK", "GPU_RELEASED"} & set(self.events())


def test_held_cancel_ignored_priority_coalescing_l0_then_complete_stale_and_next_post():
    async def scenario():
        async with FakeHTTP() as server:
            server.responses = [response(), response(chunked=True)]
            rig = Rig(server, ignore=True)
            old = rig.submit(level="L2")
            assert await server.next_post() == 0
            future = rig.adapter._attempt.future
            first_task = rig.adapter._attempt.task
            assert future.get_loop() is asyncio.get_running_loop()
            a = rig.submit(priority=3)
            rig.submit(priority=2)
            assert rig.owner.pending is a
            latest = rig.submit(priority=3)
            for _ in range(100):
                latest = rig.submit(priority=4)
            assert rig.owner.active is old and rig.owner.pending is latest
            assert rig.adapter.transport_tasks == 1 and rig.adapter._attempt.task is first_task
            assert len(server.posts) == 1 and not future.done()
            ran = []

            async def l0():
                assert not server.finished[0].is_set()
                ran.append("independent callback")

            receipt = await rig.owner.urgent_l0(CONTEXT, l0)
            assert ran == ["independent callback"] and receipt.l0_completed
            assert not receipt.backend_stopped and not receipt.gpu_released
            assert rig.events().index("DISPLACED") < rig.events().index("HOST_CANCEL_REQUESTED")
            server.release[0].set()
            await rig.terminal()
            assert rig.owner.tick() is None
            assert "STALE_REJECTED" in rig.events()
            assert rig.owner.active is latest
            assert await server.next_post() == 1
            assert rig.adapter._attempt.future is not future
            assert len(server.posts) == 2 and rig.adapter.transport_tasks == 1
            server.release[1].set()
            await rig.terminal()
            result = rig.owner.tick()
            assert result.request is latest and result.value == "transient-output"
            assert rig.owner.tick() is None
            assert len(server.posts) == 2 and rig.adapter.transport_tasks == 0
            assert len(rig.owner.receipts) <= 64
            rig.assert_sanitized()
            await rig.adapter.aclose()
    asyncio.run(scenario())


def test_disconnect_cancel_is_unknown_while_server_continues_and_pending_expires():
    async def scenario():
        async with FakeHTTP() as server:
            server.responses = [response()]
            rig = Rig(server)
            old = rig.submit(level="L2")
            await server.next_post()
            future = rig.adapter._attempt.future
            urgent = rig.submit(priority=2)
            assert not server.finished[0].is_set()
            assert future.done() and isinstance(future.exception(), TransportUnconfirmed)
            await rig.terminal()
            rig.adapter.cancel(old)  # idempotent, no second task or signal
            assert rig.owner.tick() is None
            assert rig.owner.active is old and rig.owner.pending is urgent

            async def l0():
                return "UNKNOWN"
            assert await rig.owner.run_l0(l0) == "UNKNOWN"
            rig.now = 5
            assert rig.owner.tick() is None
            assert rig.owner.pending is None and rig.owner.active is old
            assert "CANCEL_UNCONFIRMED_BACKEND_BUSY" in rig.events()
            assert len(server.posts) == 1
            server.release[0].set()
            await asyncio.wait_for(server.finished[0].wait(), 2)
            assert rig.owner.tick() is None and len(server.posts) == 1
            assert "BACKEND_COMPLETION_OBSERVED" not in rig.events()
            assert rig.adapter.transport_tasks == 0
            rig.assert_sanitized()
            await rig.adapter.aclose()
    asyncio.run(scenario())


BAD_HTTP = [
    response(status=204), response(status=302), response(status=429), response(status=503),
    response(b"not json"), response(b"[]"), response(b'{"choices": []}'),
    b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 1000\r\n\r\n{}",
    response()[:-4],
    b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nTransfer-Encoding: chunked\r\n\r\n8\r\n{}",
    response(chunked=True)[:-5],
    b"HTTP/1.1 200 OK\r\nX-Huge: " + b"x" * 9000 + b"\r\n\r\n",
    b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 131073\r\n\r\n",
    response(b"x" * 131073),
    b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nTransfer-Encoding: chunked\r\n\r\n20001\r\n",
    response().replace(b"Content-Length:", b"Content-Length: 2\r\nContent-Length:"),
    response().replace(b"Content-Length:", b"Transfer-Encoding: chunked\r\nContent-Length:"),
    response().replace(b"application/json", b"text/html"),
    response().replace(b"Content-Type:", b"Content-Encoding: gzip\r\nContent-Type:"),
    response().replace(b"Content-Length:", b" Bad-fold: yes\r\nContent-Length:"),
    b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{}",
    b"HTTP/1.1 100 Continue\r\n\r\n" + response(),
    response(chunked=True).replace(b"0\r\n\r\n", b"0\r\nX-Trailer: foreign\r\n\r\n"),
    response(b'{"choices":[],"choices":[]}'), response(b'{"choices":NaN}'),
]


@pytest.mark.parametrize("wire", BAD_HTTP)
def test_http_negative_controls_fail_closed_no_next_post(wire):
    async def scenario():
        async with FakeHTTP() as server:
            server.responses = [wire]
            rig = Rig(server, ignore=True)
            old = rig.submit(level="L2")
            await server.next_post()
            rig.submit(priority=2)
            server.release[0].set()
            await rig.terminal()
            assert isinstance(rig.adapter._attempt.future.exception(), TransportUnconfirmed)
            assert rig.owner.tick() is None and rig.owner.active is old
            assert "PROVIDER_UNCONFIRMED" in rig.events()
            rig.now = 5
            rig.owner.tick()
            assert rig.owner.pending is None and len(server.posts) == 1
            assert "CANCEL_UNCONFIRMED_BACKEND_BUSY" in rig.events()
            assert "BACKEND_COMPLETION_OBSERVED" not in rig.events()
            rig.assert_sanitized()
            await rig.adapter.aclose()
    asyncio.run(scenario())


@pytest.mark.parametrize("change", [
    {"model": "foreign"}, {"choices": [{"message": {"content": ""}}]},
    {"choices": [{"message": {"content": "x", "tool_calls": []}}]},
    {"choices": [{"message": {"content": "x", "role": "user"}}]},
    {"choices": [{"message": {"content": "x"}, "index": True}]},
    {"choices": [{"message": {"content": "x"}, "finish_reason": "tool_calls"}]},
    {"choices": [{"message": {"content": "x"}}, {"message": {"content": "x"}}]},
    {"usage": {"completion_tokens": 33}}, {"usage": {"completion_tokens": -1}},
    {"usage": {"prompt_tokens": True}}, {"usage": "bad"},
    {"usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 8}},
    {"unknown": PRIVATE}, {"created": True}, {"object": "foreign"}, {"id": []},
])
def test_response_contract_rejects_foreign_unbounded_or_unknown_shape(change):
    value = envelope()
    value.update(change)
    test_http_negative_controls_fail_closed_no_next_post(response(json.dumps(value).encode()))


@pytest.mark.parametrize("field", ["world_seq", "intent_revision", "retained_revision", "session_id"])
def test_context_change_stale_socket_completion_never_action_learning(field):
    async def scenario():
        async with FakeHTTP() as server:
            server.responses = [response()]
            rig = Rig(server, ignore=True)
            rig.submit(level="L2")
            await server.next_post()
            rig.submit(priority=2)
            current = replace(CONTEXT, **{field: "new" if field == "session_id"
                              else getattr(CONTEXT, field) + 1})
            rig.owner.observe(current)
            assert rig.owner.pending is None
            server.release[0].set()
            await rig.terminal()
            assert rig.owner.tick() is None and rig.owner.active is None
            assert "STALE_REJECTED" in rig.events() and len(server.posts) == 1
            await rig.adapter.aclose()
    asyncio.run(scenario())


@pytest.mark.parametrize("order", ["cancel_first", "completion_first", "expiry_first"])
def test_cancel_completion_and_expiry_races(order):
    async def scenario():
        async with FakeHTTP() as server:
            server.responses = [response(), response()]
            rig = Rig(server, ignore=order == "expiry_first")
            old = rig.submit(level="L2")
            await server.next_post()
            if order == "completion_first":
                server.release[0].set()
                await rig.terminal()
            pending = rig.submit(priority=2)
            if order == "cancel_first":
                await rig.terminal()
                server.release[0].set()
            if order == "expiry_first":
                rig.now = 5
                server.release[0].set()
                await rig.terminal()
            assert rig.owner.tick() is None
            if order == "completion_first":
                assert rig.owner.active is pending
                assert await server.next_post() == 1
                server.release[1].set()
                await rig.terminal()
                assert rig.owner.tick().request is pending
            elif order == "cancel_first":
                assert rig.owner.active is old and len(server.posts) == 1
            else:
                assert rig.owner.active is None and rig.owner.pending is None
                assert len(server.posts) == 1 and "PENDING_EXPIRED" in rig.events()
            await rig.adapter.aclose()
    asyncio.run(scenario())


def test_false_completion_foreign_duplicate_ticket_and_client_future_cancel():
    async def scenario():
        async with FakeHTTP() as server:
            server.responses = [response()]
            rig = Rig(server)
            old = rig.submit(level="L2")
            await server.next_post()
            future = rig.adapter._attempt.future
            for ticket in (old, replace(old)):
                with pytest.raises(TransportUnconfirmed):
                    rig.adapter.start(ticket)
            with pytest.raises(TransportUnconfirmed):
                rig.adapter.cancel(replace(old))
            with pytest.raises(TransportUnconfirmed):
                future.set_result("false local success")
            with pytest.raises(TransportUnconfirmed):
                future.set_exception(RuntimeError(PRIVATE))
            future.cancel()
            # Let the Future's cancellation callback close the exact stream.
            await asyncio.sleep(0)
            await rig.terminal()
            rig.submit(priority=2)
            assert rig.owner.tick() is None and rig.owner.active is old
            assert len(server.posts) == 1 and future.cancelled()
            assert rig.adapter.transport_tasks == 0
            await rig.adapter.aclose()
    asyncio.run(scenario())


@pytest.mark.parametrize("scope", ["read", "whole", "connect"])
def test_deterministically_expired_transport_timeout_is_unknown(monkeypatch, scope):
    async def scenario():
        scopes = []
        real_timeout = asyncio.timeout

        def capture(delay):
            context = real_timeout(delay)
            scopes.append((delay, context))
            return context
        monkeypatch.setattr(transport, "timeout", capture)
        async with FakeHTTP() as server:
            server.responses = [response()]
            config = LoopbackTransportConfig("offline-model", server.port,
                                             connect_s=7, read_s=11, whole_s=17)
            rig = Rig(server, ignore=True, config=config)
            old = rig.submit(level="L2")
            if scope == "connect":
                real_open = asyncio.open_connection
                connect_entered = asyncio.Event()

                async def hold_open(*args, **kwargs):
                    connect_entered.set()
                    await asyncio.Event().wait()
                    return await real_open(*args, **kwargs)
                # No connection launched until task's first event-loop turn.
                monkeypatch.setattr(transport.asyncio, "open_connection", hold_open)
                await connect_entered.wait()
            else:
                await server.next_post()
            rig.submit(priority=2)
            duration = {"read": 11, "whole": 17, "connect": 7}[scope]
            selected = [c for d, c in scopes if d == duration and c.when() is not None]
            # Expire an actual asyncio timeout scope after an event barrier; no wall sleep.
            selected[-1].reschedule(asyncio.get_running_loop().time())
            await rig.terminal()
            assert isinstance(rig.adapter._attempt.future.exception(), TransportUnconfirmed)
            assert rig.owner.tick() is None and rig.owner.active is old
            rig.now = 5
            rig.owner.tick()
            assert rig.owner.pending is None
            assert len(server.posts) == (0 if scope == "connect" else 1)
            assert "BACKEND_COMPLETION_OBSERVED" not in rig.events()
            await rig.adapter.aclose()
    asyncio.run(scenario())


@pytest.mark.parametrize("mode", ["task_cancel", "stream_close", "server_disconnect", "prestart_cancel"])
def test_client_and_server_close_or_task_cancel_are_never_completion(mode):
    async def scenario():
        async with FakeHTTP() as server:
            server.responses = [None]
            rig = Rig(server, ignore=True)
            old = rig.submit(level="L2")
            if mode != "prestart_cancel":
                await server.next_post()
            if mode in ("task_cancel", "prestart_cancel"):
                rig.adapter._attempt.task.cancel()
                await asyncio.sleep(0)
                await asyncio.sleep(0)
            elif mode == "stream_close":
                rig.adapter._attempt.writer.close()
            else:
                server.release[0].set()
            task = rig.adapter._attempt.task
            await asyncio.gather(task, return_exceptions=True)
            await asyncio.sleep(0)
            assert rig.adapter._attempt.future.done()
            assert isinstance(rig.adapter._attempt.future.exception(), TransportUnconfirmed)
            rig.submit(priority=2)
            assert rig.owner.tick() is None and rig.owner.active is old
            assert len(server.posts) <= 1
            await rig.adapter.aclose()
    asyncio.run(scenario())


@pytest.mark.parametrize("change", [
    {"model": "foreign"}, {"stream": True}, {"max_tokens": 1025}, {"max_tokens": True},
    {"temperature": 1}, {"messages": []}, {"messages": [{"role": "tool", "content": "x"}]},
    {"messages": [{"role": "user", "content": "x" * 65537}]},
    {"api_key": PRIVATE}, {"messages": [{"role": "user", "content": ""}]},
])
def test_invalid_payload_never_creates_transport_task(change):
    async def scenario():
        async with FakeHTTP() as server:
            data = payload()
            data.update(change)
            rig = Rig(server, supplier=lambda request: data)
            old = rig.submit()
            assert rig.adapter.transport_tasks == 0
            assert rig.owner.tick() is None and rig.owner.active is old
            assert not server.posts
            rig.assert_sanitized()
            await rig.adapter.aclose()
    asyncio.run(scenario())


@pytest.mark.parametrize("change", [
    {"port": 1024}, {"port": 65536}, {"port": True}, {"slots": 2}, {"slots": True},
    {"model": "host\r\ninjection"}, {"model": ""}, {"max_tokens": True},
    {"read_s": float("nan")}, {"whole_s": float("inf")}, {"connect_s": 0},
])
def test_config_rejects_nonloopback_or_unbounded_binding(change):
    args = dict(model="offline-model", port=12345)
    args.update(change)
    with pytest.raises(TransportUnconfirmed):
        LoopbackTransportConfig(**args)


def test_l0_unknown_errors_propagate_while_socket_is_held_no_retry():
    async def scenario():
        async with FakeHTTP() as server:
            server.responses = [response()]
            rig = Rig(server, ignore=True)
            rig.submit(level="L2")
            await server.next_post()
            calls = []

            async def unknown():
                calls.append("unknown")
                return "UNKNOWN"

            async def fail():
                calls.append("error")
                raise RuntimeError("UNKNOWN")

            assert await rig.owner.run_l0(unknown) == "UNKNOWN"
            with pytest.raises(DisplacementRejected):
                await rig.owner.urgent_l0(CONTEXT, unknown)
            with pytest.raises(RuntimeError):
                await rig.owner.run_l0(fail)
            assert calls == ["unknown", "unknown", "error"]
            assert "L0_COMPLETED" not in rig.events()
            assert not server.finished[0].is_set() and len(server.posts) == 1
            await rig.adapter.aclose()
    asyncio.run(scenario())


def test_refused_socket_is_unknown_and_environment_not_consulted(monkeypatch):
    async def scenario():
        async with FakeHTTP() as server:
            port = server.port
        monkeypatch.setenv("OPENAI_BASE_URL", "https://foreign.invalid")
        monkeypatch.setenv("OPENAI_API_KEY", PRIVATE)
        monkeypatch.setenv("http_proxy", "https://foreign.invalid")
        rig = Rig(server, config=LoopbackTransportConfig("offline-model", port))
        old = rig.submit()
        await rig.terminal()
        assert isinstance(rig.adapter._attempt.future.exception(), TransportUnconfirmed)
        assert rig.owner.tick() is None and rig.owner.active is old
        assert not server.posts
        await rig.adapter.aclose()
    asyncio.run(scenario())


def test_binding_is_exact_single_owner_and_closed_adapter_cannot_restart():
    async def scenario():
        async with FakeHTTP() as server:
            rig = Rig(server)
            with pytest.raises(TransportUnconfirmed):
                rig.adapter.bind(rig.owner)
            other = LoopbackDisplacementAdapter(rig.adapter.config, lambda request: payload())
            with pytest.raises(TransportUnconfirmed):
                other.bind(rig.owner)
            await other.aclose()
            await rig.adapter.aclose()
            rig.submit()
            assert "PROVIDER_UNCONFIRMED" in rig.events() and not server.posts
    asyncio.run(scenario())
