# Cognitive v0.1 TargetContract × L0 ApproachController (CPU-only DEV)

**Owner:** #828 / #829 / #843 / Draft #882. This is a separate *unissued*
control/contract seam, not a replacement physical MOVE, an ATTACK range
certificate, or any promotion of the 2026-11-16 real-world
`NATIVE_ISSUED_UNKNOWN` trial. That trial's original Self/WAL/Action remains
`PREPARED_UNRESOLVED` and must not be replayed.

## Split the responsibilities

- **Schema/Goal:** declares the *meaning* and desired acceptance envelope of a
  Target, which may be a region in the World, a Self-relative step frozen at a
  source-qualified starting pose, or a live Entity-relative reach envelope.
  It does not prescribe a Minecraft control key.
- **L1:** selects a specific Goal+Skill+source-bound Target revision, or defers /
  escalates. A new condition hash must require a new L1 bind before it could
  ever enter the real motor path.
- **WorldBody:** supplies observed position, velocity, heading, target/entity
  age and visibility, route clearance, and source-qualified/age-bounded
  calibrations of gait stopping distance. A guessed STOP distance is not
  qualified physical evidence.
- **L0 ApproachController:** *recommends* APPROACH(gait), DECELERATE(gait),
  STOP_RECOMMENDED, VERIFY_STILLNESS, REPLAN, HOLD_UNKNOWN, or
  TARGET_CONDITION_OBSERVED from those inputs. It never sends LOOK,
  set_control, clear_controls, Paper markers, or a new Action. It does not
  manage WAL, authorizations, or a retry loop.
- **Physical ActionPort:** remains the **only** exclusive WAL-owned motor
  issuance path. It may consume a qualified controller plan in a **future
  separately gated integration**, with a single parent Action and auditable
  internal control transitions. No new authority is granted here.
- **Evaluation:** distinguish a geometric condition being observed from
  actual physical settling, a native Action Outcome, and Skill/Goal success.

## Typed interface

New modules:

- `src/relay_self/target_contract.py`
- `src/relay_self/approach_controller.py`
- `experiments/cognitive_move_target_resolution.py`:
  `propose_arrival_contract_for_selected_move` (source-bound **proposal** only)
- `tests/test_target_contract_and_approach_controller.py`

`TargetContract` binds Self/World scope, selected `target_ref`, Goal,
semantic TargetKind, reference frame, original provenance, bound native
sequence and `ArrivalCondition`. Its `contract_ref` is a deterministic
SHA256 of scope, source, geometry, target identity, freshness and **all
precision requirements**. Changing an allowed region from 1m to 0.1m or
changing an Entity UUID/observation contract creates a distinct reference.
The hash does not authenticate the creator; original ownership/source must
still be admitted.

`ArrivalCondition` contains an acceptable **distance interval**, vertical
tolerance, optional facing tolerance, line-of-sight requirement, maximum body
speed, and separately specified quiet tick count plus maximum positional
drift. These are caller- or Schema-selected **goals**, not one global .05m
motor threshold.

| Example | Coordinate interpretation | Condition shape | Typical control response |
|---|---|---|---|
| Enter location | Static WORLD region | Radius and Y bound, possibly no standstill | Fast approach, then transition to slow/STOP if precision requires |
| One step ahead | SELF_AT_BIND snapshot (origin + endpoint) | Small endpoint radius + 8 settled ticks | Slow/SNEAK if calibrated, STOP early, verify |
| Attack-position of moving Zombie | ENTITY_LIVE at fresh Entity observation | Min/max reach range, facing, actual LOS; may not require standstill | Move toward live envelope; abort/replan on stale enemy, too-close or blocked LOS |
| Escape | Future Target proposal | Safe region/distance from threat, time and risk constraints | May prioritize speed; **not implemented** as a special-case motor |

No Minecraft-specific hardcoded 1-block step, 3m attack range or acceleration
curve is introduced. Different numerical examples in tests are **synthetic
source-shaped fixtures** demonstrating that differing demands yield differing
controller decisions, not real-world calibration.

## Controller and evidence boundary

`TargetBodyObservation` carries typed, same-World/source-sequenced Body
observations. A moving entity must have the exact matching ID and a fresh
observation at or after the contract's bound source sequence; wrong IDs,
stale `entity_observed_seq`, missing LOS/facing, or an unknown Body speed
fail closed. `BodyApproachCapabilities` carries bounded gaits with
per-gait *observed* speed and *conservative* stopping distance, separate
source and freshness limits, and positional uncertainty.

The pure `recommend_approach` function computes the distance to the *nearest
valid Target envelope boundary*, not the distance to an arbitrary XYZ
centroid. It chooses the fastest calibrated gait only if:

```text
calibrated_stop_distance + position_uncertainty < gap_to_envelope
```

No fitting gait => `STOP_RECOMMENDED`, **not another uncontrolled forward
burst**. A selected gait slower than the currently calibrated mode yields
`DECELERATE`. Unknown route, stale gait, stale observation, missing speed or
foreign Self/World => `HOLD_UNKNOWN`. Inside a precision envelope but still
moving => `VERIFY_STILLNESS`. Too near an enemy, bad Y, missing or blocked
line of sight, or wrong orientation => `REPLAN` or `HOLD_UNKNOWN`, never
implicitly ATTACK or backward MOVE.

