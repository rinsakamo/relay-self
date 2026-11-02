# RelaySelf L — B1 prediction/abstention and self-evaluation V2 (2026-11-02)

Child of Draft PR #686. Prior real World execution HEAD 167c9128d7a7b057a46b4fb25b4faa42f8bb5d98 and final evidence HEAD 9cfb0418efbb1f10025a2c961328ce1366334dae are UNCHANGED.

## Historical evidence and limits

Previous actual Paper World: original S49 Action3/S15 clear3/S16 OUTCOME3, 3 WAIT8 windows, real Gemma OPEN2 and all three independent source audits PASS. A=PASS_DEV, B1=NOT_ESTABLISHED, B2=NOT_ESTABLISHED, C=NOT_RUN_BY_DESIGN. H1 forecast null; Action2 WAIT8 measured 0.06424660150896089 m, so H1 prediction error DOES NOT EXIST. H2 KEEP_PRIOR cited T1_W8/T2_W8 but used mistaken "predicted and actual wait times" explanation, confusing duration with displacement. Never fabricate a missing H1 forecast, fix old model output, rewrite SHA or promote old B1.

## Explicit new V2 contract, default OFF

V1 strict ten-field JSON stays the default with original V1 hypothesis SHA and unmodified historical re-read. B1 V2 uses strict native JSON Schema with FOUR more required fields, fourteen total:
- measurement_target: always NEXT_TRIAL_WAIT8_TOTAL_DISPLACEMENT_M. WAIT8 is TOTAL displacement over 8 World ticks in METERS, never wait duration or single next tick.
- forecast_status: NUMERIC_ESTIMATE iff predicted_wait_total_m is a finite 0..3 m point forecast. An actual null must use ABSTAIN_INSUFFICIENT_EVIDENCE, ABSTAIN_OUTSIDE_APPLICABILITY, or ABSTAIN_MODEL_UNRESOLVED. Abstention is meaningful, not silently zero, not cheap forecast substituted.
- prior_evaluation_basis: FIRST_UNTESTED for H1; for H2 SCORED_ERROR requires an actual numeric H1 forecast and both source IDs T2_H1ERR and T2_W8; QUALITATIVE_ONLY requires T1_W8 and T2_W8 observations, does not establish a scored forecast; NO_SCORABLE_FORECAST requires unscored H1 and ABSTAIN_ON_PRIOR.
- prior_evaluation_reason: 16-120 characters of explicit evidence/limitation explanation. An unscored KEEP_PRIOR can be qualitatively hypothesized using both actual WAIT8 IDs, but is never labeled numeric error scoring. The source owner rejects incompatible enum/basis/forecast and a narrow set of unambiguous duration-vs-displacement or unscored "prediction error" contradictions. The lexical checks are not general semantic understanding.

L2 always remains an unadmitted read-only hypothesis with no Action authority. Model can choose and cite a correct observation yet produce mistaken physics; independent semantic B1 judgment still required.

## Source integrations prepared, physical test NOT RUN

- Original L2 OPEN request/parser: optional explicit V2; new frozen proposal subtype with new fields in SHA, no alteration of legacy V1 structure or request. Historical H1/H2 never become V2 by readback.
- Actual local llama.cpp Gemma wire: opt-in native fourteen-field strict JSON Schema, same reasoning_effort none, enable_thinking false, 512 output cap, no retries and no reasoning channel.
- Preflight: opt-in --b1-contract-v2 with L_MP11_B1_CONTRACT_V2_DEV=1. New actual Gemma synthetic probe must succeed and its raw SHA/mode must match World. A prior V1 preflight cannot unlock V2.
- Original S49 World runner: opt-in --l-mp11-b1-contract-v2-dev requires same env gate; old S49 executor and World authority unchanged.
- W3 trial prepare/run: opt-in --b1-contract-v2 on prepare, and the original S49 run CLI must match; no stale preflight or re-use of a spent World.
- Independent H1/H2 original feedback readback re-runs declared V1/V2 parser against immutable Paper prefix and exact previous hypothesis SHA; it does not automatically establish semantic B1.

Tests include original immutable #686 frozen H1/H2 from docs/evidence/l-cognitive-loop-20261102/world, point-vs-abstain, source numerics, qualitative-only, mismatch and future-data denial, synthetic strict Schema/Thinking-off preflight, no V1/V2 mode crossing, and old G2/G3/S49/EOF regressions.

## Next physically authorized milestone

This PR itself does NOT call actual local Gemma or Minecraft. On a separately authorized new one-World DEV trial, confirm exact clean execution HEAD, actual Gemma4-12B Q4_K_M GGUF SHA and process mmap, llama.cpp build10874, context8192, slot1; run ONE fresh V2 synthetic HTTP preflight before any Paper; then prepare fresh pre-Java W3 root, run original bounded 3-Action/2-OPEN World with new V2 flags, independently audit original G3, live-prefix and H1/H2 feedback. Any failure remains FAIL and no automatic retry is allowed. Actual model completion under 512 tokens with 14 keys is unproven. Do not presume B1 numerical error scoring from a valid ID or successful A.

Classification: B1_V2_OFFLINE_ONLY / HISTORICAL_A_PASS_DEV_B1_NOT_ESTABLISHED_UNCHANGED / REAL_GEMMA_0_NEW / REAL_WORLD_0_NEW / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
