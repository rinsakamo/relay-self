# Post-MAIN S1-S17 architecture freeze

## Status and scope

S18 freezes the architecture implemented and qualified through exact S17 HEAD:

```
64868337510a960c140e96d5d3d20949ad53fb8e
```

The supported milestone claim is:

```
SINGLE_TRANSACTION_COGNITIVE_ACTION_LEARNING_ARCHITECTURE_QUALIFIED
```

with the terminal interpretation:

```
S18_FROZEN_AS_SINGLE_TRANSACTION_COGNITIVE_ACTION_LEARNING_ARCHITECTURE_WITH_EXPLICIT_OWNERSHIP_AND_AUTHORITY_BOUNDARIES
```

This is a **single explicitly invoked transaction** architecture freeze. It is
not an autonomous-agent qualification, not a continuous-cognition
qualification, and not a live-Minecraft qualification.

The final `STOP` after one governed retained learning update is part of the
architecture.

## Canonical graph

Legend:

- `--cog-->`: stateless cognitive transformation/orientation;
- `--guard-->`: explicit authority/contract guard;
- `--owner-->`: real owner transition;
- `--env-->`: bounded environment I/O;
- `--feedback-->`: explicit outcome-to-learning interpretation;
- `==retained==>`: governed retained-state update.

```text
structured input
      |
      --cog--> ATT
      --cog--> BLF
      --cog--> CNC
                 +--cog--> PRD --cog--> PLAN --+
                 |                              |
                 +---- caller cue ----> HABIT --+
                                                |
                                      --cog--> ROUTE
                                                |
                                          ControlCandidate
                                                |
                                      --guard--> ADMISSION
                                                |
                                             ADMITTED
                                                |
                                      --guard--> EXEC_BIND
                                                |
                              --owner--> SkillExecution.STARTED
                              --owner--> ActionLifecycle.PROPOSED
                              --owner--> AUTHORIZED
                              --owner--> ActionSupervisor.ISSUED
                                                |
                                       --env--> WORLD_EXEC
                                                |
                                         WorldConsequence
                                                |
                                      --guard--> ACTION_OUTCOME
                                                |
                              --owner--> OUTCOME / UNKNOWN / TIMEOUT
                                                |
                                   --feedback--> FEEDBACK
                                                |
                                         LearningFeedback
                                                |
                                        --cog--> LRN proposal
                                                |
                       explicit LearningUpdateAuthority
                                                |
                              ==retained==> LearningPreferenceState
                                                |
                                              STOP
```

LRN does not reenter ATT, PLAN, ROUTE, execution, or a next epoch
automatically.

## Capability taxonomy

The identifiers below are `CapabilitySpec` metadata. A CapabilitySpec itself
owns no cognitive state and executes no behavior.

### Semantic/runtime surfaces

| ID | Frozen role |
| --- | --- |
| MEM | Explicit durable Memory retention seam. |
| CTL | Existing decision-epoch coordination and bounded RelayEngine seam. |
| SKL | Existing Skill start and Action proposal owner seams. |
| TALK | Separately available open provider expression seam. |

### Cognitive mechanisms

| ID | Frozen role | Retention |
| --- | --- | --- |
| ATT | Explicit structured attention selection. | Stateless |
| BLF | Explicit evidence-support belief assessment. | Stateless |
| CNC | Explicit structured concept classification. | Stateless |
| PRD | Explicit transition prediction. | Stateless; no criterion descriptor |
| PLAN | Explicit bounded preference selection. | Stateless |
| LRN | Explicit feedback-oriented proposal + governed retained commit. | Retained owner-local LearningPreferenceState |
| HABIT | Cue-conditioned read/reuse of retained repertoire. | Retained owner-local HabitRepertoire; selection is stateless |

### Integration-only metadata

| ID | Frozen role |
| --- | --- |
| ROUTE | Stateless PLAN/HABIT route adjudication metadata. |
| ADMISSION | Stateless execution-entry guard metadata. |
| EXEC_BIND | Explicit admitted-candidate Skill/Action binding integration. |
| WORLD_EXEC | Bounded Mineflayer environment-I/O integration. |
| ACTION_OUTCOME | WorldConsequence interpretation over the existing Action owner. |
| FEEDBACK | Stateless explicit Action-outcome learning orientation. |

These integration IDs exist because `EpochPlan` requires schedulable operators
to belong to declared capability metadata. They are not new faculties and do
not establish new retained owners.

## Owner matrix

