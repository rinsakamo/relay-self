# S60-B2 P0 frozen protocol v1

Prospective authority: Issue #528, user P0-only request. Freeze this file alone,
publish its SHA256, Git blob and commit to #528 and read back before code/tests.
Base B1 `66b8045fd2b47d9c35febb12c495379d1248bb4e`; A
`71d7daeaade1562a0f0c9684d18f88cc6383e7ff`; S57
`564b52cfead748258594be65927072489fee963d`. Protected main observed
`4348a614900c1d0828581a8eec2c523ba5ae237f`. Only additive B2 files,
Draft target B1. No merge, auto-merge, science subjects or Minecraft.

## Prospective stock version and source audit

Read-only local source HEAD `e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d`,
clean tracked tree. Build-info: build 10874, GNU 13.3.0 Linux x86_64.
Prospective binary measured SHA256
`ad5d4787bc739ad88a55b614c18d29580b3ec071cad632edb0ebb42b89f78536`.
Historical S57 model pin (operator must rehash selected bytes at P1):
`c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`.
No binary execution, including --help/--version: backend initialization could
access GPU. Build artifacts plus source are compatibility evidence, not an
independently reproducible source-to-executable attestation.

Source file SHA256 at the exact version:

| File | SHA256 |
| --- | --- |
| tools/server/server.cpp | a0b400372a697182fb552c946579f74e81a845aa6d37e4b40b978ff4be5e016c |
| tools/server/server-context.cpp | 6abaa516f75cc284503f1d694603eb350696b50054e5512f852e9295e8b172bd |
| tools/server/server-task.cpp | 0fd5c8df2525e61214986e8abe3fc4edbb92f5dd652c9c2bfd1bc2712218a585 |
| tools/server/server-http.cpp | fc9d307525d7db13fcee3d32e0d4587cbd2f3d93bcc70a86b2cedc16b336ce11 |
| tools/server/server-queue.cpp | 0e196113d16f130230d2cc0b232915e1f5b4f1dda184790afbfdc4986dd1fd58 |
| common/arg.cpp | bab0fa0fe008c964a8fcc8e91b5f08ad88f0aa454934c7eebbe1646bb1898471 |

server.cpp routes GET /health, GET /slots, POST /v1/chat/completions.
server-context.cpp get_health returns status=ok, not occupancy. get_slots
requires endpoint_slots, queues SLOT_GET and returns slot.to_json; optional
fail_on_no_slot gives an availability error, not GPU evidence. common/arg.cpp
supports --slots, --parallel, --n-gpu-layers; common.h defaults slots enabled.
Use explicit --slots. Slot JSON contains id, n_ctx, is_processing, id_task,
prompt counters and next_token.n_decoded; it ALSO contains prompt/generated
and params. Never persist raw slot JSON. Slot snapshots are server reports,
not hardware attestation. /metrics is optional, disabled without --metrics;
its availability counters are not hardware quiescence and are not used here.
server-task.cpp to_json_oaicompat_chat has model, usage, finish_reason,
optional timings/reasoning; use unchanged B1 framing/envelope validation.
server-http.cpp passes connection-closed callback; server-queue.cpp next
checks it on polling timeout and stop posts task cancel; server-context.cpp
CANCEL releases the matching slot in its task loop. Thus stock source has
best-effort disconnect cancellation, with no request STOP ACK or hardware
preemption proof. Continued generation AND eventual idle are possible
observations; source alone predicts neither actual timing nor physical result.
Unknown version/hash/source mapping or unsupported live slots =>
SLOT_IDLE_ATTESTATION_UNAVAILABLE, blocked/undetermined, no fallback.

## Frozen bounds and arm isolation

P0: default/no-argument --plan only, no file hashing, sockets or subprocesses.
--run needs separate local operator approval JSON binding exact clean runner
HEAD, manifest SHA256, private config SHA256 and selected arm. No environment
switch alone grants execution. Refuse CI. Config/approval <=8192 bytes each,
strict keys/duplicates/types; immutable known binary/model pins, model alias,
127.0.0.1 port 1025..65535, ctx 512..32768, layers 0..120, parallel=1.
Use argv vector, no shell, no inherited LLAMA_ARG/proxy/auth/env overrides;
no arbitrary CLI flags. Rehash files before spawn, check GGUF magic, refuse
occupied port. Preserve private paths/prompts locally; publish no such bytes.
Exclusive new evidence directory reserves exactly one launch durably before
process creation. Reuse/resume/replay prohibited, including a preflight failure.
No process adoption, no duplicate start, no automatic inference retry.

One independently approved arm per process/receipt root, one prescribed
repetition. Same PID/executable/starttime/listener and model mmap identity
throughout that arm. Separate fresh approved root/process for another arm;
previous unresolved cleanup blocks operator approval of a successor. Existing
S57 World launcher is NOT invoked. D is conditional future diagnostic only,
not automatically run and no idle-to-B1 lease reconciliation API is added.

