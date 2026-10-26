# T1i — T1h owner wired into the bounded Self multi-epoch / EAT boundary

Base: `self/dev-t1h-s49-stop-20261026`,
`2531ba0a08ac77aca79f4d939122784e8556f3e5`.
**DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.
T1i native results are now recorded in
[`t1i-native-dev-results-20261027.md`](t1i-native-dev-results-20261027.md).
The observed ceiling is `DEV_WORLD_OBSERVED`; prior T1h remains separate.

## What is connected

- `t1f_continuation_dev.run_continuation(..., stop_owner=..., stop_mode="MOVE")`
  uses the existing S49 multi-epoch L0 choice, actual S51 issuance,
  ActionSupervisor and original `execute_mineflayer_command`. The same
  `S49DevStopOwner` instance is reused through many normal MOVE epochs
  and the existing genuine EAT boundary. One explicit DEV operator event
  requests STOP on the following MOVE, after the configured number of
  completed epochs.
- The original S49 executor polls the **same** owner latch; the existing
  single Motor writer sends the one original `clear_controls`. On
  `FAILED/UNKNOWN`, only the same owner can accept the matching native
  clear ACK. The Paper console marker is then set by the existing owner,
  independent Paper post-clear callback samples are checked, and a
  scoped T1h `S49_DEV_STOP_ACK_PAPER_IDLE_WINDOW` is committed **while
  Paper runs**. No next Action issues. Neither Node bridge shutdown nor
  `clear_controls` alone is that ACK.
- The same STOP latch is now passed into existing
  `IssuedEatingExecutor.execute` via default-OFF
  `stop_requested_dev` **only with explicit `paper_tick_dev=True`**.
  Its sole EAT receiver polls the owner during equip/consume receipt
  wait and final correlated probes, refusing additional effect/probe
  sends after STOP. Already issued Action IDs are consumed once, and
  interrupted EAT is closed by its actual ActionSupervisor as `UNKNOWN`.
  There is no duplicate consume, invented `EatingOutcome`, or M0 meal
  credit. No unobserved tick is fabricated or attributed to P1.
- **Very important:** Mineflayer's async `bot.consume()` is
  non-idempotent and is not proven physically cancellable by this STOP
  callback. Food/inventory may still change after a pending consume
  receipt; `EAT physical interruption=UNVERIFIED`. Therefore EAT STOP
  never generates the high-level DEV STOP ACK; it is only a fail-closed
  *decision/effect admission* test. A future Node native cancellation
  design remains needed for affirmative physical EAT interruption.
  The original receiver now performs bounded passive post-STOP probes and
  retains the independent Paper callback stream. These observations never
  reopen UNKNOWN or create an EatingOutcome/credit.
- No new native reader, plugin, Action issuer, TPS actuator,
  high-TPS Motor, R/V grant, or P1 profile/gait law is added.
  `WAIT_DEV` never becomes qualified P1 WAIT.

## DEV cases

`adapters/mineflayer/t1e_native_dev.py` supports:

- `--cases t1i_stop_loop --loop-moves 2`: same World/session
  two normal S49 MOVE outcomes, existing genuine EAT, then the STOP
  on the third issued MOVE. Expected original clear ACK, original Paper
  post-marker idle window, scoped DEV STOP ACK, and zero next Action.
- `--cases t1i_stop_eat --loop-moves 2`: two normal S49 MOVE
  outcomes, then operator STOP while original non-idempotent
  `consume_held` is pending. Expected `EAT UNKNOWN`, no meal
  receipt/credit/second consume, STOP owner latched, **no STOP ACK**.
  Node's eventual effect may still complete: do not report physical
  interruption as PASS. A regular transport cleanup is an independent
  condition.

Both use the original fresh disposable Paper 1.21.8 setup and the same
`--confirm T1E-DISPOSABLE-DEV-ONLY`, `--paper`, `--plugin`,
`--bootstrap`, and a distinct fresh absolute `--output` from
T1g/T1h. Do not operate on existing Worlds.

## Required LocalCodex/native verification

1. Check HEAD/clean isolated worktree and compatibility with T1h
   source. Run Python3.12 focused on
   `tests/test_t1i_eat_stop_dev.py`,
   `tests/test_t1i_multi_owner_dev.py`,
   `tests/test_feature_s51_eat_execution.py`,
   `tests/test_t1h_stop_s49_executor_dev.py`,
   `tests/test_t1h_stop_owner_dev.py`,
   `tests/test_t1f_t2_dev.py`. Fix test/code faults without weakening
   STOP/receipt/World/source predicates. At module completion run FAST,
   related Node22 and Paper Java21 as required; no FULL until main merge.
2. Run fresh `t1i_stop_loop` with raw native original and Paper logs.
   Verify two genuine normal outcomes, genuine EAT receipt/credit once,
   third MOVE `FAILED/UNKNOWN`, exactly three motor starts/clears,
   STOP owner ACK, bounded residual Paper movement followed by
   stationary eight-transition window, no next Action, normal resource
   cleanup. Check that the physical owner is the same instance across
   epochs and no duplicate effect IDs.
3. Run fresh `t1i_stop_eat` and verify one equip/consume effect-ID
   each at most, supervisor EAT UNKNOWN, no M0 credit, no new Action,
   STOP owner latches, **no high-level STOP ACK**. Observe whether the
   actual `bot.consume()` completes after the request and report it
   as observed, not assumed. If the native consume does not settle in
   the existing cleanup deadline, preserve FAIL and the original World.
4. Check original journal hash, explicit client effect ACKs,
   separate `shutdown_ack/connection_end`, Java/Node exit, PID
   disappearance and port rebind. Preserve failed originals and rerun
   modified code in NEW disposable Worlds. Existing earlier Worlds
   must remain unchanged.

## STOP accounting and boundary probes

`--eat-stop-stage` selects before_equip, after_equip, consume_send,
consume_wait (default), after_receipt, or after_observe in fresh DEV Worlds.
At STOP the existing DEV tick consumer freezes M0/P1 and retains exact
energy/fatigue/tick/credit values; subsequent raw native/Paper frames remain
available as observations without fabricated WAIT or catch-up ticks. World
metabolism continues independently; this frozen Self ledger is incomplete
beyond STOP and must not be interpreted as zero World cost. Resume remains
forbidden. No M0/P1 equation or profile changes.

See the dated results for actual runs, original failures, cleanup and limits.
