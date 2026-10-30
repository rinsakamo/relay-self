# RelaySelf L9 — L Lane × SelfWorld/SelfBody × returned S epoch (2026-10-30)

## Purpose

**Independent cross-lane DEV only.** The existing L8 `observe_s_epoch_l1` consumes an already-returned S `DecisionEpochResult` and contrasts S's fixed S42 World choice with an L6/L7 next-epoch L1 experience *shadow*. The SelfWorld/SelfBody v0 cognitive views live on a separate independent branch. L9 joins the **same original typed S Mineflayer Present** to those two views before observing the one existing S epoch, without mutating any of the three owners. This is a source/identity interface, not proof that L1 learned from body features or that a physical Minecraft Action changed.

Base: L8 branch `learning/l8-epoch-result-observer-20261030`, exact parent `4defb6e8b78f2e050921b521eb2253a14bc260c4`. Isolated branch: `integration/l9-world-body-s-epoch-shadow-20261030`.

Two **unmodified** SelfWorld/SelfBody typed v0 code snapshots from `self/selfbody-world-live-cognition-dev-20261024` were copied to the integration branch, not merged into main or overwritten in the parallel source branch:
- `src/relay_self/self_world.py` original Git blob SHA `38fc8dc2be182b77abf6f2c382147386388da0a5`; integration readback blob SHA **identical**.
- `src/relay_self/self_body.py` original Git blob SHA `3f861f84913928a691ac04469384591b79963859`; integration readback blob SHA **identical**.

Both source branches remain untouched. This branch is a staged intersection, not a replacement for a reviewed future merge/owner adoption.

## Implemented

`src/relay_self/l9_world_body_epoch_shadow.py`: `observe_s_world_body_epoch_l1(s_epoch, *, native, world, body, retained, learning, retention_enabled)` returns immutable `WorldBodyEpochShadow`.

The input is the already-typed `NativeThreat` from S34/S42, actual `SelfWorldView` and `SelfBodyView` v0, existing `LearningEpochResult` from L6, existing `LearningPreferenceState`, and **the same completed S coordinator result**. S owns the native Present and the original S decision; L6 owns qualified historical Memory admission and retention state. L9 creates no new native read, Action, L2/model request, Memory write, policy or Habit permission.

Fail closed before calling L8 if:
- Self/observer identity, session, epoch, native seq, request ID, typed source provenance or accepted current-probe SHA do not agree; SelfWorld must contain the *exact same SelfBodyView instance*.
- The external positive entity list differs from the original native bounded registry in IDs, names, coordinates, distances, visibility action or source coverage metadata; a positively observed target must be the same zombie ID and measured distance. **Unlisted is UNKNOWN, not safe/absent**.
- The internal six observed native body fields (x/y/z, health, food, saturation) disagree with the original probe, or an S16 Action readback is retroactively presented as the current predecision source. Minecraft `food` is **not** M0 energy; no P1 fatigue, WAIT or physical movement is inferred.
- A remembered SelfWorld item is not in the L6 owner-local immutable Memory snapshot, or SelfWorld/SelfBody metadata is foreign/aliased. Beliefs, hypotheses, forecasts and private memories are never promoted to current physical observations.
- The S coordinator did not return a completed, quiescent `WorldConditionedChoice`, original S42 choice cannot be reproduced, current source is unadmitted, or L8's retention-mode and shadow assumptions fail.

Only on valid input does L9 invoke the **existing** `observe_s_epoch_l1` comparator. The S original choice is always kept; L1 advice remains a candidate/shadow and no Action issuer is called. The result carries S/L8 contrast, exact source refs and positively observed distance/food/health, with fixed zeros for action issues, source reads, Memory writes, learning commits and Habit grants.

**No model-based L1 memory improvement is demonstrated.** The current L6/L7 context cue tags and externally goal-labeled training remain S/R/V-admitted independently; L9 checks that all referenced views are sourced to the *same* current probe but **does not generate or certify arbitrary learning cue tags from SelfWorld/SelfBody**. Future L10 should only introduce such a feature encoder with an explicit upstream source/Goal admission contract and same-information cheap comparison.

## Verification

**Exact tested source/workflow HEAD**: `d56498c80609f00c5e40d5f33a45e422aa64eb69`.
[GitHub Actions focused run #41037698006 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/41037698006) — Python 3.12, **162 focused pytest PASS**, Ruff PASS, compileall PASS, repository contracts PASS. Tests include the genuine existing S coordinator invocation from L8 (offline typed S fixture), L6/7 contextual historical retention contrast, SelfWorld/Body views built from that same typed native source and dozens of negative controls (cross-self/session/epoch/seq/request, altered entity geometry/coverage, wrong food/health/position, invented World contents, foreign Memory, current-session source/retention mismatch, no S cognition).

Original CI failures are preserved: [#41037138358](https://github.com/rinsakamo/relay-self/actions/runs/41037138358) and [#41037560406](https://github.com/rinsakamo/relay-self/actions/runs/41037560406) failed Ruff import order; [#41037229790](https://github.com/rinsakamo/relay-self/actions/runs/41037229790) failed three test fixture expectations because original SelfWorld/SelfBody constructors correctly rejected malformed typed inputs **before** the L9 boundary. The final test accepts fail-closed rejection by either the original constructor or L9. No falsified passes or altered source semantics.

No real Minecraft run, Java/Paper physical Action, GPU/LLM call, S49 behavior change, T2/P1/M0 owner change, separate S cognition call, S10 committed learning or S11 automatic Habit adoption. No FULL, QUAL, SCIENCE, main/protected Draft PR merge or force push.

## Next staged steps

1. S owner supplies **one** independently source-admitted Present and its matching already-existing S epoch, plus typed SelfWorld/SelfBody composed by their existing views. Do not install a second native reader.
2. Introduce S-owned, explicitly preregistered **bounded cue projection** from positively observed SelfWorld and SelfBody into L6 feature tags; use genuine prior OUTCOME + separate Goal receipts in *different* prior sessions, admit them independently, and compare the same-data cheap baselines. No actual S49 Action changes until owner authorizes.
3. Only then pursue disposable real World DEV S49 observer integration, followed by separately granted QUAL/SCIENCE. Keep G4.x source read-only diagnostics historical; do not extend motor duration merely to obtain stable G1 evidence.

**Classification:** `DEV_ONLY / L9_S_WORLD_BODY_TYPED_READONLY_INTEGRATED / PY312_162_FOCUSED_PASS / ORIGINAL_S_CHOICE_UNCHANGED / NO_NATIVE_WORLD_RUN / NO_NEW_ACTION / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
