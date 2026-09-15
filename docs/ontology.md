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

| Term | Meaning |
| --- | --- |
| Perception | Observation of the external environment. |
| Interoception | Observation of internal, body, resource, or operational state. |
| Body State | Current regulated internal state relevant to continued agency. |
| Homeostasis | Regulation toward preferred operating ranges. |
| Need | Regulatory pressure caused by deviation from a preferred range. |
| Viability Constraint | Constraint protecting continued agency or preventing unacceptable state. |
| Event Admission | Decision that an incoming event should enter active processing. |
| Reconsideration | Decision whether to continue the current intent or deliberate again. |
| Arbitration | Selection among eligible motivations or candidate intents. |
| Skill | Temporally extended feedback controller or embodied capability. |
| Action | Primitive effect command directed toward the environment. |
| Action Authorization | Gate determining whether a proposed action may execute. |
| Consequence Observation | Observation of what actually followed an action. |
| State Update | Update caused by newly observed consequences or evidence. |
| Scheduler | Runtime coordination across different timescales and priorities. |
| Time Model | Representation of runtime, world, subjective, or branch time. |
| Trace / Provenance | Causal record of why state, decisions, and actions changed. |

## Environment

| Term | Meaning |
| --- | --- |
| World State | Environment state external to the self. |
| World Dynamics | Rules or processes by which the environment changes. |
| Observation | Information available to the self about world state. |
| Affordance | Action possibility available under current world and boundary state. |
| Consequence | Actual environment result following an action or external event. |
| External Intervention | Change introduced from outside the self's ordinary action loop. |

Core distinction:

```text
World State != Observation != Belief != Appraisal
```

## Authority / Provenance

Authority determines who or what is permitted to establish or mutate a class of state. Provenance records where a claim or transition came from.

Useful authority classes include:

- **Specification Authority** — rules, policies, grants, and constraints.
- **Attested State Authority** — observations or source-of-record state supplied by a boundary adapter or external system.
- **Predictive Estimate** — learned, heuristic, or model-derived estimate that does not become specification authority merely because it is confident.

## Arbitration without ontology collapse

Needs, questions, goals, relationship concerns, tasks, and opportunities should not be represented as one universal motivational object merely to make scheduling easier.

They may emit a common transient arbitration projection, but the source ontology remains distinct.
