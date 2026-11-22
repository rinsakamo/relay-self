# I Lane I2g — NEW authentic original A/B born-v3 source → independent SHA seal → inert fork

Parent: #1078. Original Draft PR: #1080. This is **additive** to I2f; it does not change the historical Stage28b default source/manifest, merge another lane, issue a Physical Action or grant QUAL/SCIENCE.

## Purpose and nonclaims

Prior I2f accepted only a source with an *already* durable A/B PatternRegistry and an explicitly recorded empty per-Self SchemaSnapshot in one committed typed v3 original generation. The historical Stage28b original had neither. It is incorrect to upgrade that old source in-place, or to infer an exploration Pattern. I2g adds the **separate real-original generation path**, under explicit opt-in, reusing the original `experiments/p0d_real_resident_presence_dev.py` bridge, owners, Paper and typed World capture.

GitHub Actions checks this via **synthetic CPU fixtures only**; it cannot run the user's local WSL2 Paper process or actual RTX 3060. Not a real-World result unless the local one-shot and *independent* post-run audit have really executed with complete original source bytes.

## Stages

### Stage I2g-0 — new source Paper / original three Native sessions

`experiments/i_lane_i2g_new_original_v3_world_dev.py` is a new one-shot opt-in LOCAL entrypoint. It checks pinned Paper 1.21.8 plugin/JAR assets, original Node/Mineflayer dependency preflight and EULA before a new disposable World. It must **not** reuse the historical Stage28b generation.

`run_real_resident_presence(i2g_original_v3_source=True, typed_owner_cut_dev=True)`:
- Constructs the canonical original `CheckpointedCognitiveOwner` A/B (no alternate/second owner), with only `initial_patterns()` (innate, revision 0, **no exploration Pattern or Skill**).
- Writes the exact same original initial `PersistentCognition.pattern_registry` to each owner's `cognition.json` before first Native JOIN; independently re-reads it. `register_i2g_born_original_empty_schemas` registers `SchemaSnapshot(A,0,())` and `SchemaSnapshot(B,0,())` on the same original `ResidentCognitiveWorkOwner`, after checking their true offline-born IDs, World tick 0, first provenance, empty histories and durable Registry.
- Uses the existing actual original `OwnedResidentPhysicalBridge` / `_owned_resident_trial`: A+B initial JOIN, A logout, B continuing Native observe, A new Native reJOIN, A+B final logout, World-only quiescence and stopped Paper; `capture_retired_resident_typed_world` stores one original same-generation full World + typed A/B owner v3.
- Captures the original **three** post-startup Native child sessions' exact stdout JSONL and stdout-consumed stdin observe-only JSONL via the existing Mineflayer process-session audit methods. Files are exclusively created/fsynced; the initial `adapter_started` event is consumed by launch *before* the audit starts and is **not** part of these raw sources. Original login request-correlated probe bytes are included, and the original A first-session and A new-session receipts are both archived.
- Returns **`I2G_REAL_ORIGINAL_V3_TYPED_A_B_CAPTURED_AUDIT_PENDING`** only after every Native raw source is finalized and the typed v3 cut is verified. No LLM POST, B MOVE, attack, physical Action or Self-generated exploration. Failure leaves original partial evidence on HOLD, with no automatic World retry.

### Stage I2g-1 — separate-process raw original audit + one-time root SHA seal

`experiments/i_lane_i2g_independent_origin_audit_dev.py` is run in a **fresh, independent Python process** after the World source has stopped. It validates:
- original single trial's report and typed same-generation COMMITTED source; A+B saved cognition SHA equals the pre-first-login innate snapshot, each saved typed Owner includes an **actual recorded** empty v3 Schema and revision-0 Registry;
- real owned Paper stdout event chain: A twice JOIN/QUIT, B once JOIN/QUIT, independent PRESENT events for both;
- **three distinct original Native session IDs**: A first, B continuing, A reJOIN; exact per-session original stdout/observe-only stdin raw files and SHA/length, request-ID-correlated login probes and Native World time; B's continuing request; zero effect output or physical command;
- special nested checksum files are in the *specific committed typed generation*, not arbitrary peer paths.

Only after all these independent checks does `--seal-once` write a **new**, exclusive `original-evidence/SHA256SUMS`. It then invokes the original full outer manifest validator with a **distinct I2g expected original report classification** and the new observed file count; the historical Stage28b default remains pinned at 285 with its old classification. No re-sealing or mutation of an existing immutable root is allowed.

