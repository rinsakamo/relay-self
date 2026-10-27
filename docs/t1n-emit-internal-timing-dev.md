# RelaySelf T1n — Node emit()内部の受動計測（DEV）

Baseline T1m `037d37325b5019ae9c28156ef8cacf6a1828a304`.

**DEV_ONLY / OFFLINE_IMPL_ADDED / T1N_NATIVE_UNVERIFIED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.**
Prior T1m 7 new Minecraft Worlds, 6 PASS/1 STALE-refused original,
remain independent `DEV_WORLD_OBSERVED / NATIVE_SOURCE_REFUSAL_OBSERVED`.
This T1n code has NOT been run in a new native World.

## Motivation

T1m's original run-006 and run-007 localized 52.418903ms and
57.706166ms to **Node evaluation-complete → original bridge emit return**,
not its diagnostic hook (0.091ms / 0.078ms). The next Paper tick reused
the old challenge and A expanded to 103.684ms / 108.631ms.
These timings do NOT identify synchronous trace writing, JSON,
stdout, Node GC or OS descheduling as root cause. T1n splits the same
DEV `bridge.mjs` native `emit('paper_snapshot')` without changing
normal non-DEV output semantics.

## Exact boundaries — ONE Node monotonic clock

The helper `t1n_emit_timing_dev.mjs`, enabled only for native
`paper_snapshot`, records:

- `entry_ns` → `envelope_return_ns`: original `makeEnvelope`
- `envelope_return_ns` → `trace_serialize_return_ns`: JSON stringify
  of existing `node_timing.jsonl` record, including original timestamp
- `trace_serialize_return_ns` → `trace_write_return_ns`:
  original synchronous `writeSync` to existing Node trace
- `trace_write_return_ns` → `stdout_serialize_return_ns`:
  canonical native envelope JSON stringify (plus original seq advance)
- `stdout_serialize_return_ns` → `stdout_write_return_ns`:
  original `process.stdout.write` call
- CPU user/system microseconds for the whole instrumented emit call
  through stdout write return, as a **reference**, not per-phase causality.

The T1n diagnostic `writeSync` occurs **after** stdout write return to
a separate fresh `t1n_emit_timing.jsonl`. T1m's
`previous_emit_return_ns - stdout_write_return_ns` allows the
residual diagnostic write/return duration to be bounded in the same
Node clock, where the next T1m challenge record is available.

The post-evaluation boundary is explicitly split as
`node_complete_ns → entry_ns` (pre-emit entry delay),
`entry_ns → stdout_write_return_ns` (measured canonical native work),
and `stdout_write_return_ns → previous_emit_return_ns` (CPU accounting,
T1n sidecar write and other residual, only when T1m next-issue
metadata exists). `process.stdout.write()` returning false is reported as
backpressure, **not** native receipt or server ACK.

All of these wall times MAY include Node GC or OS scheduling stalls
inside a call. `writeSync` duration does not by itself prove disk
latency; `stdout.write` return is NOT a Python receipt, flushing
guarantee or native ACK. CPU-vs-wall contrast can help target later
observations but does not isolate GC/scheduler cause. T1m Node
event-loop-delay histogram is only window-level and has sampling gaps.

**No changes** to original `paper_snapshot` wire, source seq,
canonical T1f receiver/admission, STOP/Motor, M0/P1 formulas,
150ms age, 25ms evaluation, 2400 challenges, T1l soft stop index2300,
R/V/SCIENCE permissions. Default OFF for all normal cases.

## DEV implementation and regression

- `adapters/mineflayer/t1n_emit_timing_dev.mjs`:
  isolated one-use native emitter with stage timestamps. Original
  `bridge.mjs` calls it only for `paper_snapshot` when
  `RELAYSELF_T1N_EMIT_TRACE_DEV` is set, and keeps the historical
  code path for ordinary cases. T1n sidecar open/write errors leave native emission intact,
  but the reducer will classify absent rows as diagnostic failure;
  no successful source or shutdown claim is synthesized.
