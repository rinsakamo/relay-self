# I Lane I2f — explicit new v3 original A/B real-World one-shot runner and independent auditor (DEV)

Scope: Issue #1078 / Draft PR #1080. No automatic merge. No other B, D, C or I integration branches are modified. **The historical Stage28b source constants and default runner/auditor path must not change.**

## New source prerequisite: no old Stage28b backfill

I2f accepts a **new** typed, committed A/B generation whose original Owner persisted its initial PatternRegistry and explicitly recorded empty per-Self SchemaSnapshot in the new I2c v3 owner cut. The new source must be accompanied by independently archived original Native/Paper evidence from its own source run, not copied from the historical Stage28b experiment. Previous real World Stage28b did not capture these Schema/Pattern facts and **cannot** pass this gate; historic I1 independent source remains untouched.

The caller provides a six-field JSON file of independently fixed source pins:

    {
      "source_world_id": "original-world-uuid-from-original-paper",
      "source_branch_id": "original-source-branch",
      "source_committed_sha256": "64-lowercase-hex-commit",
      "fork_branch_id": "new-fork-branch",
      "original_manifest_sha256": "64-lowercase-hex-evidence-manifest",
      "original_manifest_files": 0
    }

The above is a **shape example, not valid pins** (the file count must be an independently measured positive integer). These are not auto-derived or guessed from local files, and a random UUID does not provide authorization. Use the exact original evidence count and SHA pinned before this new isolated run; do not use the previous source SHA as a fallback. A full original saved report with original A/B initial and rejoined Native sessions and exact owner-state typed generation linkage is required.

## Run gating

- `src/relay_self/i_lane_i2f_future_source_pins_dev.py`: validates source pins and reuses I2e future A+B exact v3 OFFLINE Schema/Registry readback plus the already existing full historical Native/Paper manifest checker against the newly pinned original evidence. Returns only transient OFFLINE Owner handles. Re-checks source after a trial.
- `experiments/stage28c2b_real_recovered_rejoin_dev.py`: **additive** optional `future_pins` only; when absent its historical old cut, old hardcoded original source and old I1/Stage28c2c test behavior are retained. When present, it preflights the distinct future source before any new World, creates one isolated source-verified physical World copy, restores exactly **recorded** original A+B Schema in the new copy, uses the existing exact same OriginalOwner/physical issuer/Native/Paper World lifecycle and read-only I1 physical source. It allows an original callback after normal I1 source sampling only for a typed new source. Its output is always *CAPTURED_INDEPENDENT_AUDIT_PENDING*.
- `experiments/i_lane_i2f_future_one_world_dev.py`: explicit LOCAL CLI; before any World and again before model POST, verifies pinned GGUF/llama-server process ownership of model socket/GPU (RTX 3060)/single idle slot. Attaches one existing shared inference lane **after** original A+B Native/Paper real JOIN and matched WorldBody. Invokes original A's I2d proposal/vote through the real I2e OPEN L2 and BOUNDED L1 raw entity provider, **max two attempts, no retry**. Saves original CPU/Raw Native + Paper, model body bytes and Owner before/after cognition. Physical issue remains observation-only/zero. Model may choose ACCEPT, DEFER or UNRESOLVED; a failed L2/World/GPU source is HOLD, not a synthetic acceptance. Saves reason, partial original files and terminal cleanup evidence.
- `experiments/stage28c2b_independent_rejoin_audit_dev.py`: **additive** future `future_pins` path, still old default read-only historical audit when omitted. Verifies exactly the new pinned World/fork/Native/Paper/ACK/exit/retirement and the A durable cognition delta (B remains identical). It independently invokes the existing I2e dual HTTP model-bundle auditor. It never labels an independently unaudited World PASS.
- `experiments/i_lane_i2f_independent_world_audit_dev.py`: **second-process** read-only CLI. In addition to above, verifies original A model-cited Native request/response in actual raw stdout and exact outbound observe-only stdin, original line-complete Paper log prefix SHA and its main-thread nonce ACK/owned Popen stdout, model identity against pre-World PID/GPU/GGUF gate and a post-POST idle single slot. Only its complete positive result yields scoped DEV **I2F_NEW_V3_ORIGINAL_WORLD_L2_L1_SOURCE_AUDITED_DEV**. Does not attest packet-level HTTP headers, general Schema migration, Q/SCIENCE or authorization to issue a physical MOVE.

