# Architecture

## Purpose

RelaySelf separates persistent cognition, the currently active self-state, and the causal boundary through which an agent perceives and acts.

The architecture is intentionally organized around a small basis before introducing implementation-specific modules.

## Minimal architectural basis

### 1. Persistent Cognition

State that remains meaningful across moments, sessions, and changes in the immediate environment.

Typical contents include identity specifications, self-models, relationship models, goals, commitments, questions, beliefs, memories, appraisal dispositions, and capability models.

### 2. Present Projection

The currently active cognitive projection produced from persistent cognition and current boundary/world conditions.

Typical contents include the situation model, attention state, current appraisal, affective state, active goals or questions, transient tensions, and current intent.

A useful abstract form is:

```text
Present_t = Project(PersistentCognition_t, BoundaryState_t, Events_t, Time_t)
```

Present Projection should be recomputable where practical. It may be traced, but it should not automatically become durable cognition.

One supported ownership pattern for cold-start appraisal is:

```text
Identity Specification / governed initial condition
  -> Appraisal Disposition          # Persistent Cognition

target-native Observation
+ applicable Appraisal Disposition
+ later exact-scope lived evidence
  -> Current Appraisal              # Present Projection
```

The projection is Self-relative. A World or adapter may attest an entity species/type/identifier,
position, distance, motion, or body event; it does not thereby establish `enemy`, `ally`,
`fear`, or an Action requirement.

A distinct supported projection exists at the cognition-provider boundary for durable identity:

```text
Identity Specification             # Persistent Cognition authority
  -> canonical CognitionDatum       # pure transient projection
  -> request-carried identity input
  -> provider rendering
```

The projection is not another identity store and is not part of dynamic Present/Memory context.
Generated provider renderings may place the canonical identity block in a stable leading prefix
before mode-specific cognition instructions. Jev/System One may carry the same identity semantics
inside its explicit state representation. Semantic equivalence across provider surfaces does not
establish token/KV-cache compatibility, and cache eligibility remains a separate mechanism /
qualification question.

Preserve:

```text
Identity Specification
  != model-facing identity projection
  != prompt prefix bytes/tokens
  != KV cache
  != compiled model artifact
```

### 3. Embodied Boundary

The causal coupling surface between Self-side cognition/control and external environment/body execution.

RelaySelf owns the Self-side processing around that surface, including perception and interoception intake, body/resource state estimates, homeostatic regulation, viability constraints, reconsideration, arbitration, skills, action proposal/authorization/issuance/supervision, consequence observation and integration, scheduling, time, and trace.

RelaySelf does **not** own authoritative external body/world state or physical/simulated execution merely because those states are represented or acted upon by the Self.

The boundary therefore preserves both representational and causal distinctions:

```text
Self-side body state / estimate
  != authoritative external body state

Action Proposal
  != Action Authorization
  != Action Issuance
  != External Execution
  != Consequence
```

The current Action Lifecycle's `ISSUED` state is the Self-side handoff to an execution boundary. It is not proof that external execution occurred or succeeded.

Language or model output cannot by itself establish that an external action occurred.

### 4. Environment

State and dynamics outside the self, including authoritative external body state and external physical/simulated execution when a concrete environment provides them.

RelaySelf does not own environment truth. It owns observations, estimates, beliefs, appraisals, commitments, and control decisions derived from interaction with the environment.

Environment implementations may live in separate systems such as RelayWorld, simulators, desktop environments, or physical robotics stacks. They may model an external actor/player/avatar role and body substrate separately; RelaySelf does not need to own those environment-side identities in order to issue actions or interpret feedback.

### 5. Authority / Provenance

A cross-cutting layer that records what a claim or state transition is grounded in and which source is authorized to change it.

Examples include specification authority, attested state, predictive estimates, evidence provenance, action authorization, and persistence rules.

Authority is not equivalent to infallibility. A source can be authoritative for a state field while still carrying uncertainty, freshness, or sensor error.

The architectural notion of provenance is broader than the current Python bootstrap value named `Provenance`. The current `relay_self.provenance.Provenance` value is deliberately only an immutable `source` / `reference` evidence pointer shared across runtime owners. It can ground an owner-local event, while causal reconstruction may additionally depend on that owner's event history, structural associations, explicit authority fields, and other trace information.

That minimal value is therefore not by itself a complete derivation graph, proof that the named source is legitimate authority, repository-wide causal trace, or claim of compatibility with an external provenance standard such as W3C PROV. Richer provenance structure should be introduced only when a concrete owner or consumer demonstrates information that cannot be reconstructed from current contracts.

## Core invariants

The architecture preserves these distinctions:

```text
Persistent != Present
Observation/Evidence != Belief
Self-side representation != external body/world truth
Proposal != Authorization != Issuance != External Execution != Consequence
Self != Environment
```

These are architectural boundaries, not merely naming conventions.

## Boundary-facing self representation

The useful explanatory idea of a current "Self Image" does not currently require another architectural basis or executable owner.

RelaySelf can represent what it currently understands about itself-in-a-body/world through existing concepts:

```text
Self-Model
  + Working Self
  + Situation Model
  + Capability Model
  + Body State / body-resource estimate
  + Belief / Appraisal
```

This composition can change when external observations indicate a body swap, morphology change, capability change, resource change, or other embodiment change. Such changes do not make the external body's authoritative state part of RelaySelf.

Introduce a separate Self Image owner only if future implementation demonstrates independent state, authority, or lifecycle that cannot be represented by these existing owners.

## State flow

A representative closed loop is:

```text
External Environment / Execution
  -> Observation / Interoception
  -> Self-side Boundary State
  -> Present Projection
  -> Reconsideration / Arbitration
  -> Current Intent
  -> Skill
  -> Action Proposal
  -> Authorization
  -> ISSUED
  ---- Embodied Boundary ---->
  -> External Execution
  -> Environment Consequence
  -> Observation / Evidence
  <---- Embodied Boundary ----
  -> Belief / Appraisal / Body State / Memory / State Update
```

The exact external execution implementation is not owned by RelaySelf. A cognition system may be coupled to a simulator avatar, game actor, desktop executor, robot body, or another environment implementation while preserving the same Self-side distinction between issuance and observed consequence.

Not every event requires deliberative model inference. Deterministic regulation, admission, viability checks, scheduling, and skill control should remain outside the language model where possible.

## Ownership rule

When deciding where a concept belongs, ask:

> Would this concept still make sense without a body, an environment, and an autonomous clock?

If yes, it is a candidate for Persistent Cognition. If no, it is more likely part of Present Projection, the Self-side processing around the Embodied Boundary, the external Environment, or their coupling.

Do not infer ownership merely from causal proximity. A body fact can matter deeply to the Self while remaining external truth; an action can originate from Self-side intent while its physical execution remains external.

## Design principle

Different motivational objects may share arbitration without sharing ontology.

Needs, questions, goals, relationship concerns, tasks, and opportunities should remain distinct source objects even if they emit a common transient representation for scheduling or arbitration.
