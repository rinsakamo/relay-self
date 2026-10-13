# M Lane M2 — Inherited predisposition selection / Colosseum 2.0 (offline reduction)

**Authority:** #616. Child of M1 Draft #618 exact HEAD `529b00243e1af77e3d5bca4dd3a9df5d86e3dfd8`; itself child of M0 Draft #617. The entire M2 transaction is experimental, offline, **not** RSEE, production, Minecraft, intrinsic emotion, or V-accepted scientific evidence.

## Physical selection mechanism vs programmed semantics

- Reuses **M0** `metabolism_step` / `observe_energy` for basal and action expenditure, verified food acquisition, energy capacity and final starvation.
- Reuses **#42** `Agent`, `RewardGenes.mutate`, and `make_child` *solely* as a two-allele Gaussian mutation and parent→child energy-transfer adapter. In **M2**, the internal `RewardGenes.food` field transports `Traits.cue_bias` and `RewardGenes.movement` transports `Traits.sensor_coupling`. They are **not reward coefficients**: `Agent.learn` and `apply_body_dynamics` are never called. No fitness target, energy delta, or explicit survival/food label enters an individual learning update.
- A public encounter cue (0 no food; 1 WAIT; 2 MOVE; 3 FIGHT) unambiguously identifies the action that can acquire one food. This **hardcoded cue/action mapping is an engineered, cheap food-seeking predisposition**, not an emergent discovery. The inherited alleles control the chance of exploiting that action: `sigmoid(bias + coupling * normalized_sensed_energy)`, with declared stochastic exploration. Crucially, the coupling *sign* can vary (not predeclared hunger), but the architectural ability to exploit food is **already supplied**.
- The agent only receives cue + quantized/noisy `EnergyObservation`; its policy never receives true evaluator energy, physical reproduction outcome, birth count, fitness, external observer labels or a post hoc 'good/bad' signal. Sensor gain/noise are **fixed experimental factors**, not yet inherited loci. Contingent viability under this narrow model is not evidence of general-purpose cognitive motivation.
- Following M0 tick physics, if a live sufficiently mature body exceeds the **physical** reproduction threshold, the #42 `make_child` adapter subtracts precisely the transfer energy from the parent and allocates it to a newborn. Parent energy is written back to the evaluator ledger; offspring retain only two initial alleles and inherited *physical provisioning*, never episodic Memory or #42 Q tables. Every parent has a bounded births cap.
- A cohort ends after a bounded number of steps or starvation. Born children populate the next cohort, subject to a genotype-blind stochastic capacity bottleneck; **no birth means extinction**, with no population resurrection, elite reseeding, or hidden age-mortality.
- **Inherited arm:** offspring acquire mutated parent alleles. **Disconnected inheritance null:** physical births and genealogy are still measured, but next-generation alleles are deliberately redrawn/mutated from the *frozen founding cohort*, severing phenotype/parent fidelity. This null is a non-biological experimental shuffle, not an alternative real reproductive biology. The initial generation and World cue schedules are paired for both arms.
- **Passive learning ON/OFF:** reuses the M1 `DeltaProbe` for sensory transition prediction as a non-authorizing diagnostic. It does not influence action probabilities. ON/OFF therefore **must produce identical physical trajectories and lineages**; learnable directional behavior is **not implemented**. This isolates natural selection of predispositions from within-lifetime learning rather than claiming both have been shown.

## Comparators and qualification ceiling

A run produces cohort size, true births, starvation deaths, meals, mean lifespan, actual parent IDs, mutable alleles, inherited child provisioning, capped next cohort and Q-independent passive forecast updates. **Heldout schedules are entirely separate** from every training generation. Heldout mean births per individual, mean meals, ticks and starvation fraction are reported for frozen founder traits, final retained-lineage traits (or `null` if extinct), **strong fixed-cue oracle**, random and wait controls; extinction is reported, not filtered away. A genotype-blind cap and different selected cohort sizes can introduce additional variance; comparisons use per-evaluation means, not raw population totals.

`python -m experiments.metabolism_m2 --seed 17` prints deterministic descriptive JSON. Across-seed reliability, independent prospective pre-registration, stochastic dominance, real food provenance, sensor gain/noise regimes and blinded V evaluation are **NOT QUALIFIED** by unit tests. Never select seeds based on a desired effect. The current reduction permits cheap fixed cue rule to match or outperform selected genomes; **NO_GO** is a valid outcome.

### Explicit failure and non-claims

