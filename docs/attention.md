# S5 Bounded Attention

## Purpose

S5 introduces the first genuinely new post-Paper2 RelaySelf cognitive mechanism:
bounded deterministic attention (\`ATT\`).

The mechanism is intentionally narrow:

\`\`\`
already-available structured candidates
        -> explicit AttentionCriterion
        -> filter / priority order / top-k gate
        -> immutable AttentionSelection
        -> explicitly bound downstream work
\`\`\`

ATT is not a persistent controller and does not own the source candidates.

## Ownership model

\`AttentionCandidate\` contains only:

- a stable \`candidate_id\`;
- an opaque \`payload_ref\` pointing back to caller/source-owned data;
- explicit \`Provenance\`;
- an integer priority;
- explicit structured focus keys.

It does not contain an arbitrary mutable payload and it does not transfer ownership
of Present, evidence, Memory, Skill state, or any other source state into ATT.

\`AttentionSelection\` is a frozen transient value. No selection is retained after
the caller stops referencing it unless another existing owner explicitly integrates
derived data through its own contract.

## Criterion semantics

\`AttentionCriterion\` is the first RelaySelf criterion that is legitimately
classified as \`COGNITIVE_ORIENTATION\`.

It can explicitly specify:

- one structured focus key;
- one minimum priority;
- bounded \`top_k\`.

The implemented operator always orders eligible candidates by descending supplied
priority. Equal priorities preserve caller/source order.

ATT does not infer semantic relevance from free text.

This is distinct from existing \`CONTRACT_GUARD\` criteria:

\`\`\`
contract guard
  = validates whether data or an owner transition is admissible

attention criterion
  = chooses orientation / priority among otherwise valid candidates
\`\`\`

S5 does not relabel existing MEM / CTL / SKL / TALK guards as cognitive attention.

## Capability and descriptor surface

S5 preserves the frozen S2 descriptor inventory and extends it without rewriting it.

The new capability is:

\`\`\`
ATT

operator:
  att.select
    -> relay_self.attention.select_attention

criterion:
  att.explicit_orientation
    -> COGNITIVE_ORIENTATION

port:
  attention.selection.out
\`\`\`

ATT declares no durable state scope and no capability dependency.

The operator is classified \`READ_ONLY\`: it produces a transient immutable result
but does not mutate a semantic owner.

## EpochPlan integration

ATT work is admitted exactly like other S3 work:

\`\`\`
source-owned due item
+ ATT enabled
+ exact explicit binding
-> att.select EpochStep
\`\`\`

The planner does not invent attention triggers, candidate relevance, or priority.
Descriptor \`implementation_ref\` remains audit metadata and is never dynamically
imported.

The minimum ATT path makes zero provider/model calls.

## ON / OFF semantics

ATT ON means an explicitly due and explicitly bound \`att.select\` item may run.

ATT OFF means that due ATT item is placed in \`EpochPlan.suppressed\`.

Turning ATT OFF does not:

- delete or mutate caller-owned candidate data;
- delete retained Memory;
- disable unrelated MEM, CTL, SKL, or TALK routes;
- fabricate an \`AttentionSelection\`;
- substitute the full candidate set.

An explicitly ATT-dependent downstream binding must call
\`require_attention_selection\` (or perform an equivalent explicit check). If no
selection exists, it fails closed before the downstream cognition runner is called.

That dependency remains caller/route-owned. TALK and CTL do not acquire a global
dependency on ATT merely because one bounded route composes them.

## ATT + TALK qualification

The combined bounded profile is:

\`\`\`
structured candidates
  -> ATT deterministic top-k selection       # zero provider calls
  -> explicit ATT-dependent TALK binding
  -> one RelayEngine.open call               # exactly one provider call
\`\`\`

The qualification verifies that the TALK request contains only the selected
candidate references. Disabling ATT suppresses the ATT work and the dependent TALK
binding fails closed rather than silently using all candidates.

An unrelated TALK route remains independently runnable with ATT disabled.

## Authority negatives

S5 explicitly preserves:

\`\`\`
attention != belief
attention != truth
attention != current intent
attention != memory
attention != skill mutation
attention != action authorization
attention != action issue
attention != scheduler ownership
\`\`\`

The selection function receives none of the Current Intent, SkillExecution,
ActionLifecycle, PersistentCognition, ActionSupervisor, or RelayEngine owners.

Tests hold these owners beside ATT selection and verify that no owner transition is
caused by attention.

## Failure modes

S5 fails closed for:

- malformed candidate metadata;
- duplicate \`candidate_id\`;
- malformed criterion bounds;
- an explicitly ATT-dependent route with no \`AttentionSelection\`;
- normal S3 missing/mismatched binding errors.

An empty selection is still a valid explicit ATT result. Whether downstream work can
act on an empty result remains the responsibility of that downstream route.

## Why ATT is not a central executive

ATT has:

- no persistent instance;
- no event loop;
- no clock;
- no trigger detector;
- no runtime registry;
- no dynamic dispatch;
- no action authority;
- no cognition provider;
- no mutable candidate store.

It is a pure deterministic transformation over one caller-supplied candidate tuple
and one explicit criterion. The existing stateless EpochPlan only orders an already
due ATT binding.

## S5 scope limit

S5 does not implement BLF, CNC, PRD, PLAN, LRN, or HABIT.

It also does not add model-based attention. If a future experiment needs model
cognition for attention, that path must be explicitly admitted and separately
qualified rather than being hidden inside the minimum ATT mechanism.
