# S60-B2 R3-A implementation and evidence boundary

Primary authority: Issue #557; frozen manifest commit
`e0fad49ea86bf6f69bc2338a9b253153fa275d27` is unchanged.

`adapters/mineflayer/s60b2_owned_backend_probe.py` is explicitly a new
prospective R3 implementation version. Its only change is a keyword-only,
typed `measure(..., diagnostic_adapter=...)` seam accepting the exact R3
class for Arm A. No argument retains the original A/B/C adapter selection
and measurement loop. B/C and arbitrary adapter substitution are refused
before HTTP or file work. Historical commits retain their original bytes.

R3 inherits R2's observer classification and B1/B2's completion authority.
The original R2 file is unchanged. The R3 buffer retains the first 64
receipts, counts observations across drains per attempt generation, and
fails closed on overflow instead of rolling away early failure evidence.
Malformed receipts and failed writes remain pending and cannot fabricate
success. Cancellation during a diagnostic fsync waits for the committed
write and removes it once, so a later drain cannot replay it. Diagnostics
are flushed through B2 `durable_write` in worker threads outside start,
cancel, response/parser and L0 callbacks.

A diagnostic row contains only `DIAG_<R2 allowlisted stage>`, numeric
attempt generation, journal monotonic elapsed time and observation elapsed
time relative to the same journal. R2 millisecond resolution is retained;
no raw exception, body, header, token, prompt, model alias or private path
is emitted. A cancellation can produce two R2 observations (response
interception and inherited cancellation record); these are distinct
observations, not a replay or two attempts. Successful completion emits
no diagnostic failure.

## Offline verification

The new tests call actual B2 `measure` over barrier-controlled stock-shaped
localhost HTTP, comparing baseline and injected Arm A terminal/result,
non-diagnostic phase sequence, accounting and independent slot witness.
They cover valid fixed/chunked 200, JSON and duplicate/NaN decoding,
model/fingerprint, usage, schema, HTTP error/truncation, cancellation and
outer measurement timeout. Direct observer tests additionally exercise
HTTP read timeout and connection refusal. Inherited B2 tests retain
A/B/C, synthetic proc identity, L0, unknown lease, no successor after
failure, reservation/approval/CI/port refusal and owned cleanup coverage.
The protocol checks use Node 22.22.2; no Minecraft server is launched.

Early red attempts are disclosed: the first measurement fixture mixed an
accelerated B2 clock with R2's real monotonic clock and correctly failed
the diagnostic time gate; the revised fixture uses a real monotonic clock.
Another fixture initially expected one cancellation observation, whereas
R2 emits two. A buffer fixture's 50ms HTTP read deadline expired during
64 durable writes; its independent timeout was extended to isolate the
buffer gate. An intermediate fixture tried assigning a read-only config
property; it now sets the synthetic private fixture configuration. Ruff
initially found two import ordering errors, corrected. The contracts checker
also initially traversed npm-installed third-party Markdown and reported
broken dependency links; moving the newly installed dependency directory
outside the checkout restored the repository-only check.
These do not change the frozen acceptance conditions.

## Remaining UNKNOWN and live boundary

`R3_LIVE_AUTH_PENDING`: R3-A only qualifies offline injection. `run()` and
the CLI expose no diagnostic toggle and never construct this observer.
The existing P1 exact-head admission cannot reuse the consumed historical
Arm A grant on the new HEAD. This PR does not introduce R3-B admission or
claim that a newly minted old-format P1 grant authorizes R3 diagnostics.
A future live diagnostic entrypoint requires a separately frozen R3-B
protocol and a new local grant bound to the R3 manifest and exact HEAD.

Historical Arm A cause remains UNDETERMINED. The read/framing and
pre-response classifications remain coarse: no finer HTTP substage,
server internals, native stop acknowledgement, GPU preemption, physical
same-process slot reentry or production qualification follows from these
offline fixtures. Synthetic slot/proc identity is not physical attestation.

Always: `NO_NEW_PHYSICAL_RUN`, `ARM_A_CAUSE_STILL_UNDETERMINED`,
`NO_STOP_ACK`, `NO_SAME_PROCESS_SLOT_REENTRY_PROOF`, `NO_PRODUCTION_GO`.
