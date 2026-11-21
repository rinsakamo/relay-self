# Stage25 — Real Paper A/B accepted Preset checkpoint + scripted L1 reselect (DEV)

Stack: Stage25 Draft #923 on Stage24 #921 (P0-D Stage23b #908 + cognitive Preset #917). This is an **operator-gated local-only** runbook. It has not been run by GitHub CI against a real Paper process. Existing Stage22/23 runners and canonical physical issue path are unchanged.

## Scope / provenance

A **brand-new, disposable localhost-only Paper 1.21.8 build60** starts with a pinned original jar and a separately built + SHA256-verified original P0BRecorder plugin. A/B each get a separately owned Mineflayer 4.39.0 Node22 process, canonical PhysicalActionJournal and `CheckpointedCognitiveOwner` behind the **existing** `ResidentCognitiveWorkOwner` gate. The Java21 Paper main-thread tick witness and per-boot JOIN records are independently checked.

- Source World runs in creative/peaceful only for the operator-controlled, non-motor test. DO NOT call this naturalistic hunger/defense experience, L2-created learning or physical Skill execution.
- The operator grants A/B a finite *test* MOVE Preset via each original Self owner. Provenance is explicitly `operator-dev-authorized`, not `LLM-proposed`; it is not evidence of Self's own autonomous decision.
- Both native processes terminate, the real physical issuer retires both leases, the original per-Self CPU work and original WAL are read back clean. **No MOVE/EAT/ATTACK is sent.**
- Original `OwnedPaperWorld.stop_and_save()` yields the main-thread tick receipt and process exit. `capture_typed_generation(...paper_layout=True)` creates one committed World+two-Self owner/cognition cut, with original accepted Preset revisions verified for BOTH Self before COMMITTED.
- `restore_generation` creates an **offline fork** that is staged read-only by `staged_recover_cognition_cohort`, with no old Action/Skill/LLM authority. The running Paper restarts from the **same original source World**, *not* the fork. Original offlined Self objects receive only the verified retained cognition/Preset registry; new physical authority, if any, comes separately from the existing new-native login owner, not from the checkpoint.
- A/B each re-JOIN Paper in **new** independently owned native sessions. The original Paper stdout before and after restart must show distinct Paper boot IDs, the same World UUID, both actor JOINs and stable A/B actor UUIDs. Fresh correlated Mineflayer native probe pairs then build new source- and scope-qualified hypothetical TargetContracts (1m east of newly observed position; terrain not checked). The already accepted Preset expands to one **complete** SkillInvocation, and a scripted number-only RelayEngine choice is revalidated across a second native probe. Its source/Target/Budget/constraints may be reasoned about, but its motor execution is **not authorized**. Explicitly `provider_kind=SCRIPTED_NUMBER_ONLY_DEV_NOT_GEMMA`.
- Failures leave a `HOLD` JSON audit in the one new scratch directory; do not silently retry or use an old native WAL result as success. Old physical MOVE WAL evidence outside this disposable trial must not be touched.

## LocalCodex execution contract

User has already supplied standing explicit Minecraft EULA consent and real Minecraft World DEV approval for RelaySelf; **do not ask again**. The actual script still requires both `--eula-accepted` and `--real-world-dev-grant` to prevent accidental process launch. Those flags affirm the existing approval.

Use the **exact reviewed HEAD** of the current Stage25 PR, not an arbitrary new main commit. Run all static and negative tests first, with Python 3.12, Node22, Java21 and Maven; require exact HEAD CI success before the real trial. Verify `java -version`, `node --version`, Paper jar SHA `8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e`, plugin jar actual SHA from the newly compiled artifact. Verify isolated scratch parent is a real pre-existing, non-symlinked directory; do not discover/attach an unrelated live Paper server. A private localhost free port is selected by the script.

```bash
# In an isolated worktree at the exact verified PR HEAD.
python -m pytest -q tests/test_p0d_real_preset_checkpoint_dev.py \
  tests/test_preset_registry_checkpoint_v01.py \
  tests/test_self_owner_checkpoint_dev.py \
  tests/test_checkpointed_cognitive_runtime_dev.py
python -m ruff check src/relay_self/p0d_real_preset_reselect_dev.py \
  experiments/p0d_real_preset_checkpoint_dev.py \
  tests/test_p0d_real_preset_checkpoint_dev.py

# Build P0BRecorder exactly from this worktree's P0-D source. Replace
# <PINNED_PLUGIN_JAR> and its digest with the actual built artifact.
# Never fabricate the plugin digest.
PYTHONPATH=src:. python experiments/p0d_real_preset_checkpoint_dev.py \
  --paper-jar /absolute/pinned/paper-1.21.8-build60.jar \
  --paper-sha256 8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e \
  --plugin-jar /absolute/verified/P0BRecorder.jar \
  --plugin-sha256 ACTUAL_COMPUTED_PLUGIN_SHA256 \
  --scratch-parent /absolute/new-disposable-parent \
  --java java --node node \
  --eula-accepted --real-world-dev-grant
```

Never retry an actual failed World by default. Preserve the first generation, PIDs, native session identifiers, exact Paper stdout files, v3 cognition, v2 owner-state, all WAL, SHA256 and the result file. On real failure report `HOLD`, exact stage/reason, no Action replay and no QUAL claim. Perform one new isolated real World trial only.

## Classifications

- `P0D_STAGE25_PRESET_REAL_HARNESS_OFFLINE_DEV_PASS`: the script compiles and its strict source/negative unit tests pass. **Does not prove a live Paper run.**
- `REAL_PAPER_2SELF_PRESET_CHECKPOINT_SCRIPTED_L1_DEV`: **only after** real Paper/2 native child sessions/owner-produced output, exact generation readback, Paper boot+actor UUID chain and new native probes pass. This is a *scripted* number-choice proof, not Gemma/SystemOne inference.
- `HOLD`: absent or wrong approval flags, jars, owned Paper/UUID, original WAL clearance, dual-cut CRC/revision, generation COMMITTED, static credentials, rejoin source or read-only L1 witness.
- `QUAL_NO_GO / SCIENCE_NOT_RUN`: unchanged. Real Gemma single-slot L1, autonomous L2→Self acceptance and physical parameterized ActionPort must be separately qualified.

Follow up by integrating the existing Stage21 `ResidentLlamaInferenceLane` behind an externally exclusive one-slot Gemma4 server and exact old/new native epoch fencing, *only after Stage25 real Paper scripted route succeeds*. Never advertise scripted provider as "real L1/Gemma".