- `adapters/mineflayer/t1n_emit_diagnostic_dev.py`:
  read-only original-native/T1m/T1n join by
  `session_id + native seq + challenge + Paper index`, preserving
  original ADMITTED/STALE decisions. Requires monotone phase times,
  exact source status and no duplicate or missing emit records; returns
  per-phase distributions, top 20 long emits and UNKNOWN root cause.
- `tests/test_t1n_emit_diagnostic_dev.py` and
  `adapters/mineflayer/t1n_emit_timing.test.mjs`: dedicated negatives
  on missing/duplicate/forged phase, stdout ACK misconception,
  trace stall 52ms, stdout stall 58ms, diagnostic sidecar failure
  not changing native stream.
- Existing `t1e_native_dev.py` supports
  `--cases t1n_source_soak --soak-ticks 1200`. Original T1l source
  and T2 owner run action-free; T1m JVM + Node sidecars and the T1n
  emit sidecar are all enabled ONLY for this case.

## LocalCodex DEV acceptance

Check exact T1n HEAD/isolated clean worktree, JDK21/Node22/Python3.12,
the already built Paper1.21.8 JAR and source-compatible T1m Java Plugin
with verified SHA256; rebuild with Java21 only if required.
Test:

```sh
node --test adapters/mineflayer/t1n_emit_timing.test.mjs \
  adapters/mineflayer/t1m_paper_timing.test.mjs \
  adapters/mineflayer/paper_snapshot_admission.test.mjs

PYTHONPATH=src:tests python3.12 -m pytest -q \
  tests/test_t1n_emit_diagnostic_dev.py \
  tests/test_t1m_timing_join_dev.py \
  tests/test_t1l_source_diagnostic_dev.py \
  tests/test_t1l_source_soak_dev.py
```

Fix any focused failures without relaxing original source admission or
changing historic originals; then run module FAST/related Node tests,
Ruff/contracts and verify the Java21 artifact. FULL is reserved for main merge.

Run two ordinary DEV fresh disposable Worlds (1200 source/accounting
ticks each); a controlled light-load separate World only if normal
runs pass and timing overhead is acceptable. Compare with T1m (without
T1n) as historical context, not causal noninterference proof.

```sh
PYTHONPATH=src:tests python3.12 \
  -m adapters.mineflayer.t1e_native_dev \
  --output /NEW/ABSOLUTE/T1N-BASELINE-001 \
  --paper /EXISTING/READONLY/PAPER-1.21.8.jar \
  --plugin /EXISTING/T1M-COMPATIBLE/REBUILT-PLUGIN.jar \
  --bootstrap /EXISTING/READONLY/BOOTSTRAP \
  --confirm T1E-DISPOSABLE-DEV-ONLY \
  --soak-ticks 1200 --cases t1n_source_soak
```

Ensure exactly 1200 consecutive T2 rows, all Paper native ADMITTED,
no source/identity/seq gaps, original/sidecar join cardinality,
no Motor/eat/STOP/LLM/TPS actuator, zero EAT credit, real 20TPS sample
measurement and proper Java/Node shutdown_ack+connection_end/PID/port.
If fail-closed occurs keep original FAIL, stale latch and accounting
frozen; never upgrade it to normal PASS. Preserve every World/source
and original SHA256. Report all native source phases and compare
per-phase min/median/p95/p99/max and largest 20 outliers, plus
current CPU/scheduler evidence limitations.

**Not qualified:** physical STOP, independent authenticated source,
P1 WAIT, all-subtick stillness, R/V, >2400-challenge lifetime,
scientific/autonomous performance.

Issue reporting: #150 (full timing), #627 (Physical Control time
boundary), #537 (S integration), #616 (M0/P1 continuity). No #626 unless
fatigue code changes. Do not touch main, Draft #545/#634, S18, R/V,
or earlier T1h–T1m original World evidence.
