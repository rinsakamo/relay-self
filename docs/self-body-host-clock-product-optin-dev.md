# SelfBody S49 passive host-clock — opt-in product DEV staging

**OFFLINE_PRODUCT_OPTIN_VALIDATED / DEV_ONLY /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**

Base: `6753fc260437cb1836149ccefd3ec03480174203`, previously
`S49_HOST_CLOCK_LIVEPROBE_LOCAL_DEV_VERIFIED` (local Python3.12 focused 326
PASS and W4 adoption-v2 52 PASS, as reported). **Those results are NOT
tests of this new product opt-in.** No real World, Java, Node or physical
Action is authorized or executed by this stage.

## Minimal product seam

Add a default-OFF `--self-passive-host-clock` flag to existing
`adapters/mineflayer/self_demo.py`. It is permitted only with explicit
`--mode DEV --run-disposable --confirm` and model-free `native` mode;
conflicts with `--self-passive-views`, Stage W3/R/L/N/O, model/L2 and
other owners fail before World launch. Existing default or legacy passive
flags remain on their original path.

The new opt-in constructs one original `PassiveSelfViews` and passes
it to one `S49PassiveHostClockDEV`. The existing S49 original owner
still invokes precisely one `await live_probe(reading)` after a
single native probe; the observer calls `PassiveSelfViews.observe`
exactly once and reconstructs a typed view from the SAME received
Python object, checking session/seq/request/self/epoch/provenance.
Only subsequent optional read-only Python observer work is timed.
No new native `receive`, `observe` request, Action issuer,
L0/S16/S17/S10 owner or mutable physical Body control exists.

The original protected `s49_normal_session_real_ci.py` and
`process_session.py` are NOT changed. Product-side adapter is
registered only when opt-in is selected, never on default path.

## Bounded separate evidence

Two diagnostic sidecars are written in the existing DEV report directory:

- `self_views.jsonl`: original passive Body/World source-join rows
- `self_host_clock.jsonl`: bounded callback interval rows, bounded
  advisory errors and a final `DEV_ONLY_NOT_QUALIFIED` summary

Each file is serialized and published with same-directory temporary
storage, flush/fsync and an atomic **link-if-absent** operation, never
overwriting existing bytes or following an existing target symlink.
Each sidecar is atomic individually; the two-file set is **not** a
transaction. Missing one file, incompatible source pairs, a bad native
terminal, missing/extra/replayed clock sample, altered elapsed value,
synthetic clock source, aborted/incomplete observer, error ledger
or missing final native report yields `UNDETERMINED`, not success.

The strict receipt compares against S49's original
`source_pair_trace` through existing `verify_passive_source_join`.
It accepts precisely three same-session original source-correlated
Python callback intervals with origin `PYTHON_PROCESS_MONOTONIC`,
no errors, no aborts, no new reader/issuer, S10 and Memory writes zero.
This is **producer-local correlation**, not independent native/physical
source attestation. The receipt labels only
`SOURCE_JOINED_CALLBACK_DEV_ONLY` on exact source-joined successful
original DEV report, with `engineering_qualified=False` and
`science_success=False`. The sidecar itself always records
`source_qualified=False` and `physical_timing_attested=False`.

Asynchronous callback elapsed includes time suspended at `await`;
it is **not** CPU time, L0/L1/L2 cognitive latency, action-authorization
latency, Node clock time, motor onset, World displacement or successful
dodge. Native seq and Minecraft ticks remain ordering information,
not clock conversions.

## Cancellation, cleanup, and error contract

Ordinary observer/clock failures are advisory to original S49 L0,
reported in bounded histories and never converted into a successful
timing row. Cancellation and system interruptions are aborted when
ticket exists, then propagated unchanged into original owner cleanup.
The product `finally` restores S49 environment before sealing
diagnostic sidecars. If sidecar publication fails while an original
cancellation/error is already propagating, the primary exception is
preserved with a diagnostic note; without an original failure, the
sidecar error propagates and prevents success. No implicit retry
or second World run.

## Tests and next gate

New `tests/test_self_body_host_clock_product_optin_dev.py` stages
fake-original-owner tests and source/receipt/atomic-writer negatives.
They have been independently executed under Windows 11 Home / WSL2 Ubuntu 24.04.4, Python 3.12.3, pytest 9.1.1. The existing source
`experiments/self_body_host_clock_s49_liveprobe_dev.py` and its
locally verified 326 focused test result are reused without change.

