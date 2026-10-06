# Existing Execution Descriptors

## Purpose

S2 maps already-existing RelaySelf runtime seams onto the declarative capability composition introduced in S1.

The mapping is metadata only.

```
CapabilitySpec
  -> operator_id / criterion_id

CapabilityDescriptorSet
  -> audit metadata for those ids

existing RelaySelf method/function
  -> remains the only executable implementation
```

There is deliberately no generic dispatcher, callable registry, scheduler, or new state owner in this slice.

## Why descriptors are separate from execution

The post-MAIN reintegration suggests that reusable cognition can be composed from typed state, transformations, criteria, ports, and temporal ordering without requiring a new persistent central coordinator.

RelaySelf therefore records composition without transferring authority:

```
descriptor
  != executable owner
  != semantic state
  != authority
  != scheduler
```

An `implementation_ref` is an audit reference to an already-existing Python seam. It is not dynamically imported or invoked by the descriptor layer.

## S2 bounded scope

S2 covers only four current/partial capabilities:

- MEM
- CTL
- SKL
- TALK

No ATT, BLF, CNC, PRD, PLAN, LRN, or HABIT implementation is inferred from the research result.

### MEM

Current descriptor coverage:

```
mem.retain
  -> PersistentCognition.retain_memory
```

This is a governed owner transition over durable Memory. S2 does not claim that RelaySelf already has a general Memory retrieval operator.

The associated criterion is an existing contract guard: valid Memory data and unique `memory_id`.

### CTL

Current descriptor coverage:

```
ctl.coordinate_decision_epoch
  -> coordinate_decision_epoch

ctl.bounded_cognition
  -> RelayEngine.__call__
```

The decision-epoch seam is coordination plumbing over existing owner state. It is not a general control policy and does not own Present, Intent, Skill, a clock, or a world model.

The bounded cognition seam is an explicit transient cognition call. Its current descriptor criterion is only the existing admissibility guard that a resolved provider choice must belong to the request's finite choice set.

S2 does **not** invent a general value or viability criterion where no standalone implementation exists.

### SKL

Current descriptor coverage:

```
skl.start_execution
  -> SkillExecution.start

skl.propose_action
  -> ActionLifecycle.propose
```

Existing contract guards remain authoritative:

- a Skill execution requires an actual Current Intent;
- an Action proposal requires the current STARTED Skill snapshot;
- the Skill's intent must match the actual Current Intent.

SKL remains dependent on CTL in the declarative composition plan.

### TALK

Current descriptor coverage:

```
talk.open_cognition
  -> RelayEngine.open
```

The current criterion descriptor records the already-existing provider-expression contract: OPEN output must be non-empty and provenance-bearing.

The expression remains transient. It does not become Belief, Memory, Current Intent, Action authority, or proof of external delivery.

## OperatorDescriptor

An `OperatorDescriptor` records:

- operator id;
- capability id;
- implementation reference;
- declared read scopes;
- declared write scopes;
- observable effect class.

The effect classes distinguish:

- `READ_ONLY`;
- `OWNER_TRANSITION`;
- `COGNITION_CALL`;
- `COORDINATION`.

Every descriptor rejects `hidden_persistent_state=True`.

This does not prove that the referenced implementation is globally pure. It prevents the composition layer from adding hidden persistence of its own.

## CriterionDescriptor

A `CriterionDescriptor` distinguishes:

- `CONTRACT_GUARD`;
- `COGNITIVE_ORIENTATION`.

All current S2 criteria are **CONTRACT_GUARD**.

That distinction is intentional. The current runtime has concrete validity/admission guards, but the research-level Q role must not be backfilled by pretending that every capability already has an implemented cognitive objective.

Criterion descriptors are non-mutating metadata.

## CapabilityDescriptorSet

The set validates that an enabled `CapabilitySpec` has explicit matching operator and criterion descriptors.

Validation fails closed when:

- an operator descriptor is missing;
- a criterion descriptor is missing;
- a spec references a descriptor assigned to another capability.

Validation does not execute the referenced seam.

## Explicit S2 plan

`s2_capability_plan(...)` constructs the bounded MEM/CTL/SKL/TALK plan and validates enabled descriptors.

Nothing is enabled by default.

For example:

```python
from relay_self.execution_descriptor import s2_capability_plan

plan = s2_capability_plan(
    enabled_ids=frozenset({"CTL", "SKL"})
)
```

This validates that SKL's CTL dependency and descriptor coverage are present.

It does not start a Skill, run cognition, or schedule an epoch.

## Boundary toward S3

S3 may compile enabled declarative routes into an ordered **stateless epoch plan**, but it must preserve these S2 boundaries:

```
descriptor -> may identify an admitted seam
descriptor -> must not invoke it by itself

epoch plan -> may order explicit work
epoch plan -> must not own hidden persistent state

scheduler/order selection
  != semantic owner
  != world model
  != intent
  != belief
```

S3 should bind only concrete, explicitly supplied callables or owner operations. It must not auto-import `implementation_ref` strings as executable code.
