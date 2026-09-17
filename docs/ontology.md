# Ontology

This document defines the preferred general vocabulary for RelaySelf. Relay-specific historical abbreviations should map onto these terms rather than become new base concepts.

## Persistent Cognition

Persistent cognitive objects remain meaningful beyond the current moment.

| Term | Meaning |
| --- | --- |
| Identity Specification | Normative identity, values, constraints, and externally or internally accepted rules for how the self should be. |
| Self-Model | The self's current durable understanding of itself. |
| Relationship Model | Persistent model of the relationship with a particular other. |
| Other Model | Beliefs, expectations, and uncertainty about another agent. |
| Goal | A desired future state. |
| Commitment | A goal, promise, or obligation that should persist over time. |
| Question | A persistent epistemic object that remains unresolved until answered, abandoned, superseded, or judged unknowable. |
| Evidence | Provenance-bearing observation, report, or outcome used as grounding. |
| Assessment | Interpretation of what evidence supports or contradicts. |
| Belief | The self's current proposition-level estimate about itself or the world. |
| Memory | Durable retained experience or knowledge. |
| Appraisal Disposition | Persistent tendency to evaluate classes of events as important, threatening, desirable, familiar, and so on. |
| Capability Model | The self's current estimate of what it can do. |
| Experience Integration | Process that converts lived evidence into governed updates to persistent cognition. |

Core distinctions:

```text
Identity Specification != Self-Model
Evidence != Belief
Belief != Memory
Goal != Current Intent
```

## Present Projection

Present Projection is the transient cognitive state that matters now.

| Term | Meaning |
| --- | --- |
| Working Self | Integrated active projection of currently relevant persistent and boundary state. |
| Situation Model | Semantic interpretation of the current situation. |
| Current Appraisal | Evaluation of what the current event or situation means for the self. |
| Affective State | Short-lived affective state associated with current appraisal. |
| Attention State | What currently receives cognitive resources. |
| Active Goal | A persistent goal currently relevant to action selection. |
| Active Question | A persistent question currently eligible for investigation. |
| Tension | Transient action pressure produced by a source object in the current situation. |
| Opportunity / Affordance | A currently available possibility for action or information gain. |
| Current Intent | The action-level objective currently committed for execution. |
| Expression State | Current state governing what and how the self presents outwardly. |

These are not automatically durable. A persistent object may remain unchanged while its present activation changes.

## Embodied Boundary

The Embodied Boundary is the causal coupling surface between Self-side cognition/control and external environment/body execution. The terms below describe Self-side state and processing around that seam; they do not make external body or world truth part of RelaySelf.

| Term | Meaning |
| --- | --- |
| Perception | Observation available to the Self about the external environment. |
| Interoception | Observation available to the Self about body, resource, or operational state. Its provenance/authority remains distinct from the Self's later estimate or appraisal. |
| Body State | Self-side regulated state or estimate relevant to continued agency, derived from available body/resource evidence and runtime state. It is not automatically authoritative external body truth. |
| Homeostasis | Self-side regulation toward preferred operating ranges. |
| Need | Regulatory pressure caused by deviation from a preferred range. |
| Viability Constraint | Constraint protecting continued agency or preventing unacceptable state. |
| Event Admission | Decision that an incoming event should enter active processing. |
| Reconsideration | Decision whether to continue the current intent or deliberate again. |
| Arbitration | Selection among eligible motivations or candidate intents. |
| Skill | Temporally extended feedback controller or embodied capability. |
| Action | Primitive effect command directed toward the environment. |
| Action Authorization | Gate determining whether a proposed action may be issued toward external execution. |
| Consequence Observation | Observation of what actually followed an action. |
| State Update | Update caused by newly observed consequences or evidence. |
| Scheduler | Runtime coordination across different timescales and priorities. |
| Time Model | Representation of runtime, world, subjective, or branch time. |
| Trace / Provenance | Causal record of why state, decisions, and actions changed. |

An informal **Self Image** can be useful when explaining the Self's current relation to an external body or world, but it is not currently a separate canonical ontology object. The needed information can presently be expressed by composing existing owners such as `Self-Model`, `Working Self`, `Situation Model`, `Capability Model`, `Body State`, `Belief`, and `Current Appraisal`.

This keeps the representational and material sides distinct:

```text
Self-side body representation / Body State
  != external body or resource truth

Action issued toward an execution boundary
  != external physical or simulated execution
```

If future implementation demonstrates independent state, authority, or lifecycle that cannot be represented by these existing concepts, that responsibility must earn a new owner through the normal Grand Null process.

## Environment

| Term | Meaning |
| --- | --- |
| World State | Environment state external to the self, including authoritative external body state when an environment provides one. |
| World Dynamics | Rules or processes by which the environment changes. |
| Observation | Information available to the self about world state. |
| Affordance | Action possibility available under current world and boundary state. |
| Consequence | Actual environment result following an action or external event. |
| External Intervention | Change introduced from outside the self's ordinary action loop. |

Core distinctions:

```text
World State != Observation != Belief != Appraisal
External body state != Self-side Body State / estimate
```

## Authority / Provenance

Authority determines who or what is permitted to establish or mutate a class of state. Provenance records where a claim or transition came from.

Useful authority classes include:

- **Specification Authority** — rules, policies, grants, and constraints.
- **Attested State Authority** — observations or source-of-record state supplied by a boundary adapter or external system.
- **Predictive Estimate** — learned, heuristic, or model-derived estimate that does not become specification authority merely because it is confident.

The current Python bootstrap's shared `Provenance` value is only the minimal immutable `source` / `reference` evidence pointer carried by owner-local events. It is one representation used inside the broader Trace / Provenance concern above; it is not equivalent to the whole causal record.

In particular, that value alone does not prove that its named source is legitimate authority, reconstruct every derivation or dependency, or establish compatibility with a generic provenance model such as W3C PROV. Existing owner-local histories, associations, authority fields, and future justified trace mechanisms may carry additional causal information without creating a new semantic owner merely because they contribute to provenance.

## Arbitration without ontology collapse

Needs, questions, goals, relationship concerns, tasks, and opportunities should not be represented as one universal motivational object merely to make scheduling easier.

They may emit a common transient arbitration projection, but the source ontology remains distinct.