### Stage I2g-2 — inert future fork and explicit source pins

`--prepare-fork-once` requires the **preexisting sealed manifest SHA** and entry count from the previous separate-process audit, and uses the existing Stage28c1 `prepare_stage28c_inert_restore` to create exactly one *fresh* World fork in a path outside the original source. It verifies the full original source unchanged after copying, then writes `I2fFutureSourcePins` as a distinct path outside the original and restored trees. This exports the exact new source World UUID, source branch, COMMITTED SHA, new fork branch, original Native/Paper manifest SHA and file count; not a synthetic signed declaration. Operator must preserve immutable pins and prohibit later source writes.

**Only then** can I2f inspect the new origin and potentially run a separate second real World trial with actual Gemma L2/L1 and independent raw model/Native/Paper audit. I2g itself invokes NO model and issues NO Physical Action.

## Local opt-in command outlines

First inspect assets/dependencies read-only (no World or model):

    PYTHONPATH=src:. python3 -m experiments.i_lane_i2g_new_original_v3_world_dev \
      --inspect-only --eula-accepted \
      --paper-jar /PATH/KNOWN_PAPER.jar --plugin-jar /PATH/KNOWN_PLUGIN.jar \
      --scratch-parent /SAFE/FRESH/PARENT

Then exactly one new original World capture:

    PYTHONPATH=src:. python3 -m experiments.i_lane_i2g_new_original_v3_world_dev \
      --execute-once --eula-accepted --real-world-dev-grant \
      --paper-jar /PATH/KNOWN_PAPER.jar --plugin-jar /PATH/KNOWN_PLUGIN.jar \
      --scratch-parent /SAFE/FRESH/PARENT

The output reports the specific `/ORIGINAL/evidence/resident-presence-result.json` and its `typed_world_self_generation` path. After the owned processes are gone, first do read-only independent inspection:

    PYTHONPATH=src:. python3 -m experiments.i_lane_i2g_independent_origin_audit_dev \
      --original-evidence /ORIGINAL/evidence \
      --generation /ORIGINAL/evidence/typed-world-self-generations/g-... \
      --inspect-unsealed

With only that genuine successful readback, in an independent process seal **once**:

    PYTHONPATH=src:. python3 -m experiments.i_lane_i2g_independent_origin_audit_dev \
      --original-evidence /ORIGINAL/evidence \
      --generation /ORIGINAL/evidence/typed-world-self-generations/g-... \
      --seal-once

Record the printed root SHA-256 and positive file count independently. Then prepare a *fresh* inert fork and external pin file, using the exact previous sealed values:

    PYTHONPATH=src:. python3 -m experiments.i_lane_i2g_independent_origin_audit_dev \
      --original-evidence /ORIGINAL/evidence \
      --generation /ORIGINAL/evidence/typed-world-self-generations/g-... \
      --prepare-fork-once \
      --expected-manifest-sha256 64-HEX-FROM-SEAL \
      --manifest-files EXACT-COUNT-FROM-SEAL \
      --restored /DIFFERENT/FRESH/RESTORED \
      --restore-id NEW-UNIQUE-FORK-ID \
      --pins-output /DIFFERENT/EXTERNAL/I2F-NEW-SOURCE-PINS.json

The final `I2fFutureSourcePins` file is a source *coordinate*, not proof of actual GGUF ownership or World survival. I2f rechecks the entire sealed evidence, exact committed A+B owner and recorded v3 Schema before World admission.

## Holds and boundaries

**I2G_NEW_V3_ORIGINAL_SOURCE_CPU_OFFLINE_DEV_PASS** is a local code/CI verdict only. Without a genuine owned original Paper+Native trial and separately verified source manifest, **I2G_PRE_WORLD_HOLD / REAL_ORIGINAL_SOURCE_NOT_RUN / REAL_GEMMA_NOT_RUN / QUAL_NO_GO / SCIENCE_NOT_RUN** remain.

Do not claim that source archive generation is an L2 learning event: it is **innate bootstrap**, not new exploration. Any later learned non-motor exploration Schema must come from actual model OPEN L2 and BOUNDED L1 accepted by the original Self, with an independently verified owner durable readback. The old Stage28b cut, I1 real-World audit and other B/D/C/I branches are immutable and retain their original statuses.
