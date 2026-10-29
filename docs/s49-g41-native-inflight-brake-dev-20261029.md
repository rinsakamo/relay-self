# G4.1 DEV native in-flight early brake (provisional)

Base: G4 original real-World code/report at `c20a463a6e9ceed807cfbb7d60a38c57bae211cc`.
This branch is isolated from `main`, Draft #545 and Draft #634.

## Control and ownership boundary

- Explicit opt-in: `--g4-auto-gait-dev --g41-inflight-brake-dev` and
  `S49_G41_INFLIGHT_BRAKE_DEV_ONLY=1` plus all inherited G4/T2 gates.
- The original S15 reader polls live native positions within its own
  0.10–0.35s already-issued motor Action. Session, sequence, request prefix,
  source and non-truncated threat coverage must be valid.
- DASH/RUN may clear early for a new slower G4 Action; JOG may hand off to
  WALK. Every mode stops input inside L1 tolerance for the original L0
  settle verification, which alone may decide REACHED.
- No second Action issuer, no mid-Action gait mutation, no second P1/M0
  owner, no new packet consumer and no claimed full-tick physical gait.
- A requested early CLEAR still requires physical displacement and the
  original S16/after-CLEAR native probe to earn OUTCOME; otherwise UNKNOWN.
  Hazard, stale source and incomplete coverage fail closed.

## Verification status

Development implementation only: no physically verified G4.1 result yet.
Follow up with focused unit tests and disposable Paper matched-start A/B
runs. Record the source-bound brake request and original CLEAR ACK, S16,
T2 receipt, final error, overshoot, physical travel, Action count and
observed WorldTicks. Separate DEV from QUALIFICATION and SCIENCE.
Sampling is opportunistic (~60ms), not hard real-time or per-WorldTick.

G4.2 may explore within-Action gait changes only with explicit native
effect ACK, original S49 identity and single-owner T2 posting contracts.
