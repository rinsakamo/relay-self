# SelfBody #632 × S50 #627 — optional motion companion (DEV)

**Owner and scope**: this is an isolated read-only *consumer seam* on the
original SelfBody [Draft #634](https://github.com/rinsakamo/relay-self/pull/634),
not a change to `src/relay_self/self_body.py`, original S49/Action/S16
control, L0/L1/L2 policy, M/P1 exhaustion, or L8 learning.

The producer remains S50 [Draft #645](https://github.com/rinsakamo/relay-self/pull/645)
stacked on [S Draft #642](https://github.com/rinsakamo/relay-self/pull/642).
This branch does **not copy or fork** the S50 parser, read native packets,
mutate existing SelfBodyView, or declare the source independently authenticated.

## Why

A previous genuine Paper1.21.8 DEV World in [#643](https://github.com/rinsakamo/relay-self/pull/643)
used one original S49 MOVE_BACKWARD, S15 clear seq32, S16 after seq34,
with additional post-S16 native movement 0.12287857661821566m. Paper
fullTime 251–258 had eight consecutive WAIT and INPUT samples; all
server-last-reported input bits were OFF, yet position changed at ticks
251 and 252. Node control history was back ON → clear all OFF;
outbound observed `player_input` write-returns were zero, position-like
write-returns were 23. Paper `PlayerInputEvent` zero. Source clocks
are separate; no effective server clear tick has been attested.
Actual original HEAD `2afb7250952ae490bcddc8244c19264ff1f73bf5`,
[original evidence](https://github.com/rinsakamo/relay-self/tree/2afb7250952ae490bcddc8244c19264ff1f73bf5/docs/evidence/s50-client-packet-20261031/run2).

The S50 producer in [#645](https://github.com/rinsakamo/relay-self/pull/645)
already replayed this true physical original and produced an immutable
S50SelfBodyMotionSource with source refs, exact eight Paper tick
displacements, and local Node clear snapshots. Source replay
[CI #41188914643](https://github.com/rinsakamo/relay-self/actions/runs/41188914643)
passed 56 focused tests; it did not launch a new World.

## New SelfBody consumer

`adapters/mineflayer/self_body_s50_motion_companion.py` accepts:

- The **same existing** `relay_self.self_body.SelfBodyView` instance,
  already made by original SelfBody v0 and containing a *typed*
  `ActionOutcomeInterpretation` with executed S16 OUTCOME and an
  *action-associated* native `BodyObservation` whose consequence
  provenance matches original S16 world provenance.
- A producer-reviewed S50 motion **dict** (equivalent to `asdict` of
  `S50SelfBodyMotionSource` or the `physical_body_diagnostic` member
  of the saved replay CLI JSON), with complete eight-tick Paper source,
  Node clear effects, packet counters, SHA256 of both originals, and
  hard-coded negative authority ceiling.

It rejects foreign session/Action/marker, missing S16 or original
action-associated native Present, S50 producer data missing or exceeding
the DEV-only authority ceiling, nonfinite or broken tick sequences,
unbounded/incorrect packet counts, invalid clear state, forged
physical-stability/Goal/P1/L10 flags and mismatch between physical
displacement and the `motion_while_reported_input_off` index.

When both owners' typed inputs are supplied, the returned frozen
`SelfBodyS50MotionCompanion` holds the **original** `self_body`
instance by identity, and a separate bounded sampled-motion readout:

- `sampled_at(Paper_world_fullTime)` returns
  `SAMPLED_POSITION_CHANGED` or `SAMPLED_ZERO_DELTA`. These are
  *callback displacements*, not actual continuous velocity or
  guaranteed whole-tick idle.
- `cognitive_summary()` gives bounded, non-authoritative source
  context (Paper motion with last-reported input OFF, source hash,
  World, session and epoch), but zero new Action/Model/Memory/Goal/P1
  authority.
- Missing Paper tick returns `None`; never interpolates or invents
  position history.

This companion is an **optional extra argument/readout**, *outside*
`SelfBodyView.observed()/sensed()/predicted()`, not a new
`BodyOrigin.OBSERVATION` or `BodyInteroception`. It does not
add an `authorize_action` method, issue STOP, edit a controller, or
automatically select L0/L1/L2 Action.

**Important same-real-run boundary:** the archived #643 S49
`after_observation` is not automatically the correlated native Present
required by SelfBody #634. The real archived S50 diagnostic alone is
**insufficient** to instantiate this companion as a genuine *host*
SelfBody epoch. The typed S16/Present must originate from the actual
SelfBody owner, not be synthesized from Paper or its JSON output.
Current isolated tests use explicit synthetic owner inputs and carry
a `NOT_QUALIFIED` classification for host admission.

## Dev acceptance and next action

Focused test must import original typed SelfBody, build the existing
native/action view unmodified, join the optional S50 record, confirm
`companion.self_body is existing_body`, confirm normal observed /
hypothetical / sensed answers do not change, and reject a view with
UNKNOWN or missing S16 or missing same-action Present.

Source producer remains separate. The next actual host integration
requires a deliberate #632 owner opt-in which supplies a genuine
same-Action typed view **after** the original S16 owner has admitted
it. That seam must stay fail-closed on unavailable correlation; there
is no reason to start a new physical World just to verify that the
two DEV schemas fit offline.

**Ceiling:** DEV / OFFLINE_CONSUMER_ONLY /
NO_NEW_MINECRAFT_WORLD / NO_NEW_NATIVE_PRESENT /
NO_ACTION_POLICY_CHANGE / EFFECTIVE_CLEAR_NOT_ATTESTED /
FULL_TICK_INPUT_IDLE_UNPROVEN / PHYSICAL_STABILITY_UNPROVEN /
GOAL_UNDETERMINED / P1_WAIT_0 / L10_0 /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