| Thing | Semantic owner | Frozen ownership claim |
| --- | --- | --- |
| Identity / Memory / retained appraisal dispositions | `PersistentCognition` | Durable immutable snapshots; explicit governed writes only. |
| Current Intent and Intent event history | `IntentCommitment` | PLAN/ROUTE cannot replace it. |
| Skill lifecycle | `SkillExecution` | Immutable lifecycle snapshots with stale-snapshot lineage guard. |
| Action lifecycle | `ActionLifecycle` | Owns legal PROPOSED/AUTHORIZED/ISSUED/terminal transitions. |
| Supervised issued Action retention, deadlines and terminal recording | `ActionSupervisor` | Typed Action runtime owner; not a cognitive scheduler. |
| Learning preference | owner-local `LearningPreferenceState` via S10 commit | New retained snapshot only after proposal + exact explicit authority. |
| Habit repertoire | owner-local `HabitRepertoire` snapshot | HABIT reads it; selection does not mutate it. |
| Epoch plan | none | Immutable stateless execution plan. |
| Capability/descriptor metadata | none | Audit/composition metadata; implementation refs are not dispatch. |
| ROUTE | none | No persistent arbitration owner. |
| ADMISSION | none | No Intent/Skill/Action ownership transfer. |
| EXEC_BIND | none | Uses existing Skill/Action owner transitions. |
| WORLD_EXEC | Mineflayer adapter only for bounded environment I/O | No Action authority, cognition, deadline, or scheduler ownership. |
| ACTION_OUTCOME | none; `ActionSupervisor` remains terminal owner | Interpretation does not create a second Action owner. |
| FEEDBACK | none | Produces structured LearningFeedback only; does not own LRN state. |

A CapabilitySpec state scope is an accessible semantic surface, not proof that
the capability metadata owns that surface. This is particularly important for
CTL and SKL.

## State taxonomy

### Transient / immutable outputs

The frozen transient objects are:

- `AttentionSelection`;
- `BeliefAssessment`;
- `ConceptRepresentation`;
- `PredictionResult`;
- `PlanSelection`;
- `HabitSelection`;
- `RouteDecision`;
- `ControlCandidate`;
- `AdmissionDecision`;
- `ExecutionBindingResult`;
- `MineflayerCommand`;
- `WorldConsequence`;
- `ActionOutcomeInterpretation`;
- `LearningFeedback`;
- `LearningUpdateProposal`.

They are audit/selection/interpretation objects, not a shared mutable global
state.

### Retained or lifecycle-owned state

The architecture retains distinct state under distinct owners:

- `PersistentCognition`: Identity, Memory, appraisal dispositions;
- `IntentCommitment`: Current Intent and event history;
- `SkillExecution`: Skill lifecycle;
- `ActionLifecycle` / `ActionSupervisor`: Action lifecycle, issued retention,
  deadlines, terminal recording;
- `LearningPreferenceState`: owner-local retained learning preference;
- `HabitRepertoire`: owner-local retained habit rules.

These are intentionally not flattened into a single `SelfState`.

## Authority ladder

The frozen progression is:

```
candidate selected
!= route adjudicated
!= admitted
!= bound
!= Skill STARTED
!= Action PROPOSED
!= AUTHORIZED
!= ISSUED
!= environment execution
!= Action OUTCOME / UNKNOWN / TIMEOUT
!= LearningFeedback
!= LearningUpdateProposal
!= committed retained update
```

More compactly, the mandatory invariants are:

```
selection != admission
admission != commitment
binding != proposal
proposal != authorization
authorization != issue
issue != physical execution
physical execution != Action outcome
Action outcome != LearningFeedback
LearningFeedback != retained update
```

No earlier stage implicitly grants a later authority.

## Frozen single-transaction trace

Trace identifier:

```
S18_DETERMINISTIC_TEST_APPARATUS_TRACE_V1
```

Evidence class:

```
DETERMINISTIC_TEST_APPARATUS_TRACE
```

Canonical trace:

```text
ATT
  selected zombie evidence

BLF
  nearby threat SUPPORTED

CNC
  spatial:nearby_threat MATCHED

PRD WAIT
  comparison_score = 8

PRD MOVE_AWAY
  comparison_score = 3

PLAN
  MOVE_AWAY

HABIT
  MOVE_AWAY

ROUTE
  AGREED(MOVE_AWAY)

ADMISSION
  ADMITTED under Current Intent escape-threat

EXEC_BIND
  skill = escape-movement
  action_ref = MOVE_BACKWARD

SkillExecution
  STARTED

ActionLifecycle
  PROPOSED
  AUTHORIZED

ActionSupervisor
  ISSUED

WORLD_EXEC
  deterministic Mineflayer test apparatus
  WorldConsequence.EXECUTED

ACTION_OUTCOME
  ActionState.OUTCOME
  reason = observed_execution

FEEDBACK
  explicit criterion
  target = risk_weight
  direction = INCREASE

LRN
  risk_weight 3/rev0
  -> proposal 4
  -> explicit LearningUpdateAuthority
  -> 4/rev1

STOP
```

The deterministic structured transaction requires:

```
provider/model calls = 0
```

This does **not** mean RelaySelf never needs an LLM. TALK and RelayEngine remain
separately available qualified mechanisms. The frozen claim is only that this
specific structured deterministic path does not require provider/model
cognition.

## Forbidden implicit edges

The following edges do not exist in the frozen architecture:

