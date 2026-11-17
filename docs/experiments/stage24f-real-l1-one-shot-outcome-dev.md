# Stage24f DEV — single real Gemma / Paper World attempt, naturally selected MOVE or no-net Outcome

Parent [#911](https://github.com/rinsakamo/relay-self/issues/911); Stage24f [#946](https://github.com/rinsakamo/relay-self/issues/946); stacked on Stage24e [#944](https://github.com/rinsakamo/relay-self/pull/944) and Stage24d [#939](https://github.com/rinsakamo/relay-self/pull/939).

## Scope and authority

**This document is an operator-facing LocalCodex runbook.** It does not launch Minecraft, Mineflayer, Paper, or real Gemma by merely being committed. The user has permanently granted Minecraft EULA acceptance and isolated real World DEV / real Gemma permission for RelaySelf. Do not request these approvals again. This experiment still uses explicit flags so a different process cannot accidentally run it.

**One isolated World attempt only; no automated or operator retry**. If a pre-World HOLD occurs, preserve its original manifest; audit/repair in a new, separately versioned attempt, never edit a previous receipt. A prior Stage24b physical HOLD and Stage24c two-case synthetic model experiment are immutable.

Goal: show the actual independent chain **SelfBody + Schema standing EXPLORE_WORLD Need → genuine bounded SystemOne Gemma number → frozen Skill/Target/preset → original Self-owned Intent/Skill/ActionPort → original canonical WAL PREPARED → native START and STOP → stable World-tick readback → terminal physical Outcome**. The Self is not compelled to pick MOVE. If it picks ESCALATE_L2, DEFER, or Jev's reserved unresolved, the attempt is NO_ACTION/HOLD; no fallback number or fabricated physical effect.

Stage24e deliberately removed body-based preauthorization: missing/zero oxygen, hunger, low health, World time, neighboring Zombie and truncated entity coverage never remove a *cognitive* exploration Goal. Technical native source provenance, actual capability, ownership, World tick STOP evidence, immutable choice and exact selected target remain enforced.

## Before World creation: source, assets and one-owner runtime

1. Read latest repo, exact stacked HEAD, PRs #939/#944 and #946, and all source files in this runbook; inspect clean isolated worktree and expected CI 5/5 at that exact HEAD. No arbitrary merge/rebase from main during a trial.
2. In the new experiment-specific worktree install locked JavaScript deps with `npm ci --prefix adapters/mineflayer`. Then **explicitly** run:
   ```bash
   node adapters/mineflayer/oxygen_owner_patch.mjs --apply
   node adapters/mineflayer/oxygen_owner_patch.mjs --inspect-only
   npm test --prefix adapters/mineflayer
   ```
   Save before and after installed `entities.js` SHA256. The package is now **patched 4.39.0 + upstream PR #4052**, not original unmodified upstream 4.39.0. The existing Paper preflight and the real Mineflayer bridge both fail closed unless this exact owner guard is installed locally. No external `NODE_PATH` or symlink bypass. If `--apply` says it was already applied, inspect source; do not apply twice.
3. Paper 1.21.8 build 60 jar SHA256 must be `8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e`. The original P0BRecorder jar pin is `cabf144a275c1582ecbbdcb6fb394b311f0705f5ca7d330bb80659437abe324e`. The `stage24b_pinned_assets_launch_dev.py` uses these independently archived pins; do not substitute a local build without separately attesting its exact bytes on a new branch.
4. Model runtime: RTX 3060 owned CUDA PID, actual Gemma-4-12B-it Q4_K_M GGUF mapping, exact GGUF SHA256 `c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`, actual served alias, Jev-compatible API `/v1/systemone` or configured endpoint, one idle `n_parallel=1` slot, no other experiment clients on the owned backend. Never stop a non-owned GPU process. Read-only model probe first; no duplicate SystemOne choices.
5. Java 21, Node 22 with locked Mineflayer, Paper and plugin identity, a fresh root with no original WAL or World generations, and explicit dedicated/owned native session. Hash every input and executable.
6. Stage24d `RELAY_P0B_OXYGEN_WITNESS_PATH` is optional for own-source read-only oxygen events; set it **only** to a new private writable file if capturing receipts, verify files contain session/seq/generation and never claim they are raw `entity_metadata` packets. `oxygen_level=null` is UNKNOWN, not a reason to veto exploration.

### Read-only inspect, then exactly one execution

From the isolated worktree with `PYTHONPATH=src:.`, define environment variables for known exact assets/backend in the operator shell; never paste an invented path. For example, **after discovering their real paths**:

```bash
PYTHONPATH=src:. python3 -m experiments.stage24b_pinned_assets_launch_dev \
  --paper-jar "$PAPER_JAR" \
  --plugin-jar "$P0B_RECORDER_JAR" \
  --scratch-parent "$FRESH_WORLD_SCRATCH_PARENT" \
  --eula-accepted --inspect-only \
  --java "$JAVA21_BIN" --node "$NODE22_BIN"
```

Expected `STAGE24B_ASSET_CHECK_OK` and `STAGE24B_RUNTIME_CHECK_OK` **before** any World/GPU. The reused runner name is historical; the *source code HEAD* contains Stage24f outcome integration. Check it, do not infer from old Stage24b experiment labels.

If and only if all checks are satisfied, invoke once:

```bash
PYTHONPATH=src:. python3 -m experiments.stage24b_pinned_assets_launch_dev \
  --paper-jar "$PAPER_JAR" \
  --plugin-jar "$P0B_RECORDER_JAR" \
  --scratch-parent "$FRESH_WORLD_SCRATCH_PARENT" \
  --eula-accepted --execute-once \
  --real-world-dev-grant --grant-real-llm \
  --llama-endpoint "$LLAMA_ENDPOINT" \
  --systemone-endpoint "$SYSTEMONE_ENDPOINT" \
  --model "$ACTUAL_SERVED_GEMMA_MODEL" \
  --java "$JAVA21_BIN" --node "$NODE22_BIN" \
  --timeout-s 120
```

The actual original resident runner logs in Self A+B, logs out A, and **Self B** generates CPU Schema candidates from native WorldBody; Gemma returns **one real number**. It only enters original B physical issue if Gemma selected a real prebound MOVE. It attempts A re-JOIN and World-only save/restart under the original runner when the attempt reaches that phase. Never feed an operator MOVE target/number, prefill oxygen=300, or force the model response.

The `stage24b_pinned_assets_launch_dev` legacy flag names do not mean the old original Stage24b candidate policy is still used; source is Stage24f stacked HEAD. A new numerical/semantic experiment begins at this HEAD.

## Independent outcome classification

No claim below is allowed without original evidence and SHA256 readback:

- **`L1_UNRESOLVED` or `NO_ACTION`**: real model returned reserved Jev unresolved / ESCALATE_L2 / DEFER / error, and there is no original physical Action. Keep no-move HOLD or actual selected non-physical response, no forced MOVE.
- **`NATIVE_MOVE_SETTLED` and Paper `MOVEMENT_CORRELATED`**: genuine Self L1 selection, frozen Skill+Target, original ActionPort, ACKed native START/STOP, 8+8 tick stable readback, canonical fsynced terminal WAL, independent Paper movement/presence timeline. Existing report `REAL_PAPER_B_L1_SELECTED_MOVE_CORRELATED_WORLD_ONLY_DEV` is permissible when World-only generation completes. **It is correlation, not action-ID Paper causation or Goal success.**
- **`NATIVE_MOVE_NO_NET_DISPLACEMENT` and Paper `PRESENCE_CORRELATED`**: same valid model selection and executed motor attempt, original native ACK/STOP/settle and WAL, net displacement [0,0.1)m. May report `REAL_PAPER_B_L1_SELECTED_NO_NET_DISPLACEMENT_WORLD_ONLY_DEV` only if all original source checks and requested World-only generation pass. `native_move_no_net_displacement=true` and **`paper_movement_correlation_attested=false`**. This proves terminal *net displacement outcome*, **not** that movement did not happen during pulse, *not* that fatigue/wall caused it and *not* MOVE skill success.
- Native / Paper conflict, bad source session or HASH, stale or missing STOP ACK, unstable stop, unresolved journal, stale original preissue binding => `HOLD / PREPARED_UNRESOLVED`. Don't silently promote no-net to rescue the trial. If peer A or World-only checkpoint not observed, report exactly the partial evidence, not global PASS.

Use the existing source audit `resident_move_raw_audit_dev.readback_owned_move_native_source` to prove native stdout original, W100/world generation checks, and Paper owned log independently. This evidence does not contain complete raw SystemOne HTTP response bytes; mark `model_raw_http_bytes_archived=false` unless a separately verified raw capture was actually performed.

## Save before interpreting

Capture immutable original:
- exact source HEAD, CI run and branch, Paper jar/plugin/GGUF/llama binary/Node patch before+after sha and GPU PID;
- inference raw request choice set, native WorldBody oxygen/food/health (including null), actual Gemma status and number, preset and candidate digest;
- native process session/probe IDs, selected Intent/Skill/ActionPort binding and original PREPARED WAL;
- Native START and STOP effect ACKs, all tick-scoped settling probes, WAL final state/digest, native final net displacement and Paper position+UUID timeline;
- A QUIT, A re-JOIN and World-only generation verification when reached;
- receipt files, readback equality, SHA256SUMS and its own manifest digest;
- `classification`, `QUAL_NO_GO`, `SCIENCE_NOT_RUN`, no extra retries.

Submit one clearly labeled DEV report to Stage24f issue #946, stacked Draft PR and parent Issue #911. Read back exact posted reports. Preserve all previous Stage24b/24c/24d/24e evidence unchanged. In this ChatGPT/GitHub-only environment, **no real Paper/Gemma test has been performed**.
