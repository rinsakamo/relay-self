# T1h — S49 high-level STOP, original clear ACK, independent Paper idle DEV

**DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.** Source base:
`self/dev-t1g-stop-disconnect-20261026` at
`9f97473227bc839413f5ee31bc5469dcb425fa5b`.
No modifications to main, Draft #545/#634, archived World/evidence, or R/V grants.

## Owner and STOP distinctions

The existing runtime implements S49 primitive Action issue/S16
`clear_controls` and Node `shutdown`. Neither is itself an existing
product-level high STOP command or STOP ACK. T1h introduces one
**opt-in owner-local DEV STOP request state** rather than mislabelling
either primitive:
- `S49DevStopOwner.request(stop_id, active_action_id)` latches once;
  thereafter `allows_action=false`. It has no effect writer or native
  receiver. The original S49 owner uses the same exact original Action ID.
- `execute_mineflayer_command(..., l0_interrupt_dev=True,
  stop_requested_dev=lambda: owner.requested)` polls that flag during
  pre-motor admission, receipt waits and its one existing motor receive
  turn. An external owner event aborts only the currently issued MOVE
  and enters the **existing once-only S49 cleanup** (no additional
  `set_control`, second `clear_controls` or receive task). The
  interrupted Action remains `FAILED` / supervised `UNKNOWN`, not
  a successful OUTCOME. Default `stop_requested_dev=None` is unchanged.
- Once the original single-stream client `clear_controls`
  `MineflayerEffectResult(applied)` for exactly that effect ID has
  arrived, the DEV owner may issue a **Paper-console diagnostic marker**
  `relaydevsnapshot T1H_AFTER_STOP_CLEAR` via the existing host-side
  Paper console (not a client motor writer). The Paper JVM independently
  logs later `PAPER_DEV_MOTOR_SAMPLE` source rows on actual server ticks.
- A unique marker, matching World/Player, **8 consecutive observed idle
  transitions with identical stationary pose**, no gaps or duplicate
  post-marker Paper server ticks are required for a bounded S49-owner-local
  `S49_DEV_STOP_ACK_PAPER_IDLE_WINDOW` receipt. Residual movement
  before the settled window is allowed and must remain visible in original
  log. A missing clear ACK, session mismatch, insufficient Paper samples,
  sustained movement, input activity, or log discontinuity keeps STOP
  unacknowledged.
- Node `shutdown_ack`, Node `connection_end` and Java/Node
  `exit=0` are required for normal transport custody but cannot
  replace the owner-local STOP ACK or physical Paper callback evidence.

**Qualification limit:** The Paper callback is one sampler per World
tick, not a full action/input census nor cryptographically independent
source attestation. The DEV STOP ACK records a bounded later *sampled
idle window*; it is **not** R-qualified World STOP, STOP ACK provenance,
P1-qualified WAIT, proof of no sub-tick motion, or verified time of
physical stop. Fresh 50ms WorldTick deadline and absolute Paper→Node
latency remain UNKNOWN. TPS actuator and high-TPS Motor are disabled.

## Executable isolated DEV fixture

`adapters/mineflayer/t1e_native_dev.py` adds `--cases t1h_stop_move`
using the pre-existing disposal-world owner and original Mineflayer
JSONL reader/writer. It stages one bounded issued MOVE, requests STOP
after 80ms from host owner (no new native receive task), verifies
`FAILED`/UNKNOWN with matching original clear ACK, issues the Paper
marker only **after** that ACK, observes later Paper callbacks, and
evaluates the post-marker native log after owned shutdown.

Run on LocalCodex's Windows11/WSL2 machine with Python 3.12,
Node22, JDK21, disposable Paper1.21.8 and built plugin:

```sh
python3.12 -m pytest -q tests/test_t1h_stop_owner_dev.py tests/test_t1h_stop_s49_executor_dev.py tests/test_t1g_next_tick_liveness_dev.py
python3.12 -m pytest -q tests/test_t1f_t2_dev.py tests/test_s49_l0_interrupt_owner_dev.py
# Use existing exact `--paper`, `--plugin`, `--bootstrap` paths
# and fresh absolute output from docs/t1f-s49-t2-dev.md:
python3.12 -m adapters.mineflayer.t1e_native_dev \
  --cases t1h_stop_move \
  --paper /path/to/disposable/paper-1.21.8.jar \
  --plugin /path/to/new/relay-metabolism-dev.jar \
  --bootstrap /path/to/readonly/bootstrap \
  --output /new/absolute/t1h-dev-root \
  --confirm T1E-DISPOSABLE-DEV-ONLY
```

First verify original CLI version, JDK21 and paths before actual run.
Do not run against existing R/V World. For a native FAIL, retain its
complete original world and repair on the isolation branch, then rerun
with a different fresh output directory.

### Verification at initial integration

The new pure STOP ownership, S49 executor opt-in hook, dedicated
Paper-log parser, negative tests and disposable DEV case are committed.
**Python3.12 FAST, exact repository integrated pytest, full Node and
Java21 build, and new Minecraft T1h DEV World have not been executed
in this chat tool environment.** GitHub read-back validates code
publication, not runtime correctness.

Further trials: STOP at an epoch boundary, STOP during EAT,
unexpected client disconnect before Paper marker, absent/duplicate
clear ACK and recovered stale source. Avoid high-level STOP promotion
on partial evidence. See Issue #150 and #627.
