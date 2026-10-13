# V2 / #619 — Product-first interoception knockdown: pre-registration, not science

**Authority:** [#619](https://github.com/rinsakamo/relay-self/issues/619), [#544](https://github.com/rinsakamo/relay-self/issues/544). Stack only on frozen V1 [#595](https://github.com/rinsakamo/relay-self/pull/595) HEAD `53d50029da64a95c56bb56c6d48b5d14ce94e84a`. S B0 opt-in sensor design [#545](https://github.com/rinsakamo/relay-self/pull/545) exact HEAD `34cf226e55645f85172317172c37ae6cbd481ae4` is read-only. No cross-lane merge, source edits, RSEE World start or original evidence read.

## The first falsifiable question

Does access to the experiment-local **M0 energy sensor**, when used by a hand-coded S-owned SEEK gate, improve **independent food acquisition / bounded M0 survival net of action and computation cost** beyond sham ON and the equal-input cheap `native_only` policy?

**This is not yet a hypothesis about learned cognition.** S's optional masked sensor is `Interoception(gain=0,bias=12)` with fixed SEEK threshold 8; ON/sham is gain1/bias0. Masking is a **fixed high readout** and may alter the policy in a trivial and biased way; it does not remove M0 physics, terminal safety, sensory channels from Minecraft, or learning.

## Paired arms (one cohort, no micro-Issues)

| Arm | Sensor | Decision policy | Interpretation |
| --- | --- | --- | --- |
| SENSOR_ON | gain1/bias0 | sensor_gate | reference |
| SHAM_ON | gain1/bias0, same setting path | sensor_gate | toggle artifact control |
| SENSOR_MASKED | gain0/bias12 | sensor_gate | expression lesion; artificially high M0 reading |
| CHEAP_NATIVE | gain1/bias0 | native_only | simple native-hunger / visible-ground-food comparator |

Freeze one qualified **real product** reference after #537's ability threshold is satisfied; the historical single/two staged-food sessions are *not* automatically such a Golden ability and do not provide matched ON/OFF cases. Minimum **4 independent World starts × 4 arms** is a proposed *feasibility* floor, not evidence of statistical power for generalization. Each arm requires a fresh, separately authorized physical run. Study remains **NOT_RUN**.

**Runner prerequisite:** S/R must expose a **non-forcing, bounded** episode that continues after real nonissued WAIT. The current `ground2` runner rejects lack of SEEK as an engineering error, so using it unchanged would create an *artificial failure*. WAIT is never a fictitious issued S16 Action. Keep existing safety L0 and Action owner intact. Operator-driven food item injection must be on a **precommitted external schedule**, identical across arms for a matched World start and independent of policy outcomes. Exogenous seeds, full World initial snapshot, tick cadence, M0 physics, baseline hunger, food availability, retained state, body & resource budgets must be matched. Adaptive trajectories naturally diverge after intervention.

## Outcomes and classification

- **Primary:** terminal-free ticks within a fixed **16-M0-tick horizon**, explicitly reporting horizon-censored survivors. M0 is a **separate experimental ledger**, not Minecraft physiological survival. Do not infer genuine native hunger benefit.
- **Secondary:** native verified S51 issued EAT outcome, M0 terminal/energy/intake, S50 issued MOVE count, item pickup source uncertainty, native food-meter change, timing/CPU/GPU/tokens as *separate measured units*. No guessed joules and no blanket assumption that a ground item was a zombie drop.
- **Analysis:** per independent matched World start, SENSOR_ON–SHAM_ON, ON–MASKED and ON–CHEAP, with survival censoring and cost; no pooled pseudo-replication of frames, no posthoc threshold tuning. Compare cheap table/fixed food strategy where same input suffices.
- **Positive interpretation only after independent V and R original bytes and source/Goal eligibility:** bounded contribution to this hand-coded **sensor-gated** policy under the tested environment, not intrinsic motivation, learning, actual interoceptive necessity for cognition, consciousness or evolution.
- **Null:** no verified ON advantage over sham/strongest cheap; possible redundancy or environment too simple. **Invalid:** source mismatch, forced WAIT rejection, incomplete Action/Goal lineage, forged S16, unqualified physics, inconsistent seed/revision, stale/censored represented as terminal, policy-dependent item distribution, unequal budgets, reused user grant. **Blocked:** reference Golden, independent R/V source proof, non-forcing runner or explicit physical permissions absent.

## Implemented here

- `experiments/validation/v2_knockdown_manifest.json`: **frozen pre-registration**, fixed four arms, metric horizon, no-science authority fence.
- `experiments/validation/v2_knockdown.py`: pure schema admission; only *synthetic* four-arm comparisons allowed. Fake physical receipts, source promotion, arm alias, mismatched World reset, forced SEEK or WAIT-as-Action fail closed. No live evidence can be scientifically admitted by this module.
- `tests/test_validation_v2_knockdown.py`: falsification/negative suite including cheap parity. CI independently runs S owner's unchanged energy-bridge unit tests at pinned SHA.
- `.github/workflows/validation-v2.yml`: offline exact-parent ancestry plus pinned read-only S checkout and full inherited regression.

A synthetic ON vs masked difference, even one with a longer simulated ledger lifetime, is explicitly classified `V2_SYNTHETIC_PAIRED_CONTRAST_ONLY / G3_NO_GO` and never qualified as actual World causal impact. Real original-byte verifier, real trial outcomes, genuine ability freeze and sufficient replication are **future independent gates**, not present in this implementation.

**No new World/Java/Node/GPU/LLM, no Action, no consumed-grant replay, no protected main edit or Draft merge.**
