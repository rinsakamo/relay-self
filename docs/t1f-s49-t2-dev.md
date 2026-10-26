# T1f / S49 continuation / T2 DEV

Refs #150 / #627 / #537 / #616 / #626. DEV_ONLY / QUALIFICATION_NO_GO /
SCIENCE_NOT_RUN. Default OFF; no TPS actuator, protected World or R/V runner.

## Source and admission

`RELAYSELF_PAPER_TICK_DEV=1` + `RELAYSELF_T1F_DEV=1`, and the disposable
Paper plugin's `adaptive-tick-observer-dev` + `t1f-snapshot-dev`, select the
new snapshot format on the **existing** `relayself:world_tick_dev` channel.
Legacy T1e cache-shadow format and default tests stay available.

Paper captures position, health, food, received movement input bits, nearby
hostile position/type/distance within 4 blocks, bounded scan completeness,
plugin boot / World / Player, server tick and World full time. It includes
existing physical M0.2 basal/movement cumulative counters. No Mineflayer cache
field supplies L0. Cache disagreement is a diagnostic only; entities outside
the bounded scope and absolute safety are not established.

Node sends a random session challenge on the same connection. Paper echoes
its latest challenge at the actual snapshot callback. If `N0` is challenge
send, `Nr` receive and `Ne` evaluation completion, the snapshot occurred after
`N0` and before `Nr`: its age at completion is in `[Ne-Nr, Ne-N0]`.
All differences use the **same Node monotonic clock**. No oscillator-offset
estimate or JVM/Node subtraction is used. Exact one-way Paper→Node latency
remains UNKNOWN. Paper's relative `paper_ns` is retained separately.

A finite 16-challenge history handles startup/catch-up ticks; one challenge
can causally precede multiple distinct snapshots. Tick/index continuity still
rejects a replay, duplicate, loss, reversal or changed source identity.

Admission records ADMITTED / STALE / MISSING / LATE / UNDETERMINED, actual
Node receive/start/completion, latest **confirmed received** tick, causal age
bounds, completeness and refusal reason. The DEV policy requires age upper
bound **<150 ms** and Node receive→completion **<25 ms**. These are explicit
DEV limits, not a guarantee of completion within the current Paper 50 ms tick
or proof that no newer unreceived tick exists. Receive cadence never establishes
freshness. A broken lineage/refusal latches the bounded session; initial
subscription without a challenge can remain UNDETERMINED without granting
an Action. Malformed body fields emit the existing adapter error, never an
invented valid snapshot. The plugin stream is bounded to 2,400 callbacks.

The existing Node motor effect handler rechecks current admission and the
elapsed causal bound immediately before `set_control`. Python consumer delay
therefore cannot turn a formerly admitted queued snapshot into a new motor
permission. The original bridge Action-ID deduper remains in effect.

## Owner-local continuation

The existing T1e CLI owns fresh World staging, one Paper process, one recorded
Mineflayer session, shutdown and collectors. `t1f_continuation_dev` runs in
that foreground owner. A designed cheap L0 policy selects short MOVE_BACKWARD
from benign Paper body observations; danger/UNKNOWN admits no new movement.
S51 `_issue`, ActionSupervisor, S49 executor, its interruption watchdog and
S16 clear remain the sole Action/effect path. No L1/L2/model call is needed
for this bounded policy. This is not general navigation or learned behavior.

The next issue requires the previous supervised Action terminal, exact clear
ACK, a correlated boundary probe and later Paper samples: eight consecutive
idle-input/stationary intervals. Residual movement before this window remains
in the trace. Snapshot challenge timestamps must postdate the actual Node
clear, and the motor generation must remain unchanged. Old epoch messages
cannot satisfy current Action/clear IDs; an ACK loss forbids continuation.
Interrupted primitive results remain FAILED with supervised UNKNOWN; they
are not relabelled successful OUTCOME. Clear ACK is not a physical STOP ACK.
The fixture does not send a separate high-level STOP request.

## T2 bridge and limits

The current P1 pure module and tests are adopted **byte-for-byte** from
`0ab76b4e46efd914877e543a65de58b6cfc71326`, paths
`experiments/fatigue_p1.py` / `tests/test_fatigue_p1.py` in Draft #626.
Module SHA256: `2f7ae969fcb4676558c30a06483d219353b8ca9214b61756db202b6821461c5a`.
This copies only that existing model and tests, not its unmerged ancestor
stack or R qualification contracts. #620 is a research index; the concrete P1
implementation is #626.

T2 consumes consecutive admitted actual World ticks. Its initial snapshot is
an anchor, not an elapsed tick; no missing interval is filled with zero/WAIT.
Each row represents 1/20 reference World second, irrespective of target TPS.
The existing B0EnergyLedger / M0 metabolism_step records virtual E with explicit
uncalibrated DEV bridge rates: basal .001/tick, movement .002/native observed
block, bounded L0 work .0001/evaluation. Node evaluation duration is recorded
separately; symbolic E is not measured joules or Minecraft exhaustion. Native
motion cost uses the difference of existing cumulative Paper packet-motion
counters, not command duration, requested distance, TPS or a second chord bill.
Paper M0.2 exhaustion is retained as a separate physical ledger, not added to E.

A genuine S51 EAT receipt must prove consumed inventory and food increase;
B0's unchanged validation consumes its Action ID once, on a later stationary
source tick. Pickup, requested eating, cached intention, missing receipt and
replay confer no credit. The DEV meal is provided steak under a staged hunger
effect; it demonstrates consumption/credit, not autonomous food acquisition.

P1 uses native measured blocks for MOVE, including post-clear residual motion.
Blocked/active/unresolved intervals never recover. After Action terminal and
clear, later causally bound Paper idle inputs/pose/counters can produce
**WAIT_DEV** into `advance(FatigueFrame(WAIT))`. This is a bounded callback
observation, **not P1-qualified WAIT**, not a full-tick R witness. Basal and L0
cost continue during WAIT. No historical 8tick result is retroactively upgraded.

The unchanged current P1 model has WAIT recovery and distance-based MOVE; it
has **no ordinary non-WAIT recovery and no distinct WALK/JOG/RUN/DASH rates**.
This integration labels only the exercised ordinary movement as WALK, does
not invent a second fatigue formula, and leaves those extensions unresolved.
High-TPS RUN/DASH, TPS actuation, long-duration product reliability and R/V
qualification remain separate work. No Self Memory/Habit promotion is made.

## Run

Bind Python 3.12, Node 22 and Java 21; install the pinned Mineflayer package
as for T1e and build the existing Maven plugin. Set `PYTHONPATH=src:tests:.`.
The existing S-owned CLI accepts, for example:

```bash
python -m adapters.mineflayer.t1e_native_dev \
  --output /absolute/fresh/dev-run \
  --paper /absolute/paper-1.21.8.jar \
  --plugin /absolute/relay-metabolism-paper-dev-0.2.0-dev.jar \
  --bootstrap /absolute/bootstrap-library-root \
  --confirm T1E-DISPOSABLE-DEV-ONLY \
  --cases t1f_observe t1f_loop t2_loop --loop-moves 20
```

Only `cache/`, `libraries/`, `versions/` are copied from bootstrap; existing
World contents are never copied or started. `--loop-moves` bounds benign
MOVE epochs (2–32), followed by one staged LOW_HEALTH interruption and a
subsequent observed no-Action decision. Failures use fresh output/run IDs.
The old five T1e cases remain the default; no redundant old trial is required.
