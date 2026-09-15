# Migration from the former RelayLM architecture

This document maps historical RelayLM concepts onto the current general vocabulary. It preserves conceptual continuity without treating historical implementation boundaries as authoritative for RelaySelf.

## Migration principle

The former RelayLM architecture mixed several concerns inside a chat-oriented runtime: persistent cognition, present-state projection, request interpretation, memory lifecycle, runtime orchestration, and presentation.

RelaySelf separates those concerns by ontology and causal responsibility.

## Concept mapping

| Former RelayLM term | General term | Current architectural home | Migration note |
| --- | --- | --- | --- |
| SOUL | Identity Specification | Persistent Cognition / Authority | Preserve the normative identity concept; do not treat learned state as equivalent authority. |
| SELF | Self-Model | Persistent Cognition | Rename to avoid collision with RelaySelf as the whole system. |
| REL | Relationship Model | Persistent Cognition | Preserve as durable relationship state. |
| OTHER MODEL | Other Model | Persistent Cognition | Preserve uncertainty and provenance about others. |
| GOAL | Goal / Commitment | Persistent Cognition | Durable goal semantics stay persistent; present activation is separate. |
| Current GOAL / active goal | Active Goal | Present Projection | Present relevance should not mutate the durable goal merely by activation. |
| MEM | Memory | Persistent Cognition | Preserve durable memory and lifecycle semantics. |
| SCN | Situation Model | Present Projection | Generalize from request-local scene framing to current semantic situation. |
| EMO | Current Appraisal / Affective State | Present Projection | Treat current affect as transient rather than durable truth. |
| EMOTION.md or durable emotion profile | Appraisal Disposition / Expression Policy | Persistent Cognition | Preserve durable affective tendencies separately from current affect. |
| Working Self | Working Self / Present Projection | Present Projection | Preserve as the runtime projection of currently relevant self-state. |
| ATN | Event Admission / Attention State | Embodied Boundary + Present Projection | Split event admission from the resulting attention state. |
| INT | Request Interpretation | RelayLM proxy/session layer | Historical INT interpreted user requests; it is not Current Intent. |
| Current Intent | Current Intent | Present Projection | Reserve Intent for the currently committed executable objective. |
| REF | Consequence Observation / Post-output Observation | Embodied Boundary or proxy-specific feedback | Generalize feedback from response observation to action consequence observation where appropriate. |
| SLP | Experience Integration / Consolidation | Persistent Cognition | Preserve the concept of metabolizing lived evidence into governed durable updates. |
| CTX | Context Assembly / Context Compiler | Proxy or model-adapter mechanism | Treat as model-facing mechanism, not persistent cognition. |
| RUN | Execution Orchestration | Runtime mechanism | Split request-specific orchestration from general loop scheduling and trace. |
| Analyzer Candidate | Interpretation Candidate | Runtime mechanism | Candidate output is provisional until validated. |
| Candidate Governance | Validation / Authority Gate | Authority / Provenance | Preserve the rule that candidate inference does not become authority by itself. |
| Capability Boundary | Action Authorization | Embodied Boundary / Authority | Preserve the separation between language output and executable authority. |
| Character Workspace | Persistent State Workspace | Tooling | Product/tooling mechanism, not a cognitive ontology primitive. |
| Source Compiler | State / Projection Compiler | Tooling | Preserve deterministic compilation where useful; do not make compiler output a new source of truth. |
| Presentation Mapper | Presentation Mapping | Presentation layer | Keep presentation separate from belief and authority. |

## Concepts that were distributed across multiple former modules

### Question

Question semantics previously appeared across self-model, goal, and context structures.

The current model treats Question as a persistent epistemic object, while activation is present-state behavior:

```text
Persistent Cognition:
  Question
  Evidence
  epistemic state

Present Projection:
  Active Question
  salience
  pursue-now eligibility

Embodied Boundary:
  affordance
  blocker change
  information-gathering skill
```

### Emotion

Historical emotion handling is separated into three general concepts:

```text
Appraisal
  -> Affective State
  -> Expression
```

Durable affective tendencies belong to persistent cognition; current appraisal and affect belong to present projection; outward expression belongs to presentation or action.

### Goal and intent

A durable Goal is not a Current Intent.

```text
Goal / Commitment
  -> present activation
  -> arbitration
  -> Current Intent
  -> Skill
  -> Action
```

## Historical mechanisms versus enduring concepts

Not every former module should survive as a software component.

A historical name may represent:

1. an enduring cognitive concept,
2. a runtime mechanism used to realize that concept in a chat proxy, or
3. a product-specific surface.

Migration should preserve concepts first. Software boundaries should be recreated only when current contracts justify them.

## Non-regression principles

The migration must retain these conceptual separations:

- Evidence is not belief.
- Belief is not presentation.
- Knowing is not permission to disclose.
- Candidate inference is not authority.
- Language output is not action completion.
- Persistent cognition is not present activation.
- Self state is not environment truth.

The purpose of this migration is not to reproduce the former RelayLM implementation. It is to recover valid concepts and place them behind clearer boundaries.
