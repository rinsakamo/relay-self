# S60-B1 opt-in localhost HTTP adapter

Authority: Issue #514 and frozen S60-A Draft #507. The adapter is additive:
S52, S57, S48, S53 and S60-A implementation bytes are unchanged. No launcher,
CLI, environment switch, Action sink, Learning sink or automatic promotion.

Construct `LoopbackDisplacementAdapter(config, payload_for)` in the foreground
asyncio loop. Construct `BestEffortDisplacement` with that adapter's bound
`start` and `cancel` methods, then call `adapter.bind(owner)` once. This explicit
binding checks exact callbacks and loop. `start` checks `owner.active is request`
and current context; copied/foreign/duplicate tickets cannot start transports.
Owner admission/submit remains the trusted source of tickets. This integration
uses the frozen owner's private callback/loop attributes for identity checks;
changes to that interface require fresh review. Python object access is not an
adversarial sandbox or independently authenticated backend identity.

Use immutable `LoopbackTransportConfig(model, port)` or
`LoopbackTransportConfig.from_owned_spec(spec)` to project a separately bound
S57 `OwnedBackendSpec` alias/port/one slot. Projection never reads/hashes files,
launches processes or sends health traffic. Offline fixtures supply explicit
synthetic binding values. This configuration does not attest an actual server
or replace B2 binary/GGUF/process admission. Only IPv4 `127.0.0.1`, port
1025-65535, plain HTTP, fixed `/v1/chat/completions` is implemented. No DNS,
proxy, redirects, auth, environment overrides, UDS, SSE or server cancel API.

`payload_for(request)` is an independently trusted **nonblocking** caller
callback invoked only when S60-A actually starts that exact request. It returns
model/messages/temperature=0/max_tokens/stream=False; no other request fields
are supported. Caller must retain at most the active/latest eligible pending
payload and discard superseded/expired/context-stale payloads. Prompts live
outside `ModelRequest` and receipts. The adapter snapshots/validates/encodes
payload before the first await, never calls S52 synchronous urllib and creates
one transport task per started lease; pending has zero workers. Callback trust
and host tick cadence remain explicit integration requirements, not measured
physical event-loop latency guarantees.

Bounds: 64 messages, 65536 combined content characters and encoded request
bytes; 131072 response body bytes (S52 ceiling); 8192 aggregate HTTP header
bytes; 8192 chunk-framing bytes / 1024 chunks. Output budget 1-1024 tokens;
returned completion_tokens cannot exceed the actual request limit. Connect,
read/write-drain and whole-call scopes each have explicit finite 0-120 second
bounds; defaults 5/15/45 seconds. Whole-call timeout covers slow partial reads.
Length-delimited and strictly chunked HTTP/1.0-1.1 200 JSON responses are
supported; malformed/duplicate headers, conflicting framing, unsupported
encoding, trailers, unframed EOF bodies and interim responses fail closed.
No retries, polling or successor attempt on any ambiguous failure.

Only the transport owns Future success. Public `set_result`/`set_exception`
reject local false completion; caller Future cancellation is failure and closes
the associated task/stream. Idempotent `cancel(request)` targets object identity,
sets sanitized failure before nonblocking stream/task cancellation, and never
asserts backend stop. Cancelling before the transport coroutine's first step
also fails via its done callback. `aclose()` permanently disables starts and
joins only owned transport cleanup; it is not reconciliation or server stop.

A complete framed response is parsed/validated before success. The bounded
text-only envelope permits one assistant choice and stop/length finish reason;
model, choices, usage and optional metadata are validated when present.
S52 permits omitted model/usage/finish fields; B1 preserves those minimal
response semantics. Optional stock `prompt_tokens_details.cached_tokens`,
finite numeric `timings` and string `reasoning_content` are validated and
then discarded, as are IDs/fingerprints. Tools, non-null logprobs, unknown
shapes, verbose diagnostics and non-text messages are unsupported and fail
closed. Full HTTP success permits only a **next connection attempt**, never
independent physical slot-idle, same-process identity or STOP ACK evidence.

For optional stock metadata, the public ggml-org/llama.cpp source was inspected
at `1623d8ce47bc0bee9757068780c23ca7abd45160`:
`tools/server/server-task.cpp`, `server-common.cpp`, `common/chat.cpp`.
This static source check is not linkage to the S57 binary or physical model
compatibility qualification. No backend code is copied or modified.

S60-A fences old L2 before cancel. Complete late responses are stale-rejected
before a pending start; disconnect/timeouts/HTTP errors retain the unknown
lease, and bounded pending expiry emits CANCEL_UNCONFIRMED_BACKEND_BUSY.
Host services `tick()` and `observe()` for each causal revision. L0 runs the
existing separately authorized callback without awaiting HTTP; UNKNOWN and
exceptions remain unchanged. Transient `CognitiveResult` is never Action or
Learning authority. Generation/event-only receipt rings each cap at 64; no
prompt, output, exception details, auth or paths are published.

Offline-only ceiling: S60_B1_LOCALHOST_TRANSPORT_CONTRACT_OFFLINE_QUALIFIED
when all gates/CI pass; NO_REAL_LLAMA_OR_GPU_INFERENCE,
BACKEND_STOP_UNCONFIRMED, NO_PHYSICAL_SLOT_RELEASE_CLAIM, NO_PRODUCTION_GO.
Real llama.cpp/selected GGUF compatibility, same-process slot availability,
native cancellation, GPU/VRAM release, Minecraft and physical L0 latency
remain unqualified and require separate S60-B2 authority.
