# T1w — client physics / outgoing packet / Paper movement candidate correspondence

Date: 2026-10-28. **DEV_ONLY / OFFLINE_IMPL_ADDED /
NODE_PYTHON_TESTS_NOT_RUN / NEW_WORLD_NOT_RUN /
NATIVE_GAIT_UNVERIFIED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.

Starting HEAD `0cbe20125b84d05398b80e1ec358ff8c4fb7be9a` (T1v measured).
The measured T1v baseline contains two new Worlds, each verifying one
`PHYSICAL_IDLE_DEV` pre-Action tick, both refusing the first MOVE onset.
Movement ~0.098 block at onset and continued post-clear movement
~0.0827234 block are actual observed displacement, **not** authenticated
full applied gait for a World tick.

## Boundaries: what is actually available

The existing Mineflayer 4.39.0 `physicsTick` event is a *sample event*.
We cannot infer the precise interval of simulation from the event alone.
The existing `client.write` emits the outgoing protocol movement packet;
the wrapper can observe its original return without creating a packet, but
the return is **not** proof of delivery or Paper acceptance. The original
Paper `M02_DEV_MOTION` log already captures physical PlayerMoveEvent
from/to, World full time, server-side event id, and observed distance,
but it does not carry a client physics step id or network packet id.
Paper `PlayerMoveEvent` at HIGHEST also does not independently certify
all downstream plugin modifications.

**An equality of coordinates is a candidate match, not a causal match.**
Node and Paper process-local nanosecond counters MUST NOT be subtracted,
and neither clock is treated as the authoritative other-process tick.
We do not reinterpret this candidate as a `SourceBoundTick`, P1
transition, R qualification, or a free DASH M0 charge.

## Implemented isolated instrumentation

- `adapters/mineflayer/t1w_motion_witness_dev.mjs`: existing bot's
  `physicsTick` listener samples all seven applied control states and
  client pose. A wrapper around the one original `client.write`
  records only `position`, `position_look`, `flying`, `look`
  **after the original write returns**, including outgoing
  coordinates and latest *sample* physics-event index.
  It leaves the writer's receiver, packet name, arguments, call count,
  return value and thrown error unchanged. It does not write a packet.
  The index is an event-order hint, **not a physics-step identity**.
- The T1w sidecar is separate from canonical `native.jsonl` and
  from the older synchronous Node clock trace. It uses `wx`
  (new absolute path), asynchronous buffered I/O, bounded at 8,192
  records. Backpressure, write error, missing terminal footer, or a
  truncated stream invalidates **the trace**; it does not turn data
  into synthetic evidence. The footer records row count and loss.
  Unknown/unobserved tail is never silently filled.
- `adapters/mineflayer/bridge.mjs` attaches the sidecar ONLY under
  explicit `RELAYSELF_T1W_MOTION_TRACE_DEV`, with existing T1f,
  existing Paper tick DEV and Minecraft 1.21.8 required. No extra
  stdout source envelopes or native receiver; **default OFF**.
- `adapters/mineflayer/t1e_native_dev.py` registers the isolated
  `t1w_motion_receipt_probe` case, enabling the same original
  Paper `t1u-gait-dev` passive observation and T1v strict physical
  idle/unknown-onset path. It must still refuse unproven MOVE onset.
  An ordinary inability to prove an exact gait is **not** a successful
  continuous gait integration.
- `adapters/mineflayer/t1w_motion_correspondence_dev.py` reads the
  complete Node sidecar and **existing** Paper M02 movement log.
  It reports `NO_GEOMETRY_MATCH`,
  `GEOMETRY_AMBIGUOUS`, or
  `GEOMETRY_SINGLE_UNATTESTED`. In **all** cases
  `p1_transitions_admitted=0` and
  `exact_client_step_to_paper_tick_proven=false`.
  It rejects missing footer, source row loss, forged sent/accepted
  flags, foreign World, reorders and duplicate Paper events.
  The existing Paper M02 log only includes its first 300 motion
  event rows; absent rows outside that limit are UNKNOWN, not zero.
