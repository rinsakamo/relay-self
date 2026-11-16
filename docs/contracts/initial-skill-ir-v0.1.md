# RelaySelf Cognitive v0.1 — initial physical Skill IR / finite L0 DEV

**Scope:** offline only, independent of #860/#851/#878, based on Draft #844
`b7e043ff4897051e53635b327c8f928feef70ef7`. Parent #828,
Common I/O #829, Schema #831, physical Skill/Action #843.

## Source audit and physical status

| Initial Skill | Existing input | Actual bridge ability | v0 status |
|---|---|---|---|
| EAT | `initial_patterns()` HUNGER_RELIEF / FOOD; L1 Option | Mineflayer `equip_item` + `consume_held` already ordered as the **single parent EAT@1** by #844's WAL-owning DEV issuer | L0 Interpreter → opt-in single EAT parent WAL issuer; physical food/inventory observation verified only in scripted DEV |
| ATTACK | `initial_patterns()` DEFEND_SELF / ZOMBIE; L1 Option | `attack_entity(entity_id)` in Mineflayer bridge | proposal plus opt-in one-shot ATTACK WAL issuer for native ACK/hurt correlation; no independent damage attestation |
| MOVE | optional `EXPLORE_WORLD / MOVE@1` Goal, explicit exploration Need and hash-bound configured L1 target | Mineflayer `look → set_control(forward) → clear_controls`, native position/probe | **opt-in bounded motor WAL issuer**, positive motion + two post-STOP native probes; **Paper tick settling/arrival NOT attested** |
| REST | fatigue is a **constraint-only** Schema signal | `clear_controls` does not attest stamina recovery / REST success | **UNMAPPED**, no compiled IR/physical issue |

The above bridge methods are protocol entry points, **not** proof of native
authorization, physical effects or independent Paper World truth. No action
succeeded in a real World as a result of this PR. A known action name does not
make a target valid. `PhysicalCapability.available` is an adapter claim, not
a permission grant; the trusted gateway/issuer must ground it at runtime.
The native `attack_entity` target uses a process-local entity ID, not a
cross-restart UUID. MOVE is a strictly bounded, guarded DEV motor action;
REST remains unmapped. Neither is enabled by swapping strings.

## Data flow (no hidden chooser)

```text
WorldBody/source-qualified Percept
    -> existing CPU Schema / Goal candidate / matched bounded Option
    -> existing L1 SELECT -> Selection.READY(goal, skill@version, exact target)
    -> existing Self IntentCommitment.commit + SkillExecution.start [CALLER]
    -> compile_initial_skill(Option, typed PhysicalCapability)
    -> FiniteSkillInterpreter.begin(Selection, IR, existing owners,
                                   registered_versions, deadline_ns)
    -> CHECK_TARGET on typed readback (missing/foreign=UNKNOWN)
    -> propose(binding, capability, readback, owners, supervisor)
       -> original PhysicalActionPort -> ActionLifecycle.PROPOSED
    -> external one-shot DEV issuer alone: auth, durable PRE-ISSUE WAL,
       Native Action ACK/Outcome / unresolved STOP; NO default permissions
    -> observe_action(ActionLifecycle, authenticated issuer witness)
       -> NEXT_STEP / YIELD_EVALUATION / NOT_EXECUTED / STOP_UNKNOWN
    -> original SkillExecution/Intent/Experience owners evaluate [CALLER]
```

The interpreter has **no native methods, scheduler, IO, model execution or
journal writes**, and does not mutate the Intent/Skill/Action owner. It never
calls `authorize`, `issue`, `succeed`, `complete`, or an automatic restart.
`YIELD_EVALUATION` means at most qualified physical *step progress*; it is
**not Skill/Goal success, C1 evidence or World-side consequence**.

## Paper STOP tick/XYZ independent evidence extension (DEV-only)

The new isolated `P0MMoveWitness` Paper plugin is a **read-only**
main-thread actor position sampler and is **not** the Checkpoint #878
P0D tick witness. The original native MOVE parent keeps the existing
Self-owned physical WAL and CPU L0 Action owner. An optional strict
`PaperMoveWitnessSession` arms a nonce+World UUID+actor UUID+native
session+original Action ID **after** the WAL PREPARED reservation and
**before** native LOOK; it sends its STOP marker only after the native
`clear_controls/applied` ACK. Paper's live main-thread task records
a consecutive tick/XYZ series through STOP marker + 16 ticks.

