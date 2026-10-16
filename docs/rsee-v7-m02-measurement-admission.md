# V7 M0.2 — R independent pre-science measurement admission

Authority: V #619, R #575, S #537. Latest source of five-arm 1-seed DEV originals: S run `38819265395` at exact S HEAD `944a68ca36f90380ffa5481ba85a6f95ed08ba18`; R byte reviewer run `38819700537`. Original R archive artifact `12012577361`. Existing qualified M0.2 one-shot run `38730925452` remains unaffected.

## Status and exact limits

R has independently verified each of five original DEV World snapshots and the per-packet WALK cost, with old Paper JAR+plugin/config hashes. This is `RSEE_V7_M02_FIVE_ARM_DEV_SOURCE_REVIEW_ONLY`, NOT engineering qualification of changed multipliers and NOT V science.

The V7 predeclared 0.005-block across-arm path-match tolerance is violated:
`BASE_ON=1.039090342887362`; the other four observed paths are approximately `1.282891353309864`, giving `0.24380101042250235` blocks spread. The true difference must remain visible; neither normalize by requested one-block step nor change the 0.005 tolerance after results. A single arm cannot be replaced/discarded retroactively.

Paper logger samples `sampled_tick=1,20,100,200` from the plugin's target-player scheduler; that establishes at least 200 player callbacks, but **not** a rigorously synchronized 200-tick observation bracket starting before movement. The baseline BASAL 0.001/tick is read from the pinned plugin config and was mathematically inferred. **The old plugin does not log BASAL per-tick charge write or cumulative actual requested debit separately.** Food/saturation/exhaustion snapshots can be affected by native thresholding and other reasons and cannot substitute for separated source charges.

New R `v7_m02_prescience_gate.py` reads the unmodified *source-review-only* R receipt and returns `RSEE_V7_M02_PRESCIENCE_MEASUREMENT_NOT_ADMITTED`. Negative tests explicitly refuse passing the original despite intact native STOP/Paper motion proof, and refuse forged science/qualification, native 200-tick and physical path reports. All generated results are READ_ONLY and carry `science_trials_credited:0`.

## Historic five-arm receipt tamper resistance (R-only)

The read-only `v7_m02_prescience_gate.py` now pins the **independently observed historical** per-arm native movement packet counts (BASE_ON 7; other arms 9) and exact source-derived paths (BASE_ON 1.039090342887362; SHAM_ON/BOTH_ZERO 1.2828913533098643; BASAL_ZERO/WALK_ZERO 1.2828913533098634). A caller cannot rewrite the per-arm paths, WALK debits, aggregate spread and paired-path flag into an internally consistent false pass. Focused negatives explicitly exercise a single changed arm, forged packet count, and all-five perfectly matched paths with forged aggregate metadata.

This numeric freeze does **not** cryptographically authenticate an arbitrary JSON input. The original R source-review workflow and its pinned GitHub producer run/archived original bytes are the independent evidence. The JSON gate returns `original_bytes_authenticated_by_this_json_gate=false`; it is a read-only historical consistency classifier, not a replacement for original-byte review or a future engineering qualification. New instrumentation or new cohorts must use a new R source verifier and fixed prospective admissions, never edit or widen the five frozen historical values. V7 remains NOT_ADMITTED, even when its source shape is intact.

## Prospective DEV improvement gate

To test genuine BASAL source billing independently, S should first modify **only new DEV instrumentation** to log source-time `BASAL` quantities at the Paper write boundary. At each applied target player tick, accumulate the exact input `delta` associated with `p.setExhaustion` while separately recording the resulting native meter state. Emit source-authenticated `tick index`, `BASAL multiplier`, and `cumulative written/debited value` at baseline, tick20, tick100, tick200, and terminal checkpoint. Explicitly label commanded/write-side billing versus observed native food-meter effect; do not claim that a saturated/clamped meter accepted the full write solely from the command. Preserve log bytes and plugin JAR hash. For `BASAL_ZERO` and `BOTH_ZERO`, expected cumulative direct source billing is exactly zero, while `BASE_ON`, `SHAM_ON`, and `WALK_ZERO` have candidate 0.001/tick.

Also define and preserve a source-tick phase boundary **before** the governed S50 MOVE, followed by the exact 200 target-player-tick experimental interval. Set all food/forage to OFF for these source-only DEV World trials. Save pre-Action `level.dat`, unique source session, initial native food/saturation, original World seed/properties and all process/STOP witnesses. Never reuse the old three spent QUALIFICATION grants; never reinterpret historical source in place.

For matched walking distances, define any active runtime control (physical steering and stop strategy) **before** starting the new five-arm batch; preserve all actual native packet paths. The current S50 `SeekCursor` nominal `max_step_m=1.0` does not promise 1.0 block physical path. No post-hoc outcome selection, path equalization on paper, or per-arm recentering toward a target after inspecting other arms. A predeclared engineering DEV feasibility target can test revised native stop/steering controls with multiple batches; the first five physical DEV attempts remain historically original. Scientific cohort uses independently specified rules and entry gates, not these DEV retries.

## Admission is strictly layered

1. S isolated DEV: new Paper plugin instrumentation, explicit original config/JAR hashes, true World tick, packet path, no-food initial World, STOP and process cleanup.
2. R offline readback: independently recompute Paper-source per-tick BASAL and packet-WALK charge against raw originals and require session/config identity. Mark source-shape vs matched-arm comparison separately, including failure.
3. R separate engineering qualification of changed config/JAR + World identity, if later explicitly authorized.
4. V prospective SCIENCE pre-registration/explicit separate authorization for 20 physical independent trials, only after S/R admissible source. The 20 V slots remain `NOT_RUN`.

Neither BASAL/WALK numerical rates nor cognitive benefits/foraging/pickup/survival fitness are ecologically qualified by this gate. V7 science=0/20, V6 science=0/48; production NO_GO. Freeze all prior original evidence.
