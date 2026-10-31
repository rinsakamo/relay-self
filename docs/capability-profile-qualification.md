# S4 Existing Capability Profile Qualification

## Purpose

S4 qualifies the first concrete RelaySelf capability profiles using only mechanisms that already exist in the repository.

No new cognitive mechanism is introduced.

Frozen profiles:

- MEM
- CTL
- CTL + SKL
- TALK
- MEM + CTL + SKL
- MEM + TALK

These profiles are immutable named selections over the S2 capability set. They do not own state and do not add execution behavior beyond S3's explicit epoch bindings.

## Qualification target

The S4 question is:

> Does enabling or disabling one already-declared capability change only its admitted runtime route while preserving existing semantic ownership and authority boundaries?

The qualification exercises real current seams instead of dummy descriptor coverage.

## MEM

The MEM profile executes a real:

```
PersistentCognition.retain_memory(...)
```

through an explicit S3 binding.

Expected properties:

- one governed Memory is retained;
- PersistentCognition remains the durable owner;
- no cognition call is made.

## CTL

The CTL profile executes a real bounded:

```
RelayEngine.__call__(BoundedChoiceRequest)
```

through an explicit `CognitionInvocation`.

Expected properties:

- exactly one BOUNDED provider call when THINK is disabled;
- the explicit finite-choice admissibility contract remains active;
- no hidden retry or per-tick cognition appears.

## CTL + SKL

The profile executes:

```
SkillExecution.start(...)
ActionLifecycle.propose(...)
```

in source-supplied due order.

Expected properties:

- the Skill remains owned by `SkillExecution`;
- the Action proposal preserves Skill and Current Intent association;
- the Action stops at `PROPOSED`;
- capability composition does not authorize, issue, or externally execute the Action.

This is an important negative qualification: composing CTL + SKL does not create action authority.

## TALK

The TALK profile executes:

```
RelayEngine.open(OpenCognitionRequest)
```

exactly once.

Expected properties:

- one OPEN provider call;
- transient expression result;
- no Action identity or authority is created.

## MEM + CTL + SKL

This profile demonstrates multiple owner-local transitions in one stateless epoch plan:

```
Memory retention
-> Skill execution start
-> Action proposal
```

CTL is enabled because SKL depends on it, even when no CTL cognition operator is due in that epoch.

The profile does not infer a need for a central executive from the fact that the work is composed.

## MEM + TALK

This profile demonstrates a deterministic owner transition followed by exactly one final cognition call:

```
mem.retain
-> talk.open_cognition
```

This also supplies the principal toggle-isolation pair.

### MEM OFF

With the same MEM + TALK due-work surface:

```
MEM OFF
TALK ON
```

must produce:

- MEM work in `EpochPlan.suppressed`;
- TALK still executed;
- existing retained Memory unchanged;
- exactly one OPEN provider call.

### TALK OFF

With the same due-work surface:

```
MEM ON
TALK OFF
```

must produce:

- TALK work in `EpochPlan.suppressed`;
- MEM still executed;
- zero model/provider calls.

These two cases demonstrate that capability OFF changes route admission rather than deleting state or globally disabling the epoch.

## Authority invariants

S4 must preserve:

```
Memory retention != current World truth
Action proposal != authorization
authorization != external execution
generated expression != belief
generated expression != memory
generated expression != action authority
capability enablement != semantic ownership
```

The S4 tests therefore check both positive execution and negative authority acquisition.

## Scope limit

S4 does not qualify:

- ATT
- BLF
- CNC
- PRD
- PLAN
- LRN
- HABIT

Those require new mechanism work or separate bounded qualification.

S4 also does not add:

- automatic trigger detection;
- learned scheduling;
- global priority;
- persistent scheduler state;
- central executive state;
- dynamic implementation lookup;
- generic operator dispatch;
- LLM-per-tick execution.

## Boundary toward S5

After S4, the existing MEM / CTL / SKL / TALK composition path is qualified as a bounded executable substrate.

The next new-mechanism work should proceed one capability at a time.

A conservative order remains:

```
ATT
-> BLF
-> CNC
-> PRD
-> PLAN
-> LRN
-> HABIT
```

LRN and HABIT remain late because durable self-modification, invalidation, rollback, and authority requirements are stronger than read/select/transform routes.