## Explicit local commands (only after new origin evidence exists)

Read-only inspection (does not create Paper/World or POST):

    PYTHONPATH=src:. python3 -m experiments.i_lane_i2f_future_one_world_dev \
      --inspect-only --eula-accepted \
      --generation /PATH/NEW_V3_GENERATION \
      --restored /PATH/NEW_V3_RESTORED \
      --original-evidence /PATH/NEW_ORIGINAL_EVIDENCE \
      --new-source-pins /PATH/EXTERNALLY_PINNED_SOURCE.json \
      --paper-jar /PATH/PINNED_PAPER.jar --plugin-jar /PATH/PINNED_PLUGIN.jar \
      --gguf-path /PATH/PINNED_GEMMA.gguf --llama-pid OWNED_PID \
      --model-alias EXACT_MODEL_ALIAS \
      --llama-endpoint http://127.0.0.1:PORT/v1/chat/completions

One World trial, never automatic retry, with **two separate explicit** World and model grants:

    PYTHONPATH=src:. python3 -m experiments.i_lane_i2f_future_one_world_dev \
      --execute-once --eula-accepted --real-world-dev-grant --model-post-grant \
      --generation /PATH/NEW_V3_GENERATION --restored /PATH/NEW_V3_RESTORED \
      --original-evidence /PATH/NEW_ORIGINAL_EVIDENCE \
      --new-source-pins /PATH/EXTERNALLY_PINNED_SOURCE.json \
      --paper-jar /PATH/PINNED_PAPER.jar --plugin-jar /PATH/PINNED_PLUGIN.jar \
      --gguf-path /PATH/PINNED_GEMMA.gguf --llama-pid OWNED_PID \
      --model-alias EXACT_MODEL_ALIAS \
      --llama-endpoint http://127.0.0.1:PORT/v1/chat/completions \
      --execution-dir /FRESH/DIR --evidence-dir /DIFFERENT/FRESH/DIR

Run the completely separate **read-only** auditor after the above successfully stops (never run the auditor inside the World process):

    PYTHONPATH=src:. python3 -m experiments.i_lane_i2f_independent_world_audit_dev \
      --result /FRESH/EVIDENCE/stage28c2b-recovered-world-result.json \
      --generation /PATH/NEW_V3_GENERATION --restored /PATH/NEW_V3_RESTORED \
      --original-evidence /PATH/NEW_ORIGINAL_EVIDENCE \
      --new-source-pins /PATH/EXTERNALLY_PINNED_SOURCE.json \
      --execution-dir /FRESH/DIR

These commands are documentation, **not a claim that this runner or model was actually executed locally**. GitHub Actions uses CPU-only synthetic fixtures, not a user's WSL2 or live Minecraft session.

## Classification and remaining gates

Until new independently pinned v3 *real original* source exists: **I2F_PRE_WORLD_HOLD / REAL_WORLD_NOT_RUN / REAL_GEMMA_NOT_RUN / QUAL_NO_GO / SCIENCE_NOT_RUN**.

If only local CPU tests and exact-HEAD CI pass: **I2F_NEW_V3_PINNED_WORLD_RUNNER_INDEPENDENT_AUDITOR_CPU_OFFLINE_DEV_PASS**, not World PASS.

A positive real-world classification requires one *actual* isolated World plus new native/Paper/GGUF/model entity bytes and independent second-process auditor PASS. Even then only a narrow new A/B source-bounded cognitive adoption DEV result; D Question/Goal/Intent, motor skill execution, B general migration and SCIENCE remain separately held.