- Focused Node and Python tests assert no second writer and no
  false source promotion. These tests have been authored, **not**
  executed in the GitHub-only authoring environment.

## LocalCodex verification

Use isolated worktree of
`self/dev-t1w-motion-step-receipts-20261028`.
Confirm HEAD ancestry and protected refs before changing anything.
Use the existing Python3.12 venv and Node22; avoid FULL:

```bash
node --test adapters/mineflayer/t1w_motion_witness_dev.test.mjs
PYTHONPATH=src:tests:. python3.12 -m pytest -q \
  tests/test_t1w_motion_correspondence_dev.py \
  tests/test_t1v_physical_idle_dev.py \
  tests/test_t1u_gait_source_dev.py \
  tests/test_t2_gait_integration_dev.py \
  tests/test_p1_gait_dev.py \
  tests/test_t1f_t2_dev.py
```

Fix **real failures** and rerun focused and impact-scoped FAST, Ruff,
syntax and repo contracts; do not relax negative controls. Preserve
the failed-first logs. The Java/Paper source is unchanged in T1w:
verify the existing T1u Paper plugin SHA and avoid needless rebuild.

Run one fresh **disposable** DEV World after offline checks; use
the original T1e CLI `--help` to verify syntax and all actual
local absolute paths. Example, replace paths with verified ones:

```bash
PYTHONPATH=src:tests:. python3.12 \
  -m adapters.mineflayer.t1e_native_dev \
  --cases t1w_motion_receipt_probe \
  --loop-moves 2 --node-trace off \
  --output /ABSOLUTE/FRESH/T1W-001 \
  --paper /ACTUAL/PAPER-1.21.8.jar \
  --plugin /ACTUAL/UNCHANGED-T1U-PLUGIN.jar \
  --bootstrap /ACTUAL/BOOTSTRAP \
  --confirm T1E-DISPOSABLE-DEV-ONLY
```

This probe intentionally uses the original T1v strict P1 provider.
An unknown gait at onset must still latch. After normal resource
cleanup the Node trace should contain one `TRACE_END` with
`complete=true`; otherwise the trace is NOT reviewed as complete.
Extract the original `paper.log` and run **read-only**:

```bash
PYTHONPATH=src:tests:. python3.12 \
  -m adapters.mineflayer.t1w_motion_correspondence_dev \
  --node /ABSOLUTE/ORIGINAL/t1w_client_motion.jsonl \
  --paper /ABSOLUTE/ORIGINAL/paper.log \
  --output /ABSOLUTE/FRESH/geometry-review.json
```

Audit original hashes, row continuity, Node writer returns and
Paper source World IDs; preserve one external SHA256 manifest and
all complete disposable World bytes. A `GEOMETRY_SINGLE_UNATTESTED`
candidate is **NOT** native P1 integration, cannot unlock 2nd MOVE,
and may not be used as a full-tick fatigue rate.

## Follow-on after real evidence

For actual P1 accounting, a future owner-reviewed DEV must establish
which client step / packet was **accepted** for which Paper
WorldTick. This may require an authoritative server-side inbound
movement-packet receipt with an explicit provable binding to
Paper PlayerMoveEvent. Merely adding equal clocks or interpolating
a tick is insufficient. If there is no proven unique chain, keep
`NATIVE_GAIT_UNVERIFIED` and consider **explicit P1 uncertainty
intervals**, not an exact hidden fatigue value.

**Do not mutate** the original 4-gait P1 model blob
`d241978d0eba1843e3a6caed96c90e3c16e8dc39`.
Maintain one P1, original M0 and original S49 issuer. Preserve main,
all protected Draft HEADs, frozen S18 and T1q/r/s/u/v original Worlds.
No force push, FULL, R qualification, SCIENCE or main adoption.
