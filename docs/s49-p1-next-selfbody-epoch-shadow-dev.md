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

## Actual disposable Paper World evidence — 2026-10-27

**Code tested HEAD:** `7369d125738138d06b68eb5d5d272ec59ff4f2ee`.
**GitHub Actions:** [run 40468001013](https://github.com/rinsakamo/relay-self/actions/runs/40468001013), `SUCCESS`.
Python 3.12 focused **453 PASS**, Ruff PASS, Node test PASS,
Java 21 Paper plugin `BUILD SUCCESS`, then one genuine disposable
Paper 1.21.8 World with two original S49 native OUTCOMEs:

- First/second actions: `s49-native-move-20` and `s49-native-move-58`;
  original action issuer retained. Source session and World UUID correlated.
- Owner fence START 264, END 448; conservative Paper static candidate
  ticks **270..443 inclusive, 174 contiguous**, maximum horizontal delta 0.
  Node local controls OFF on 187 physics samples; no global WAIT assertion.
- There are **8 unclassified World ticks** after the first DASH and before
  the candidate; no native post-candidate P1 measurement.
- Source-revalidated tick replay on a disposable P1 model:
  `0.6155145675022867 -> 0.2166880178084883`;
  conditional model recovery `0.39882654969379844`, NOT posted.
- One-epoch SelfBody `p1-dev-retrospective-before-second-443` exposes
  `BodyHypothesis` cases, P1 fatigue in basis points **6155 vs 2167**,
  prospective requested-power-1.0 model ceiling **7690 vs 10000** basis
  points. **2310 bp** model ceiling gain is NOT real-world power approval.
- Candidate Paper tick SHA256:
  `8a0551a1c6a78cf17ea3cc82e9327b63a257bf3f081545aa75b672a718a8e2d3`.
- M0 original native remaining `10.421312745176191`; not modified by
  this read-only projection. No extra issuer/receiver, no SourceBoundTick,
  no formal WAIT, no real fatigue update, no production merge.
- Artifact ID **12716989058**, name
  `s49-inter-action-static-40468001013-1`, digest
  `sha256:cdb1b2bb52433be11fe5d0187696540c1a53e6313477e491ab4cd9bf1d081984`.

Historical pre-World CI failures are preserved:
`40467750526` (Ruff import order) and `40467868600`
(negative-test literal escaped newline); both fixed before the
success run. No real Paper World was launched in those failed runs.

Overall: `DEV_WORLD_OBSERVED / DEV_ONLY / QUALIFICATION_NO_GO /
SCIENCE_NOT_RUN`. This demonstrates **source-bound hypothetical capability
comparison**, not an online decision or a recovery in physical P1.
