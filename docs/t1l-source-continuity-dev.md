# RelaySelf T1l — source age diagnosis and bounded continuous T2 ledger DEV

Base branch: `self/dev-t1k-stop-resume-faults-20261027`, exact
`2efabc7b901189418ac99e3a0ce37661568ccd35`.
**DEV_ONLY / DEV_WORLD_OBSERVED /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.**

WSL2 execution results: [2026-10-27 native report](t1l-native-dev-results-20261027.md)
and [measurements](t1l-native-dev-results-20261027.json). Three fresh Worlds;
final first-snapshot-baseline 1,200 and separate 2,000 tick runs PASS.
T1k's 2 positive 2-generation Minecraft Worlds and 3 native fault examples
remain independently `DEV_WORLD_OBSERVED / NATIVE_FAULT_OBSERVED`.

## A. Existing T1k original logs: isolate the 150ms age-bound components

The existing Node `SnapshotAdmission` issues a same-connection challenge
and records `challenge_sent_ns`, `received_ns`,
`evaluation_start_ns`, `evaluation_completed_ns` and
`age_upper_ns` using **one Node monotonic clock**.

Thus the upper bound can be split *without* comparing clocks from Paper
JVM, Python and Node:

```text
causal-age upper = (received - challenge_sent)
                 + (evaluation_completed - received)

evaluation_completed - received
    = (evaluation_start - received)
    + (evaluation_completed - evaluation_start)
```

The first component includes *challenge transmission, Paper callback and
return transmission, plus any Node-side delivery wait* and cannot identify
one-way Paper↔Node transport, JVM execution duration or its cause. The
other components cover Node-side queue-to-assessment and assessment
execution only. **Do not assert a hardware or transport root cause from
these upper-bound components alone.** Node's 150ms age ceiling and 25ms
processing budget are unchanged.

Run the read-only diagnostic on individual preserved T1k original
`native.jsonl` files (including the 191–199ms age refusal in run-006
and 488–491ms refusal in run-009):

```sh
PYTHONPATH=src:tests python3.12 \
  -m adapters.mineflayer.t1l_source_diagnostic_dev \
  --native-jsonl /home/rinsa/work/t1k-evidence-20261027/run-006/t1k_fault_set_ack/native.jsonl \
  --output /NEW/ABSOLUTE/t1l-run006-age-diagnostic.json
```

Verify the actual paths from the T1k evidence index first. Never change
the original logs, never overwrite a previous diagnostic output.
Repeat on run-009 and on normally admitted run-004 as control.

The analyzer audits Paper sample index, source sequence monotonicity,
consecutive server/world ticks, identity continuity, original statuses,
clock order and actual age-bound consistency. No retroactive acceptance
and no authentication upgrade. Original non-Paper native effects remain
in the input but do not need consecutive sequence values because they
interleave with Paper messages.

## B. Source-only M0/P1 soak

New existing-runner case `t1l_source_soak` issues **no MOVE/EAT/STOP**.
It uses the original native session receiver and exactly the existing
T2 `TickAccounting.observe` path, never a parallel reader or an
independent decision maker. The first received admitted Paper snapshot
is a baseline and consumes **zero** virtual-energy tick charges; the
next **N consecutive admitted WorldTicks** (default 1,200, range
100–2,000) are individually admitted, accounted, and checkpointed
every 200 ticks. One skipped/reordered/stale/foreign tick immediately
fails closed and latches source and ledger; no fake WAIT recovery or
missing-tick synthesis.

At an ideal 20TPS, 1,200 ticks correspond to about 60 World seconds and
2,000 ticks to 100 World seconds; actual host elapsed seconds/TPS must
be measured independently, not inferred from the target count.

**Hard lifecycle bound:** Paper T1f protocol v1 and Node challenge
generation currently support at most **2,400 indexed challenges per
session**. The DEV soak refuses a projection reaching **index 2,300**
before starting (including the next issued challenge) and checks that guard during the run. It does not bump
the protocol cap, wrap/restart a counter, reconstruct an interrupted
session or call a shorter run "longer than 2,400 challenges".

T2 may label no-Action samples `MOVE_OR_UNDETERMINED`; this case
does not infer P1-qualified WAIT merely because no control was sent.
M0 and P1 formulas are unchanged. All per-tick rows are saved by
the existing T1e shutdown owner in `t2_ticks.json`, while checkpoint,
Node-age and source continuity metadata are included in report. Each 200-tick
checkpoint is also saved immediately in `checkpoints/`, preserving it across a later failure.
The source-only case starts immediately after spawn, without the legacy
teleport, startup sleep or observe barrier discarding early Paper samples.

New fresh, disposable 20TPS Minecraft World example (reusing the
*already built* Paper1.21.8 assets, not a prior saved World):

```sh
PYTHONPATH=src:tests python3.12 \
  -m adapters.mineflayer.t1e_native_dev \
  --output /NEW/ABSOLUTE/T1L-SOAK-RUN \
  --paper /EXISTING/READONLY/PAPER-1.21.8.jar \
  --plugin /EXISTING/BUILT/relay-metabolism-dev.jar \
  --bootstrap /EXISTING/READONLY/BOOTSTRAP \
  --confirm T1E-DISPOSABLE-DEV-ONLY \
  --soak-ticks 1200 --cases t1l_source_soak
```

No T1j/T1k STOP-resume operator tokens in the source-only case.
The initial run should use 1,200; run 2,000 only after the shorter
trial passes and confirms sufficient remaining challenge budget.
The sole normal PASS requires all source samples ADMITTED/continuous,
exactly N consecutive accounted WorldTicks, *zero* Motor sends/clears,
and independent normal transport shutdown/PID reap/port rebind.
A 150ms refusal is a **real FAIL** with frozen owner; retain its original
journal, do not enlarge 150ms to get a PASS.
Use fresh Worlds for all retries.

## Source and verification limits

LocalCodex on actual WSL2 needs to run:
```sh
PYTHONPATH=src:tests python3.12 -m pytest -q \
  tests/test_t1l_source_diagnostic_dev.py \
  tests/test_t1l_source_soak_dev.py \
  tests/test_t1f_t2_dev.py
```

Repair any new test errors, then do Python3.12 FAST after the module
is complete, related Node22 tests and Java21 Plugin build if required
for native execution. The initial pushed T1l code was unverified. It has now been exercised on
WSL2/Python 3.12 and in fresh Minecraft Worlds; see the linked execution report.
The final focused selection passes 50 tests, existing FAST plus T1l passes 615,
Node22 passes 68, and the Java21 Plugin build succeeds.
FULL regression remains main-merge-only.

Report run-004 vs run-006/009 original Node-domain age component
distributions; source seq/WorldTick coverage and refusals; first/last
indexed challenge and remaining headroom; exact M0/P1 ledger ticks and
credit counts; process cleanup and unique IDs. Make no claims of
continuous autonomous behavior or guaranteed age beyond the observed
source-only window. Longer >2,400 indexed challenges require separate
versioned protocol/owner lifecycle work with new grant and tests,
not silent extension of the T1f v1 limit.

Do not alter main, Draft PR #545/#634, S18/R/V qualification originals,
T1k evidence roots or the physical M0/P1 formulas.
