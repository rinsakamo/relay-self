# G Lane G1 — Genesis / Heredity (Issue #622)

**Scope:** experiment-local, deterministic, offline mechanical infrastructure.
G1 is NOT a live Self factory, evolution-result claim, authority to operate
Minecraft/LLM/GPU, or a substitute for an M/R-authenticated physical receipt.

## Reused reference and why the original remains intact

`experiments/evolved_values.py` (#42) already contains the key causal pattern:
a seeded founder distribution; `RewardGenes.mutate`; a child with an explicit
parent ID and fresh `q_values`; and survival/reproduction outside the
learning-reward function. It is the non-production comparison baseline.
However, its nearest-food oracle, evolving intrinsic reward genes, age cutoff,
and integrated food/energy/reproduction controller cannot be silently
equated with Colosseum 2.0's proposed starvation-only lineage terminal
semantics. G1 extracts **only the generic heredity pattern**, not its controller.
#48's paper-matched Student-t mutation stays a separate experimental protocol.

## Fixed G1 boundary

```text
M / R: World outcome and metabolic ledger
       -> MOutcomeBatch(tick, batch_id, complete active roster)
       -> ALIVE (with nonnegative declared surplus) or STARVED
G:     update living set, retain terminal record once
M / R: physical birth-cost debit and birth opportunity authorization
       -> BirthAuthorization(receipt_id, same batch/tick, count, debited_total)
G:     choose an eligible parent and spawn immutable heritable Genome
       -> lineage Individual(parent_id, generation, genome, receipt)
S:     future separate construction of live Self from the genome
L:     future separate fresh lifetime Memory / Habit / learned state
V:     controlled selection-vs-learning, mutation/selection/OFF, knockdown
```

### Actual authentication limitation

`MOutcomeBatch` and `BirthAuthorization` are **typed offline example
envelopes**. Their receipt IDs and reported `debited_total` are not signatures,
and G1 cannot prove who produced them. It rejects invalid/stale/duplicate
inputs, but does not independently confirm World or M source, actual birth
payment, or newborn physical spawn. An M/R production adapter must check
original provenance, immutable ledger version, exactly-once debit and World
admission **before** supplying these objects. No G1 call can itself debit
energy, heal a defeated Self, refill food, or start Minecraft.

The M0 Draft #617 remains independent: its `metabolism_step` and
`combat_respawn` are owned by M. A combat HP knockout/respawn is not
a terminal G event. A permanent G `STARVED` means M already confirmed true
metabolic exhaustion; no G inference from damage, win rate, or energy reading.
M's true energy is never copied to `Genome` or `Individual`.

### Traits: only three initially justified experimental knobs

| Genome trait | Intended downstream initialization | Range |
| --- | --- | --- |
| `sensor_gain` | M0 `Interoception.gain` | 0..2 |
| `exploration_rate` | #42-like `epsilon` | 0..1 |
| `learning_rate` | #42-like Q update rate | 0.01..1 |

Founders are uniform in the declared founder intervals. Offspring inherit
one parent plus independent seeded Gaussian mutation with explicit per-trait
sigmas, then clip to their bounds. This is NOT a paper-matched biological
mutation distribution. The production S/L initial trait bindings are not yet
qualified; a field name alone does not make an actual adjustable Self trait.
Do not add ad hoc intelligence, survival-preference, aggression, or
reward-for-food genes in G1.

## Parent selection, budget, controls

- Default: uniform draw among the current M-qualified surviving cohort.
  This includes survivors reporting zero surplus.
- Comparator: draw among the same cohort with weights equal to M-supplied
  nonnegative energy surplus. All-zero surplus is an explicit no-selection
  failure, not an automatic random fallback.
- Parent stays alive. Newborns are NOT eligible as parents until their first
  subsequent complete M status batch.
- G1 bounds simultaneous population and cumulative births. Every birth
  window carries positive pre-debited external cost; G only checks the declared
  total and consumes its ID exactly once. Actual resource conservation is
  outside this library and is NOT qualified by these tests.
- Mutation OFF: `mutate=False` (or multiplier=0) with true inherited Genome.
- Inheritance OFF: `inherit=False` samples an independent new Genome but
  keeps a parent ID to expose the ancestry/contact opportunity. The independent
  child genes are not claimed to be genetically inherited.
- Selection OFF: requires **M/V-matched exogenous opportunity control** (e.g.
  standardized forced eligibility/distribution) because permitting a starved
  parent to reproduce would falsify World viability. G1 deliberately does not
  forge this control; no selection-off scientific effect has been measured.
- Same Genome replication for V knockdowns can be represented by an immutable
  `Genome` value later; copying acquired Memory/Habit is an S/L/V state-cloning
  transaction, deliberately absent from G1.

## Running the offline tests

```bash
python -m pytest tests/test_genesis_heredity_experiment.py tests/test_evolved_values_experiment.py
python -m pytest
ruff check src tests experiments adapters observability
python tools/check_repository.py
```

Expected claim ceiling: offline mechanics validated under exact HEAD only
when GitHub CI actually reports success. Neither selective advantage nor
generational emergence is inferred from deterministic unit tests. No
legacy experimental results are rewritten. No automatic physical runs.


## G2 — funded-parent commit protocol (2026-10-13)

The independent M Lane has already implemented M2 physics and its own offspring
population (#621, latest inspected M2 HEAD
`7410e1a806b205ebc795fa9c27e06cb394b4f46f`).
**Do not duplicate or graft M2's simulator onto this G branch.**

### Reconciliation: a real parent identity gap in G1

In G1, `spawn_children` could receive a generic paid-total assertion and *then*
choose a random parent. That is adequate only for its isolated mechanistic
exercise; it cannot bind the claimed M debit to the genetic parent. G2 introduces
`experiments/genesis_g2_handoff.py`, an additive **offline** upgrade:

1. G1 retains the original separate legacy experimental API and its frozen
   mechanical tests. For G2, instantiate **`FundedGenesisRegistry`**, which
   rejects the old generic `spawn_children` call outright.
2. External M/R declares **`BirthOpportunity`** for the current complete M
   survivor snapshot and lists only its physically funded-eligible parent IDs.
   G does not calculate eligibility from an assumed hunger/fitness target.
3. `prepare_births` fixes the **exact sampled parent IDs** *before* any
   claimed M debit. One plan per M batch, unique plan ID and cap checks; the
   parent sampling distribution is explicit and deterministic.
4. M must subsequently fund precisely those parents. An offline
   `FundedBirthReceipt` declares a unique event ID, plan ID, same tick/batch,
   and ordered `PhysicalBirthDebit` records with parent IDs, before/after
   parent energy and transferred child energy.
5. `commit_funded_births` refuses wrong parent, missing birth, extra birth,
   duplicate debit, incorrect transfer cost, broken energy conservation,
   nonconsecutive repeated-parent debits, stale tick/plan/receipt and any
   previously finalized plan. Only after **all** checks does G assign a
   `Genome`, generation and immutable genealogical `Individual`.
6. `abort_birth_plan` closes a plan without newborns. No second random
   selection from that same M tick, so a failed selected parent cannot
   trigger silent genotype-favorable re-selection. The next M batch may make
   a new plan.

Both parent and child remain in the G active roster after a successful
commit, but G has not constructed either physical body, S Self runtime,
L learned state or Minecraft avatar.

**Remaining external-proof gap:** These are structural, caller-reported
energy-debit fields, **not signed, source-qualified original M/R receipts**.
A forged object passing shape checks is not evidence of paid energy.
If M actually debits an energy ledger then G rejects/aborts the plan, G2
does not roll back M's physical state; an authoritative caller must ensure
all-or-nothing ordering, idempotency and reconciliation across M/G/S/R
before production admission.

**Current M2 contract mismatch:** M2 `BirthRecord` contains generation,
parent/child ID, physical energy before/after, child provisioning and traits,
but lacks G2's exact **batch/tick, preselected parent plan ID and unique debit
receipt identity**. M2 also runs generation-disjoint cohorts (offspring become
the next cohort) while G1/G2 preserve an active parent with concurrent
offspring. M2's two trait alleles are `cue_bias` and `sensor_coupling`, *not*
the G1 three initial knobs. Therefore **a direct adapter is NOT QUALIFIED**:
neither copy M2 child IDs/genes into G2 nor claim source/transfer identity.
M/R owners should decide on a shared event schema and real funded/declined
authorization only when integration is required.

### G2 verification ceiling

- Dedicated deterministic tests cover plan/parent binding, conserved
  per-parent debit chains, lineage, mutation/identity, capacity, duplicate
  and forged-field rejection, no retries after abort, and untouched acquired
  state. Existing G1 and historical #42 regression tests remain intact.
- Main-target GitHub CI is the only exact-head qualification when completed.
- Selection OFF still requires externally defined M/V-matched viability and
  independent study; setting `inherit=False` is **not selection OFF**.
- No original World birth, true authorized energy debit, M2↔G2 production
  adapter, S-constructed Self, Minecraft/LLM/GPU, science or merge.
