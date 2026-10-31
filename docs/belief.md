# S6 Bounded Belief Assessment

## Purpose

S6 introduces bounded deterministic Belief (BLF) as a transient proposition-level
assessment over explicitly qualified evidence.

The minimum mechanism is intentionally stateless:

\`\`\`
qualified structured evidence
        -> explicit BeliefCriterion
        -> deterministic support/conflict aggregation
        -> immutable BeliefAssessment
\`\`\`

S6 does not create durable belief persistence merely because the capability is named
BLF. Persistence across epochs is not required to qualify the evidence-to-belief
boundary and would add an owner before a concrete persistence requirement exists.

## Evidence, belief, and truth

The central boundary is:

\`\`\`
evidence != belief
belief != attested World truth
belief != Memory
belief != Current Intent
belief != Action authority
belief != provider output
\`\`\`

A \`BeliefEvidence\` item records only an explicit relation to one structured
proposition and its provenance. It has no truth flag.

A \`BeliefAssessment\` records what the admitted evidence warrants under the bounded
S6 rule. It does not claim that the proposition is true in the World.

## Structured proposition identity

S6 does not parse arbitrary natural language into propositions.

\`PropositionKey\` has exactly three structured components:

- \`domain\`
- \`subject\`
- \`predicate\`

For example:

\`\`\`
PropositionKey("route", "ridge", "safe")
-> route:ridge:safe
\`\`\`

Each component is one non-empty token without whitespace or embedded colon. This is
an identity contract, not a semantic language parser.

## Evidence model

\`BeliefEvidence\` contains:

- \`evidence_id\`
- one \`PropositionKey\`
- \`EvidenceRelation.SUPPORT\` or \`EvidenceRelation.OPPOSE\`
- explicit \`Provenance\`

S6 does not infer reliability from a source name, provenance string, generated text,
or free-text description. No probabilistic weight is invented.

Duplicate evidence identity fails closed.

Evidence for a proposition other than the explicit criterion proposition also fails
closed rather than being silently ignored.

## Assessment rule

The S6 rule is categorical and deterministic:

\`\`\`
support only
  -> SUPPORTED

oppose only
  -> UNSUPPORTED

support + oppose
  -> CONFLICTED

no admitted evidence
  -> UNDETERMINED
\`\`\`

Evidence order never resolves a conflict. Reversing SUPPORT and OPPOSE evidence
therefore remains \`CONFLICTED\`.

There is no last-write-wins revision, recency preference, numeric confidence,
Bayesian terminology, or hidden source reliability model.

The resulting \`BeliefAssessment\` retains the exact immutable evidence objects, so
evidence identity, relation, ordering, and provenance remain auditable.

## Ownership model

S6 chooses the transient assessment design rather than a persistent \`BeliefState\`.

BLF therefore has:

- no durable belief owner;
- no belief store;
- no mutable proposition dictionary;
- no revision history owner;
- no persistence across epochs.

The capability has no state scope. Its operator effect is \`READ_ONLY\`, producing
only \`transient.belief_assessment\`.

If later work demonstrates that belief persistence across epochs is necessary, that
requires a separate owner-local design and separate qualification. S6 does not
pre-authorize that architecture.

## Capability and descriptor surface

New capability:

\`\`\`
BLF
dependencies = ()
\`\`\`

New operator:

\`\`\`
blf.assess
  -> relay_self.belief.assess_belief
  -> READ_ONLY
\`\`\`

New cognitive criterion:

\`\`\`
blf.evidence_support_orientation
  -> COGNITIVE_ORIENTATION
\`\`\`

This criterion is cognitive because it evaluates explicit evidence relations to
determine the warranted belief status for a target proposition.

Structural checks such as proposition shape, evidence type, duplicate identity, and
proposition matching remain ordinary contract validation and are not relabeled as
cognition.

## ATT interaction

ATT and BLF remain separate mechanisms:

\`\`\`
candidate evidence
  -> ATT: which candidate evidence receives processing?
  -> BLF: given that admitted evidence, what belief status is warranted?
\`\`\`

The qualified ATT + BLF case uses:

- E1: SUPPORT P
- E2: OPPOSE P
- E3: SUPPORT Q

ATT focuses on P and selects E1/E2 only. BLF receives only E1/E2 and returns
\`CONFLICTED\`.

BLF does not re-run ATT and does not search the unselected evidence set.

If a route explicitly requires an \`AttentionSelection\` and ATT is disabled, the
route fails closed through \`AttentionSelectionUnavailable\`. It never falls back to
the full evidence set.

BLF itself does not globally depend on ATT; directly supplied qualified evidence is
a valid BLF input.

## ON / OFF semantics

BLF ON permits explicitly due \`blf.assess\` work with an exact S3 binding.

BLF OFF suppresses that work only. Unrelated MEM or other enabled capability work
remains admissible.

Because S6 BLF is stateless, there is no persistent belief state for OFF to delete.
Capability OFF therefore changes route admission only.

## Downstream boundary

A \`BeliefAssessment\` may later be supplied explicitly as one input to TALK, CTL,
or CNC work.

S6 does not add those integrations.

In particular:

- provider expression is not BeliefEvidence;
- provider text does not update BLF;
- belief does not write Memory automatically;
- belief does not mutate Current Intent;
- belief does not start or mutate SkillExecution;
- belief does not propose, authorize, or issue Action.

## Why BLF is not a World model

S6 represents one explicitly named proposition per assessment. It has no entity
database, map, universal state table, automatic observation ingestion, source
reliability model, or claim of global truth.

The mechanism cannot answer arbitrary questions about the World unless the caller
supplies a structured proposition and qualified evidence for that proposition.

## Why BLF is not a central executive

BLF has no:

- event loop;
- clock;
- scheduler;
- trigger detector;
- dynamic descriptor dispatch;
- model provider;
- mutable persistent state;
- action authority.

The source/caller owns why belief work is due. EpochPlan only orders an explicitly
bound operator after Action supervision under the existing S3 rules.

## S6 scope limit

S6 does not implement CNC, PRD, PLAN, LRN, or HABIT.

It also does not implement:

- persistent belief revision;
- learned reliability;
- numeric confidence;
- model-assisted belief inference;
- automatic provider-output integration;
- automatic Memory integration.

Those remain separate future mechanism questions.
