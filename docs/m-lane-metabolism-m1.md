# M Lane M1 — Individual Adaptation / Offline Colosseum 1.0

**Authority:** #616, built directly on M0 Draft #617 exact `4bdc9daf0444e55908cff321111bae9a2927942c`. No edits to S/L/R/V owners or protected main. No Minecraft/LLM/GPU. This is a bounded *offline research fixture*, not a qualified Colosseum World.

## Discriminating hypotheses and cheap controls

- **H1-null (primary):** body metabolism + noisy energy sensation + pre-existing #42 Q learning, when the Q learner receives **zero** reward, need not learn food-seeking behavior. Test `q_zero` with learning ON/OFF under exactly paired World schedules. Do not interpret survival filtering or random meals as within-lifetime learning. A finding of no difference is valid negative evidence only for this restricted controller/environment.
- **H1-coupling:** a prewired sensor/action rule (`reactive`) can change eating with sensor gain/noise, but is **engineered**. It is a cheap explicit-value baseline and cannot establish emergence.
- **Positive control:** `q_food` gives #42's existing `Agent.learn` an overt +1 for a consumed food unit, explicitly injecting food preference. Its learned Q values demonstrate that the measurement/controller channel can respond to a teaching signal, **not** that reward arises from metabolism. The no-learning version is its ablation.
- **Strong baseline:** `fixed_cue` already knows the public opportunity/action mapping. Compare it alongside `fixed_wait` and `random`; never claim learning is necessary if an inexpensive rule matches it.
- **Sensing costs:** use `observation_cost` as a **declared basal-expenditure increment**, not measured GPU cost. Alter `gain`, `quantum`, and `noise_sigma` with paired independent action/World/noise RNG streams. Changes in performance are not themselves evidence of a latent value mechanism.

## Protocol

Each World tick supplies a publicly visible `opportunity` cue: 0 none, 1 WAIT, 2 MOVE, 3 FIGHT. Exactly one verified food unit is collected only when an action matches the cue. This is a deliberately artificial, fixed encounter schedule; it is not Minecraft loot or a real arena win. `metabolism_step` from M0 owns physical cost, genuine evaluator-side consumption, capped intake, and once-only terminal starvation. HP respawn is not used by this reduced fixture. Separate seeds freeze the cue schedule regardless of actions or sensing.

The controller gets only the cue and the output of `observe_energy` (plus optional independent sensor noise). It never receives `BodyState.energy`, death labels, fitness, reproductive outcome, or an evaluator energy delta. The legacy #42 `Agent` Q-controller is reused solely for `choose_action` / `learn`; its `energy` field is a *constant dummy zero* unrelated to M0 body physics. It cannot serve as a World observer. `q_zero` passes zero on every learning update. `q_food` is **explicit reward injection** and strictly a positive-control arm.

Run `python -m experiments.metabolism_m1 --seed 17 --horizon 48`; output is reproducible JSON with individual policy survival ticks, observed meal count, gross intake, expenditure, overflow, terminal state, and the number of Q updates/nonzero Q entries. Import `paired_suite` for tick-level audit traces. Evaluate seed families before considering any effect; a single seeded outcome is not scientific significance. Descriptive pre/post statistics on survivors alone are vulnerable to survivorship/censoring bias. Do not silently select the winning seed or tune thresholds to make a result positive.

## Stop/negative criteria

1. No **positive** H1 learning claim if reward-free ON/OFF are identical, or if sensor changes do not affect action through an independently stated coupling.
2. No claim that direct-food-positive-control Q learning proves reward emergence; it is a deliberately injected training target.
3. No success classification based solely on alive fractions or favorable chance food, or if `fixed_cue` matches/exceeds the learning arm.
4. If reward-free learning is blocked because Q values are all zero, record this *mechanistic boundary* rather than adding survival-positive or food-positive training targets behind the scenes.
5. Real World authentication, HP combat, food provenance and live Resource/Action authority remain entirely with R/S. The M1 cue model does not authenticate real food. Engineering CI may pass without behavioral/scientific validity; V #544 independently adjudicates any future qualification.

M2 must reuse #42 inheritance/mutation/selection and add held-out no-selection comparators; this M1 fixture neither creates offspring nor equates population persistence with lifetime learning.