- If no physical births occur, the entire lineage dies; do not repopulate it silently. No fake forced reproduction or survival positive signal.
- A new allele frequency or phenotype after generations shows **selection under this programmed cue affordance**, not emergence of a learned value or emotion. A null-control failure does not prove motivation.
- An observed survival/birth advantage requires comparison against detached-inheritance and **fixed-cue cheap control**, plus independent heldout/seeds before any V adjudication. M Lane never awards scientific SUCCESS itself.
- No S Lane Action owner, L Lane learning/Memory owner, RSEE runtime, Minecraft launcher, LLM/GPU experiments, R/V source receipts, or protected main changed.
- M3 group dynamics and inherited sensor fidelity/cognition-cost loci remain future separate hypotheses, not hidden extensions of this minimal M2.

## M2b — resource scarcity discrimination (predeclared 2026-10-13)

**Prior M2 result is frozen:** Four historical seeds 7/17/31/43, uniform
encounters, permissive food and 3-birth ceiling: fixed WAIT achieved
3.000 births per individual, so H2 remains SCIENCE_NO_GO. This extension
does not modify that configuration, seed family, results or interpretation.

**New independently fixed synthetic condition:** profile `scarce_active`
changes ONLY opportunity scheduling: each third tick has exactly one food
opportunity, with a seeded MOVE or FIGHT cue; other ticks have no food
and WAIT is never a food-producing action. The same M0 energy physics,
threshold, transfer, genetic initialization, mutation and parent-funded
reproduction are retained. Each generation and three heldout episodes
use profile-specific immutable sequences, independent of policy choices.
Seed family is frozen in source before running: **101, 211, 307, 419**.
No tuning/reseeding allowed after opening results. A predeclared
resource constraint follows the **mechanical necessity** that WAIT-only
cannot reach the reproduction threshold when initial energy is below it.

**New cheap controls:** fixed MOVE and fixed FIGHT alongside WAIT,
random and full-cue oracle. Zero WAIT reproduction is a calibration
identity only, not an adaptive-cognition effect. Either cheap active
controller matching/exceeding evolved lineages implies no distinctive
H2 support. Oracle is a designed upper bound for food acquisition,
not an expected evolutionary competitor to beat.

**Study logic:** compare (i) genetically inherited (ii) disconnected
genotypes with independently redrawn frozen-founder distribution,
(iii) cheap behavior, using independent heldout mean births, starvation
and meals, reporting `null` when a lineage goes extinct. Do not
treat changed offspring counts, a designed cue-action mapping, or a
sensor-dependent stochastic exploitation coefficient as endogenous
value learning. Sensor coupling is genetically selected but still
pre-wired; passive lifetime prediction is nonauthorizing.

**Engineering gates:** legacy schedule preservation, exact seed family,
no WAIT food, terminal starvation, real parent-to-child energy transfer,
cheap active nulls, deterministic behavior, invalid profile/seed fail
closed. The dedicated CI must print all four seed results and all
ordinary repository checks must pass. Results are DESCRIPTIVE ONLY.
A potential heldout advantage versus disconnected inheritance
is not H2 qualification without V's independent design, replication
and improvement beyond the cheapest competitive active controller.

Run `python -m experiments.metabolism_m2_scarcity --seeds`. No
Minecraft/LLM/GPU, new central owners, S/L/R/V changes, or PR merge.

## M2c — MOVE/FIGHT physical expenditure factorization (prospective matrix)

After M2b's 4-seed result was frozen, the user noted that energy costs
for MOVE/FIGHT should be consequential. M2 already has physical costs:
per-tick `basal=0.23`, additional `MOVE=0.12`, `FIGHT=0.28` and
food intake `+4`. M2c does NOT change any baseline; it measures how
increasing action costs independently changes real accounting and cheap
baselines under the already fixed `scarce_active` profile.

A new separate fixed seed family is `503,607,709,811`, not any of the
previously inspected seed sets `7/17/31/43` or `101/211/307/419`.
Before first observations, predeclare the following full 2x2 factorial
of additional MOVE/FIGHT expenditure per tick (WAIT remains basal):

| Condition | MOVE additional | FIGHT additional |
|---|---:|---:|
| original | 0.12 | 0.28 |
| costly_move | 1.10 | 0.28 |
| costly_fight | 0.12 | 1.45 |
| costly_both | 1.10 | 1.45 |

These high levels are **mechanistically motivated**, not fit to outcomes:
in the scarce World there is a food opportunity only every third
tick and the rewarded action alternates MOVE/FIGHT via precommitted
random cues. An always-MOVE / always-FIGHT policy typically accesses
only half of opportunities; even before move cost the expected 4
energy intake per 6 ticks is about 0.667 energy/tick. At high cost,
each corresponding fixed policy has cost above its expected intake.
An informed cue-conditioned cheap controller that rests on blank
ticks still has an advantage, which is why it stays a mandatory
strong comparator.

