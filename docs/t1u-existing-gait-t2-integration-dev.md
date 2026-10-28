# T1u — reuse existing four-gait single-P1 dynamics in original T2 (DEV)

2026-10-28 · **DEV_ONLY / OFFLINE_IMPL_ADDED / TESTS_NOT_RUN /
NATIVE_GAIT_NOT_ATTESTED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**

## Provenance and decision

This branch starts exactly at successful T1s physical-run HEAD
`946708c2daab0741b34f3b669efafb4622262a43`.
The other engineering lane already designed **one** movement-fatigue
model in `experiments/p1_gait_dev.py` on
`self/dev-p1-matched-boost-7ticks-20261027`, exact upstream HEAD
`d2ecdb5c2609615c84ef55a75b1ca2bfb8b382b1`.
This branch copies that file **unchanged** (upstream blob
`d241978d0eba1843e3a6caed96c90e3c16e8dc39`) and the associated
focused tests (upstream blob
`4887ccc32b7e0aede95b0301d7778fe9a16f9c45`).

This is NOT a merge of two diverged repository branches, not a new P1
physical theory and not an override of T1r/T1s historical evidence.
The T1s profile-only exponential WAIT kinetics are a distinct
comparison baseline. They must **not** be stacked on top of the
four-gait model's built-in net recovery.

## Established model we reuse

The existing per-WorldTick analytic gait transition changes the
**same P1 fatigue state**, not a second reservoir:

```text
F(t+dt)/C = (F(t)/C) * exp(-k(g)*dt)
          + (L(g,p)/k(g)) * (1-exp(-k(g)*dt))
dt = 0.05 World seconds
```

- WAIT: L=0, k=.12/s.
- WALK: L=0, k=.10/s.
- JOG: L=.002/s, k=.06/s.
- RUN: L=.004/s, k=.025/s.
- DASH: variable load for actual applied forward boost,
  k=.02/s; full-power fatigue limit is an engineered 20-second anchor.
  Additional M0 power charge is proposed in the original transition
  but NOT automatically posted to the original M0 ledger.

Nominal WALK is a sneak mode. Vanilla regular movement is JOG;
vanilla sprint is RUN. The original T1s native runner uses
`MOVE_BACKWARD` regular input (not a proven WALK/sneak observation).
Its historical `motor_mode=WALK` label comes from
`control.phase=MOVING` and is NOT sufficient gait evidence.
Do **not** remap it to WALK by renaming the label.

## Minimal actual integration

Existing `adapters/mineflayer/t2_tick_accounting.py` has
**one** P1 state and one admitted WorldTick stream. An optional
`gait_source(frame, predecessor, is_causal_wait)` returns an
existing typed `GaitTickDev` from the authoritative *applied*
World/Action owner. T2 verifies exact session, consecutive WorldTick,
same WAIT eligibility and obvious input-direction contradictions
before calling existing `advance_gait_dev()` once.

- Default `gait_source=None` keeps original T1p/T1q/T1r/T1s
  `fatigue_p1.advance` and M0 unchanged, including T1s SHA/receipts.
- Opt-in uses `advance_gait_dev`, never the legacy P1 `advance`
  on the same tick. The T1s 40s tau field is prohibited when
  `gait_source` is enabled: one recovery equation, not two.
- The `GaitTickDev` input is *NOT* an authenticator. Caller must
  verify the applied direction and motor mode. Any missing or
  ambiguous source raises an error, latches the owner and prevents a
  subsequent Action. Never replace unknown with WALK, JOG, or WAIT.
- The Paper input bitmap allows only contradiction detection for
  unambiguous back-only vs forward-only input, not automatic reliable
  gait classification. A model preview is NOT evidence that Paper
  applied that gait.
- Original `WAIT_DEV` remains conservative T2
  post-clear, stationary, consecutive WorldTick evidence; never a
  R-qualified full-tick WAIT. Internal recovery within a genuinely
  applied gait is distinct from World-stillness admission.
- Forward DASH's positive additional M0 charge is NOT posted by this
  bridge. Such a gait is **rejected** until the original M0 owner
  explicitly accepts its cost; no free DASH or new energy ledger.
- Original S49/S51 Action issuer, Motor writer, Paper receive loop,
  P1 session ownership and SelfBody interfaces remain unchanged.
- No new independent P1 state, no dual accumulation, no food credit,
  no LLM call, no TPS actuator, no high-level STOP or R/SCI claim.

A small optional `gait_source` parameter in original T1p owner
passes the evidence provider to T2 without altering the original
Action or command. This branch deliberately does **not** add a
new native runner case until actual gait and unknown post-clear
boundary ticks can be certified by the existing motor owner.

## Tests (not yet executed in this GitHub-only editing environment)

New `tests/test_t2_gait_integration_dev.py` covers:
- Legacy T2 remains the same and original source anchor is not billed.
- Confirmed synthetic Paper back input + applied ordinary JOG produces
  exactly one original P1 gait transition in the same T2 owner.
- Uncertain residual post-clear tick cannot be silently treated as
  gait or WAIT; second action must fail closed.
- Missing/foreign/wrong-tick/fake WAIT/direction-contradictory gait fails.
- Positive DASH extra M0 cannot be charged without atomic ledger posting.
- T1s tau+gait simultaneous recovery is rejected.
- Existing WALK recovery and long steady gait mathematics unchanged.
- Upstream `tests/test_p1_gait_dev.py` is copied unchanged.

LocalCodex, Python 3.12 focused (use existing venv if needed):

```bash
PYTHONPATH=src:tests:. python3.12 -m pytest -q \
  tests/test_p1_gait_dev.py tests/test_t2_gait_integration_dev.py \
  tests/test_p1_physiology_calibration_dev.py \
  tests/test_t1f_t2_dev.py tests/test_t1p_body_runtime_dev.py \
  tests/test_t1q_interoception_dev.py \
  tests/test_t1r_fatigue_timecourse_dev.py
```

Run FAST/Ruff/contracts after focused fixes; preserve first FAIL,
do not weaken negative controls. Do not run FULL/QUAL/SCIENCE.

Then, to advance to a *new physical DEV* result, the original
S49/Paper owner must offer exact per-WorldTick evidence of the
**applied** gait and direction, preserving unknown tick classification.
Reuse original T1e reader and ledger; no new native receiver or
duplicate P1. If a source is insufficient, leave `T1U_NATIVE_GAIT_UNVERIFIED`
and do not simulate continuous WAIT or move authorization.
A new single World DEV run would need original issued Action/clear/
OUTCOME 2/2, exact admitted per-tick source, verified mode evidence,
one P1 transition per source tick, explicit M0 cost proof if DASH,
normal cleanup, trace OFF and independent originals audit. Record
actual FAIL/UNKNOWN and all evidence. No changing old T1s World.

Historically protected: main, Draft PR #545/#634/#626, frozen S18,
T1q/T1r/T1s originals, R/V owner and PR HEADs. No merging/force push.

## Why the correction matters

T1s's `calibrated_walk_profile_dev` is a valid *separate model*
engineering PASS with constant WALK load (0.0001/block), no
moving recovery, and 40s WAIT recovery tau. It is not a suitable
basis to recreate speed-specific P1 recovery already implemented
in the gait lane. The objective is to reuse the existing
gait transition in the source-bound T2 owner, not to invent
a fourth physical fatigue architecture.
