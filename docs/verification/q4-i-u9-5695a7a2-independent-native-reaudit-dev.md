# Q4 independent re-audit — U9 Native fail-closed fix (2026-11-22)

**Q lane read-only code / Node fault-injection review. Not a World or physical-action qualification.**

## Pinning and exact-head CI

- Repo: `rinsakamo/relay-self`, unified I Draft [#1124](https://github.com/rinsakamo/relay-self/pull/1124).
- **Audited immutable integrated I HEAD:** `5695a7a20e4762b25251e634ec7893fd63976937`. At Q re-audit end, the named I integration branch still pointed to exactly this SHA.
- Prior rejected Q4 I U8: `6cf580c056a35b55750de533223350c05b0bdc22`. GitHub diff: **3 forward commits / 0 behind**, only `adapters/mineflayer/bounded_place_guard.mjs` and its `.test.mjs` changed. Original B Owner, WAL, lease issuer, Native protocol, host abort and existing previous-world evidence were not changed by this repair.
- **Audited Native module Git blob:** `0ac91642345159bf19f48313424f201bd00e2f21`. Q independently reconstructed source from the exact fetched GitHub module and verified `git hash-object` against that SHA before running the hostile tests.
- [Exact-head GitHub Actions run #45007510369](https://github.com/rinsakamo/relay-self/actions/runs/45007510369) completed **5/5 SUCCESS**. Q separately read job outcomes and logs: **pytest 2,887 passed in 112.07s**, Node mineflayer-adapter **47 tests passed / 0 failed**, lint, repository-contracts, Paper witness jobs successful. These are test jobs, not real Minecraft motion evidence.

## Previous three Q4 defects: independently reproduced PASS after fix

The unchanged Q-owned `experiments/q_lane_q4_native_fail_closed_audit_dev.mjs` was executed with Node v22.16.0 on the exact new target blob:

```text
PASS start applies forward then throws
PASS stop clear-controls throws
PASS timer registration fails after start
Q4 independent guard assertions: 3 PASS / 0 FAIL; target blob 0ac91642345159bf19f48313424f201bd00e2f21
```

The source changes explain the improvement: `start` now marks its session active and installs a watchdog before setting forward control, and trips irreversibly on partial control-apply, initialization or timer failure; `stop` does not discard its watchdog before successfully clearing controls and escalates exceptions to trip. `trip` first sets the one-shot irreversible flag, and calls `onTrip` even if Native clear or timer-cancel throws.

## Additional independent race/exception review

A second independent `q_lane_q4_native_race_audit_dev.mjs` covers cases relevant to the new ordering. Equivalent Node v22.16.0 hostile fixtures against the same byte-pinned module returned:

```text
Q4 U9 supplemental independent Node tests: 3 PASS
```

It covers: (1) `interval()` fires timeout synchronously before returning its handle: START rejected, stale handle canceled, no control START; (2) `clearInterval` exception while STOP otherwise cleared controls: permanent trip and quit request; (3) repeated `clearControlStates` failure after START: active forward control remains *unproven neutralized*, but `onTrip` requests disconnect and same-session START is refused. **A callback invocation is not a verified process exit or Native/Paper STOP receipt.** Node's actual `bot.quit` and the original host TERM→KILL with exit readback remain separate live checks.

Read-only reproduction (with two Q scripts and an explicit checkout of audited I):

```bash
node /path/to/q-checkout/experiments/q_lane_q4_native_fail_closed_audit_dev.mjs \
  /path/to/i-checkout/adapters/mineflayer/bounded_place_guard.mjs \
  0ac91642345159bf19f48313424f201bd00e2f21
node /path/to/q-checkout/experiments/q_lane_q4_native_race_audit_dev.mjs \
  /path/to/i-checkout/adapters/mineflayer/bounded_place_guard.mjs \
  0ac91642345159bf19f48313424f201bd00e2f21
```

## Decision and remaining boundary

- **`Q4_U9_NATIVE_CONTROL_ERROR_FAIL_CLOSED_CPU_PASS`** — the previous **3/3 FAIL** at `6cf580c0` are now **3/3 PASS** on the exact fixed blob; additional synchronous watchdog / cancellation / repeated-STOP exception checks **3/3 PASS**.
- **`Q4_U9_EXACT_HEAD_CI_PASS`** — five I jobs SUCCESS, 2,887 pytest, 47 Node tests from exact-head logs.
- **`Q4_NATIVE_MOTOR_PROCESS_EXIT_REAL_HOLD`** — no real Native exit/ACK or original host watchdog under an actual World run was witnessed by Q.
- **`Q4_REAL_WORLD_MOVE_STOP_REPEAT_NOT_RUN`** — no authentic MOVE→STOP 8+8 ticks→second Action was run or observed; also no real failure-injection/termination readback.
- **`PRE_WORLD_HOLD` for actual physical issuance until original B owner observation-only opt-in/typed MOVE_PLACE runner and local isolated-world preflight are explicitly established**. The narrow Native guard CPU blocker is CLOSED. Do not make full historical independent S1 custody a prerequisite of this basic DEV test; it remains a separate qualification HOLD.
- **`QUAL_NO_GO / SCIENCE_NOT_RUN`**. Keep I #1124 and Q #1089 Draft.

**Next:** original I owner on the WSL/Paper runtime must explicitly validate launch opt-in, real issuer/lease, one Self, watchdog/kill switch, and then perform two short flat-world 0.5m-class WALK actions with Native/Paper ACK and 8+8 settled tick observations, plus one controlled failure trial. Q reviews raw measurements and process exit before issuing the *real* DEV verdict. No real World was launched by Q.

**No I runtime or archived raw evidence modified by Q.**
