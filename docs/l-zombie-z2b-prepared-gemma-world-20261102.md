# RelaySelf L-Z2b — Real Gemma prepared policy / real Paper trajectory DEV

Date 2026-11-02. Stacked on Draft #698. This stage is **offline implementation until the user's genuine local GPU and a separately authorized new World have run**. Do not upgrade a historical Z1b/Z2a trial into a real Gemma forecast.

## Why this architecture

A Paper +20 tick horizon is typically about 1 second. Never pause Minecraft or hold the original executor while a 12B LLM is generating. Earlier epoch L2 chooses a bounded, falsifiable *conditional prediction rule*, using ONLY two already completed real worlds; the next world's exact positions and zombie UUID are not available to the model until Paper tick10. At tick10, Paper synchronously evaluates the selected strategy, freezes the outcome before tick11, then compares to the exact tick30 physical observation. No online LLM call.

Choice: STATIONARY / CONSTANT_VELOCITY / TARGET_APPROACH(speed_m_per_tick in (0,0.30]) / ABSTAIN. The target is the zombie's next x,z in meters at exactly +20 server ticks, NOT WAIT duration. TARGET_APPROACH moves a predicted point towards the *current* player's x,z by no more than 20×speed, clamped to current separation. These are prepared model policy candidates, NOT learned L1, independently improved B2, autonomous C, or L0 promotion.

## Existing real old-world original Paper logs (immutable)

- [Z1b actual source, run #41409851129 artifact #13124703525](https://github.com/rinsakamo/relay-self/actions/runs/41409851129/artifacts/13124703525). Raw paper-console-original.raw SHA256 31dd510390c75492c023889f7f0d876c702bebea422314fe8151474762b7e49e.
- [Z2a actual source, run #41414648412 artifact #13127615709](https://github.com/rinsakamo/relay-self/actions/runs/41414648412/artifacts/13127615709). Raw paper-console-original.raw SHA256 3e70f39251d30cd16952e8a2fdf8a5141bbe0ea777c6160ba7a0b5609fb6c32d.

Download both original ZIPs in the local WSL independently, extract into separate protected directories and compare exact raw SHA. Do NOT use documents/recreated summaries in their place. The built-in source_summaries function independently replays Z1b Paper 31 ticks and Z2a original CHEAP freeze and only then constructs past-only Gemma context. Model output must cite the two original IDs, reason and falsification plan; old-world context has no new World future.

## First: one real local Gemma request, no Minecraft World

Use exact clean new L worktree HEAD and user's authorized L-lane DEV grant. Verify genuine live llama.cpp build10874, actual process/GGUF memory mappings, served alias, context8192, slot1, model GGUF SHA256 c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed. Do not start a duplicate server or substitute mocked HTTP. API must be loopback /v1/chat/completions. Native strict JSON schema (7 keys), strict true, reasoning_effort none, enable_thinking false, temperature0, seed1, stream false, cache_prompt false, max_tokens384. Reject finish_reason length, malformed/incomplete/duplicate output or reasoning leakage; preserve raw and stop, never retry failed request. The preparation tool does NOT attest real GGUF process mapping by itself; original process proof must be recorded separately.

~~~bash
export PYTHONPATH=src:tests:.
export L_ZOMBIE_Z2B_REAL_GEMMA_DEV=1
python -m tools.l_zombie_z2b_prepare_gemma \
  --endpoint "$ENDPOINT" --model "$MODEL_ALIAS" \
  --z1b-paper-original "$Z1B_RAW" \
  --z2a-paper-original "$Z2A_RAW" \
  --evidence-root "$PREP_ROOT"
~~~

PREP_ROOT must be new, its parent existing, no symlinks. This uses exactly one real HTTP call. It writes original llama-request-1.raw.json, llama-response-1.raw.json, prepared-zombie-l2-policy-v1.json, request-status.json. Any transport/schema failure is an immutable failed attempt, not a license to change the same model request and call it success.

## Second: one NEW physical Paper World (after successful model preparation)

Pin actual Paper1.21.8 build60 JAR SHA256 8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e and 52,811,717 bytes. Build the current standalone zombie Java21 plugin and pin its SHA. Node22, Mineflayer4.39.0, clean exact HEAD, free localhost 25565, separate new absolute World/evidence roots, 16-hex run ID. No retry. The preworld gate independently re-verifies old Paper raws and full actual model request/response from PREP_ROOT; it fails before Java if any source/policy SHA is mismatched. It configures only this isolated World, with prepared rule SHA and CHEAP baselines; no extra Self Action issuer, learning update, L0 adjustment or online Gemma call.

~~~bash
export PYTHONPATH=src:tests:.
export L_ZOMBIE_Z1_ONE_WORLD_DEV=1
export L_ZOMBIE_Z1_PURSUIT_DEV=1
export L_ZOMBIE_Z2A_CHEAP_DEV=1
export L_ZOMBIE_Z2B_PREPARED_DEV=1
python -m tools.l_zombie_z1_one_world_dev \
  --confirm Z2B_ONE_PREPARED_L2_SHADOW_WORLD_DEV_NO_RETRY \
  --pursuit-dev --prospective-cheap-dev \
  --prepared-l2-root "$PREP_ROOT" \
  --z1b-prior-original "$Z1B_RAW" \
  --z2a-prior-original "$Z2A_RAW" \
  --repo "$REPO" --expected-head "$EXACT_HEAD" \
  --paper-jar "$PAPER_JAR" --plugin-jar "$PLUGIN_JAR" \
  --plugin-sha256 "$PLUGIN_SHA" \
  --world-parent "$WORLD_PARENT" \
  --evidence-parent "$EVIDENCE_PARENT" \
  --run-id "$RUN_ID"
~~~

Original S49 executor is not replaced. This is an operator-staged protected survival target + one native zombie source rig, NOT proof of autonomous L0 physical danger response or causal chase. Freeze candidate at Paper offset10 strictly before offset11; if absent/invalid/late/changed entity -> FAIL/DEFER with raw intact, not interpolation or re-execution. Cleanup Java/Node PID and localhost port; delete disposable World, retain original evidence including failure.

## Third: independent original post-World audit

After the owned server terminates and complete raw Paper stdout is preserved with SHA:

~~~bash
python -m tools.l_zombie_z2b_paper_policy_audit \
  --paper-original "$NEW_PAPER_RAW" --sha256 "$NEW_PAPER_SHA" \
  --marker z1-source-1 --session z1-client-1 \
  --prepared-root "$PREP_ROOT" \
  --z1b-paper-original "$Z1B_RAW" \
  --z2a-paper-original "$Z2A_RAW" \
  --report "$NEW_AUDIT_REPORT"
~~~

Auditor requires ARM + 31 consecutive Paper tick rows + END, a frozen CHEAP entry AND one prepared-L2 policy entry after tick10 but before tick11, same zombie and future tick+20, same original model packet SHA and policy arithmetic, null error on abstention. Compare the actual *prospective* prepared rule error against both CHEAP errors using the SAME World, regardless of whether better or worse. Keep exact Paper↔native packet join, real GGUF process mapping and survival safety as separate qualifications.

## Claims

Offline CI / mocked HTTP ≠ actual Gemma. Actual Gemma strict transport and frozen policy ≠ real World application. Real +20 Paper prospective model-prepared policy error ≠ within-World Gemma reasoning, L1 autonomous learning or independent B2 improvement. B1-N/U/Q, B2, C and SCIENCE require their own conditions/holdouts. Until tested: Z2B_OFFLINE_READY / REAL_Z2B_GEMMA_0 / REAL_Z2B_WORLD_0 / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
