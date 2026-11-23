# R2-2 — Original L1 candidate vs R2-1 Context, Stage28 read-only DEV

**Scope:** CPU-only, opt-in, original **first-login Stage28** Question-adoption L1
candidate comparison. Not a product L1 prompt migration, not real U31
S1→S2/reJOIN certification, no Model/World/Native/Paper launch, and no
Cognitive/Physical authority changes.

## Exact pinned baseline

- Original I U31: `d3034026a8eea3d2d4927527f5bc0d6ad0455457`;
  original U31 files previously rechecked by LocalCodex Q for Q6/Q7/Q8/Q11.
- R1 `06349c7a216b042511a90e05ad0196f4a7164378`:
  initial Stage28 read-only Original Owner/3Self/Schema CURRENT comparator.
- R2-0 `a8d1492a1e54f3f647109da183cf71179c7b5932`:
  one pure nine-field Present validation rule.
- R2-1 `c9a3eec3172af17c8dc87bbb1aaf9ec1a455be81`:
  opt-in `ResidentCognitiveWorkOwner.read_context_shadow_cpu`.
  Independent Q [#1088](https://github.com/rinsakamo/relay-self/issues/1088)
  reported `Q_R2_1_ORIGINAL_OWNER_READONLY_PINNED_GIT_AND_RUNTIME_CPU_DEV_PASS`,
  exact Q SHA `6276cb0a...`, with 26 independent tests. This approved
  only candidate comparison, not runtime L1 input routing.

## Why the existing Stage28 Question candidate

The actual U31 S2 MOVE request is issued after a different, qualified
post-reJOIN original Source boundary. The R2-1 Context reader is deliberately
Stage28 initial epoch 1. Comparing a later S2 request to that earlier Source
would manufacture a false qualification. This stage instead uses the
**already original-registered** `IUnifiedExplorationTurn` and its original
`CoverageAdoptionTurn.request` (L1 Question-adoption choices), which are
genuinely constructed on the same Stage28 Original B Owner Source.

The new optional function is
`compare_r2_2_original_l1_candidate_context(bridge, boot, world, links, receipt)`.

- Requires an existing typed, registered and independently source-revalidated
  `IUnifiedExplorationTurn`. **Does not call preparation**, register a
  candidate, build or modify L1 prompts, mint an inference ticket, execute
  a backend, accept a Question, commit an Intent, or issue any physical action.
- Under the original Resident Owner's **existing** lock, validates the
  original frozen L1 turn, calls the existing opt-in R2-1 read-only Context,
  and compares original/current Owner, source revisions, epoch, Schema,
  qualified exploration Need, Question focus, original `CHOICES`, identity
  Context and non-THINK requirement.
- Explicitly expects Schema CURRENT `coverage=UNKNOWN`. Old 3Self Native
  OBSERVED claims remain legacy lens observations, never copied as CURRENT
  fact. A past Memory pointer is not an action-candidate source.
- Validates the **original L1 turn again** and the R1 Context freshness
  against live Original Owner/Native/Paper at the end. Paper can advance
  outside the original Python lock; no returned comparison is a durable
  admission or a proof that later model submission will still be current.
- Returns only a frozen `R22CandidateContextComparison` with original
  request ID/Question reference/choice IDs/Source revision/Need signal
  reference, all admission/mutation flags explicitly `False`.
  Any missing/foreign/stale/replaced data throws
  `R22CandidateContextHold`, rather than producing a new candidate.

## What remains deliberately unchanged

No changes to the original Owner/Resident/3Self/Memory writers, original
`CoverageAdoptionTurn` builder, I/B original L1 request, inference
scheduler, L1 prompt or model provider, Intent/Skill, Native/Paper/World,
Physical STOP/WAL or U31 code. The comparison is an **opt-in diagnostic**
with **no call site** in the existing L1 submission path.

The original L1 request is *not* reconstructed from R2-1 and no semantic
equivalence of generated model prompts has been established. That would be
a separate design and verification step, especially after reJOIN.

Full exact-head CI and focused CPU negative tests for original A/B, zero
Owner/Memory/Question/action side effects, invalid request/source/Owner,
and concurrent Paper changes are required for
`R2_2_ORIGINAL_L1_CANDIDATE_CONTEXT_CPU_DEV_PASS`.

**Remaining:** `R2_3_HOLD / QUAL_NO_GO / SCIENCE_NOT_RUN`.
