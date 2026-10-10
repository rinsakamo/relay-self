# S60-B1 offline validation record

Frozen manifest-only commit: 9b7481d20ba72985443533c252374c3c0872636f.
Blob: 965a76c8205c36e7e352b072f47c01456fcd36ad.
SHA256: 68e7983c06e4501cab519a0c55fe0f9e14ef336058310191e22891f0d016b739.
Posted/read back on #514 comment 6095674798 before implementation/test writes.
All code is additive to 71d7daeaade1562a0f0c9684d18f88cc6383e7ff.

## Transparent fixture repairs

Initial implementation/test snapshot retained in d18778f26fa96f51b8dd142d8071178bd2b69fd1.
First focused invocation was terminated while fixture teardown waited for
open clients: the initiating assertion looked for DISPLACED after 100 queued
replacements had evicted it from the frozen 64-receipt ring. Diagnostic
stack inspection reproduced that assertion and the Python 3.12 server close
wait. Move ordering assertion before history eviction, close/cancel fake
connections before server.wait_closed. Next complete focused run: 1 failed,
116 passed (0.43s); fixture registry cleanup was interrupted by task cancellation
inside writer.wait_closed. Protect registry removal with finally. Subsequent
run: 117 passed (0.36s). These are test-fixture defects; no acceptance limit or
frozen predecessor changed. Extra stock metadata/foreign Future controls then
passed with 128 focused tests (93 B1 + 35 S60-A, preliminary 0.37s).

## Controls and interpretation

All positive/negative transport controls use real ephemeral loopback TCP to
asyncio.start_server, never model/GPU/Minecraft/llama-server. Held-handler and
arrival/release barriers prove ordering without a latency threshold. Clock
injection controls pending expiry; captured real asyncio timeout scopes are
explicitly expired after barriers for connect/read/whole-call controls.
Two-second wait_for guards are failure guards only, never acceptance latency.

Positive: held old POST, cancellation deliberately ignored by a test adapter,
independent L0, one active/one newest priority pending, complete valid old 200,
stale rejection, then exactly one new POST and fresh transient result. Both
Content-Length and complete chunked framing succeed. Optional stock metadata
is validated and excluded from receipts. IgnoreCancel exists only in tests.

Negative: default client cancel/disconnect while server remains held, exactly
one POST, no backend completion, no successor, pending expiry. Tests also
cover 204/redirect/429/503; partial, oversized, malformed/duplicate HTTP and
JSON; unknown envelope/metadata; refusal; deterministic timeout; stream/task/
prestart/Future cancellation; false success injection; exact ticket identity;
foreign/replayed Futures at the unchanged S60 boundary; completion/cancel/
expiry races; World/intent/retained/session changes; L0 UNKNOWN/error; explicit
binding; bounded tasks/receipts; complete fake transport cleanup. Receipts
remain sanitized. Error paths retain the lease even after host task ends.

Required final gates: focused/full pytest, whole-repo Ruff, repository contracts,
Node 22 locked protocol/syntax, manifest digest/blob and unchanged predecessor
tree. Dedicated workflow s60b1-offline.yml checks out/asserts exact push or PR
head and runs all four jobs. Final HEAD and terminal CI URLs/counts are recorded
in #514 and the Draft PR after the workflow completes, avoiding a self-referential
final commit hash. No claim is final until those receipts are read back.

No physical stop, slot availability, GPU/VRAM, real-backend output/latency or
production acceptance is inferred from these offline controls. S60-B2 remains
deferred to separately authorized real hardware/World qualification.

Local Node install initially caused repository-contract Markdown scanning to
include third-party node_modules documentation and report broken links. Move
that generated dependency directory outside this isolated checkout after the
33-test Node check; repository contracts then pass. Frozen checker unchanged;
CI uses separate clean jobs for contracts and Node.

First completed local full regression (earlier source snapshot): 8 failed,
1762 passed in 262.70s. All eight failures are inherited S30 offline Node
subprocess tests: this shell had no node on PATH. An additional in-progress
full run with the same missing PATH was stopped after identifying the cause.
Use installed Node 22.22.2 nvm bin on PATH for the final regression; also add
explicit Node 22 setup to the dedicated pytest CI job. No Node options,
acceptance thresholds or predecessor tests are changed; no real Minecraft
process is launched by these offline test-only Node shims.
