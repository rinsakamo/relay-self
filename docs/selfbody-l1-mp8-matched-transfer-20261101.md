# RelaySelf MP8 — paired surface challenge and next-World ice-prior transfer

2026-11-01 / [Issue #653](https://github.com/rinsakamo/relay-self/issues/653) / stacked on MP7 [Draft #660](https://github.com/rinsakamo/relay-self/pull/660).

## Scope and stage

**Stage 0 implementation (this Draft): offline only.** No new Paper server, Minecraft World, native S49 Action, fresh source attestation or training admission has been executed here. This stage introduces a pinned MP7 ice-prior fit, an immutable two-World matched design ticket and a diagnostic comparison. Its output must NEVER be described as actual learned transfer or qualified evidence.

Prior MP7 packed-ice readback is frozen at Git blob SHA-1 `7458cbee8f830507cbded9ad9f64894afc35637c`, actual 1-World Actions run `41274077794`, original executing HEAD `49ba1f5f1d2d0c255fc471542c9f7c062229641c`. Seven ordered WAIT transition pairs yield the **in-sample** fit `c_ice ≈ 0.43487855972244` for `displacement[t+1] = c * displacement[t]`. Earlier normal-surface prior `c_normal = 0.20331885786720635`. Neither coefficient is an executable Action policy.

## Proposed Stage 1 — exactly two NEW matched DEV Worlds

1. Use the *existing* S49/S16/S50 owner, original Paper 1.21.8 / Mineflayer 4.39.0 / Java 21/Node 22; same pinned experiment assets and a new unique output root per World. Preserve all MP3–MP7 originals, prior branches, and protected main.
2. **Before either original S49 Action**, independently record the experimenter-fixed seed, actual spawn and position (x/y/z), yaw/pitch, velocity, onGround, game tick, movement mode/input duration, health/food/effects, surrounding 5×5 geometry, inventory, world settings and relevant TPS timing. Match these in paired conditions, recording exact differences and causes. If the starting location or state cannot be matched, **PAIR_INVALID**; do not call two unrelated random spawns a control.
3. World A: retain 25 original solid `GRASS_BLOCK` floor blocks. World B: Paper changes exactly the same 5×5 from `GRASS_BLOCK` to `PACKED_ICE` before original Action; verify block intervention receipts and all subsequent actual underfoot samples. Use a separate world UUID; do NOT use a second Action to cause the change. All other relevant pre-Action state/Action parameters are held fixed or explicitly classified `UNMATCHED`.
4. Freeze the model ticket and both expected conditions **before target WAIT observations**. If two sequential Worlds cannot both have known UUIDs before both actions, freeze a pair-plan pre-World and freeze each bound target before its Action, then seal both target identities and verify the pair independently. Do not substitute later observations into prior training.
5. Run each World via an independently preflighted, explicit DEV opt-in once; no reuse of a previous consent token; owner-issued original S49 Action only. Preserve Paper stdout, S49 report, S16 clear/outcome, prediction-original journal, active config/asset hashes, failures and process cleanup. No L0 action change, no S10/S11/L10 adoption, no real LLM calls.
6. The **original-Paper auditor** (not this offline stage) must authenticate source World/Body identity, action-before-WAIT ordering, eight consecutive callback ticks, seven FIXED-before-next-SCORE pairs, normal/ice floor and matched state. Do not rely only on claimed metadata or a copied report. No claim of physical match unless this audit passes.

**Important:** The MP7 Stage 0 `TargetSetup.matched_state_sha256` is a placeholder interface for a canonical, original-source-confirmed matched-state digest *excluding the intended floor material*. Creating the same literal hash in both Worlds does **not** itself establish physical state equality. A Stage 1 independent auditor is required to derive/verify it, otherwise retain `PAIRED_PHYSICAL_CONTROL_NOT_ATTESTED`.

## Proposed primary evaluation (preregistered before target results)

For each heldout World, evaluate fixed normal `c_normal`, fixed MP7-trained ice `c_ice`, zero, last observation, and a same-information cheap implementation of the selected coefficient. Report per-world MAE/RMSE on 7 one-step predictions and the paired surface contrast; do not collapse into one combined headline.

- **ICE_TRANSFER_OBSERVED_DEV** only if real original source is audited, both Worlds are physically matched, the prior ticket is pre-Action frozen, ice-prior heldout MAE improves versus old normal-prior on the ICE target by **at least 0.005 m**, and normal-prior MAE does not get worse than ice-prior on the NORMAL target. Otherwise classify negative/equivocal. This 0.005 m is an engineering diagnostic threshold, not a scientific significance level.
- A self-contained same-information cheap linear implementation must be acknowledged **mathematically equivalent**; beating old/zero/last does not establish a distinctive intelligence gain over cheap coefficients.
- The two heldout Worlds are a DEV pair, not a replicated randomized controlled study. Even a matched success is at most preliminary evidence; `QUALIFICATION_NO_GO / SCIENCE_NOT_RUN` remains until separate R/V work.
- If sources, conditions, tick order, pre-Action freezing or cleanup fail, keep failure originals and label `PAIR_INVALID`, `SOURCE_UNATTESTED` or `DEV_FAILED` as appropriate, not transfer.

## Stage 0 code and offline verification

- `adapters/mineflayer/self_body_s50_l1_mp8_transfer.py`: uses exact pinned MP7 readback bytes; rejects mutation or World reuse; recomputes source-bound ice slope; freezes typed paired target setup and immutable hash; scores future eight-element sequences without promoting an offline result to physical evidence.
- `tests/test_self_body_s50_l1_mp8_transfer.py`: pinned in-sample fit, source tamper/symlink, pair mismatch, World reuse, forged ticket, nonfinite/short samples and comparison checks. Any synthetic fixture has **zero** real-World evidentiary weight.

### Status

`MP8_OFFLINE_SHADOW_IMPLEMENTED / MP7_ICE_TRAINING_FIT_ONLY / MATCHED_NEW_WORLD_PAIR_NOT_RUN / PHYSICAL_TRANSFER_UNDETERMINED / L0_UNCHANGED / S10_S11_L10_ZERO / GOAL_UNDETERMINED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
