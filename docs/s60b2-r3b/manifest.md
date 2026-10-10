# S60-B2 R3-B0 prospective one-shot diagnostic Arm A live-gate freeze

Primary owner: RelaySelf Issue #563. Status: pre-implementation protocol v1.
This freeze is **offline preparation only**, not authorization for inference.

Base: R3-A Draft PR #558 exact HEAD
`82988fb889079ae8e420d76f4436fa9ff2b88397`.
Branch: `self/s60b2-r3b-diagnostic-live-gate-20261011`.
Target: `self/s60b2-r3-diagnostic-runner-20261010`.
Old R3-A/R2/B2/B1/A branches and first P1 Arm A evidence remain frozen.
Frozen B2 manuscript SHA256
`1ce5eefa1125d9701f0987cf2ea14489a6c978720f06d89bb3f5a1522560e07d`.
Owned stock source `e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d`,
binary `ad5d4787bc739ad88a55b614c18d29580b3ec071cad632edb0ebb42b89f78536`,
GGUF `c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`.
No native STOP patch or llama.cpp modification permitted.

## R3-B0 mission

Enable the already-qualified `R3DiagnosticTransport` observer in the actual
B2 `run`/CLI **only when an operator supplies a new explicit diagnostic
Arm A grant**. No GPU/GGUF/llama-server/Minecraft execution during B0.
Use the smallest prospective B2 runner change; keep legacy
`--plan` and ordinary `--run` behavior and R3-A `measure`
unchanged by default. No implicit env flags, monkeypatch, duplicated runner,
new scheduler or switch for B/C.

New mode can be `--diagnostic-arm-a`, accepted **only** together with
`--run`, Config.arm=A, and an independent exact local approval explicitly
binding: R3-B0 manifest digest and clean runner HEAD, base B2 manifest,
exact-byte config SHA256, Arm A, diagnostic mode true, reviewed
stock source/binary/runtime/libraries, previous cleanup, a unique 64-hex
operator token and a fresh external private evidence root. An old Arm A or
R3-A grant must not be usable for this mode. Both CLI and direct Python
run API must reject missing or malformed new grants *before* process launch.
No tool should invent filled private grant credentials for a live run.

Existing B2 `authorize` fail-closed gates (CI refusal, binary/model pins,
loopback port, single-slot, clean HEAD, model mmap, owned PID/starttime/argv
and listener, no retry, no adoption, safe cleanup) must remain in effect.
The implementation may introduce a new prospective grant schema but must
not turn a rejected existing grant into an implicit accepted one.
One Arm A, exactly once, no follow-on B/C, zero automatic retry.

Diagnosis is observation only. Durable journal events
`DIAG_<R2_ALLOWLIST_STAGE>` with generation and bounded monotonic time,
written off the foreground event loop via the R3-A observer. No prompts,
answer content, headers, HTTP body, exception text, private paths or
uncontrolled metadata. Max 64 diagnostic stage observations, and preserve
redacted failure evidence on interrupted fsync. Successful normal response
must have zero diagnostic failure, actual two complete accepted HTTP
inferences on same process before claiming a successful Arm A.
Unknown remains UNKNOWN; slot idle is not validated HTTP completion,
backend stop or release of B1 unknown lease.

## Required offline tests and gates

Use real R3-A `measure` path through the R3-B0 opt-in but only
synthetic process/proc/GGUF identities, fake local HTTP server, monkeypatches
limited to **test harness**. Test valid Arm A two starts and two completions
with no diagnostic failures, JSON/source/fingerprint/usage/schema/frame
failures with stage code and no next POST, truncated/timeout/refusal and
coarse unknown, L0 scheduling and independent slot accounting, fallback,
cleanup and journal redaction. Check both CLI and direct-API grants:
old/consumed grant, wrong HEAD/manifest/config/arm/token/root,
nonempty CI env, dirty checkout, port in use, same root replay.
Show ordinary legacy `--plan`, `--run` unchanged and no B/C diagnostics.
Verify exact manifest SHA256, Git blob, protected ancestors; run focused and
full pytest, Ruff, repository contracts, Node 22 protocol, exact-head push
and PR CI before declaring PASS. Keep CI incapable of a live run.

## Freeze/evidence ceiling

Commit this file alone before modifying source/tests. Publish commit, Git
blob and SHA256 in #563 and read back. Separate Draft PR target R3-A,
no merge. Any change to physical thresholds requires a new pre-results
freeze rather than rewriting this acceptance after tests.

Positive B0 ceiling:
`S60_B2_R3B_OFFLINE_LIVE_GATE_QUALIFIED`,
`PHYSICAL_R3B_NOT_YET_AUTHORIZED`,
`OLD_ARM_A_CAUSE_UNDETERMINED`, `NO_NEW_PHYSICAL_RUN`,
`NO_STOP_ACK`, `NO_SAME_PROCESS_SLOT_REENTRY_PROOF`,
`NO_PRODUCTION_GO`.

Physical R3-B1 must have **separate explicit user authorization** after B0
and new exact local grant binding the final runner HEAD/this manifest,
new port and root, independently reviewed provenance and cleanup.
