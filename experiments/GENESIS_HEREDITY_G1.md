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
