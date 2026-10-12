# RelaySelf S9 — native clearance before second controlled target (offline)

Owner: [Issue #537](https://github.com/rinsakamo/relay-self/issues/537).
Stack: S9 Draft #609 on immutable S8 Draft #608, exact parent
`eac08081d497b11f8386edd1229704c816d1a78d`.
No change to S8/S7 source evidence, #583 Golden World, R/L/V, main or user RSEE.

## Motivating actual terminal: S8 one-shot (spent)

The operator-reported S8 session [#537 comment 6119140571](https://github.com/rinsakamo/relay-self/issues/537#issuecomment-6119140571)
closed one original S49 `MOVE_AWAY` Action (0.9444m) and retained one
S3 observation; the next original probe recalled that historical Memory.
Original entity frames on stage 2 contained both old zombie entity 2
and new zombie entity 4. `NormalWorldL0._check` correctly rejected
multiple current zombie witnesses and the second Action never closed.
The CLI reported only the exception class, so the exact original
exception message is unverified. No original artifacts are regenerated.

S8 permission `#6118976649` is CONSUMED; the S9 branch refuses it
at the CLI authorization gate. **No permission to execute this new code
against a physical World has been given.**

## Single prospective change

1. First original S49 Action and typed terminal OUTCOME are source-authenticated
   by the unmodified S16/normal host. S3 retains an observational Memory.
2. Operator sends exactly one tagged `CLEAR` attempt, separately logged
   before the write. Stdin drain is NOT server execution ACK.
3. Instead of immediately summoning target 2, the operator performs at most
   four **new read-only, correlated Mineflayer native probes**, serialized on
   the one existing session (0.4s apart, up to 1.5s per probe). Each must be
   `kind=probe`, with exact request ID, session, source,
   strictly increasing native seq after the first Action's terminal
   after-observation, **untruncated** coverage and exact candidate count.
4. `SUMMON` for stage 2 is sent **once** only after one such original bounded
   snapshot contains **zero zombies**, even if unrelated items are visible.
   Existing L0 strict single-zombie logic remains entirely unchanged.
5. If old zombie persists, another zombie remains, probe is stale/foreign/
   truncated/uncorrelated, or the bound is exhausted: STOP, preserving the
   first original terminal without second summon, retry, replay or fallback.

A zero-zombie snapshot proves only a source-scoped, distance-bounded
observation. It does **not** prove a server kill ACK, full-World absence,
actual stage-2 entity identity, Safety/Goal success, causal influence of
Memory, S10 learning, S11 Habit, natural hostile survival, or V scientific
discrimination. The second Action would still require its own independent
S49 source, grant, typed OUTCOME and distinct entity/Action IDs.

## Prospective exceptional evidence

The normal S3 snapshot `s3_observed_memory.json` remains success-path only.
If the World run raises after retaining S3 observations, S9 attempts to
write **`s9_partial_observed_memory_on_failure.json`** from the exact
already existing in-memory read-only owner snapshot, preserving the
original exception. If this independent write itself fails, a minimal
`s9_partial_memory_save_failure.json` records the save failure class
and retained in-memory count. No missing S8 snapshot is backfilled.
`session_failed` now includes a bounded `reason_detail` only for a
typed `ReactiveL0Rejected` error, instead of losing its precise guard
reason. This does not convert UNKNOWN physical operations to OUTCOME.

## Verify WITHOUT World or model

```bash
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD"
python -m adapters.mineflayer.self_s8_trial
python -m pytest -q tests/test_self_s8_two_epoch.py \
  tests/test_self_s9_failure_receipts.py tests/test_self_s1_runtime.py \
  tests/test_self_continuous_host.py
python -m pytest -q
python tools/check_repository.py
```

Dedicated `.github/workflows/self-s9-offline.yml` validates exact S8
ancestry, existing source contracts, focused and full Python regression,
Ruff and Node Mineflayer adapter. Everything is synthetic source-shaped
and `PHYSICAL_NOT_RUN`; no independently user-granted S9 execution
or learned/scientific claim exists. Any prospective physical single-run
test would need an entirely fresh exact-S9-HEAD grant and independent
local operator preflight, not a recycled S8 URL.
