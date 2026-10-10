# S60-B2 P0 implementation and future operator plan

Refs Issue #528; frozen [protocol v1](manifest.md). Additive instrument only;
S60-A/B1, S48/S53, S52/S57 and research lanes remain byte-identical. Draft
against B1, no merge/auto-merge/issue close. No model/GPU/Minecraft execution
is authorized by P0. See the manifest for exact source audit and trust matrix.

## Safe default

```bash
PYTHONPATH=.:src python3 -B -m adapters.mineflayer.s60b2_owned_backend_probe --plan
```

No arguments have the same behavior. Plan performs no config reads, hashing,
networking or subprocess calls. It reports P0_ONLY, zero launch/inference and
the unqualified physical dimensions. CI tests this path and deterministic
fake process/proc + real localhost HTTP only. CI green qualifies the apparatus
contracts at its exact head; it cannot qualify physical cancellation.

## Future P1 preparation (requires separate explicit operator approval)

Keep files outside Git on the operator's own Linux/WSL host. This runner
supports only the frozen binary/source/model pins. A different model or stock
build requires a newly frozen prospective version, not a hash override.

Private config JSON has exactly these fields; replace the path placeholders
locally, never upload the filled file or weights/prompt:

```json
{
  "binary": "/operator/private/llama-server",
  "gguf": "/operator/private/model.gguf",
  "source": "/operator/private/stock-source-checkout",
  "binary_sha256": "ad5d4787bc739ad88a55b614c18d29580b3ec071cad632edb0ebb42b89f78536",
  "model_sha256": "c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed",
  "source_commit": "e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d",
  "alias": "relay-self-s60b2-model",
  "port": 12345,
  "ctx_size": 4352,
  "gpu_layers": 50,
  "arm": "A",
  "prompt": "Operator selected bounded text that allows actual progress observation."
}
```

Explicit argv: binary, --model GGUF, --alias, --host 127.0.0.1, --port,
--ctx-size, --parallel 1, --n-gpu-layers, --slots. No shell or user extra flags.
Environment is only PATH=/usr/bin:/bin and LANG=C.UTF-8. Unsupported local
library/runtime arrangement fails closed; do not silently change environment
or retry. GPU/runtime/library identity and source-to-binary linkage must be
reviewed independently before approving P1; file hashes and build-info alone
do not establish a reproducible build or actual tensor placement.

After obtaining separate operator approval, a private approval JSON must have
exactly runner_head (current clean full Git HEAD), manifest_sha256 (v1 digest),
config_sha256 (SHA256 of exact private config FILE BYTES), arm (same selected
arm), operator_token (operator-selected unique 64 lowercase hex characters),
allow_model_gpu_launch=true, source_binary_mapping_reviewed=true,
prior_cleanup_confirmed=true, and evidence_root (absolute resolved new external
directory). These declarations are a local authorization record, not a remote
signature or adversarial security sandbox. Never fabricate approval during P0.
The grant is tied to one directory: using another directory rejects the grant,
and reusing its consumed directory fails even after preflight/spawn failure.
Deletion by an operator is outside the no-replay trust boundary; retain roots.

Only after that separate approval, the operator may opt in with --run,
--config private-config.json, --approval private-approval.json and --evidence
that exact fresh external directory. This document supplies no live invocation
with usable approval. Do not infer P1 authority from this plan or Issue #528.
Choose exactly one A/B/C arm per approval and process. D is deferred. Require
confirmed cleanup of each prior arm before any new approval; no chained arms,
automatic retry, adoption, restart, or attempt to release B1 unknown lease.

The runner reserves/flushes/fsyncs evidence before preflight and records the
one process invocation before spawn. It independently checks executable inode,
file fingerprints, command argv, PID starttime, exclusive listener inode, and
GGUF mapped device/inode before/after each stock slot read. Transport callbacks only append bounded scalar observations in memory;
ordered journal writes and process/slot filesystem checks run outside the
foreground event loop through awaited thread work. Observation elapsed time
and append elapsed time are distinguished for buffered transport/L0 records.
L0 callback itself performs no file I/O. Slot snapshots
strip all strings/content; only processing/task/progress scalars persist.
Healthy process and socket POST cannot produce NEW_INFERENCE_STARTED. Actual
busy slot with processed prompt or decoded tokens is required; a response too
fast to observe progress is UNDETERMINED. Source-supported server slot reports
still do not attest GPU state or signed model identity.

A naturally completed, framed B1 response provides provider terminal evidence.
B2 additionally requires the emitted stock model alias, usage object and exact
stock build fingerprint b10874-e2d2c0d6a; missing or different source metadata
fails closed. This narrows the probe only and never changes B1 semantics.
B keeps its stream through logical displacement and relies on unchanged B1/A
completion and stale fencing; if pending's 5s window expires, it is skipped.
C closes the exact client stream and retains the unknown lease. Subsequent
independent busy/idle reports do not mutate that lease, nor authorize reentry.
The CANCEL_UNCONFIRMED_BACKEND_BUSY receipt is logical S60 fallback even if
later server reports idle; BACKEND_BUSY_OBSERVED is a distinct server source.

L0 uses the existing BestEffortDisplacement.run_l0 callback seam and monotonic
entry/return receipts while L2 is in flight. The callback in first P1 is a
content-free scheduling marker, not an Action and not a Minecraft movement
outcome. The 0.1s ceiling measures this callback scheduling only; a slow
callback or busy/progress miss fails the arm without synthetic delay.

Raw backend logs are discarded. Sanitized events.jsonl is append-only,
failure-inclusive and bounded; summary.json is secondary. Client cleanup and
process TERM/forced KILL/exit are distinct receipt phases, never STOP ACK or
slot-reuse proof. Cancellation at process creation retains ownership before
cleanup. Unconfirmed process cleanup blocks further operator approvals.

## Validation and evidence ceiling

Tests exercise the actual A/B/C measurement routine with a barrier-controlled
stock-shape loopback server and accelerated explicit host clock, plus fake
/proc/PID/listener/model identities and fake process lifecycle. Fixtures use
synthetic paths/pins as test data, never real backend loading. Frozen B1/A
controls supply deadline/coalescing/causal revision and parser coverage.
Full pytest, Ruff, repository contracts, locked Node protocol and exact-head
push/PR CI must pass before claiming S60_B2_P0_OFFLINE_PREFLIGHT_QUALIFIED.

An initial offline test run was interrupted after 73 passing tests because
fake-server teardown waited for its live connections before releasing the
held backend. Python 3.12 Server.wait_closed waits for those connections.
The fixture now releases/cancels/joins owned handlers and closes streams
before waiting for listener closure. No physical attempt was made. The next completed run had 82 passes and four
assertion failures because a redaction metadata key contained the word
"private". Those assertions now check actual secret values/paths/diagnostics
rather than rejecting the metadata key. Acceptance criteria are unchanged.

P0-only ceiling: PHYSICAL_RUN_NOT_AUTHORIZED, BACKEND_STOP_UNCONFIRMED,
NO_SAME_PROCESS_SLOT_REUSE_PROOF, NO_GPU_PREEMPTION_CLAIM, NO_PRODUCTION_GO.
Physical selected-model compatibility, same-process stock endpoint provenance,
actual cancellation timing, safe re-admission/reconciliation (separate B3),
GPU compute/VRAM, hardware contention and Minecraft physical L0 are unqualified.
Future live completion returns P1_RECEIPTS_REVIEW_REQUIRED, never automatic
physical PASS or production GO.
