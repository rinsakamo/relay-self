# R2-3a — first reJOIN A / continuing B: Original Owner tri-source CURRENT

**Status:** CPU/DEV opt-in source compatibility; **no L1 input routing switch**,
no QUAL/SCIENCE promotion. This is the first bounded part of R2-3,
not permission for any model, Intent, Physical, or U31 S2 production cutover.

## Immutable inputs and the missing source distinction

- I U31 exact `d3034026a8eea3d2d4927527f5bc0d6ad0455457`,
  R1 exact `06349c7a216b042511a90e05ad0196f4a7164378`.
- R2-0 `a8d1492a1e54f3f647109da183cf71179c7b5932`;
  R2-1 `c9a3eec3172af17c8dc87bbb1aaf9ec1a455be81`;
  R2-2 `368dac0cbb051e875680839d859d362d6f529386`.
- Q independently reviewed R2-1's original Owner read API using pinned
  Git/CPU tests (Issue #1088), allowing candidate comparison only.
- Prior U31 original WSL Q6/Q7/Q8/Q11 PASS attests its old motor evidence,
  **not** a live R2 Context rollout.

R1/R2-1 Stage28 `CurrentSchemaFrame` has **two** Source refs (Native+Paper)
and a first-login epoch-1 check. The existing post-reJOIN original
`ResidentCognitiveWorkOwner.read_present_cpu` uses a **third**
`composite:rejoin:<revision>` ref to qualify A's new Native session and
B's continuing Native with the new shared Paper source. Passing old
`boot/world/links` to read that composite would incorrectly promote
historical receipts to current authority.

## Bounded R2-3a implementation

The original Owner now offers a second **opt-in read method**,
`read_rejoined_context_shadow_cpu(bridge, self_id,
initial_receipts, historical_composite)`.

- The new module `r2_3_rejoin_composite_context_dev.py` delegates live
  source authentication to the **existing original**
  `ResidentCognitiveWorkOwner.read_present_cpu` and its
  `build_rejoined_owner_present` /
  `build_rejoined_owner_source` / native+Paper Composite verifiers.
- The method does **not** install or change the original source family,
  run a scheduler, issue L1, start new Native/Paper processes, register a
  Schema, or mutate original Memory/Intent/Skill.
- Project the already qualified original Present to
  `R23RejoinedCurrent`: original `RejoinedOwnerSource` including the
  immutable Composite receipt, original current `SchemaSnapshot`, only
  qualified `CognitiveSignal`, and the **three** exact source refs.
  `coverage=UNKNOWN`; original OBSERVED WorldBody lens claims are *not*
  promoted to CURRENT.
- Bind the same original Owner pointer and exact Native session, Owner
  epoch, registry revision, Self, Paper scope and Source. Reject
  misqualified reJOIN types (A must be `RejoinedCompositeSourceReceipt`;
  B `ContinuingCompositeSourceReceipt`), source refs, detached or
  retired Owner, changed original Schema, and altered signal provenance.
- Re-read original qualified Present under the **existing** resident
  lock before returning. Paper may advance outside the lock; cached
  readers must call `r23_rejoined_context_is_live` to reread **both
  original source and current Owner**, not reuse stale history.
- The report is frozen and has `model_invoked=False`,
  `l1_input_switched=False`, `memory_adopted=False` and
  `physical_authorized=False`.

Original **second A reJOIN** remains under
`b_np1b_second_rejoin_rearm_dev.py` with a distinct cut and verifier:
R2-3a refuses it rather than silently treating second-generation source
as first reJOIN. It also does not yet compare a post-reJOIN L1 request.
Neither a new L1 candidate nor a GPU/Physical admission is created.

## Verification boundary

CPU test fixtures reuse the **existing original Bridge / two Mineflayer
sessions / synthetic owned Paper process** and its genuine A logout/reJOIN
transition. Tests require separate original A/B Owner identities, A new
Native, B continuing Native, same current Paper, all three exact source
refs, original files and cognition byte/state invariants; negative
cases include foreign Owner, stale Paper, native probe, owner epoch,
registry, historical composite, second cut, mutated CURRENT and a
Paper change between two reads.

Pass only after exact-head full pytest, lint, repository contracts,
Mineflayer and Paper witness succeed. New independent Q approval does
not automatically follow from its earlier pinned R2-1 PASS.

**Next before R2-3 product migration:** match the actual model-facing
post-reJOIN Original L1 request under a separate original Source receipt;
demonstrate no prompt/choice/Need regression and obtain independent
Q review before permitting any input switch. U31 original S1→S2 is
not rerun in this CPU verification.

**Gate:** `R2_3A_FIRST_REJOIN_COMPOSITE_CURRENT_CPU_DEV_PENDING /
R2_3_PRODUCT_L1_SWITCH_HOLD / QUAL_NO_GO / SCIENCE_NOT_RUN`.
