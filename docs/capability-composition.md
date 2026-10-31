# Capability Composition

## Purpose

RelaySelf can compose cognitive and control capabilities without turning the capability list into a new cognitive state owner.

The first executable slice is deliberately declarative:

```
CapabilitySpec
  -> names required state scopes / operator seams / criteria / ports / dependencies

CapabilityPlan
  -> selects which declared capabilities are enabled
```

Neither type schedules work, calls a model, mutates Persistent Cognition, projects Present, changes Current Intent, starts a Skill, proposes an Action, or establishes World truth.

## Authority boundary

Capability composition is an execution-availability description.

It does not change the existing ownership model:

```
Persistent Cognition
  owns durable cognition

Present Projection
  owns current transient projection

IntentCommitment
  owns Current Intent commitment state

SkillExecution
  owns one Skill execution lifecycle

ActionLifecycle
  owns one primitive Action lifecycle

Environment / adapters
  provide external observations and execution boundaries
```

A capability may later be bound to these owners, but the plan itself owns none of their state.

## CapabilitySpec

A `CapabilitySpec` contains only immutable identifiers:

- `capability_id`
- `state_scopes`
- `operator_ids`
- `criterion_ids`
- `port_ids`
- `dependencies`

The identifiers are intentionally opaque to this layer. This module does not define a generic State Store, Operator runtime, Criterion registry, Port registry, or Scheduler.

That separation prevents declarative composition from silently acquiring semantic authority.

## CapabilityPlan

A `CapabilityPlan` contains:

- an immutable tuple of declared specs;
- a frozen set of enabled capability identifiers.

Construction fails closed when:

- capability identifiers are duplicated;
- an enabled capability is undeclared;
- a dependency is undeclared;
- the dependency graph contains a cycle;
- an enabled capability depends on a disabled capability.

Changing one enabled flag returns a new validated plan.

Disabling a capability therefore changes only route availability metadata. It does not delete retained state or rewrite an owner.

## Example

```python
from relay_self.capability import CapabilityPlan, CapabilitySpec

control = CapabilitySpec(
    capability_id="CTL",
    state_scopes=("present", "execution.intent"),
    operator_ids=("control-select",),
    criterion_ids=("viability",),
    port_ids=("action-proposal-out",),
)

skill = CapabilitySpec(
    capability_id="SKL",
    state_scopes=("execution.intent", "execution.skill"),
    operator_ids=("skill-step",),
    criterion_ids=("skill-progress",),
    port_ids=("skill-feedback-in", "action-proposal-out"),
    dependencies=("CTL",),
)

plan = CapabilityPlan(
    specs=(control, skill),
    enabled_ids=frozenset({"CTL", "SKL"}),
)
```

This example does not execute control or skill logic. A later integration must explicitly bind the named seams to existing owners and runtime mechanisms.

## First intended profiles

The first bounded integration target is the set of already-supported or partially supported RelaySelf paths:

- MEM — Memory
- CTL — Control
- SKL — Skill
- TALK — open expression/cognition path

ATT, BLF, CNC, PRD, PLAN, LRN, and HABIT remain separate future mechanism work. In particular, Learning and Habit should not gain durable write authority merely because they can be named in a plan.

## Non-goals

This slice does not add:

- a universal mutable State Store;
- a global cognitive registry;
- a general runtime Scheduler;
- persistent scheduler state;
- automatic capability discovery;
- a general Skill registry;
- new Belief, Concept, Prediction, Planning, Learning, or Habit owners;
- LLM-per-tick execution;
- any bypass around Intent, Skill, Action authorization, or consequence boundaries.

A later runtime integration must preserve the repository rule that shared execution plumbing does not become a semantic owner merely because several mechanisms use it.


## S2 continuation

S1 only declares capability metadata and ON/OFF dependency structure.

The bounded S2 continuation is documented in
[`execution-descriptors.md`](execution-descriptors.md). It maps MEM / CTL / SKL / TALK
identifiers onto already-existing RelaySelf seams without adding a dispatcher or runtime behavior.