The evaluator adds a **read-only physical ledger** to `Episode`:
counts of WAIT/MOVE/FIGHT and true energy intake, actual expenditure,
capacity overflow, and the unpaid shortfall on terminal starvation.
Energy balance checks include the energy *actually transferred* to
offspring. No new energy/reward information enters the individual
controller, and no new L/World model is created. These diagnostics
are internal engineering measurements and do not attest authentic
Minecraft action costs.

The matrix reports inherited, disconnected-inheritance, fixed WAIT,
MOVE, FIGHT, cue oracle, starvation, mean births per individual,
and realized physical costs; extinct populations are reported as null
rather than re-seeded. **No score threshold or winner is selected in
advance.** Equal birth ceiling, widespread extinction, or cheap
controller dominance remain fully acceptable NO-GO results. This
parameter survey maps conditions; it cannot establish H2,
within-lifetime cognitive learning, or value emergence from physical
metabolism.

Run `python -m experiments.metabolism_m2_costs --fixed-matrix`.
The CI runs all 16 fixed cases on the exact PR HEAD, as well as the
previous frozen M2/M2b experiments without changing their inputs.
This is a new offline engineering check, not an S/R/V approval
or user-host GPU/World experiment.

## M2d — uncertain action outcomes and temporal memory discrimination

The M2c physical-cost factorial and its seeds **503,607,709,811** are
historical/frozen. This M2d *experiment-local individual pilot*, built
after those results, uses **new prespecified seeds**
`907,1009,1103,1201,1301,1409,1511,1601`.
It does not modify the prior M2/M2b/M2c results or qualify evolution.

**World:** hidden binary regime, known only to the evaluator. In one
regime FIGHT is relatively food-profitable, in the other MOVE is. The
regime is either persistent (same-state probability 0.94) or IID
(same-state probability 0.50) at each step. Agent receives an imperfect
public hint (63% accurate), plus M0 quantized interoception; never
the true regime, food probabilities, damage draw or future cue. Agent
can optionally **SCAN** instead of acting: it pays extra energy
0.55 **now**, receives no food, and the *next* tick receives a
precommitted 90%-accurate hint. SCAN costs WAIT basal energy plus
information cost; it is never free observation or retroactive knowledge.

MOVE and FIGHT obtain at most one food unit per tick with fixed
probabilities (0.80 if the latent regime favors that action, 0.08
otherwise). FIGHT has a second independently precommitted injury
outcome (probability 0.08 in the favorable regime, 0.35 otherwise);
an injury physically spends another 0.70 energy. The initial
energy/food/reproductive bounds reuse M2c `costly_both` without
changing MOVE or FIGHT costs. Independent seed-separated RNG streams
freeze **all potential Action outcomes** before selecting a policy;
policies' actions cannot reroll food, change future regime or bias
future evidence.

**Cheap policies all see precisely the same currently admissible hint
and sensed energy**: WAIT, MOVE, FIGHT, random, instant hint
classifier, last-five-hint majority, model-informed Bayesian two-state
filter, Bayesian belief reset each tick, and SCAN-triggering Bayesian
filter. The Bayes transition/observation probabilities are
**supplied by the experimenter**; its presence is not learned
World knowledge, general reasoning, or biological belief emergence.
Current-cue vs history-retaining Bayes tests the causal value of
cross-tick history in the predeclared environment; IID is a negative
control for that benefit. A full-memory filter cannot be presumed
more cost-efficient than cheap last-five memory. SCAN uses an overt
engineered 'uncertain posterior' threshold and may lose by paying
for information. Neither cue policy nor learned filter has an
endogenous reward; the policy's tendency to select the predicted
food-opportunity action is **already engineered**.

Outcomes are genuine M0 evaluator energy debits/credits (not authentic
Minecraft receipts), offspring paid for via the existing #42
`make_child` adapter, starvation, number of scans/injuries and
cost conservation, prediction of hidden-state truth scored *only by
the evaluator*. The `run_episode` call gives the policy only its
own hint and sensor reading; hidden regime is never supplied.
M2d **does not inherit selected genotypes**, because individual
prediction/decision differentiation must be characterized before
a new M2 population experiment could claim selection pressure.
There are no production L or S semantic grants.

**Acceptance is engineering-only:** deterministic World fixtures,
counterfactual draws paired within regime+seed, same first
observation, scan affects only future cue accuracy, state history
knockout effect in persistent regime and **no history benefit by
construction in IID**, physical energy conservation including injury,
SCAN cost, overflow, terminal shortfall and offspring transfer.
All metrics, including results unfavorable to Bayes or scan, are
reported for the entire frozen 8×2×9 matrix; do not tune seed,
cue quality, transition rate, injury or cost after inspecting outputs.
No claim of information-value gain, H1/H2 scientific success, or
value/emotion emergence without independent V qualification and
cost-sensitive comparisons to the strongest cheap baseline.
