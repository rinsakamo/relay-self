# Q4 independent U8 audit — bounded MOVE_PLACE Native guard and host abort

**2026-11-22 / Q independent branch / read-only adversarial review.**

- Unified I Draft #1124 exact immutable U8 HEAD: `6cf580c056a35b55750de533223350c05b0bdc22` (confirmed current branch identical at audit).
- Q3 prior I U7: `38c989472dcdf6ed5f75740f27eb7d91b9aa7920`. GitHub compare: 20 forward commits, 10 changed files (five new files: native guard, native guard test, Q4 host abort, two Python tests, plus Q4 docs = six new; four modified adapter/bridge/manifest paths; inspect compare for exact list); original B WAL/Owner not directly edited.
- Original native guard **Git blob SHA** `27bdd70639b205a03079bbd03b5950109bdb12f1`, path `adapters/mineflayer/bounded_place_guard.mjs`.
- U8 exact-head Actions [#45003534215](https://github.com/rinsakamo/relay-self/actions/runs/45003534215) completed SUCCESS; independently enumerated 5/5 job conclusions: pytest, lint, repository-contracts, mineflayer-adapter, paper-tick-witness. PR reports 2,887 scoped pytest PASS; **count is not independently read from job log in this Q pass**. The I positive tests are synthetic CPU/Node, not World.
- Q4 requested smaller DEV success criterion: measured real move, same-session Native START/STOP receipt, 8+8 post-stop tick stability, fresh second action, and a separate deliberate failure test proving neutralization/termination with no replay. Q does not request full historical cryptographic source custody as a precondition of this narrow DEV.

## Verified implemented, restricted scope

1. Explicit process-launch environmental opt-in and host one-use permit exist, and original B restored observation-only/physical grant remain OFF by default.
2. `Q4BoundedPlaceMotionGuard` checks monotonic wall time every nominal 20ms and actual sampled horizontal bot position, with 800ms forward threshold and early 0.7m distance trip below the 1.0m trial acceptance bound. A watchdog trip sets `tripped`, clears controls in `try`, and invokes `onTrip` in `finally` to quit the bot. **The timer is cooperative, not absolute real-time or real World displacement proof.**
3. Host `abort_original_place_after_start` fences original physical on the host before an await, attempts original same-session STOP for up to 0.25s, then attempts owned Node termination regardless of missing STOP ACK. TERM/KILL readback is explicit; a failed kill raises HOLD and poisons physical. The host watchdog uses `asyncio.wait` rather than blocking for a cancellation-resistant Skill. It does not reconcile WAL or attest STOP/settling.
4. Actual original Owner MOVE_PLACE runner/world opt-in, raw Native/Paper receipts, two measured nominal trials, and injected real failure trial are **NOT PRESENT/NOT RUN** in this review.

## Reproducible, pinned Native fail-open failures (Q4_BLOCKER)

The independently authored, **read-only** [Q hostile audit harness](../..//experiments/q_lane_q4_native_fail_closed_audit_dev.mjs) accepts an explicit source file and Git blob SHA; it never launches Minecraft/Native or issues actions.

Command from a checkout of the I HEAD containing the exact guard:

```bash
node experiments/q_lane_q4_native_fail_closed_audit_dev.mjs \
  /path/to/i-checkout/adapters/mineflayer/bounded_place_guard.mjs \
  27bdd70639b205a03079bbd03b5950109bdb12f1
```

The Q harness script itself lives on the independent Q branch and can be invoked from any directory using its absolute path. Q independently copied the complete fetched source to a temp Node sandbox, verified `git hash-object` is **exactly** `27bdd70639b205a03079bbd03b5950109bdb12f1`, and executed the injected tests with Node v22.16.0:

```text
FAIL start applies forward then throws: UNSAFE: forward remains active after START error, no native forced shutdown
FAIL stop clear-controls throws: UNSAFE: STOP error cancels watchdog and leaves forward active
FAIL timer registration fails after start: UNSAFE: forward remains active without watchdog timer
Q4 independent guard assertions: 0 PASS / 3 FAIL; target blob 27bdd70639b205a03079bbd03b5950109bdb12f1
```

- **START partial apply:** `start()` calls `setControlState('forward', true)` before setting `active` or installing the timer. If the native API mutates controls and then throws, `handleEffect` emits a rejection, but `tripped=false`, `timer=null`, `active=null`, and forward remains true in the injected stub. No `onTrip`/forced disconnect.
- **STOP failure:** `stop()` cancels the timer and resets `active` **before** calling `clearControlStates()`. A throwing clear thus leaves forward active without monitoring or `onTrip`.
- **Timer registration exception:** after forward is set, `interval(...)` can throw while assigning `this.timer`, leaving active forward control with no timer and no trip.

These are **adversarial stub reproductions of exact target code**, not evidence that Mineflayer 4.39.0 has thrown these exceptions in a real Minecraft World. However, when the Q4 contract asserts **fail-closed** motor limits under abnormal control/STOP/clock handling, an exception must not silently disable the last motor watchdog. Host 2s upper bound cannot by itself promise 1m/800ms in the gap.

## Minimum I owner remediation for re-audit

- Make `start()` exception-safe for all post/partial-apply failures, including timer installation: arm safety state before issuing motor control or catch and force `trip` on every failed step. `trip` must force a bot quit/host termination even when `clearControlStates` itself throws.
- Make `stop()` exception-safe: on clear failure, **trip and disconnect** instead of canceling the timer silently and returning to reusable idle state; prevent further START on the same session.
- Add three tests to the actual I Native guard JS suite, with a controlled `setControlState` partial mutation then throw, throwing clear-controls, and failing interval registration; assert forced-quit callback and no same-session restart. Integrate via `npm run check`.
- Then re-run exact-head CI and independent Q hostile harness against **new explicitly pinned blob**. Q will assess isolated World only after these local failures are closed. Keep original physical/Owner/WAL admission unchanged.

## Q exact-HEAD disposition

- `Q4_U8_BOUNDED_NATIVE_NORMAL_PATH_CODE_REVIEW_PASS` **scoped only**.
- `Q4_U8_HOST_ABORT_CPU_CODE_REVIEW_PARTIAL` — kill branch implemented; no real Native process proof.
- **`Q4_NATIVE_CONTROL_ERROR_FAIL_CLOSED_FAIL` — 3/3 injected defects reproduced.**
- **`Q4_PRE_WORLD_HOLD / Q4_REAL_MOVE_STOP_REPEAT_NOT_RUN / Q4_REAL_ABORT_FAIL_SAFE_NOT_RUN`**. Do **not** enable a real original MOVE_PLACE based on this head.
- `QUAL_NO_GO / SCIENCE_NOT_RUN`. Both PRs remain Draft.

No product branch or original real evidence was modified by Q.
