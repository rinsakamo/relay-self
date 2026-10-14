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

## V2 continuation — independent S `ground2observe` source-boundary review

S product Draft #545 subsequently implemented an **opt-in** nonforcing observation path at separately pinned exact HEAD `6f95c34918fbe29fea56bc7284e94c4edce21aff` ([#537 source report](https://github.com/rinsakamo/relay-self/issues/537)). All four arms below are replayed only on S's unchanged `test_b0_ground_foraging._ground()` **source-shaped synthetic fixture** with the same native food13 and visible staged-item target, using actual S `nonforcing_ground_decision`. V computes and enforces its own expected outputs; it never uses the S fixture's expected assertions as the result, executes no issued S Action, and reads no original WSL2 evidence.

| Arm at default M0 E12 | First synthetic decisions | M0 after decisions | Interpretation |
| --- | --- | --- | --- |
| Sensor ON | 7 × nonissued WAIT → SEEK on 8th | E8.5, tick7 | quantized sensor: E8.5 rounds to observed 8 |
| Sham ON | same as ON | E8.5, tick7 | no sham overhead observed from this source-shaped trace |
| Masked gain0/bias12 | 16 × nonissued WAIT | E4, tick16, **alive/censored** | **not** M0 starvation at V's fixed horizon |
| Native-only cheap | SEEK on 1st | E12, tick0 | strongest simple baseline already seeks |

Independent V AST source-bound check reads only S source functions and confirms `acquire_staged_ground_flesh` permits **24 opportunity decisions** and **8 issued moves per epoch**, while `run_two_ground_epochs` permits two epochs. This does **not** implement V's frozen **16 global M0 ticks / 8 total MOVE budget**. In addition, S's hunger staging and operator placement are not a precommitted paired exogenous timeline; WAIT costs **per decision**, not actual Minecraft elapsed time. M0 terminal outcome must not be described as Minecraft physiological death.

The terminal classification is `V2_S_NONFORCING_OFFLINE_PARITY_WITH_PREREG_MISMATCH`, **not a G0 live admission**. The V-owned module `v2_s_nonforcing_review.py` and negative tests reject forged real outcomes, an 8-WAIT quantization claim, premature M0 death at tick16, altered source heads or revised move/horizon totals. Read-only pinned S CI tests are executed separately. No S code or frozen V2 preregistration was changed.

**Handoff to S/R:** provide an explicit per-arm *global* M0 16-tick stop/censoring rule (inclusive of pre-item hunger staging and all M0 expenditures), a global maximum of 8 issued MOVE, identical precommitted food timing/World start/exogenous conditions for matched arms, and S/R separately qualified original physical source and nonissued WAIT envelope. Do not silently expand the V study to 24 decision probes, treat early SEEK as a measured food outcome, or call the synthetic cheap baseline test a causal nutrition benefit. After product reference and independent sources are ready, any physical run still requires a **fresh one-shot user authorization per arm**.

**Current:** V source-engineering only, World trials 0, real baseline/reference not qualified, independent original bytes NOT_RUN, `G3_NO_GO`, `NO_PRODUCTION_GO`.


## V2 pre-run mathematical non-discrimination gate (2026-10-14)

**Critical new finding, before any real outcomes or physical permissions:**
V2's frozen primary `M0_TERMINAL_FREE_TICKS_WITH_CENSORING`
is **structurally unable to distinguish all four legitimate arms** under
the registered *16 total M0 decision ticks, maximum eight issued MOVE*
profile. The already specified source-owned M0 physics has initial E12,
basal spend 0.5 for every WAIT/MOVE decision, plus 0.25 extra per MOVE.
Without food, its largest possible expenditure under this envelope is

```text
16 * 0.5 + 8 * 0.25 = 10
remaining E >= 12 - 10 = 2 > 0
```

A verified EAT adds energy and cannot cause earlier metabolic death
under these fixed costs. FIGHT is not part of this bounded single-item
S ground runner. Therefore every **valid completed 16-tick episode**
remains M0 alive, and the primary terminal-free count is **16 in every
arm**, including the sensor-masked arm. An observed primary difference
would indicate a source/physics/accounting/protocol violation, a
prematurely stopped/invalid episode or a changed experimental envelope,
**not** a valid sensor fitness effect. Variation in secondary EAT,
M0 final E or MOVE count may still be observed and recorded, but
does not rescue the registered primary contrast.

The V-owned `check_preregistered_primary_reachability()` is a
source-conditional algebraic *NO-GO* check with negative test coverage,
not original-byte readback, learned goal evidence, or power estimation.
Independently reconfirm actual M0 source config at the pinned S SHA
before any real admission; if true source costs/budget differ, FAIL
rather than treating this frozen analysis as physical authority.

**Action:** do **not** launch a 4-arm × 4-paired-start physical trial
expecting the current V2 *primary* to show discrimination. Preserve the
original V2 manifest and all past evidence unchanged. V may propose a
**new versioned prospective amendment before any physical outcome**:
either extend the M0 horizon sufficiently to permit an OFF/no-food
terminal (24 WAIT ticks are needed under the given E12/basal0.5), or
register a genuinely informative external nutrition/net-energy primary
with explicit cheap/sham baselines and cost/World-time controls.
A longer horizon is not by itself evidence of new cognitive value:
the cheap native-only baseline may equal or beat sensor-gated ON.
Any amended design requires its own independent reviewer/CI,
qualified R World source, exact matched environment and **fresh
per-run user authorization**. Current `G3_NO_GO` remains unchanged.
