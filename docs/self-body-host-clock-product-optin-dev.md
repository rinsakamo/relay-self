# SelfBody S49 passive host-clock — opt-in product DEV staging

**PRODUCT_OPTIN_SOURCE_STAGED / PYTHON3_12_NOT_RUN / DEV_ONLY /
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
They are NOT yet independently executed. The existing source
`experiments/self_body_host_clock_s49_liveprobe_dev.py` and its
locally verified 326 focused test result are reused without change.

**Next independent WSL2 Python3.12 qualification:**

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

The new opt-in is code-staged for review, NOT proven to run safely in
the real Java/Node/collector lifetime, and has not measured real
Minecraft physical reaction or motor capability.