- ATT -> belief mutation;
- BLF -> Memory write;
- CNC -> World truth;
- PRD -> plan commitment;
- PLAN -> Current Intent;
- PLAN -> Action proposal;
- HABIT -> Action execution;
- HABIT -> LearningFeedback;
- ROUTE -> Intent mutation;
- ADMISSION -> Skill start;
- EXEC_BIND -> authorization;
- WORLD_EXEC -> LearningFeedback;
- WorldConsequence -> Memory;
- WorldConsequence -> Belief;
- ACTION_OUTCOME -> LearningFeedback without explicit FEEDBACK criterion;
- FEEDBACK -> retained update without LRN authority;
- LRN -> automatic next epoch.

These negative edges are architecture invariants, not merely missing
conveniences.

## Central-executive audit

Result:

```
NO_PERSISTENT_CENTRAL_EXECUTIVE_INTRODUCED
```

The S5-S17 modules do not introduce a persistent object jointly owning unrelated
domains such as Memory + Intent, Belief + Action authority, Plan + Scheduler,
Habit + Action issue, Learning + route arbitration, or World state + cognition.

The deliberate retained owners remain narrow:

- PersistentCognition: durable identity/memory/appraisal;
- IntentCommitment: Current Intent;
- SkillExecution: Skill lifecycle;
- ActionLifecycle / ActionSupervisor: Action lifecycle and supervision;
- LearningPreferenceState: one owner-local learning preference;
- HabitRepertoire: retained habit rules.

## Scheduler and dispatch audit

Result:

```
NO_PERSISTENT_COGNITIVE_SCHEDULER_INTRODUCED
```

`EpochPlan` is an immutable stateless plan. Caller/source-supplied
`due_items` determine why work is due and caller-owned `EpochBinding` values
provide exact invocation bindings.

`OperatorDescriptor.implementation_ref` is audit metadata and is never
dynamically imported or executed.

Two explicit S3 callback seams remain by design:

- `EpochBinding.invoke`;
- `CognitionInvocation.runner`.

They are caller-owned explicit bindings, not hidden registry dispatch.

`ActionSupervisor` owns only its existing typed in-flight Action map,
monotonic processing time, deadlines and outcome closure. It is not a cognitive
scheduler.

The S15 Mineflayer receive loop is bounded by an explicit timeout. It contains
no background retry or reconnect loop.

## Static implementation audit

Fresh S18 audit over S5-S17 implementation modules found no:

- mutable module-global semantic store;
- hidden registry;
- dynamic import or `eval`;
- background thread/task;
- hidden provider/model fallback;
- newly introduced generic state store;
- automatic cross-owner mutation;
- persistent cognition scheduler;
- central executive object.

Relevant explicit exceptions, which are already part of the architecture:

- `ActionSupervisor` intentionally uses a typed per-instance dictionary to own
  supervised Action lifecycles;
- `SkillExecution` and `ActionLifecycle` use internal lineage objects to
  reject stale immutable snapshots;
- `PersistentCognition` explicitly persists its own governed durable JSON
  snapshot;
- S15 uses a timeout-bounded receive loop and callable interface checks;
- S3 uses explicit caller-owned invocation callbacks.

None of these exceptions constitutes hidden cross-domain ownership.

## Live field boundary

The live field is frozen exactly as:

```
LIVE_FIELD_STATUS = BLOCKED_NOT_RUN
BLOCKER = genuine Minecraft endpoint unavailable
```

The canonical trace uses deterministic structured Mineflayer test apparatus.
It is not a live physical Minecraft receipt.

## Autonomous reentry boundary

The architecture freezes:

```
AUTONOMOUS_REENTRY = NOT_IMPLEMENTED
CONTINUOUS_MULTI_EPOCH_OPERATION = NOT_QUALIFIED
```

This is deliberate. The next epoch remains caller-triggered.

S17 retained adaptation does not automatically cause another ATT, PLAN, Action,
or Mineflayer transaction.

## Explicitly unqualified next-phase areas

The S18 milestone does **not** qualify:

- genuine Minecraft field execution;
- continuous autonomous loop;
- next-epoch trigger policy;
- repeated action pacing;
- multi-step planning;
- multi-step prediction rollout;
- automatic Skill terminal closure;
- automatic Memory consolidation;
- automatic BLF update from WorldConsequence;
- Habit acquisition, reinforcement, or extinction;
- learned route arbitration;
- learned admission policy;
- transition-model learning;
- concept learning;
- belief learning;
- RL / TD learning;
- global credit assignment;
- multi-action temporal credit assignment;
- model-driven reward interpretation;
- model-selected physical action;
- arbitrary Mineflayer command execution.

These limitations are part of the frozen result.

## Freeze conclusion

The supported milestone conclusions are:

```
SINGLE_TRANSACTION_COGNITIVE_ACTION_LEARNING_ARCHITECTURE_QUALIFIED

NO_PERSISTENT_CENTRAL_EXECUTIVE_INTRODUCED
NO_PERSISTENT_COGNITIVE_SCHEDULER_INTRODUCED
DETERMINISTIC_SINGLE_TRANSACTION_PROVIDER_MODEL_CALLS_0
AUTONOMOUS_REENTRY_NOT_IMPLEMENTED
LIVE_FIELD_BLOCKED_NOT_RUN
```

No S18 runtime behavior is added. This document and the machine-readable
manifest freeze the already-qualified S1-S17 architecture for future citation.
