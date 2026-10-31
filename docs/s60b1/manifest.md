# S60-B1 prospective offline transport manifest

Primary authority: Issue #514, read back 2026-10-10. S60-A Draft #507 is
OPEN/Draft at exact HEAD 71d7daeaade1562a0f0c9684d18f88cc6383e7ff.
Base and PR target: self/s60a-best-effort-displacement-20261010.
Adopted product decision: #417 comment 6090041172 (failed stop is tolerated).
S52 local_chat_provider.py and S57 s57_owned_llama_backend.py reviewed.
Main observed: 4348a614900c1d0828581a8eec2c523ba5ae237f; protected and untouched.
Independent branch: self/s60b1-loopback-adapter-20261010.

## Frozen scope and acceptance

Only new adapter, deterministic localhost TCP tests, integration/validation docs
and dedicated exact-head offline workflow. No edits to any predecessor file,
S60-A, main, Lane A/B/C/I1-I4 or RelayTheory/Paper2. No real GGUF, GPU,
Minecraft, llama-server or llama.cpp modification. No auto-merge or issue close.

Implement adapters/mineflayer/s60b1_loopback_adapter.py using standard-library
asyncio TCP and one task only per actually started active lease. Start returns a
unique same-loop exact-attempt Future synchronously. Cancel is idempotent,
nonblocking and exact-request scoped; client cancellation, stream close,
timeout and HTTP errors cannot resolve success or release the unknown lease.
Only a complete, validated HTTP 200 response permits S60-A to attempt another
connection. This is client-observed completion, never independent STOP ACK,
physical slot idle, GPU cessation or resource release.

Explicit immutable IPv4 loopback configuration, port 1025-65535, fixed
/v1/chat/completions path, single slot, S57-compatible alias. No ambient
credentials, DNS, proxies or redirects. Caller supplies a bounded request
separately from ModelRequest; validate model/messages/non-streaming/output
budget. Bound connect/read/whole-call time, request/body/header bytes and
HTTP framing; validate JSON model/choices/usage. Published receipts and errors
exclude prompts, outputs, paths and exception details. No Action/Learning sink.

Real fake-server TCP controls: held response with urgent invalidation preceding
cancel and independent L0; ignored cancel with full response releases only the
old provider lease and starts exactly one latest priority pending request;
disconnect while server continues leaves unknown lease, one POST, bounded
pending expiry. Negative controls include partial Content-Length/chunked,
oversized headers/body, malformed JSON/envelopes, 204/3xx/429/503, refusal,
timeout, local false completion, cancel/completion races, duplicate/foreign
requests/Futures, World/intent/retained changes, expiry-before-release,
priority/newest coalescing, L0 UNKNOWN/errors, bounded tasks/receipts/cleanup.
Use event/barrier control and injected scheduling clocks; no timing-only
physical latency inference. Acceptance and constraints remain frozen on repair.

Run focused S60-B1/S60-A and inherited full pytest, whole-repo Ruff,
repository contracts, locked Node 22 adapter syntax/protocol, manifest digest
and unchanged-predecessor checks, dedicated exact-head push AND PR CI.
Draft PR targets S60-A only; report all final-head terminal checks truthfully.

Ceiling if all gates pass: S60_B1_LOCALHOST_TRANSPORT_CONTRACT_OFFLINE_QUALIFIED,
NO_REAL_LLAMA_OR_GPU_INFERENCE, BACKEND_STOP_UNCONFIRMED,
NO_PHYSICAL_SLOT_RELEASE_CLAIM, NO_PRODUCTION_GO.
S60-B2 real backend, native stop, hardware resource and latency qualification
remain deferred to separate explicit authority.
