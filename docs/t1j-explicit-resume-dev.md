# RelaySelf T1j — explicit STOP reauthorization and World reobservation (DEV)

Based on T1i source branch `self/dev-t1i-self-stop-eat-20261026`
at `0c77688ade3e028aead023d1454375e9dda5a4f5`.

**DEV_ONLY / T1J_NATIVE_UNVERIFIED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.**
The prior T1i World result remains independently `DEV_WORLD_OBSERVED`.

## What T1j changes

A MOVE-origin STOP in the *original S49 multi-epoch loop*, with the T1h
bounded **DEV** STOP ACK, leaves the old `S49DevStopOwner` latched and
the old `TickAccounting` failed/frozen. An EAT-origin UNKNOWN STOP has
**no STOP ACK** and is **not admitted to T1j resume**, even if passive
World food/inventory samples later show physical food consumption.

T1j introduces a **second explicit operator DEV opt-in** separate from
the disposable-World `--confirm`. This allows exactly one new Action ID
after all of:

1. The old STOP request, matching original `clear_controls` ACK and
   Paper 8-stationary-transition window have produced a T1h scoped DEV
   STOP ACK. Old owner stays requested/latched; no reused STOP ACK.
2. An exact new `resume_id/stop_id/session_id/next_action_id` and separate
   DEV operator reauthorization are recorded. The new ID
   `t1j-<resume_id>-move` cannot be an old Action/effect ID.
3. The **same single native reader**, with STOP-period M0/P1 disabled,
   consumes a *new* admitted Paper snapshot *after* the old STOP window,
   issues the existing correlated native observe, then consumes a second
   admitted Paper snapshot later than the probe. World/Player/boot,
   source order, current control CLEARED, stable pose/inputs,
   no threat and matching food values must agree. Native source liveness
   remains required. A failed/unsafe source consumes the attempt.
4. Only then is the one-shot permit consumed. A fresh S49 DEV STOP owner
   is created for the next segment. The original S49/S51 Supervisor and
   executor issue/execute **one new bounded MOVE** under that exact permit.
   The prior STOP owner **is not reset**. The existing single Motor writer
   admits only this next Action ID one time; lost ACK cannot reissue it.

### Accounting

Old M0/P1 ledger is preserved immutable-by-latch. T1j creates a **new
provisional segment** at the second fresh Paper baseline, with the last
known virtual energy/fatigue values carried forward, the old credited
Action IDs retained, and `unobserved_world_ticks` recorded explicitly.
It does not invent zero-cost time, retrospective debits, P1 WAIT recovery,
food intake or any qualified fatigue state during STOP. The Minecraft
World's metabolism **continues** during this interval; carried virtual
values are *not* estimates of actual elapsed physical energy expenditure.
New accounting only begins with **later consecutive admitted ticks**;
missing ticks still fail closed. P1 profile/energy formula is unchanged.

## New code and tests

- `adapters/mineflayer/t1j_resume_gate_dev.py` — pure one-shot explicit
  reauthorization and Paper → native → Paper validation. The exact
  pushed source blob matched the locally checked file SHA256 Git blob.
- `adapters/mineflayer/t1j_resume_accounting_dev.py` — provisional
  M0/P1 segment handoff, preserving old frozen ledger and prior credits.
- `adapters/mineflayer/t1j_resume_native_dev.py` — host-only S49
  integration, no second native reader or Motor issuer.
- `adapters/mineflayer/t1e_native_dev.py` — isolated opt-in
  `t1j_resume_move` case with fresh authorization CLI.
- `tests/test_t1j_resume_gate_dev.py`,
  `tests/test_t1j_resume_accounting_dev.py`,
  `tests/test_t1j_native_rebase_dev.py`.

Locally executed in the chat environment: **6 PASS** independent pure
resume-gate tests on Python 3.13.5. Same *core source blob SHA* was
confirmed after publication. **Not run** in this environment: these
newly committed repository tests against the exact branch, Python 3.12
FAST, related Node22 or Java21, or new native Minecraft World.

## LocalCodex DEV execution

From a clean, isolated WSL2/Python3.12 worktree at the T1j branch HEAD:

```sh
PYTHONPATH=src:tests python3.12 -m pytest -q \
  tests/test_t1j_resume_gate_dev.py \
  tests/test_t1j_resume_accounting_dev.py \
  tests/test_t1j_native_rebase_dev.py \
  tests/test_t1i_eat_stop_dev.py \
  tests/test_t1i_multi_owner_dev.py \
  tests/test_t1f_t2_dev.py
```

Repair code/test errors on the isolation branch, without weakening STOP,
freshness, physical observation or replay rejection. Perform module FAST
only once complete (FULL reserved for main merge).

After focused PASS, use existing Paper1.21.8/Java21+Node22 assets and
**a fresh disposable absolute output root**:

```sh
PYTHONPATH=src:tests python3.12 -m adapters.mineflayer.t1e_native_dev \
  --output /NEW/ABSOLUTE/T1J-DEV-RUN \
  --paper /EXISTING/READONLY/PAPER-1.21.8.jar \
  --plugin /EXISTING/BUILT/relay-metabolism-dev.jar \
  --bootstrap /EXISTING/READONLY/BOOTSTRAP \
  --confirm T1E-DISPOSABLE-DEV-ONLY \
  --t1j-reauthorize T1J-DEV-EXPLICIT-REAUTHORIZE-ONCE \
  --loop-moves 2 --cases t1j_resume_move
```

Use exact known local paths from T1i report. Do not copy/reuse old World
directories. Confirm same World/session normal MOVE×2, actual EAT×1,
STOP on third MOVE with DEV Paper idle ACK, explicit separate reauthorization
and fresh Paper → native → Paper, one NEW fourth MOVE with original
Supervisor/Executor, no duplicated effect IDs, and separately successful
shutdown. No implicit EAT UNKNOWN resume.

Keep FAIL originals. Record any source timing gap, actual World food changes
and `PROVISIONAL_LAST_KNOWN_CARRY_WITH_UNOBSERVED_GAP` explicitly.
If a missing or aged tick refuses, do **not** extend the existing 150ms
freshness admission, stitch fake zero ticks or retry a used resume permit.

Main, Draft PR #545/#634, protected R/V/S18 Worlds and existing evidence
must remain unmodified. This is a product **DEV engineering experiment**
only; it cannot establish qualified STOP, full-tick stillness,
P1-qualified WAIT or long-lived reliable physical accounting.
