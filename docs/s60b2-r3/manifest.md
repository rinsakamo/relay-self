# S60-B2 R3-A — prospective diagnostic-runner integration v1

Authority: RelaySelf Issue #557. This is an implementation-before-tests
freeze, NOT a qualification result or permission for another physical run.

Exact parent: R2 Draft #555 at
`66afcc2017d12b760e21539bf698baf176d3dd68`.
Branch: `self/s60b2-r3-diagnostic-runner-20261010`.
Target: R2 Draft branch `self/s60b2-r2-offline-20261010`.
Historical B2 P0 #542, R2 #555, S60-B1 #523, S60-A #507 and the actual
P1 Arm A receipt in Issue #528 remain immutable as independent evidence.
Neither main nor the protected historical branches may be changed.

## Scientific/engineering question

Can a diagnostic observer be connected to the REAL B2 measurement function
(in simulated offline invocation) without changing the default success,
failure, cancellation, stale-rejection, single-slot, L0 or lease semantics?
The historical Arm A failure stage is not retrospectively recoverable.

## Narrow code change

B2 `measure` currently directly chooses `MeasuredTransport` for A/C and
`KeepStream` for B. Authorize a **prospective new R3 version** of this file,
with the smallest explicit typed/keyword-only observer injection seam. Default
without injection must keep the old behavior and the original exact
`a378d4d...` source remains frozen in its historical commit. Reject
diagnostic injection for B/C; first slice covers Arm A only.
Do not monkeypatch global module symbols, shadow imports, fork the full
measurement loop, or touch S60-A/B1/S48/S53/S57.

Use an R3-specific observer adapted from the qualified R2
`OfflineDiagnosticTransport` stage/classification semantics. It must
delegate all acceptance to the inherited frozen B1/B2 parser and never
override Future success, retry, slot-idle retirement or Action/Learning.
R2 was explicitly offline-only; its original file remains unchanged.
This R3 version is also offline-only until independent R3-B authorization.

## Diagnostics: strictly informational

Allowed stage names: HTTP_READ_OR_FRAMING_UNCONFIRMED,
JSON_DECODE_FAILURE, MODEL_OR_FINGERPRINT_MISMATCH,
USAGE_ENVELOPE_UNCONFIRMED, SCHEMA_UNCONFIRMED,
CLIENT_CANCEL_OR_UNKNOWN, TRANSPORT_PRE_RESPONSE_UNKNOWN,
TRANSPORT_STAGE_UNKNOWN. Do not claim finer source detail.
Issue only `DIAG_<ALLOWLIST_STAGE>` event phase and numeric generation
(plus bounded monotonic scalar time only when proven correctly relative
to journal start). Existing B2 `Journal.emit` accepts bounded uppercase
phase names and numeric scalar facts; do not enlarge its permitted arbitrary
strings. Append/fsync diagnostic receipts strictly outside foreground
start/cancel/HTTP callbacks. No prompts, response body, response/header
values, exception text, model text, token sequence, private paths, approval
bytes or bearer data in receipts/CI. Limit to 64 diagnostic receipts per
attempt, preserve chronological failure evidence, no success fabrication.
Unknowns must remain UNKNOWN.

## Offline verification required

Use controlled localhost fake stock HTTP server and synthetic /proc/slot/
process identity. Invoke the B2 `measure` path (not only the standalone R2
class). Compare the exact same fixtures with and without injection:

- valid 200, true old completion and one latest newly admitted request:
  identical Action/Learning-free result, no diagnostic failure;
- rejected model/fingerprint, usage, malformed JSON, schema, partial framing,
  connection refusal, cancellation and timeout: identical blocked/unknown
  lease, no extra transport, bounded allowlisted diagnostic;
- independent L0 callback in flight and slot/progress accounting unchanged;
- Arm B/C default path unchanged, no diagnostics or cross-arm state;
- no foreground blocking file IO, bounded diagnostic queue and redaction;
- exact-head identity, port/cleanup/approval fail-closed behavior, no
  accidental physical execution or retroactive qualification.

Run focused and full pytest, Ruff, repository contracts, Node 22 adapter
protocol, exact-head push AND Draft PR CI. Record any red attempts; do not
rewrite this pre-results manifest acceptance after seeing outcomes.

## Evidence boundary

Positive R3-A ceiling:
`S60_B2_R3_DIAGNOSTIC_RUNNER_OFFLINE_QUALIFIED`.
Always `NO_NEW_PHYSICAL_RUN`, `ARM_A_CAUSE_STILL_UNDETERMINED`,
`NO_STOP_ACK`, `NO_SAME_PROCESS_SLOT_REENTRY_PROOF`,
`NO_PRODUCTION_GO`.

A NEW explicit exact-head local operator approval, R3-B prospective protocol,
pin/hardware mapping and new external evidence root will be required BEFORE
any re-run of Arm A on WSL2. Previous Arm A grant is consumed. No Arm B/C,
Minecraft, native llama.cpp modification or GPU-preemption proof authorized.