`qualify_paper_move_trace` independently checks the reported Paper
boot/session/action/World/actor, ordered Paper process log markers, Paper
start/native start agreement within 0.20m, Paper targetward progress
≥0.25m and **every XYZ position during ticks STOP+8..STOP+16**
within 0.06m of the first of those post-settling positions.
The completed raw file has a SHA256 evidence digest. Any absent or
foreign Paper proof when the strict mode is enabled **blocks WAL terminal
close and leaves UNKNOWN / STOP across restart**. It is never replaced
with a native-only success.

This proves at most **an eight-Paper-tick position stability interval**,
not causally server-acknowledged STOP, terminal velocity zero, collision
freedom, arriving at target, a real-World qualification or cross-World
Checkpoint consistency. The actor UUID and purported owned process log
are operator-provided inputs, not authenticated cross-process identity.
The raw Paper traces and logs remain necessary original artifacts.

The user-optional CLI flags are `--paper-move-spool`,
`--paper-move-owned-log`, `--paper-move-world-uuid` and
`--paper-move-actor-uuid`, all or none, with exclusive
`--physical-move-dev`. The reporting field
`paper_move_position_stable_8_ticks` is true only on complete strict
trace verification. `native_move_paper_settled_attested` and
`native_move_arrival_attested` remain false for all DEV trials.

See [P0M exact-field runbook](../experiments/cognitive-move-paper-16tick-dev.md).
This PR tests scripted native/Paper observer traces and compiles
the Paper 1.21.8 plugin with Java 21. **No real Minecraft/Paper/Gemma
execution was performed** at this extension stage.

## Latest continuation — one-shot MOVE native control and two STOP probes (OFFLINE DEV)

This stage **supersedes the earlier MOVE-mapping-only status** in historical
sections below. The default Cognitive/Schema runtime remains unchanged;
actual MOVE is opt-in via `--physical-move-dev` with explicit
`--exploration-need` and `--move-destination ID,X,Y,Z`. Without the Need,
L1 has no MOVE candidate; without any configured destination its unresolved
exploration Goal may escalate to L2. Operator-configured coordinates are
non-native claims, and their source/XYZ data are SHA256-bound to the
selected L1 `destination:<id>@<digest>` reference. They are **not** claims
of a navigable route, safe terrain, nearby blocks or actual goal arrival.

The already-selected target is checked against a fresh native probe and
bounded `ResolvedMoveTarget` (0.4–4.0m horizontal, ≤0.25m vertical).
The existing `IntentCommitment`, `SkillExecution`,
`PhysicalActionPort.PROPOSED`, `FiniteSkillInterpreter`, and
`ActionSupervisor` provide the **single** lifecycle. Only the separate
`issue_selected_move_dev` may emit native effects, after independently
checking two distinct native probes, Body viability, exact Option/Goal,
target digest, current position, computed yaw/distance, scope, non-busy
movement channel and separately labelled DEV PROPOSE/ISSUE grants.
Those operator labels are **not independently authenticated principals**.

The existing shared Self `PhysicalActionJournal` now accepts a MOVE parent
with `PREPARED_UNRESOLVED` fsynced **before the first LOOK or motor command**.
Unlike EAT/ATTACK rows, a MOVE row carries a dedicated `motion` block:
configuration source/destination ID, exact start/target XYZ, and (only
upon terminal closure) progress sample plus two STOP probe seqs/positions.
The schema-1 journal validates these MOVE-specific fields without changing
the exact persisted shape of earlier EAT/ATTACK records. Cross-action
CAS/lock/source monotonicity and restart STOP/UNKNOWN are shared.

One forward burst consists of one applied `look` ACK, one applied
`set_control(forward=true)` ACK, a **native `move` observation**
showing ≥0.25m progress *toward the selected target*, one applied
`clear_controls` ACK, and two distinct request-correlated probes after
STOP separated by ≥0.15 seconds of host elapsed time. The second
probe must be within ≤0.05m of the first **in 3D**. A foreign session,
changed target, `forcedMove`/teleport-like observation, missing/rejected
ACK, insufficient progress, drift, cancellation or unavailable sensor
leaves the parent `PREPARED_UNRESOLVED`, Action `UNKNOWN`, no auto replay.
If forward might have been issued, the issuer attempts **one** best-effort
`clear_controls` on its failure path, without treating sending as evidence
of STOP ACK or reconciling the WAL. In-memory Action OUTCOME alone does
not suffice: the runner reopens the WAL and compares source, Scope, exact
Action/Intent/Skill, target, command ACK seqs and STOP probe seqs before
yielding `YIELD_EVALUATION` (never Skill/Goal completion).

