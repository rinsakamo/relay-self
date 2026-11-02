# RelaySelf L — independent next physical World: W3 capture and PID origin (2026-11-02)

Child of Draft PR #684. The prior 2026-11-02 real local Gemma synthetic strict-Schema/Reasoning-OFF probe PASSED, but the prior single actual World FAILED before S49 Action, because a W3 native capture directory was not prepared before Java startup. That original World attempt, its mandatory audit failures and original hashes are immutable. This child makes NO claims of newly executed real Gemma or Paper World.

## Goals and hard bounds

The new independent trial must be fixed at a NEW exact clean HEAD and NEW separate evidence root. One new real synthetic Gemma transport preflight (no retry), then only if it passes: one disposable Paper World, zero retries, one Mineflayer session, at most three original S49 Actions, two live real Gemma OPENs, zero L2-owned Actions, zero learning admissions, zero L0 promotions.

Do not treat source-only CI as a physical run; do not use a past preflight report after changing the execution HEAD. Confirm real Gemma4 GGUF file SHA, actual mmap PID/argv, existing llama.cpp build, active context 8192/slot1, Structured JSON Schema ON and reasoning OFF independently on local WSL.

## New operator gate

New file: tools/l_mp11_next_trial_gate.py

The prepare subcommand requires an absolute existing NEW evidence root, exact clean local Git worktree HEAD, a NEW real Gemma preflight report inside that root, matching localhost endpoint/served alias, immutable request/response and SHA readback. It creates the missing W3 namespace world/native-stdout as an existing EMPTY absolute directory with no symlink ancestors and saves l-next-world-capture-ready.json EXCLUSIVELY. It does not launch Java, issue Action, or consume a World.

The run subcommand revalidates the stored prep, preflight SHA, exact execution HEAD, empty capture root, original bounded L2 flags, and original S49 argv. It exclusively writes l-next-world-attempt-started.json BEFORE spawning the actual original S49 runner. This consumes exactly one World budget; automatic re-execution from the same evidence root fails. It does not use shell=True. It samples Linux /proc descendants of the actual spawned runner using PID, ppid, kernel start_ticks, real exe, cwd and argv, not a guessed minecraft.jar filename. It writes l-next-world-owned-processes.jsonl, l-next-world-runner-original.log and l-next-world-runner-exit.json. Java/Node ownership remains UNATTESTED if the actual PID is not observed.

## LocalCodex execution sequence

From an isolated new L child worktree at the current exact HEAD, verify branch/remote/clean, installed Java21/Node22/Python3.12 and original Paper1.21.8 assets, and real Gemma GGUF process identity. Do not reload a healthy model, download weights, change other lanes, or modify previous original evidence.

1. Create NEW absolutely addressed ROOT (existing EMPTY top-level directory for this trial). Set REPO to the absolute new L worktree; set EXACT_HEAD to git rev-parse HEAD from that worktree; set ENDPOINT to the actual localhost llama.cpp /v1/chat/completions; set MODEL_ALIAS to the served alias. Build the genuine Paper plugin/source from the already approved dependencies and validate all original assets. Probe after finalizing the source HEAD.

2. With PYTHONPATH=src:tests:. and L_MP11_GEMMA_PREFLIGHT_DEV=1, run exactly one actual local synthetic Gemma transport probe:

    python -m tools.l_mp11_gemma_structured_preflight \
      --endpoint "$ENDPOINT" --model "$MODEL_ALIAS" \
      --evidence-root "$ROOT/gemma-strict-wire-probe"

Require actual HTTP stop, full exact native strict JSON schema, reasoning_effort none, enable_thinking false, no observed thinking channel, source ID validation, original HTTP request/response bytes and SHA readback. On FAIL stop BEFORE World and keep failure raw.

3. Before any Java process, prepare and seal the fresh original W3 capture directory:

    python -m tools.l_mp11_next_trial_gate prepare \
      --evidence-root "$ROOT" --repo "$REPO" \
      --expected-head "$EXACT_HEAD" \
      --preflight-report "$ROOT/gemma-strict-wire-probe/gemma-structured-preflight.json" \
      --endpoint "$ENDPOINT" --model "$MODEL_ALIAS"

Require $ROOT/world/native-stdout to be an existing EMPTY absolute non-symlink capture directory. The ready report is NOT a physical PASS.

4. Check active authorization for this NEW independent one-World DEV trial, rather than reusing the already consumed old trial. Set these original opt-in env variables to 1:
    S49_REAL_SERVER_CI
    MP11_S49_THREE_ACTION_DEV
    MP11_G3_PAPER_THREE_WINDOWS_DEV
    L_MP11_LIVE_PREFIX_DEV
    L_MP11_LIVE_L2_DEV
    L_MP11_EVIDENCE_IDS_DEV
    L_MP11_GEMMA_STRICT_SCHEMA_DEV
    L_MP11_PAPER_EOF_DEV

5. Run exactly once via the new owned-process monitor. Set PYTHON to the absolute local relay-lm venv Python, and PAPER_JAR/PLUGIN_JAR/PAPER_CONFIG to the actual independently validated exact assets:

    python -m tools.l_mp11_next_trial_gate run \
      --evidence-root "$ROOT" --repo "$REPO" --expected-head "$EXACT_HEAD" -- \
      "$PYTHON" -B -m adapters.mineflayer.s49_normal_session_real_ci \
      --mp11-three-actions-dev --l-mp11-live-prefix-dev \
      --l-mp11-evidence-ids-dev --l-mp11-paper-eof-dev \
      --l-mp11-gemma-preflight-report "$ROOT/gemma-strict-wire-probe/gemma-structured-preflight.json" \
      --l-mp11-live-l2-endpoint "$ENDPOINT" --l-mp11-live-l2-model "$MODEL_ALIAS" \
      --mp11-g3-paper-jar "$PAPER_JAR" --mp11-g3-plugin-jar "$PLUGIN_JAR" \
      --mp11-g3-config "$PAPER_CONFIG" \
      --raw-capture-root "$ROOT/world/native-stdout" \
      --report "$ROOT/world/report.json" \
      --server-log "$ROOT/world/paper-stdout-original.log"

The separator -- passes the exact original S49 command. No retry, even if a preparation/World failure occurs after the World budget marker is written. Preserve raw success and failure originals. If additional Node runtime installation is required, prepare it before World and use existing pinned packages, not downloads.

6. Independently run the existing mandatory original G3 (for complete 2 live L2 calls), original live-prefix, and independent H1/H2 feedback source audits. Compare source prefix SHA and past-only model requests; verify H1 forecast vs the following completed Action2 WAIT8 total; confirm H2's semantic use of previous H1, error and source evidence IDs, no Action3 outcome leakage. Verify world native ACKs, actual Java/Node PID/cwd/start_ticks, exact cleanup and ports.

## Epistemic ceiling

A=valid original live real Gemma H1/H2, B1=semantic assessment of prior H1 against actual following trial, B2=effective structural model revision under independent holdout, C=autonomous physical experimentation. This single all-grass World is aimed only at A/B1. A successful synthetic preflight and accurate PID lineage are NOT proof of A/B1 and cannot replace the mandatory Paper audits. If any of the original audits fails, retain complete World FAIL.

Current state: OFFLINE_PREPARED / NEW_REAL_GEMMA_NOT_RUN / NEW_WORLD_NOT_RUN / HISTORICAL_FAIL_UNCHANGED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
