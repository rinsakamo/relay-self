# SelfBody timing and motor-capability hypothesis — DEV-only (#632)

**SOURCE_STAGED / PYTHON3.12_UNVERIFIED / DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**

This is an intentionally narrow additive source slice on PR #634 HEAD
0ceb75bbc41066b63d84037271e2b69159fc86df. It is not a physically executed
zombie dodge, a calibrated speed model, an L0 installed reflex, or an owner
qualification. It does not extend SelfBody storage or create an Action issuer.

## Problem

Detection or an L0 rule is insufficient to guarantee bodily evasion. Under
the **same hypothetical environment and body**, faster cognition can reduce
total response time. Under the **same cognition**, body acceleration/movement
latency may make a dodge physically impossible. An upper layer might therefore
adapt battlefield geometry rather than optimizing an unwinnable reflex.

A conceptual signal-to-clearance budget uses aligned reference time:

    time_to_impact_from_world_cue
      > detection_latency
      + cognition_latency
      + authorization_and_issue_latency
      + actuator_start_latency
      + time_to_clear_attack_path

The final term may be conditionally approximated as
required_clearance_distance / assumed_body_speed, but real acceleration,
hitboxes, movement mechanics, body fatigue, facing, clock jitter, network
latency and server ticks are *not* represented by that simple approximation.

## Implemented DEV-only components

- experiments/self_body_timing_dev.py reads the existing typed, immutable
  SelfBodyView and BodyObservation. It checks Self/session/native source identity.
- BodyTimingHypothesis has an explicit SYNTHETIC_DEV_HYPOTHESIS origin.
  Detection, thinking, issue, actuator, speed, clearance and impact horizon
  are *all* optional assumptions. Any missing value or absent Body position
  yields UNKNOWN.
- predict_hypothetical_dodge returns WITHIN_HYPOTHETICAL_BUDGET,
  LATE_UNDER_HYPOTHESIS, or UNKNOWN, plus the hypothesized travel/response time
  and deadline margin. This comparison is *never* an attestable dodge result,
  danger classifier, action grant, physics override or a safe-World assertion.
  A result cannot be relabeled physically successful or action-authorized.
- review_body_position_delta compares successive same-session SelfBodyViews,
  requiring positively correlated source and executed S16 Action readback
  before reporting a *producer-local, source-correlated horizontal position
  delta*. This does not cryptographically verify native origin or reconstitute
  the complete original S15 before/after pair. It reports **no elapsed time,
  native speed, acceleration or Action authority** because current probes have
  neither synchronized timestamps nor full motion semantics. Unqualified,
  unknown or absent outcomes remain UNKNOWN.
- No existing module is edited: no executor, motor owner, cognition scheduler,
  P1/M writer, packet stream, S17/S10 learning commit or persistent memory.

## Evidence and epistemic boundaries

- The existing SelfBody native Present projection currently has x/y/z,
  health, food and saturation, not verified physical actuation startup or m/s.
- Mineflayer probe sequence is an ordering marker, **never milliseconds**.
- A synthetic ms quantity cannot be claimed native; even multiple successful
  synthetic predictions are not Self-acquired capability or reflex learning.
- Real attack windup and the future hit horizon are not established for the
  Java zombie. Raised arms while pursuing are not a guaranteed attack cue.
- Hypothetical full avoidance cannot be inferred from a positive position
  delta: clearing a hitbox, receiving no damage and not falling from a cliff
  are different empirical OUTCOMEs.
- The synthetic origin and optional quantity labels are DEV bookkeeping, not
  independently issued cryptographic evidence. The existing Source/S16
  provenance checks remain prerequisite for a real World claim.

## Offline negative-control suite

tests/test_self_body_timing_dev.py provides 25 test functions with parameterized
negative examples: fixed-Body L0/L2 timing contrast; fixed-cognition variable
Body speed; deadline equality; missing time/speed/clearance and missing Body
observation; stale/foreign native source and Self/session; invalid/negative/NaN
time or speed; fraudulent native attestation; direct result upgrade to Action
authority; immutability; source-paired movement distance with velocity UNKNOWN;
ordered seq not treated as seconds; ACK/UNKNOWN/uncorrelated action evidence;
duplicate/stale/foreign pair; missing Body fields and absence of issuer methods.

## Next gates (separate authorization)

1. Independent WSL2 detached worktree at exact HEAD, Python 3.12.3:
   focused new tests and existing SelfBody/S49/S16/Action/S18 guards, Ruff,
   repository contracts; verify protected 82, historical 770 and earlier
   evidence SHA before/after. Isolated DEV fixes/retries allowed. Record errors
   and final exact HEAD. Do not claim tests PASS before execution.
2. Audit true measured host monotonic clocks at source capture, L0/L1/L2
   selection, Action authorization/issue, Mineflayer start and native movement
   observation without introducing a second native reader/motor owner.
3. If actually available, add strictly source-bound read-only timing
   observations and estimate a distribution (including tail latency and
   timer uncertainty), while separately tracking compute cost and M/P1 body
   state. Source clock conversion must be explicitly validated; native seq
   is not a substitute.
4. With a separate disposable DEV World permit, compare model predictions
   to real executed movement/damage/fall OUTCOMEs. Retain bad reflexes and
   wrong predictions as failures, not auto-fixed labels.
5. Under #426 AC-5, distinguish manual developer scaffolds from real L2
   proposals, verified S17→authorized S10 learning and L1 Habit/L0 reflex
   adoption, each behind separate owner gates. Scientific causal tests remain
   independent in V.

**Adoption is NOT performed here.** No CI/FULL/new native World/LLM/Action/
OUTCOME/S10/Memory has been run; no change to Draft PR #634/#545/main.
