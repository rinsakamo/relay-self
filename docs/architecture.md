# Architecture

## Purpose

RelaySelf separates persistent cognition, the currently active self-state, and the causal boundary through which an agent perceives and acts.

The architecture is intentionally organized around a small basis before introducing implementation-specific modules.

## Minimal architectural basis

### 1. Persistent Cognition

State that remains meaningful across moments, sessions, and changes in the immediate environment.

Typical contents include identity specifications, self-models, relationship models, goals, commitments, questions, beliefs, memories, and capability models.

### 2. Present Projection

The currently active cognitive projection produced from persistent cognition and current boundary/world conditions.

Typical contents include the situation model, attention state, current appraisal, affective state, active goals or questions, transient tensions, and current intent.

A useful abstract form is:

```text
Present_t = Project(PersistentCognition_t, BoundaryState_t, Events_t, Time_t)
```

Present Projection should be recomputable where practical. It may be traced, but it should not automatically become durable cognition.

### 3. Embodied Boundary

The causal boundary between cognition and environment.

It includes perception, interoception, body or resource state, homeostatic regulation, viability constraints, reconsideration, arbitration, skills, action authorization, action execution, consequence observation, scheduling, time, and trace.

The boundary must preserve the distinction:

```text
Action Proposal
  != Action Authorization
  != Action Execution
  != Consequence
```

Language or model output cannot by itself establish that an external action occurred.

### 4. Environment

State and dynamics outside the self.

RelaySelf does not own environment truth. It owns observations, estimates, beliefs, and appraisals derived from interaction with the environment.

Environment implementations may live in separate systems such as RelayWorld, simulators, desktop environments, or physical robotics stacks.

### 5. Authority / Provenance

A cross-cutting layer that records what a claim or state transition is grounded in and which source is authorized to change it.

Examples include specification authority, attested state, predictive estimates, evidence provenance, action authorization, and persistence rules.

Authority is not equivalent to infallibility. A source can be authoritative for a state field while still carrying uncertainty, freshness, or sensor error.

## Core invariants

The architecture preserves these distinctions:

```text
Persistent != Present
Observation/Evidence != Belief
Proposal != Authorization != Consequence
Self != Environment
```

These are architectural boundaries, not merely naming conventions.

## State flow

A representative closed loop is:

```text
Environment
  -> Observation / Interoception
  -> Boundary State
  -> Present Projection
  -> Reconsideration / Arbitration
  -> Current Intent
  -> Skill
  -> Authorized Action
  -> Environment Consequence
  -> Observation / Evidence
  -> Belief / Memory / State Update
```

Not every event requires deliberative model inference. Deterministic regulation, admission, viability checks, scheduling, and skill control should remain outside the language model where possible.

## Ownership rule

When deciding where a concept belongs, ask:

> Would this concept still make sense without a body, an environment, and an autonomous clock?

If yes, it is a candidate for Persistent Cognition. If no, it is more likely part of Present Projection, the Embodied Boundary, or their coupling.

## Design principle

Different motivational objects may share arbitration without sharing ontology.

Needs, questions, goals, relationship concerns, tasks, and opportunities should remain distinct source objects even if they emit a common transient representation for scheduling or arbitration.
