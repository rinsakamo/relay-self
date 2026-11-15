# RelaySelf Cognitive v0.1 — initial physical Skill IR / finite L0 DEV

**Scope:** offline only, independent of #860/#851/#878, based on Draft #844
`b7e043ff4897051e53635b327c8f928feef70ef7`. Parent #828,
Common I/O #829, Schema #831, physical Skill/Action #843.

## Source audit and physical status

| Initial Skill | Existing input | Actual bridge ability | v0 status |
|---|---|---|---|
| EAT | `initial_patterns()` HUNGER_RELIEF / FOOD; L1 Option | Mineflayer `equip_item` + `consume_held` already ordered as the **single parent EAT@1** by #844's WAL-owning DEV issuer | finite IR compiles **only** when actual `PhysicalCapability("EAT", 1, "hand", "FOOD", True)` is supplied; proposal possible; physical path exists in #844 but not invoked here |
| ATTACK | `initial_patterns()` DEFEND_SELF / ZOMBIE; L1 Option | `attack_entity(entity_id)` in Mineflayer bridge | proposal-only when adapter supplies versioned available capability; no canonical ATTACK WAL-owning issuer integrated |
| MOVE | no current Schema Goal/Skill option | `set_control` changes controls, but this does **not** attest general `MOVE(target)`, pathing, motion settling, collision or stop | **UNMAPPED**, no compiled IR/physical issue |
| REST | fatigue is a **constraint-only** Schema signal | `clear_controls` does not attest stamina recovery / REST success | **UNMAPPED**, no compiled IR/physical issue |

The above bridge methods are protocol entry points, **not** proof of native
authorization, physical effects or independent Paper World truth. No action
succeeded in a real World as a result of this PR. A known action name does not
make a target valid. `PhysicalCapability.available` is an adapter claim, not
a permission grant; the trusted gateway/issuer must ground it at runtime.
The native `attack_entity` target uses a process-local entity ID, not a
cross-restart UUID. MOVE/REST cannot be enabled by swapping strings.

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
    -> external single issuer alone: auth, durable PRE-ISSUE WAL,
       Native Action ACK/Outcome / unresolved STOP [NOT IMPLEMENTED HERE]
    -> observe_action(ActionLifecycle, authenticated issuer witness)
       -> NEXT_STEP / YIELD_EVALUATION / NOT_EXECUTED / STOP_UNKNOWN
    -> original SkillExecution/Intent/Experience owners evaluate [CALLER]
```

The interpreter has **no native methods, scheduler, IO, model execution or
journal writes**, and does not mutate the Intent/Skill/Action owner. It never
calls `authorize`, `issue`, `succeed`, `complete`, or an automatic restart.
`YIELD_EVALUATION` means at most qualified physical *step progress*; it is
**not Skill/Goal success, C1 evidence or World-side consequence**.

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