Startup absolute timeout 90s, health sampling <=180 at 0.5s, each HTTP <=2s.
Arm absolute timeout 60s; stock B1 connect/read/whole 5/15/45s, max_tokens=256,
stream=false, temperature=0. Slot samples <=120 at >=0.25s, each <=2s and
131072 body bytes, 8192 headers via B1 framing parser. Pending wait 5s,
request absolute deadline arm end. No timing-only acceptance: actual busy or
progress must be seen before displacement; absent busy => UNDETERMINED.
L0 scheduling observation 0.1s ceiling from call to callback return; no
synthetic delay in P1, no physical World outcome claim. All deadlines use
monotonic time. Each event records phase, monotonic elapsed, generation or
bounded scalar facts, never prompt/output/exception details. <=256 events,
each <=2048 encoded bytes, append/flush/fsync before aggregate reporting.
Raw backend stdout/stderr discarded, not an unbounded tempfile. Cleanup only
owned process group: TERM then <=5s wait, KILL then <=5s wait if needed;
record forced exit separately, never interpret exit as per-request STOP.
Timeout, parser/provenance failure => terminate arm, no successor inference.
No leaked owned tasks/streams; retain reservation and failure receipts.

| Arm | Prescribed intervention and acceptance |
| --- | --- |
| A | L2 complete validated HTTP, independent busy/progress snapshot, L0 callback, then exactly one fresh admitted L1 in same process; full response and independent progress required for both. |
| B | Busy L2 logically displaced; non-terminating cancel callback keeps stream. Coalesce two urgent L1s, invoke L0 while pending; old complete response stale-rejected. Exactly one newest pending POST only if natural completion precedes its 5s wait/deadline. Otherwise bounded skip, no retry. |
| C | Busy L2 logically displaced, B1 closes stream; independent slot observation after close; pending L1 expires by 5s, no second POST, unknown lease retained even if independent slot later idle. Busy evidence yields BACKEND_BUSY_OBSERVED; idle only yields server-reported idle. Cancellation remains unconfirmed. |

## Trust roots: zero implication between levels

| Classification | Required direct source |
| --- | --- |
| HTTP_RESPONSE_OBSERVED | Complete framed validated B1 HTTP 200 only |
| TRANSPORT_DISCONNECTED | Exact client stream/task cleanup; no server inference conclusion |
| HOST_CANCEL_REQUESTED | Exact S60 owner receipt, logical request only |
| PROVIDER_TERMINAL_OBSERVED | Complete validated response, never error/cancel/health |
| BACKEND_BUSY_OBSERVED | Version-specific slots is_processing=true plus independently verified owned PID/starttime/exe/listener/model mapping at observation |
| SAME_PROCESS_SLOT_IDLE_OBSERVED | Same verified process and supported slots is_processing=false; no lease reconciliation |
| NEW_INFERENCE_STARTED | Own exclusive request plus transition to independently observed slot processing with task/progress counters; TCP POST is insufficient |
| NEW_INFERENCE_COMPLETED | That request's complete validated response |
| GPU_COMPUTE_QUIESCED | Separate actual hardware evidence, unavailable in this instrument |
| VRAM_RELEASED | Separate independent memory measurement, unavailable here |
| CANCEL_UNCONFIRMED_BACKEND_BUSY | S60 bounded pending expiry/unknown lease; logical fallback, not independent physical occupancy |
| UNDETERMINED | Missing/ambiguous evidence, unsupported parser/version, terminal failure |

No STOP ACK, slot release, GPU stop or VRAM release equivalence. No output to
Action/Learning. P1 receipts require provenance review; no production GO.

## Prospective offline validation

Deterministic fake process/proc identity and loopback HTTP, event barriers and
controlled monotonic clocks only. Normal completion; ignored cancel/stale
response; disconnect while independent backend remains busy; unsupported
slots; model/version/source/alias/hash mismatch; HTTP/parser negatives;
port refusal; no authorization/default plan/CI; shell-safe argv; deadlines;
coalescing; nonblocking L0; bounded files/tasks/process cleanup, forced exit
separate from stop, no replay/duplicate launch. Reuse frozen B1/A negative
controls without editing them. Run full pytest, Ruff, repository contracts,
locked Node 22 protocol, exact-head push AND Draft PR CI. CI runs only P0.

Final P0 ceiling if deterministic gates pass:
S60_B2_P0_OFFLINE_PREFLIGHT_QUALIFIED, PHYSICAL_RUN_NOT_AUTHORIZED,
BACKEND_STOP_UNCONFIRMED, NO_SAME_PROCESS_SLOT_REUSE_PROOF,
NO_GPU_PREEMPTION_CLAIM, NO_PRODUCTION_GO. P1 independently measured source
mapping, selected GGUF response compatibility, slot reentry, actual hardware
and physical Minecraft L0 remain unqualified. Threshold/protocol revision
requires a new separately recorded pre-results freeze, never edit this v1.