The resulting terminal label is
`NATIVE_MOVE_PROGRESS_STOP_READBACK_DEV_ONLY`, not a universal
`MOVE(target)` arrival success. Two host-time-spaced native probes are
**not** an independent Paper tick check; they do not establish global
physics settling, obstacle clearance, no later displacement, death
immunity, or a multi-Self movement channel arbiter. Exact Minecraft
movement distances/STOP qualification require a separate real Paper
admission experiment and safe operator grant. Recovered cursors or this
terminal record must never confer new motor permission across a changed
World session/checkpoint.

CLI rejects simultaneous EAT/ATTACK/MOVE, legacy unfenced native issuance,
and explicit shadow-only mode. Tests cover the complete scripted L1→L0
MOVE sequence, preissue WAL readback before LOOK, short progress and STOP,
drift/missing ACK/forcedMove/foreign source/cancel→UNKNOWN with restart
STOP, geometry/yaw tampering and prior Skill regressions. **No real
Minecraft, local GPU or QUAL/SCIENCE run was performed.**

## v0.1 continuation — one-shot L1 EAT → L0 → WAL issuer (offline DEV)

The existing #844 `experiments/cognitive_physical_eat_runner.py` now invokes
`propose_initial_skill_from_cognitive_readonly_evidence`, rather than creating
its Physical ActionPort proposal directly. The adapter reuses the **same**
two-probe read-only selection witness and exact native Target, compiles the
already-selected `EAT@1` against the explicit WorldBody capability, and
runs `FiniteSkillInterpreter.begin → CHECK_TARGET → ACTION`. The only emitted
physical artifact is the existing `ActionLifecycle.PROPOSED`. No additional
Intent, SkillExecution, Action ID, issuer, S49 chooser or WAL is created.

Only the existing, separately guarded `issue_selected_eat_dev` may issue the
EAT parent (equip/consume children). On successful return, the runner **restores
the persisted journal** and verifies its digest, Self/World/Intent/Skill/Action,
exact native source/probe IDs, child effect sequences, after-probe, food
increase and inventory decrease against the physical receipt. Only then does
the interpreter receive an issuer-constructed `ActionOutcomeWitness` to emit
`YIELD_EVALUATION`. This **does not** complete SkillExecution, Intent or C1.
A failed journal readback/unknown effect is not retried or reported as Skill
success. The CLI exposes `initial_skill_ir`,
`initial_skill_step_status`, and `initial_skill_evaluation_status`
separately from physical native effects.

The #844 journal is still **EAT-only**; ATTACK is tested as a nonissuing
Interpreter/ActionPort proposal. MOVE remains unmapped to a verified
`MOVE(target)` capability and REST remains unmapped to verified fatigue
recovery. Legacy `--execute-native` is unchanged, unfenced and mutually
exclusive with `--physical-eat-dev`; no global process arbiter or
authenticated grants have been added. The adapter maps an existing known
bridge capability as available for this explicitly guarded DEV test only,
not as proof of WorldBody success/permission.

Tests: preflight EAT/ATTACK IR routes, unregistered version denial, CLI EAT
single parent with persisted PRE-ISSUE reservation and terminal readback,
L0 rejection before any WAL/native issue, unknown equip/consume/after-probe
and restart STOP. Synthetic scripted Mineflayer/provider only.

## 2026-11-15 continuation — ATTACK parent WAL / source-correlated hurt (offline)

`--physical-attack-dev` now selects an **exclusive** opt-in one-shot physical
mode with the same grant labels, Self-owned `PhysicalActionJournal`, L1
read-only two-probe target admission and existing `PhysicalActionPort`.
`experiments/cognitive_physical_attack_runner.py` consumes an actual L1
`ATTACK@1` and executes `CHECK_TARGET → ACTION(PROPOSED)` via the same
`FiniteSkillInterpreter`. Only the existing physical ActionLifecycle +
supervisor issue path is used. **No new Intent, SkillExecution or chooser.**

