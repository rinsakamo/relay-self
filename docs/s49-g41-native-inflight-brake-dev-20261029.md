# G4.1 DEV native in-flight early brake (provisional)

Base: G4 original real-World code/report at `c20a463a6e9ceed807cfbb7d60a38c57bae211cc`.
This branch is isolated from `main`, Draft #545 and Draft #634.

## Control and ownership boundary

- Explicit opt-in: `--g4-auto-gait-dev --g41-inflight-brake-dev` and
  `S49_G41_INFLIGHT_BRAKE_DEV_ONLY=1` plus all inherited G4/T2 gates.
- The original S15 reader polls live native positions within its own
  0.10–0.35s already-issued motor Action. Session, sequence, request prefix,
  source and non-truncated threat coverage must be valid.
- DASH/RUN may clear early for a new slower G4 Action, using an
  observed RUN clearance threshold of 1.95m; JOG may hand off to
  WALK after observed movement >=0.08m. WALK uses a fixed bounded pulse,
  then relies on S16 and the original L0 settle verification.
- The initial G4.1 real World at `4362b76cc36c3b3868858d1b883877e31e4b833f`
  reached four original S16 OUTCOMEs but the fifth short WALK ended UNKNOWN.
  Its evidence remains retained; this revision extends near JOG/WALK windows
  to 0.24s/0.20s respectively while keeping the existing <=0.35s gate.
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

## Matched-start correction from first DEV A/B

The Paper server may spawn independent disposable Worlds at distinct absolute
XZ. The G4/G4.1 comparison now matches **relative** 4.0m +Z initial
Goal distance, L1 tolerance and Paper configuration, and records the distinct
absolute native spawn positions instead of pretending they are identical.
The original `40828663409` World pair both reached Goal; the wrapper failed
because it asserted identical absolute spawn XZ and no early brake sample
was observed. This new revision makes a RUN near-goal brake reachable
at 1.95m clearance. The next World run must still demonstrate the source
probe, original CLEAR ACK, S16 OUTCOME, and single T2 owner; no automatic
promotion from static policy tests.