`TargetAssessment.condition_observed=true` is **not**
`Goal succeeded`, `Skill completed`, `Action OUTCOME`, `qualified STOP`,
or `authorized`. Those flags always remain false for this pure stage.
No inference that a static location requires standstill is made unless the
Goal explicitly demands it. Conversely, an entity-range target may be
meaningful while moving if visibility and facing are actually observed.

## Existing MOVE and staged integration

Current physical `MOVE@1` still accepts only a source-qualified configured
`EXPLORE_WORLD` destination, issues one bounded native forward burst and
checks the existing STOP/Paper requirements. **No live semantics or velocity
sensors are silently added**. Its real physical .05m residual STOP gate is
unchanged. `propose_arrival_contract_for_selected_move` can associate a
candidate `PLACE` precision with an **already L1-selected** destination
without touching the Action issuer. L1 has not yet selected the proposed
`contract_ref`; the candidate must NOT be used to grant the existing motor
path, change the earlier WAL, or claim Goal success.

Next integration requires:

1. Target precision/capabilities to be part of the *original* selected L1
   Option and source-revision check, not an unreviewed postselection overwrite;
2. Live Body speed, sprint/sneak and target entity evidence with provenance,
   actual clearance/obstacle information, and measured gait stop-distance
   calibration; reuse preexisting G4/S50 sources before adding producers;
3. An explicit finite **single-parent** approach/decelerate/STOP/settling
   execution contract with one Self-owned WAL and child control transition
   receipts; never a hidden second issuer or autonomous retry;
4. Separate reached geometry, post-STOP stillness, and native physical
   terminal observation; true STOP may require more than two immediate native
   probes, with independent Paper ticks;
5. New operator grant and fresh Self/World/WAL/Action for any real motor test.
   Prior `NATIVE_ISSUED_UNKNOWN` and raw evidence stay immutable.

## Offline adversarial fixtures

Run `pytest -q tests/test_target_contract_and_approach_controller.py`.
Tests cover static place versus precise step versus live moving Entity,
changing precision changes contract ref, early/late STOP choice, RUN→WALK
and WALK→SNEAK recommendations from **injected synthetic gait curves**,
missing Body speed, missing route clearance, stale/foreign Entity,
wrong World or Self, blocked LOS/incorrect facing, unknown stillness, invalid
target intervals and out-of-source precision mutations.

**Overall:** `OFFLINE_CONTRACT_AND_CPU_CONTROLLER_DEV_ONLY`.
No real Minecraft World/LLM/Paper attempt, new issuer, qualified MOVE
terminal, calibration validity, or transferable grant is claimed.


## 2026-11-16 second continuation — original L1 target precision selection (offline)

The optional `ControlledDestination.arrival_condition` is a typed input to
the existing *current* WorldBody/Schema projection. Before any L1 inference,
`native_schema_percept` creates a `TargetContract(PLACE, WORLD, ...)` using
the declared arrival envelope and source-stable configuration revision.
`WorldPercept.Target.arrival_contract` carries this immutable typed value into
the CPU `cpu_schema_epoch`; each matching `Option.arrival_contract` now
**includes the same contract directly**, not merely a post-L1 suggestion.
`assemble_l1_select` exposes to the model the acceptance interval,
vertical tolerance, stillness count and exact immutable `condition_ref`.
Existing EAT, ATTACK and no-envelope MOVE choices keep
`arrival_contract=None`; no default tolerance is manufactured.

The *configured target* contract is bound to its source revision at sequence 0,
not reissued at each native Percept refresh. Fresh current native Body
observation still has its **own** `observed_sequence` and is checked
independently at the source-bound MOVE Target resolver. Consequently the
original Option remains exactly equal to the later fresh Schema Option when
the Goal, Target and contract have not changed; changing a tolerance,
precision, scope, owner, target provenance or geometry makes the old selected
Option unequal or is rejected at resolution. Even if a caller tries supplying
an altered scenario with the old frame/percept and unchanged destination
coordinate hash, `resolve_selected_move_target` rejects the mismatch.

`ResolvedMoveTarget.arrival_contract` now carries **the originally selected
contract**. `assess_l1_selected_move_approach` gives a pure CPU
ApproachRecommendation only when this exact selected contract, selected
Target, current Self/World and source sequence match. It may recommend
`DECELERATE` under synthetic calibrated gait evidence, but all Action/Goal
authority flags remain false. In particular the old
`propose_arrival_contract_for_selected_move` is **still only a candidate
for a MOVE with no selected contract** and refuses to overwrite an existing
selected contract.

**Motor pre-ISSUE fail-closed**: until actual WorldBody gait calibration and
one-parent finite approach/decelerate/STOP execution are integrated,
`issue_move_from_selected_l1_dev` and `issue_selected_move_dev`
both refuse selected non-null arrival contracts **before new native controls
or WAL preparation**. The legacy unconditioned MOVE path still behaves
exactly as it did before these additions. The original real World
`NATIVE_ISSUED_UNKNOWN` parent, source hashes and unresolved Self WAL are
not changed. No new World grant is implied.

Regression tests cover the L1-numbered description, option staleness across
scenario edits with or without a fresh Percept, real-shaped post-L1 native
probe refresh, CPU read-only gait recommendation and legacy motor refusal.
To test without any motor/LLM/World:
`pytest -q tests/test_cognitive_move_target_resolution.py tests/test_cognitive_physical_move_issue_dev.py`.

**Status: ORIGINAL_L1_CONTRACT_SELECTION_OFFLINE_DEV / PHYSICAL_CONDITIONED_MOVE_HOLD /
REAL_WORLD_NOT_RUN / QUAL_NO_GO.**
