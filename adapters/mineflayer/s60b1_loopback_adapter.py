"""S60-B1 opt-in async stock HTTP transport; client completion is not STOP ACK."""
from __future__ import annotations

import asyncio
import json
import math
import re
import socket
from asyncio import timeout
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from relay_self.best_effort_displacement import BestEffortDisplacement, ModelRequest
from relay_self.relay_engine import ProviderCallFacts


class TransportUnconfirmed(ValueError):
    """Sanitized failure: transport cannot establish provider completion."""


@dataclass(frozen=True, slots=True)
class LoopbackTransportConfig:
    """Explicit S57-compatible alias/port/one-slot binding, no process launch."""
    model: str
    port: int
    slots: int = 1
    max_tokens: int = 256
    connect_s: float = 5.0
    read_s: float = 15.0
    whole_s: float = 45.0

    def __post_init__(self) -> None:
        if (not isinstance(self.model, str)
            or not re.fullmatch(r"[a-zA-Z0-9_.:/-]{1,160}", self.model)
            or type(self.port) is not int or not 1025 <= self.port <= 65535
            or type(self.slots) is not int or self.slots != 1
            or type(self.max_tokens) is not int or not 1 <= self.max_tokens <= 1024
            or any(type(t) not in (int, float) or not math.isfinite(t) or not 0 < t <= 120
                   for t in (self.connect_s, self.read_s, self.whole_s))):
            raise TransportUnconfirmed("invalid explicit loopback bounds")

    @property
    def endpoint(self) -> str:
        return f"http://127.0.0.1:{self.port}/v1/chat/completions"

    @classmethod
    def from_owned_spec(cls, spec, **bounds) -> LoopbackTransportConfig:
        # No hash/file reads, health checks, process startup or model calls here.
        from adapters.mineflayer.s57_owned_llama_backend import OwnedBackendSpec
        if not isinstance(spec, OwnedBackendSpec):
            raise TransportUnconfirmed("separately bound S57 spec required")
        return cls(spec.alias, spec.port, slots=spec.inference_parallel, **bounds)


class _Completion(asyncio.Future):
    """Read/cancel surface only; transport owns the success transition."""
    def set_result(self, result) -> None:
        raise TransportUnconfirmed("transport-owned completion required")

    def set_exception(self, exception) -> None:
        raise TransportUnconfirmed("transport-owned completion required")


@dataclass(slots=True)
class _Attempt:
    request: ModelRequest
    future: _Completion
    task: asyncio.Task | None = None
    writer: asyncio.StreamWriter | None = None
    cancelled: bool = False