The new `issue_selected_attack_dev` keeps the **same WAL file and CAS/lock/fsync
schema as EAT**. Before sending `attack_entity`, it creates one durable
`PREPARED_UNRESOLVED` parent record. It requires a positive native
`attack_entity/applied` ACK **and a separately observed `entity_hurt` on
the exact selected runtime entity ID** with non-null `source_entity_id ==
actor_entity_id` (Mineflayer reports the Self actor ID), followed by a
current correlated probe. Journal terminal:
`NATIVE_ATTACK_HURT_CORRELATED`; row `effect_seqs=[attack_ack_seq,
hurt_event_seq]`. All prior EAT rows are retained/validated unchanged.
Missing, foreign, ambiguous or rejected ACK/hurt, death, native transport
loss and after-probe failure leave the fsynced Action **UNKNOWN / STOP**;
no repeat or journal reset on restore, even if another Action type is
selected. A successful one-shot runner independently reopens WAL and
verifies the original Action/Intent/Skill/Target, probe source, ACK/hurt
sequences and terminal close before yielding `YIELD_EVALUATION`.

**Evidence limitation**: `entity_hurt` is a Mineflayer event and
`actor_entity_id` is a bridge-provided value, **not** an independent
Paper event/UUID/health delta. This remains
`NATIVE_ATTACK_HURT_CORRELATED_DEV_ONLY`, not
`DAMAGE_ATTESTED`, zombie death, semantic Skill success or qualification.
The event can arrive before the ACK and is matched within one bounded
source-qualified receive window. Native process-local entity IDs must never
be reused as immutable identity across a Minecraft restart. Real server
damage would require Paper UUID/tick/health and native source/time joins
without an invented success threshold.

CLI fields include `physical_attack_dev_selected`,
`physical_attack_parent_action_id`, `native_attack_hurt`,
`native_attack_damage_attested=false`, the same IR status fields and
per-Action shared WAL record. `--physical-attack-dev`,
`--physical-eat-dev`, legacy unfenced `--execute-native` and explicit
read-only shadow are mutually exclusive. No real world execution took
place as part of this milestone. MOVE/REST remain UNMAPPED.

## 2026-11-15 continuation — MOVE Target resolution only (OFFLINE DEV)

The existing Mineflayer protocol has `look`, `set_control`,
`clear_controls`, source-qualified position probes, and the
`mineflayer_yaw_to_target` helper. The superseded FLEE experiment uses
these commands, **but neither that code nor a `clear_controls/applied` ACK
attests qualified target-directed MOVE, path/collision clearance, final
settling or restart-safe motor ownership.** Thus the innate MOVE
`InitialSkillDescriptor` deliberately remains `UNMAPPED`, and a MOVE
IR cannot compile into `PhysicalActionPort.PROPOSED` or issue controls.

A new optional `initial_patterns_with_move()` registry (distinct revision
from the default three-pattern registry) supplies `Predicate.EXPLORE` and
the innate `exploration-move` Schema: Need signal `exploration_need=true`
→ Goal `EXPLORE_WORLD` → already-grounded destination options. The base
Schema stays unchanged for existing WorldBody runtimes. The Need signal
must be explicitly supplied by Self/Schema input; it is not fabricated from
idleness or automatically generated by the target resolver. When no
qualified destination is supplied, Goal remains `unresolved`; the existing
numbered L1 option `ESCALATE_L2` is preserved. No automatic random MOVE.

`native_schema_percept(..., exploration_need=True)` projects existing
`ControlledScenario.destinations` with **their own configured provenance**,
never relabeling them as native Mineflayer observations. A destination
`target_ref` has form `destination:<id>@<sha256>`, whose digest binds
the exact binary floating-point coordinates, ID, configuration source and
source reference. Identical IDs with changed coordinates/provenance produce
different refs; previously selected Options cannot silently retarget.
These are **configured coordinate claims**, not observed reachability.

`resolve_selected_move_target(selection, frame, percept, current_probe,
scenario)` consumes an existing L1 `Selection.READY` and revalidates
Goal/Skill/Target option, original target registry, Self/World scope, exact
fresh native source/sequence/request, body viability, positive configured
provenance, digest-bound coordinates, and distinct horizontal target.
It reuses `mineflayer_yaw_to_target`, returning a
`ResolvedMoveTarget` with current position, target position, yaw,
horizontal distance and vertical difference — **advisory geometry only**.
It does not infer a traversable path, collision status, motion result or
suitable control-duration.

