# T1p — unforced L0 / M0 / P1 body loop (bounded DEV)

Baseline: T1o `ef1cd01a36e8ca9e9621e470ce64e3cde9db60b8`.
Owner: #537 / #627; accounting #616 / #620; time-model #150.
**DEV_ONLY / T1P_NATIVE_UNVERIFIED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.

## Goal

Return from T1m/T1n/T1o source timing diagnostics to physical behavior.
This case reuses the existing disposable T1e Paper1.21.8/Node22/Python3.12
host, original single Mineflayer native receiver, S51 issuer, original
S49 executor and S16 clear/ACK, plus the existing T2 M0/P1 ledger.

Unlike the older `t2_loop` exercise, T1p does **not** inject low health, give
steak, stage hunger, or schedule a STOP. The bounded designed L0 sees current
ADMITTED Paper body data and chooses MOVE_BACKWARD only when the last Paper
input is idle, no hazard/low-food signal exists, the prior Action is closed,
and the host-owned virtual body is inside the conservative capability envelope.
This is not general planning, autonomous foraging, self-reported emotion,
learned policy, or production Self.

A decision to move is **not** itself a Motor authorization. Original Node
admission still checks source freshness (<150ms age upper bound, <25ms
evaluation) at send; S49's original watchdog/clear/supervisor determine the
actual OUTCOME. Any unexpected failure/unknown hazard stops issuing new Action
without fabricating an OUTCOME, WAIT, or food credit.

## Lifecycle and accounting

1. The original T1e owner stages a fresh World, keeps the same Java plugin
   and default T1o synchronous-trace OFF, then launches one Mineflayer session.
2. A correlated native observe barrier and an admitted next Paper tick anchor
   the existing `TickAccounting` owner. There is no second reader.
3. L0 issues a 0.2s bounded MOVE_BACKWARD through S51→S49 only while safe.
4. The original Action terminal and matching S16 clear ACK must arrive;
   `settled()` requires later Paper idle/pose transitions (8 consecutive).
5. The next 12 admitted real World ticks keep M0 basal+L0 cost charging;
   existing T2 marks only causally qualified callback-idle intervals WAIT_DEV.
6. Repeat for a user-bounded 2–32 MOVE budget; verify measured physical motion,
   M0 movement and basal debits, P1 accumulation and later recovery from the
   actual T2 ledger; then use the original T1e shutdown/cleanup owner.

This is **bounded callback WAIT_DEV**, not independently R-qualified full-tick
WAIT. The reference World-time cost remains 1/20 second/tick, even if effective
TPS drifts. No TPS actuator, high-rate RUN/DASH, LLM call, new fatigue formula,
new energy source, Paper-side Motor writer, retry of ambiguous effects, or
retroactive debits for missing ticks. Unexpected source failure latches the
session and the run reports FAIL (even when physical resources reap cleanly).

`decide_l0` combines the admitted Paper safety decision with a **host-side
capability guard** over exact virtual M0 Energy and P1 fatigue. These exact
ledger values are evaluator/safety state, not SelfBody interoceptive observations;
this case does not establish a fallible SelfBody perception of energy/fatigue.
They must not be exported as perceived body truth in a future cognition loop.
The per-tick M0 cognition debit is the inherited symbolic L0 work allowance,
not a measured count of policy calls, CPU energy, or Minecraft exhaustion.

## Tests (to run on the machine that has the repository/runtime)

```sh
PYTHONPATH=src:tests:. python3.12 -m pytest -q \
  tests/test_t1p_body_runtime_dev.py \
  tests/test_t1f_t2_dev.py \
  tests/test_t1e_native_dev.py \
  tests/test_t1o_trace_policy_dev.py
# Then the existing Python3.12 FAST subset, Ruff/contracts.
# Node22 test only when touching bridge code; Java plugin is unchanged.
```

One new disposable DEV World; run **only after the above offline checks pass**,
and only with verified existing Paper/Plugin/bootstrap assets:

```sh
PYTHONPATH=src:tests:. python3.12 -m adapters.mineflayer.t1e_native_dev \
  --cases t1p_body_loop --loop-moves 2 --node-trace off \
  --output /NEW/ABSOLUTE/T1P-001 \
  --paper /EXISTING/VERIFIED/paper-1.21.8.jar \
  --plugin /EXISTING/VERIFIED/relay-metabolism-dev.jar \
  --bootstrap /EXISTING/READONLY/bootstrap \
  --confirm T1E-DISPOSABLE-DEV-ONLY
```

Record exact HEAD, environment/assets, run ID, whole World and raw logs
(`native.jsonl`, `commands.jsonl`, `paper.log`, `t2_ticks.json`),
readback hashes, no Node timing sidecar, source continuity/status, every
Action/clear ACK/OUTCOME and actual movement, M0/P1 per-tick invariants,
zero food credits, cleanup/shutdown/PID/port rebind. Preserve negative cases
and their raw evidence. If the run fails, fix only the isolation branch and
rerun as a **new** World/run ID; never rewrite prior originals.

**Acceptance ceiling**: successful first real World implies
`DEV_WORLD_OBSERVED` only. Until then, code and tests are a candidate
(`T1P_NATIVE_UNVERIFIED`), with no CI/FULL/R/V/scientific claim. Do not
merge main, Draft #545/#634 or change S18 freeze without an owner review.