class LoopbackDisplacementAdapter:
    """One transport task, no pending workers, polling, retries or Action sinks.

    payload_for is a trusted nonblocking caller callback. Bind once to the exact
    S60-A owner constructed with this adapter's start/cancel callbacks. Failed
    attempts occupy this adapter forever; no force-release or reset API exists.
    """
    REQUEST_LIMIT = 65536
    RESPONSE_LIMIT = 131072  # S52 ceiling
    HEADER_LIMIT = 8192

    def __init__(self, config: LoopbackTransportConfig,
                 payload_for: Callable[[ModelRequest], Mapping[str, Any]]) -> None:
        if not isinstance(config, LoopbackTransportConfig) or not callable(payload_for):
            raise TransportUnconfirmed("explicit config and payload callback required")
        self._loop = asyncio.get_running_loop()
        self._config = config
        self._payload_for = payload_for
        self._owner: BestEffortDisplacement | None = None
        self._attempt: _Attempt | None = None
        self._closed = False
        self._receipts: deque[tuple[str, int]] = deque(maxlen=64)

    @property
    def config(self) -> LoopbackTransportConfig:
        return self._config

    @property
    def receipts(self) -> tuple[tuple[str, int], ...]:
        return tuple(self._receipts)

    @property
    def transport_tasks(self) -> int:
        return int(self._attempt is not None and self._attempt.task is not None
                   and not self._attempt.task.done())

    def _local(self) -> None:
        if asyncio.get_running_loop() is not self._loop:
            raise TransportUnconfirmed("same event loop required")

    def bind(self, owner: BestEffortDisplacement) -> None:
        self._local()
        if (self._owner is not None or not isinstance(owner, BestEffortDisplacement)
            or owner._loop is not self._loop
            or owner._start != self.start or owner._cancel != self.cancel):
            raise TransportUnconfirmed("exact S60 callback owner required")
        self._owner = owner

    def _record(self, event: str, attempt: _Attempt) -> None:
        self._receipts.append((event, attempt.request.generation))

    def _payload(self, request: ModelRequest) -> bytes:
        try:
            payload = self._payload_for(request)
            if not isinstance(payload, Mapping) or set(payload) != {
                "model", "messages", "temperature", "max_tokens", "stream",
            }:
                raise ValueError
            messages = payload["messages"]
            if (payload["model"] != self.config.model or payload["stream"] is not False
                or type(payload["max_tokens"]) is not int
                or not 1 <= payload["max_tokens"] <= self.config.max_tokens
                or type(payload["temperature"]) not in (int, float)
                or payload["temperature"] != 0
                or not isinstance(messages, (list, tuple)) or not 1 <= len(messages) <= 64):
                raise ValueError
            for message in messages:
                if (not isinstance(message, dict) or set(message) != {"role", "content"}
                    or message["role"] not in ("system", "user", "assistant")
                    or not isinstance(message["content"], str) or not message["content"].strip()
                    or len(message["content"]) > self.REQUEST_LIMIT):
                    raise ValueError
            raw = json.dumps(dict(payload), ensure_ascii=False, allow_nan=False).encode("utf-8")
            if len(raw) > self.REQUEST_LIMIT:
                raise ValueError
            return raw
        except Exception:
            raise TransportUnconfirmed("invalid bounded chat request") from None

    def start(self, request: ModelRequest) -> asyncio.Future:
        self._local()
        owner = self._owner
        previous = self._attempt
        if (self._closed or owner is None or owner.active is not request
            or request.context != owner.context
            or (previous is not None and (previous.request is request
                or not previous.future.done() or previous.future.cancelled()
                or previous.future.exception() is not None
                or previous.task is None or not previous.task.done()))):
            raise TransportUnconfirmed("exact active ticket and completed lease required")
        future = _Completion(loop=self._loop)
        attempt = _Attempt(request, future)
        self._attempt = attempt
        self._record("START_INVOKED", attempt)
        try:
            payload = self._payload(request)
        except TransportUnconfirmed:
            asyncio.Future.set_exception(future, TransportUnconfirmed("request unconfirmed"))
            return future
        attempt.task = self._loop.create_task(self._transport(attempt, payload))
        # Done callback also handles cancellation before the coroutine's first step.
        attempt.task.add_done_callback(lambda task: self._terminal(attempt, task))
        future.add_done_callback(lambda f: self._future_cancelled(attempt, f))
        return future

    def _future_cancelled(self, attempt: _Attempt, future: asyncio.Future) -> None:
        if future.cancelled():
            self._cancel(attempt)

    def cancel(self, request: ModelRequest) -> None:
        self._local()
        attempt = self._attempt
        if attempt is None or attempt.request is not request:
            raise TransportUnconfirmed("foreign cancellation forbidden")
        self._cancel(attempt)

    def _cancel(self, attempt: _Attempt) -> None:
        if attempt.cancelled or (attempt.future.done() and not attempt.future.cancelled()):
            return
        attempt.cancelled = True
        self._record("CLIENT_CANCEL_UNCONFIRMED", attempt)
        # Commit failure before cancelling transport. Neither is backend stop.
        if not attempt.future.done():
            asyncio.Future.set_exception(attempt.future, TransportUnconfirmed("client cancelled"))
        if attempt.writer is not None:
            attempt.writer.close()
        if attempt.task is not None:
            attempt.task.cancel()

    def _terminal(self, attempt: _Attempt, task: asyncio.Task) -> None:
        if not attempt.future.done():
            asyncio.Future.set_exception(attempt.future, TransportUnconfirmed("transport unconfirmed"))
        if not task.cancelled():
            task.exception()
        # Consume only error metadata to avoid orphan warnings; value remains transient.
        if not attempt.future.cancelled():
            attempt.future.exception()

    async def aclose(self) -> None:
        """Host cleanup only; permanently disables starts, never releases backend."""
        self._local()
        self._closed = True
        attempt = self._attempt
        if attempt is not None:
            self._cancel(attempt)
            if attempt.task is not None:
                await asyncio.gather(attempt.task, return_exceptions=True)

    async def _transport(self, attempt: _Attempt, payload: bytes) -> None:
        writer = None
        try:
            async with timeout(self.config.whole_s):
                async with timeout(self.config.connect_s):
                    reader, writer = await asyncio.open_connection(
                        "127.0.0.1", self.config.port, family=socket.AF_INET,
                        limit=self.HEADER_LIMIT + 1,
                    )
                attempt.writer = writer
                head = (
                    "POST /v1/chat/completions HTTP/1.1\r\n"
                    f"Host: 127.0.0.1:{self.config.port}\r\n"
                    "Content-Type: application/json\r\nAccept: application/json\r\n"
                    f"Content-Length: {len(payload)}\r\nConnection: close\r\n\r\n"
                ).encode("ascii")
                writer.write(head + payload)
                async with timeout(self.config.read_s):
                    await writer.drain()
                self._record("SOCKET_POST_SENT", attempt)
                body = await self._response(reader)
                value = self._validate_response(body, json.loads(payload)["max_tokens"])
                if attempt.cancelled or attempt.future.done():
                    return
                self._record("HTTP_COMPLETION_OBSERVED", attempt)
                asyncio.Future.set_result(attempt.future, value)
        except (Exception, asyncio.CancelledError):
            if not attempt.future.done():
                self._record("TRANSPORT_UNCONFIRMED", attempt)
                asyncio.Future.set_exception(attempt.future,
                                             TransportUnconfirmed("transport unconfirmed"))
        finally:
            # close is nonblocking. Do not await arbitrary peer shutdown or create
            # an additional cleanup worker; transport close is not backend idle.
            if writer is not None:
                writer.close()
            attempt.writer = None

    async def _read(self, reader: asyncio.StreamReader, size: int) -> bytes:
        async with timeout(self.config.read_s):
            return await reader.readexactly(size)

    async def _line(self, reader: asyncio.StreamReader) -> bytes:
        async with timeout(self.config.read_s):
            line = await reader.readuntil(b"\r\n")
        if len(line) > self.HEADER_LIMIT:
            raise TransportUnconfirmed("HTTP framing unconfirmed")
        return line

    async def _response(self, reader: asyncio.StreamReader) -> bytes:
        async with timeout(self.config.read_s):
            head = await reader.readuntil(b"\r\n\r\n")
        if len(head) > self.HEADER_LIMIT:
            raise TransportUnconfirmed("HTTP headers unconfirmed")
        lines = head[:-4].split(b"\r\n")
        if not re.fullmatch(rb"HTTP/1\.[01] 200 [\x20-\x7e]*", lines[0]):
            raise TransportUnconfirmed("HTTP status unconfirmed")
        headers = {}
        for line in lines[1:]:
            key, separator, value = line.partition(b":")
            if (not separator or not re.fullmatch(rb"[!#$%&'*+.^_`|~0-9A-Za-z-]+", key)
                or any(c < 32 or c > 126 for c in value)):
                raise TransportUnconfirmed("HTTP headers unconfirmed")
            key = key.lower()
            if key in headers:
                raise TransportUnconfirmed("duplicate HTTP header")
            headers[key] = value.strip().lower()
        if (headers.get(b"content-type") not in
            (b"application/json", b"application/json; charset=utf-8")
            or b"content-encoding" in headers):
            raise TransportUnconfirmed("HTTP encoding unconfirmed")
        length, transfer = headers.get(b"content-length"), headers.get(b"transfer-encoding")
        if length is not None and transfer is None:
            if not re.fullmatch(rb"[0-9]{1,6}", length) or int(length) > self.RESPONSE_LIMIT:
                raise TransportUnconfirmed("HTTP body bound unconfirmed")
            return await self._read(reader, int(length))
        if transfer != b"chunked" or length is not None:
            # Unframed EOF bodies intentionally fail closed.
            raise TransportUnconfirmed("HTTP body framing unconfirmed")
        body = bytearray()
        framing = 0
        chunks = 0
        while True:
            line = await self._line(reader)
            framing += len(line) + 2
            chunks += 1
            if (not re.fullmatch(rb"[0-9a-fA-F]{1,8}\r\n", line)
                or framing > self.HEADER_LIMIT or chunks > 1024):
                raise TransportUnconfirmed("chunk framing unconfirmed")
            size = int(line[:-2], 16)
            if size == 0:
                if await self._read(reader, 2) != b"\r\n":
                    raise TransportUnconfirmed("chunk trailer unconfirmed")
                return bytes(body)
            if len(body) + size > self.RESPONSE_LIMIT:
                raise TransportUnconfirmed("HTTP body bound unconfirmed")
            body.extend(await self._read(reader, size))
            if await self._read(reader, 2) != b"\r\n":
                raise TransportUnconfirmed("chunk framing unconfirmed")

    def _validate_response(self, body: bytes, max_tokens: int) -> str:
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError
                result[key] = value
            return result

        try:
            parsed = json.loads(body.decode("utf-8"), object_pairs_hook=unique,
                                parse_constant=lambda value: (_ for _ in ()).throw(ValueError()))
            if not isinstance(parsed, dict) or set(parsed) - {
                "id", "object", "created", "model", "choices", "usage", "system_fingerprint",
            }:
                raise ValueError
            if "model" in parsed and parsed["model"] != self.config.model:
                raise ValueError
            if ("id" in parsed and (not isinstance(parsed["id"], str) or not parsed["id"])):
                raise ValueError
            if "object" in parsed and parsed["object"] != "chat.completion":
                raise ValueError
            if "created" in parsed and (type(parsed["created"]) is not int or parsed["created"] < 0):
                raise ValueError
            if ("system_fingerprint" in parsed and parsed["system_fingerprint"] is not None
                and not isinstance(parsed["system_fingerprint"], str)):
                raise ValueError
            choices = parsed["choices"]
            if not isinstance(choices, list) or len(choices) != 1:
                raise ValueError
            choice = choices[0]
            if (not isinstance(choice, dict) or set(choice) - {"index", "message", "finish_reason"}
                or type(choice.get("index", 0)) is not int or choice.get("index", 0) != 0):
                raise ValueError
            message = choice["message"]
            if (not isinstance(message, dict) or set(message) - {"role", "content"}
                or message.get("role", "assistant") != "assistant"):
                raise ValueError
            answer = message["content"]
            if not isinstance(answer, str) or not answer.strip():
                raise ValueError
            finish = choice.get("finish_reason")
            if finish is not None and finish not in ("stop", "length"):
                raise ValueError
            usage = parsed.get("usage", {})
            if not isinstance(usage, dict) or set(usage) - {
                "prompt_tokens", "completion_tokens", "total_tokens",
            }:
                raise ValueError
            # Inherit S52 ProviderCallFacts validation and enforce request output bound.
            facts = ProviderCallFacts(max_tokens, usage.get("prompt_tokens"),
                                      usage.get("completion_tokens"), usage.get("total_tokens"),
                                      finish)
            if facts.completion_tokens is not None and facts.completion_tokens > max_tokens:
                raise ValueError
            if (all(k in usage for k in ("prompt_tokens", "completion_tokens", "total_tokens"))
                and all(usage[k] is not None for k in usage)
                and usage["total_tokens"] != usage["prompt_tokens"] + usage["completion_tokens"]):
                raise ValueError
            return answer.strip()
        except Exception:
            raise TransportUnconfirmed("completion envelope unconfirmed") from None