`execute_one_cognitive_world_turn(..., exploration_need=True)` now
takes this path on an explicitly owner-admitted MOVE skill, after an
additional fresh native probe. It returns
`MOVE_TARGET_BOUND_NO_ISSUE` with `move_target` and an unchanged
Intent/Action owner (or refuses an expired/foreign target). The old unfenced
`issue_native=True` MOVE branch is explicitly rejected rather than
falling back into the superseded FLEE executor. Until a qualified bounded
motor/STOP/settling issuer exists, MOVE has **zero native issuance**.
This new route is opt-in only: the current production/dev CLI supplies
neither the exploration Need nor MOVE registered capability.

**Checkpoint interface:** destination ref+configuration digest+source
revision, selected Goal/Skill ID/version, new native probe session/sequence,
and horizontal geometry may be recorded as *cognitive observations*, not
Action owner or motor grant. On a different World/checkpoint branch, stale
destination revisions and old cursor/position should be rejected.
Unresolved physical controls after any future MOVE issuance require
preissue WAL and STOP reconciliation; an observed final position alone is
not proof that controls were cleared or settling completed.

Offline tests cover Need absent, unresolved Goal→L2, unknown skill, two
chosen targets, geometry and same-ID hash revision, stale/missing/foreign
target, source sequence, body death, direct L1→fresh native MOVE read-only
one-turn and refusal of legacy motor issuance. No real Minecraft/Gemma
movement, distance threshold attainment, collision/settling or physical
qualification claimed.

## IR v0 / bounded semantics

- Shared immutable `PhysicalSkillIR` for INNATE and LEARNED:
  `skill_id`, `version`, `goal_id`, `target_kind`, `origin`,
  `provenance`, `steps`. Steps are `CHECK_TARGET` or
  `ACTION(capability_ref, capability_version)`; no arbitrary Python,
  LLM output execution, recursion, native commands, loops or implicit target
  selection. At most **8 steps and 4 physical Actions**.
- The interpreter receives the exact already-selected `Option`, actual
  existing `IntentCommitment`, current `SkillExecution`, and an externally
  owner-approved version set. It does **not** choose the Skill or register the
  L2 candidate. A newly generated hypothesis with no owner registration
  is rejected. To use a new learned IR, the existing owner must first accept
  its version and issue a matching, separately selected Option.
- `CHECK_TARGET` is a *positive* check only. Missing target/coverage,
  foreign session or unviable body are not interpreted as success or absence;
  no action proposal is issued. Every `ACTION` revalidates the full
  exact binding with the existing `propose_bound_physical_action`: live
  Intent and Skill, Goal, target, source/probe, capability/version, supervisor
  conflict, unresolved prior action.
- `ActionLifecycle.PROPOSED/AUTHORIZED/ISSUED` stays pending. `DENIED`
  is `NOT_EXECUTED`. `TIMEOUT/UNKNOWN` or absent/uncorrelated WAL-close
  evidence is `STOP_UNKNOWN`, never auto-retry. `OUTCOME` plus a witness
  produced and independently authenticated by the physical issuer can advance
  locally, but **does not establish semantic success**. All witness fields
  are adapter claims until linked to actual native/server evidence.
- An interpreter instance admits **one** ephemeral Skill cursor; it is not a
  second lifecycle owner, persistent executor or general multi-Intent book.
  Each cursor is tied to a process-local identity object; another interpreter
  (restart) cannot resume it. A current owner/Action outcome is required
  after recovery before a new Skill run can be admitted. No cursor, pending
  action or native identity may be reconstructed from a stale checkpoint.

## Handoff to Checkpoint #860/#851 (integration contract; not integrated)

The checkpoint branch should **not** store `SkillCursor` as a restorable
permission, persist an Action as issued based on a PROPOSED result, or
normalize UNKNOWN into failure/success. The minimal interface is:

