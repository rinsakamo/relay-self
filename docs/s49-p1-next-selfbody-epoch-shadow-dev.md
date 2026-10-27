# S49 original / Paper source ticks / P1 next SelfBody epoch — DEV

Scope: `DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.

## Goal and mechanism

Use the existing `P1_OBSERVED_STATIC_TICK_DEV_MODEL_REPLAY_NOT_APPLIED`
receipt as a *source-addressed model*, not as a confirmed physical WAIT.
An opt-in `--p1-next-selfbody-epoch-dev` builds a fresh, read-only
`SelfBodyView` at the end of the static-candidate window, before the
original S49's second Action delivery fence. Existing `BodyHypothesis`
and `PredictionState` types are used; no new body-state store or gauge.

The same first-DASH final P1 fatigue starts two mutually exclusive
**illustrative model scenarios** in one cognition epoch:

- `p1-carry-without-recovery-dev`: carry first DASH F with no recovery.
- `p1-assume-static-wait-dev`: use the P1 single-gauge replay from all
  observed static candidate ticks, conditionally assumed to be WAIT.

Both use the existing `p1_motor_power_limit_dev` forward-DASH fade with
requested power 1.0 and *hypothetically plentiful extra M0 energy 1.0*;
thus the difference isolates P1 only. Stored cognition values are
quantized to basis points (fatigue fraction and motor ceiling), not raw
P1 true owner fatigue or native sensor readings.

## Critical negative boundary

This is **retrospective**: the original second S49 action already happened
before wrapper-level Paper log review. These numbers never influenced it;
they do not issue/grant a new Action or modify L0 policy, real P1, M0,
World, native receiver, or Paper observer.

The gap between first DASH and the candidate is unclassified; there are
also potential unobserved effects surrounding the later transition.
The carry and static-WAIT cases are **not upper/lower bounds on physical
fatigue**. Stable Paper XZ movement does not certify globally inactive
World ticks. No real post-candidate native P1 sensor was read, and no
`SourceBoundTick` is created. The SelfBody `observation` and
`interoceptions` remain empty. Neither scenario is a physical capability
grant for the second or subsequent Actions.

Every call fails closed on profile digest, session, first/second Action,
Paper candidate SHA256, continuous interval, second-owner fence order,
qualified flag pollution, and invalid fatigue arithmetic.

## DEV verification

- Focused Python 3.12 and Ruff **before World**; negative controls covering
  source/actor/profile mismatch, forged admission, wrong tick/epoch, invalid
  values, and accidental P1 or M0 postings.
- The existing opt-in disposable Paper 1.21.8 World reproduces first native
  DASH and second native Action, conservative Paper static ticks and original
  S49 issuer boundary. The post-run shadow SelfBody capacity report has two
  contrasting hypotheses but no runtime physical effects.
- Workflow `self-s49-inter-action-stillness-dev.yml`, opt-ins
  `S49_P1_NEXT_SELFBODY_EPOCH_DEV_ONLY=1` and
  `--p1-next-selfbody-epoch-dev`.

Results of any specific real run and exact tested HEAD must be appended only
after its run is checked; a pushed branch by itself does not prove World PASS.