**Independent WSL2 Python3.12 verification procedure:**

1. Pin exact final remote HEAD in a clean detached worktree; save initial
   evidence outside repository. Record environment and HEAD, hash
   protected original sources and history before/after.
2. Test this new product file plus
   `tests/test_self_body_host_clock_s49_liveprobe_dev.py`,
   `tests/test_self_body_host_clock_passive_dev.py`,
   `tests/test_self_product_passive_views.py`,
   `tests/test_self_dev.py`,
   `tests/test_self_body_timing_dev.py`,
   S49/S18 owner and W4 protection tests. Run Ruff and
   repository contracts. Fix/retry only isolated DEV changes and
   retain first failures.
3. Repeat negative controls with a stub original S49 only: flag OFF
   path equivalence; conflicts rejected pre-owner; no duplicated native
   observe/Action; 3 same-source callback samples; tampered/foreign
   native source and fake origin rejected; original failure produces
   UNDETERMINED; cancellation reaches original fake-owner finally;
   sidecar publication errors do not mask cancellation. Preserve
   evidence if source/sidecar incomplete.
4. Check Protected82, Historical770/index, W4 v2 historical19/current
   unchanged15+adopted4, original S49 and all Action/L0/S10 owners.
   CI/FULL/Java/Node/real World/real LLM/physical Action/OUTCOME/
   Memory updates remain zero.
5. This branch is **not** a PR #634 adoption or real S49 World trial.
   Actual one-shot disposable DEV World requires separate owner
   authorization. QUALIFICATION and SCIENCE remain NO_GO.

The new opt-in is offline DEV verified with fake original owners, NOT proven to run safely in
the real Java/Node/collector lifetime, and has not measured real
Minecraft physical reaction or motor capability.

## Independent offline verification (2026-10-24)

Pinned input `9c20deab5d3a1a2700e1e9fe541916e7e60a8611`: focused
387 PASS, W4 adoption v2 52 PASS, contracts PASS. Initial Ruff failed on
one import ordering error; its stdout/stderr and exit code are retained.
New controls reproduced **7 failures before repair**: foreign view Self,
reused request, reversed source ordering, bool masquerading as an integer
summary counter, failed native terminal accepted by the standalone verifier,
unbounded writer record count, and cleanup I/O masking primary publication
failure. These failures are retained, not replaced by later green runs.

Repairs affect only the four authorized files: exact typed clock summary
checks; view Self and monotonic native/event ordering with unique requests;
successful original terminal gating; at most 8 records and 65536 bytes per
sidecar; complete newline-terminated object JSONL reads; preserve primary I/O
exception with cleanup diagnostic notes. Failed/incomplete product receipts
retain `UNDETERMINED`. No protected observer, native reader or original S49
owner was changed.

Expanded focused suite: **427 PASS**, including **82 product cases**
(40 added cases). W4 adoption v2: **52 PASS**. Ruff 0.17.0 and repository
contracts PASS. Final exact commit and remote publication/readback are
recorded in the external evidence root, avoiding a self-referential commit
hash in this document:
`/home/rinsa/selfbody-product-optin-evidence-20261024-verify/`.
Protected 82/82, original protected 82/82, historical 770/770 and historical
SHA256 index match; W4 historical 19, unchanged 15 and adopted 4 are checked.

Controls include original OFF call signature and zero observer construction;
fake original L0/action equivalence with ordinary success or advisory observer
failure; exactly one passive projection per delivered object; zero extra
receive; bounded error history; absent/partial/oversized/symlink sidecars;
write/flush/file-fsync/link/directory-fsync failures; cancel, KeyboardInterrupt,
SystemExit and BaseException with cleanup once and restored environment,
both with and without sidecar failure. A directory-fsync failure may leave
a complete published file; it propagates failure and is never a successful
receipt. If filesystem cleanup itself refuses deletion, the primary failure
and diagnostic note remain authoritative; no success or retry is inferred.
The two files remain separate atomic publications, not a shared transaction.

This is producer-local DEV correlation using a fake original owner. It
establishes no independent native success, physical clock qualification or
motor ability. Callback elapsed includes asynchronous suspension; it is not
cognitive speed, Action latency, physical movement speed or avoidance success.
Product PR adoption requires a separate reviewed integration and its own
permitted validation. A real World trial requires fresh explicit owner
authorization, exact runtime/source identity, lifecycle/cleanup custody and
independent native evidence. DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