| Checkpoint input/read-only claim | Origin/identity requirement | Upon restore |
|---|---|---|
| `SkillIR(skill_id, version, origin)` | accepted owner registry revision and source; candidate != qualification | keep definition, **not live execution** |
| `Option(goal_id, skill_id/version, target_ref)` | existing Schema selection + owner decision receipt | stale; reselect on new Present/current source |
| `IntentCommitment` / `SkillExecution` | original owner snapshot + intent ID and execution ID | owner-led reconcile only |
| `ActionLifecycle(action_id, run_id, intent_id)` | original ActionSupervisor + durable WAL receipt | reconciliation first; never reinterpret Action PROPOSED as ISSUED |
| native evidence | world/session/branch/checkpoint/tick, source, seq/request ID and where possible native UUID join | fresh perception/revalidation needed; runtime entity ID is not cross-restart identity |
| `PhysicalActionJournal` (EAT, #844) | Self-owned fsynced PREPARED_UNRESOLVED / terminal CAS and SHA256 | unresolved means STOP; no automatic repeat |
| `ActionOutcomeWitness` | **physical issuer** authenticates action ID/native source/journal close/effect; caller booleans are not proof | advisory only until source-verified; never enough to clear checkpoint gate |
| interpreter cursor | **ephemeral**, process-local lease | discard; don't resume or reissue |

Checkpoint's `CANDIDATE_REOBSERVE` is not an `ActionPort` grant.
The physical integrity gate and cognition/epistemic reconciliation remain
separate. Multi-Self and physical channel arbitration are not implemented
by this v0 controller; the current #844 ActionPort serializes open Actions
and retains a single CurrentIntent constraint.

## Verification / claims

`tests/test_initial_skill_ir_v0.py` covers EAT/ATTACK compilation,
MOVE/REST abstention, original Schema Goal/Option, existing owner
lineage, nonissue, lifecycle outcome distinctions, UNKNOWN/stale scope,
unsupported capability, checkpoint/restart cursor fence, deadline,
same-run duplicate, and learned registration vs hypothetical IR.

**OFFLINE DEV ONLY**. Tests contain synthetic native/issuer receipts,
not real Minecraft/Paper/Gemma sessions. No authentic issuer witness,
multi-Self checkpoint restore, automatic installation, motor settling,
physical-world success or QUAL/SCIENCE claim. Existing #844 physical-EAT
candidate remains a separate experimental path that must be used only
with its operator isolation, WAL restore and grants.

## Target-specific precision and L0 approach recommendation (CPU-only DEV)

Target semantics are not a global MOVE tolerance. The new
[TargetContract × ApproachController interface](target-contract-approach-v0.1.md)
separates (a) the selected Goal/Target's admissible position interval,
precision, facing/LOS, and stillness conditions; (b) source-qualified
WorldBody gait stopping/position uncertainty observations; and (c) the
finite CPU recommendation of APPROACH/DECELERATE/STOP/VERIFY/REPLAN/HOLD.
PLACE, SELF_AT_BIND step, and moving ENTITY_LIVE ranges share the same
mechanism but may ask for different precision and arrival behavior.

The current L1 MOVE Option selects a destination *without* an arrival
precision revision. A new condition bound via
`propose_arrival_contract_for_selected_move` is therefore **a separate
contract candidate**, NOT retroactive L1 approval or permission to alter
the one-shot native MOVE issuer. Existing 0.05m native STOP residual check,
Paper witness, WAL and unresolved 2026-11-16 original real World trial
remain unchanged. No new physical movement has been run for this interface.


## Skill parameters without complex innate Skill logic (2026-11-16 offline DEV)

[Parameterized Skill ABI v0.1](parameterized-skill-abi-v0.1.md) formalizes
`SkillDefinition` (**Goal-independent innate/learned ability**) versus
`SkillInvocation` (**source-bound selected Goal+Target+Constraints+Budget
and typed extra arguments**). The same `MOVE@1` definition can represent
exploration, a relative step, entity-relative approach or item pickup
without hardcoding each Goal as a new innate Skill or a motor routine.
The interpreter still executes the simple finite
`CHECK_TARGET → ACTION` steps. `PhysicalSkillIR.invocation` and
`SkillCursor.invocation_ref` preserve selected parameter identity.

`LearnedSkillProgram` admits explicit, bounded type-checked call templates,
including a finite acyclic DAG of registered learned Skills, but **does
not run or register** them. No native issuer can silently consume these
new parameterized IRs: until physical constraints/budgets and the
single-parent source-bound issuer exist, the interpreter refuses
parameterized `propose()` after its read-only target check.

Legacy `compile_initial_skill` and actual EAT/ATTACK/MOVE physical
issue paths keep their original Goal/Target/STOP/WAL admission. The
2026-11-16 `NATIVE_ISSUED_UNKNOWN` original WAL stays unresolved, no new
World action is claimed, and Checkpoint #878 is unchanged.
