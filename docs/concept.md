# S7 Bounded Structured Concept Classification

## Purpose

S7 introduces Concept (CNC) as a bounded deterministic classification operation over
already-structured caller-owned input.

The qualified mechanism answers:

\`\`\`
"What is this represented as under this explicit concept rule?"
\`\`\`

It does not answer:

\`\`\`
ATT: "What receives processing?"
BLF: "What proposition status is warranted?"
CTL: "What should be done?"
PRD: "What will happen?"
\`\`\`

The minimum S7 mechanism is intentionally stateless:

\`\`\`
structured ConceptCandidate
        -> explicit ConceptCriterion
        -> classify_concept
        -> immutable ConceptRepresentation
\`\`\`

No ConceptStore, SemanticMemory, KnowledgeGraph, ontology database, or model-assisted
induction is introduced.

## Concept identity

\`ConceptKey\` contains two structured tokens:

- \`domain\`
- \`name\`

Example:

\`\`\`
ConceptKey(domain="entity", name="hostile_mob")
-> entity:hostile_mob
\`\`\`

CNC never extracts a \`ConceptKey\` from arbitrary text.

## Candidate and feature model

\`ConceptCandidate\` is an immutable reference to caller-owned structured material.
It contains:

- \`candidate_id\`
- opaque \`payload_ref\`
- immutable \`features\`
- explicit integration \`provenance\`
- optional source references
- optional source provenance lineage

The payload itself is not stored by CNC.

\`ConceptFeature\` contains one structured feature key and one deliberately bounded
scalar value:

- \`bool\`
- \`int\`
- one structured string token

Mutable objects, lists, mappings, free-text phrases, and inferred embeddings are not
valid feature values.

Candidate feature keys must be unique.

## Criterion and deterministic rule

\`ConceptCriterion\` contains:

- \`criterion_id\`
- target \`ConceptKey\`
- one or more explicit required features

Required feature keys must be unique.

The S7 rule is:

\`\`\`
all required keys present
and every required value exactly matches
    -> MATCHED

at least one required key has an explicit different value
    -> NOT_MATCHED

no explicit value mismatch
but at least one required key is absent
    -> UNDETERMINED
\`\`\`

When both a mismatch and a missing key exist, \`NOT_MATCHED\` wins because an
explicit contradiction is already present.

This rule distinguishes absence from false. It introduces no weights, similarity,
prototype distance, probability, or learned semantics.

## ConceptRepresentation

The immutable result retains:

- the exact source \`ConceptCandidate\`
- the exact \`ConceptCriterion\`
- \`MATCHED\`, \`NOT_MATCHED\`, or \`UNDETERMINED\`
- exact supporting source feature objects
- missing required feature keys
- mismatched required feature keys

The source candidate and criterion are referenced directly and remain immutable.
Source identity and provenance therefore remain auditable.

A \`MATCHED\` representation means only:

\`\`\`
this structured candidate satisfies this explicit concept membership rule
\`\`\`

It does not mean that the represented fact is World truth.

## Cognitive criterion vs contract validation

S7 declares:

\`\`\`
cnc.explicit_membership_orientation
kind = COGNITIVE_ORIENTATION
\`\`\`

The cognitive operation is deciding which of the three membership outcomes applies
to an otherwise valid structured candidate under an explicit concept rule.

These remain ordinary contract validation rather than cognition:

- malformed \`ConceptKey\`
- unsupported feature value type
- duplicate feature key
- duplicate criterion requirement
- unsupported candidate type

## Capability and descriptor surface

S7 adds:

\`\`\`
CNC
dependencies = ()
state_scopes = ()
\`\`\`

Operator:

\`\`\`
cnc.classify
-> relay_self.concept.classify_concept
effect = READ_ONLY
hidden_persistent_state = false
\`\`\`

Port:

\`\`\`
concept.representation.out
\`\`\`

CNC does not globally depend on ATT or BLF. Combined routes explicitly enable those
capabilities when required.

## ATT / BLF / CNC separation

The qualified deterministic chain is:

\`\`\`
structured evidence candidates
        -> ATT
        -> selected evidence
        -> BLF
        -> structured BeliefAssessment
        -> explicit belief-to-concept projection
        -> CNC
        -> ConceptRepresentation
\`\`\`

The responsibilities remain distinct:

\`\`\`
ATT = which structured items receive processing?
BLF = what belief status does admitted evidence warrant?
CNC = what explicit concept rule does structured input satisfy?
\`\`\`

CNC does not run attention, re-read excluded evidence, or reassess belief evidence.

## Explicit BLF bridge

\`concept_candidate_from_belief\` is an explicit caller-invoked structured projection
from an already-existing \`BeliefAssessment\`.

It exposes only structured BLF fields:

- \`source_kind=belief_assessment\`
- \`belief_status=<existing status>\`
- \`proposition=<existing structured proposition identity>\`

It preserves evidence source references and provenance.

It does not recompute belief status, change \`CONFLICTED\` to true/false, or create a
concept by itself. A separate explicit \`ConceptCriterion\` is still required.

If the route requires BLF and no \`BeliefAssessment\` exists,
\`ConceptSourceUnavailable\` is raised. No belief is fabricated.

## Integrated deterministic qualification

The S7 integrated case uses:

\`\`\`
E1: SUPPORT proposition P, focus=P
E2: OPPOSE proposition P, focus=P
E3: SUPPORT proposition Q, focus=Q
\`\`\`

ATT focuses P:

\`\`\`
E1, E2
\`\`\`

BLF therefore returns:

\`\`\`
P = CONFLICTED
\`\`\`

CNC receives the structured BLF result and evaluates:

\`\`\`
source_kind=belief_assessment
belief_status=conflicted
    -> epistemic:contested_claim
\`\`\`

Result:

\`\`\`
MATCHED(epistemic:contested_claim)
\`\`\`

E3 never reaches BLF. CNC never reads E3 or re-aggregates E1/E2. The belief remains
\`CONFLICTED\`; concept classification does not convert it into truth.

ATT, BLF, and CNC each make zero provider/model calls.

## Provider-text boundary

A \`ProviderExpression\` is neither a \`ConceptCandidate\` nor a
\`BeliefAssessment\`.

For example:

\`\`\`
"That is a dangerous enemy."
\`\`\`

does not automatically become:

\`\`\`
entity:hostile_mob
\`\`\`

Natural-language concept extraction would require a future explicit interpretation
mechanism and is outside S7.

## ON / OFF semantics

CNC ON plus explicit due work and an exact binding executes the real
\`classify_concept\` mechanism.

CNC OFF suppresses only CNC due work.

The qualification includes BLF ON + CNC OFF:

- BLF still executes;
- CNC is suppressed;
- the \`BeliefAssessment\` remains available to its caller;
- no concept result is fabricated.

Capability OFF changes route admission only.

## Authority boundaries

S7 preserves:

\`\`\`
candidate/evidence != AttentionSelection
AttentionSelection != BeliefAssessment
BeliefAssessment != ConceptRepresentation
ConceptRepresentation != World truth
ConceptRepresentation != Memory
ConceptRepresentation != Current Intent
ConceptRepresentation != Skill state
ConceptRepresentation != Action authority
ConceptRepresentation != provider output
\`\`\`

CNC does not:

- retain Memory;
- change Current Intent;
- start or mutate a Skill;
- propose, authorize, issue, complete, or fail an Action;
- mutate a BeliefAssessment;
- mutate an AttentionSelection or source candidate;
- assign World truth;
- set scheduler priority.

## Why CNC is not a knowledge graph

S7 classifies one explicitly supplied candidate under one explicitly supplied rule.

It has no:

- graph owner;
- ontology database;
- persistent concept registry;
- relationship traversal;
- semantic search;
- embedding index;
- automatic fact ingestion;
- concept learning.

## Why CNC is not a central executive

CNC has no event loop, clock, trigger detector, scheduler, dynamic dispatch,
provider, or persistent state.

The source/caller owns why CNC work is due. EpochPlan only executes explicitly bound
due work under the already-qualified S3 ordering and Action-supervision rules.

## Deferred functionality

S7 intentionally defers:

- concept persistence;
- semantic memory;
- concept learning;
- prototype learning;
- embedding similarity;
- ontology induction;
- analogy;
- natural-language concept extraction;
- model-assisted induction;
- PRD;
- PLAN;
- LRN;
- HABIT.

Retained concept reuse is a separate future ownership and retention question rather
than an assumption of CNC.
