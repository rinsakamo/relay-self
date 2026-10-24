# SelfBody host-local callback time — additive offline DEV prototype (#632)

**SOURCE_STAGED / PYTHON3_12_UNVERIFIED / DEV_ONLY /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**

The verified PR #634 SelfBody timing calculation uses synthetic hypotheticals;
it does not yet have any measured physically qualified clocks. This branch is
an **isolated engineering step** towards recording one narrowly defined quantity:
the producer-local time spent inside an already invoked Python passive observer
callback. No current or historical evidence is changed.

## Exact quantity and origin

`PassiveHostCallbackTimer` receives an existing immutable `SelfBodyView`
whose observation originated from the current S49 native probe projection.
It does **not** receive a Mineflayer socket, start any process, read stdout,
request another observation, alter L0, modify a native owner, or issue Action.

An owner-controlled passive caller would call `enter(view)` at Python callback
entry and `exit(ticket)` at callback return. With the default clock, both
timestamps are sampled by `time.monotonic_ns` from **the same Python process**.
The difference is `callback_elapsed_ns` and `callback_elapsed_ms`, labelled
`PASSIVE_CALLBACK_PROCESSING_ONLY`. Injected clocks are always marked
`SYNTHETIC_DEV_CLOCK`; offline tests primarily use deterministic synthetic
samples and one local Python-process monotonic smoke case, not native World time.

The typed output explicitly has `action_start_ns=None`,
`world_cue_onset_ns=None`, `movement_speed_mps=None`,
`real_action_outcome_attested=False` and `allowed_to_act=False`.

**This cannot establish** World attack windup, native frame emission time,
Node-to-Python transfer time, physical motor start, Action authorization latency,
L0/L1/L2 cognition time or a successful dodge. The callback might contain
arbitrary Python processing overhead. No Node and Python monotonic values are
subtracted or resynchronized. The embedded native seq is an ordering marker
only, never an elapsed time. No new S17/S10 authority is present.

## Hard gates

- Concrete `SelfBodyView` type, matching self/session and exact upstream
  `mineflayer:<session>:<seq>` provenance; ephemeral source ref retained.
  This checks **declared producer-local correlation**, not independently
  cryptographic source authenticity.
- Replay/stale seq, duplicate request ID, wrong session, absent observation,
  overlapping callbacks, forged/duplicate tickets, noninteger/reversed/oversized
  timestamps, and event-count exhaustion fail closed.
- A process-ID transition or failed/reversed clock read is terminal for the
  recorder; no later recovered timestamps can relabel the failed interval.
- A failed/cancelled callback may call `abort(own_ticket)` to drop the active
  ticket without making a successful timing row; abort does not reset a
  terminal clock failure or mint an OUTCOME.
- An injected Python clock cannot be mislabeled as host-provided; the public
  `origin` property is read-only to normal callers. This is not a security
  boundary against untrusted in-process Python memory mutation.
- `PassiveHostInterval` cannot be upgraded to physical timestamp, Action
  authority, speed, a World consequence or S17 learning.
- Existing S49 is **not modified**; no hook is connected to a real runtime.
  This source has not been physically executed or tested in Python3.12 yet.
  The 24 new test functions are source-staged, NOT marked PASS.

## Next LocalCodex DEV gate

1. In independent clean WSL2 Python3.12.3 worktree at exact final source HEAD,
   run `tests/test_self_body_host_clock_passive_dev.py` plus existing
   `tests/test_self_body_timing_dev.py`, `tests/test_self_body.py`, S16/Action,
   S49/S18 guards. Ruff, repository contracts and protected SHA82, history770,
   W4 adopted19+15/4 checks, before and after.
2. Keep tests, real host measurements and synthetic clock numbers separated;
   preserve test failures and fix only isolated DEV new paths.
3. If independently verified, propose the smallest **single existing S49 owner**
   passive callback composition through existing `live_probe`, not a new
   native receiver. Such integration must be separately reviewed under #627;
   a callback-only measurement still does not measure motor execution.
4. Timing cognition, authorization/issue→movement, physical distance per
   elapsed time and attack-to-impact require **additional original-owner source
   points and clock validation**. Node/Python clocks, native seq, and
   Minecraft ticks must not be treated as one clock without evidence.
5. Only after dedicated disposable DEV World owner permission and physical
   source-qualified OUTCOME can hypotheses be compared to observed movement,
   damage/fall and failures; L2→L1→L0 learning remains separate #426 gates.

No PR #634/#545/main ref or workflow update is made by this prototype.
