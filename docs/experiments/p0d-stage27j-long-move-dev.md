# A Lane — Stage27j long MOVE: simple L0 continuation and physical WAL safety (DEV ONLY)

Parent: [Stage27 Issue #951](https://github.com/rinsakamo/relay-self/issues/951).
Stacked on [Stage27i Draft PR #990](https://github.com/rinsakamo/relay-self/pull/990).
This Stage27j change is tracked in [Draft PR #1005](https://github.com/rinsakamo/relay-self/pull/1005).

## Cognitive versus physical boundaries

**A Skill's Budget estimates how long/how far the Self should keep trying;
it is not a physical motion law or a strict in-flight completion deadline.**

- Stage27j operator-accepted (NOT autonomous/learned) Preset:
  `OperatorLongWalkSneakAt075`.
- Target: one source-bound DESTINATION **5.0m east** of fresh original
  WorldBody at L1-selection time, arrival radius **0.15m**.
- L1 chooses one frozen MOVE Skill + Target + Preset (or ESCALATE_L2 / DEFER).
  No subsequent L1 inside the original L0 MOVE loop.
- L0 picks WALK when remaining horizontal distance >**0.75m**, SNEAK
  otherwise. One finite native **0.15s pulse** per original child Action.
- Cognitive continuation limits: **12 Actions, 45,000ms elapsed,
  6.0m observed cumulative movement**. They are checked at pre-Action
  and after the **fully settled** physical child, not reserved as a
  hypothetical maximum next displacement.
- Native observation budget is **1,024**; the existing **60 STOP probes**
  per child are still pre-reserved against this *observation count*.
  This reservation is for preventing uncontrolled sensor-IO repetition,
  and has nothing to do with predicted movement metres.
- A completed Action may cross the cumulative-distance estimate or 45s.
  The observed distance/time is retained faithfully, the Action and
  original WAL stay terminal, and L0 yields for evaluation without
  issuing another Action. A Target observed after STOP takes precedence
  as a native Target condition, not Skill/Goal completion.
- Original `PhysicalIssueAdmission`, PREPARED before native effects,
  LOOK/SNEAK/forward ACK source, bounded short forward pulse, STOP ACK,
  settled native probes, terminal WAL and live owner/epoch gates stay.
  **No physical Action reissue when the WAL/STOP is unresolved**.
- A distinct **30s per-child IO watchdog** cancels genuinely stalled
  Action execution and triggers original best-effort emergency STOP.
  In that uncertain case, preserve PREPARED_UNRESOLVED and HOLD; never
  pretend the Action was a normal cognitive Budget exit. There is no
  `START` ACK fabrication or automatic creation of a no-forward
  normal terminal.
- The finite child Interpreter retains its existing local guard.
  There is **no parent absolute-deadline propagation**, no WALK/SNEAK
  distance reservation, no deadline-minus-5s forward gate, and
  no mid-Action Budget expiry decision.

## Why the simplified boundary matters

Earlier Stage27j HEAD `16ef730c35e769addabf24614e1402488c987037`
was PRE_WORLD_HOLD: cumulative distance and elapsed time could exceed
strict bounds during an Action. A later HEAD
`a0e69861d53adfd73f1035cb99b357c556dc7485` tried to guarantee
the hard bounds with WALK 0.75m/SNEAK 0.25m speculative envelopes and an
absolute 45s root deadline. Independent LocalCodex source preflight
found a 5s-margin gap after LOOK/SNEAK ACK. An uncommitted follow-up
added a pre-forward margin check but could only leave unresolved PREPARED
WAL when no START was issued; the requested normal Budget exit was not
achievable without a new WAL terminal type.

**Resolution:** do not stop a prepared physical Action because a cognitive
Budget estimate expired while waiting for LOOK or SNEAK. Either finish
its original bounded pulse/STOP/WAL and evaluate Budget afterwards,
or HOLD when native IO/STOP/ACK actually fails. Normal Budget exhaustion
at an Action boundary occurs **before any next PREPARED WAL**. This
eliminates the artificial need for a no-START normal WAL terminal.
Pre-existing PREPARED/STOP problems are not hidden or reclassified.

The prior HOLDs were pre-World, **0 real World attempts and 0 physical
Actions**. Do not retroactively mark them successful.

## Evidence and qualifications

- Existing A/B original resident identity, Intent/Skill/Memory/WAL,
  real HTTP source census (two initial L1 calls; zero within L0),
  STOP readback and Paper independent coarse correlational event
  evidence remain. Paper small-movement precision is **not expanded**.
- Previous Stage27i one-World 1.5m native target reached, but its last
  SNEAK lacked a separate Paper MOVE event. Do not rewrite that causality.
- The frozen checkpoint is prephysical unless a new post-Action source
  independently establishes otherwise.
- New synthetic adversarial tests cover: complete short Action after the
  cognitive 45s mark, Budget already expired **before** pre-Action,
  unexpectedly large but settled pulse (not falsified HOLD), actual
  cumulative travel >6m yielding Budget exhaustion, no native START ACK
  leaving unresolved WAL with one emergency STOP, unchanged gait/owner
  evidence and 5m traversal under the same original L1/Skill.
- Offline tests cannot attest true 5m real-world capability, STOP timing,
  independently nonempty B Memory preservation, Goal/Skill success,
  QUAL or SCIENCE.

## First real World: HOLD after four settled WALK Actions (2026-11-20)

Original execution HEAD `27426c029c5ee1b390bbe797e82b3278ca651294`,
isolated World UUID `39be3e79-61f8-43d2-b6a7-c4737c5b346b`.
One World trial, no retries. Original real Gemma A/B both selected #1,
with two initial recorded provider requests (post-loop HTTP census did not
complete). Four distinct WALK Actions used the original native LOOK/START/STOP
ACK, settling and terminal WAL:

| Action | Native settled displacement |
| --- | ---: |
| 1 | 0.641819m |
| 2 | 0.641819m |
| 3 | 0.641819m |
| 4 | 0.426891m |

Cumulative 2.352347m; native Target residual 2.647653m. The fifth
`stage27c-A-229` was **PREPARED_UNRESOLVED** after fsync but before native
LOOK/START, because the read-only evidence callback
`_stage27h_capture_prepared` still refused `action_index >= 4`.
This was a missed pre-World source guard and a **HOLD**, not a move failure,
Target arrival, or ordinary Budget exhaustion. No attempt is made to reuse
or silently close this WAL. The exception prevented completed post-loop B
Intent/Skill/Memory comparison, owner model HTTP census, and L0 time/observation
readback. B WAL was empty, but B full cognitive preservation is unqualified.
A/B QUIT, Paper save/stop and process/GPU cleanup were verified by LocalCodex;
183 evidence files passed SHA256 readback. No SNEAK or Goal/Skill success
was observed.

**A Lane evidence correction, future Worlds only:** The original collector
keeps Stage27h/i 4-child maximum. Stage27j's immutable, original accepted
12-Action Preset is the *only* caller that may pass
`long_stage27j=True`, and then the collector also requires the original
PREPARED WAL row to carry its exact 12 Action/45,000ms/6.0m Budget.
The collector only copies an fsynced canonical WAL, before any native
effect; it does **not** grant motor authority. A source-shaped integration
test now drives all 12 children through the original issuer and checks the
fifth, ninth and twelfth PREPARED readbacks, reject-old-cap control,
index-13 rejection, forged action and write-once no-replay.
The original fifth PREPARED remains unresolved in the old World.

## Real World DEV follow-up

Read current PR and exact-HEAD CI first; independently inspect original
asset hashes, native Paper/Mineflayer/Java/Node and Gemma/llama.cpp
ownership/slot, source ACLs and Preflight invariants. With the standing
Minecraft EULA + real DEV approval, run **at most one new isolated World**
using `experiments/p0d_stage27_real_place_move_dev.py --stage27j-long-move`.
Never reuse Stage27i World UUID
`47f52f5a-3fe9-4113-8ef5-f9065cd09245`.
If no MOVE selected, no physical Action. If PREPARED/STOP uncertainty,
HOLD and no retry. Preserve full native and original HTTP bytes, terminal
WAL per child, B cognition before/after, SHA256SUMS independent readback,
Paper save/stop and GPU cleanup. Do not claim Skill/Goal success,
learned parameter optimization, QUAL or SCIENCE.
