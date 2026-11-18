# Stage28c-2b — pinned original recovered A/B observation-only real runner

Parent #966. Stack on Stage28c2b Native/Paper dual-clock Draft #985,
Stage28c2b epoch #982, partial observation-only #981, Stage28c2a #977,
Stage28c1 #973, Stage28b #969. All old evidence remains immutable.
**GitHub CI uses synthetic fixtures only. Real Paper/native trial requires
LocalCodex and its independently checked source artifacts.**

## Exact original source pins

- Original Stage28b source World UUID:
  `f9221410-b99e-417d-98f4-e98938586472`.
- Original source branch `p0d-real-resident-presence`,
  generation `g-000000000000`,
  original COMMITTED SHA256
  `d1425c49a5ef0ff03486931427907aeed6eccf568494efd8177ed96d3ce3f4ee`.
- Original Stage28b evidence `SHA256SUMS`: **285/285**,
  SHA256 `7a202d68f6d275a0031f9c7091e0e1e7f33c4976c4565461d425e040f87209f4`.
  Source root `/home/rinsa/evidence/stage28b-1dcd48-20261118/`.
- Original Stage28c1 inert World fork:
  `/home/rinsa/stage28c1-restored-575198-20261118`;
  branch `fork-3883122c-6edb-4017-bd82-00fc4324aded`.
  Correct **64-digit** evidence manifest SHA256:
  `28d1a7548f98ab74d5e7359462e4a1f7baf5c43f80e4a9fbd4a2c74065e915c1`.
- Original stopped-Paper source tick W221, A cognitive cut C210 and B C39
  remain historical. No attempt to numerically synchronize them with
  restarted Paper `Bukkit.getCurrentTick()` or Mineflayer World-day time.

## What the local one-shot runner does

1. Inspect original 285-file manifest from disk, all file SHA256 values,
   original Stage28b real resident result and final typed original A/B
   owner sessions. Extract A-first, A-rejoined, and B-native as the *full*
   3-session historical denylist. Refuse any duplicate, mismatch, missing
   file or untracked evidence. The raw provenance is the authority,
   NOT user-supplied native session identifiers.
2. Verify Stage28b typed generation and Stage28c1 fork, full A/B cognition
   and canonical WAL via the existing recovery gate and actual original
   source digest. Do not create a new default Self.
3. Create ONE new executable copy of the saved fork, with copied
   Overworld/Nether/End and Self A/B. No original evidence file is written.
4. Pin original Paper 1.21.8 build60 jar SHA256
   `8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e`
   and Stage24g resident witness plugin SHA256
   `0b20dd042231618fc301bbe26ee48c5808c09dafddc946c49f4393ca48386fb5`.
   Use only Java21 and locked Node22/Mineflayer4.39.0 owner patch.
5. Start one owned Paper Popen from that executable copy, then obtain
   actual main-thread tick READY+nonce ACK, bound to its owned stdout.
   Boot-local Paper ticks and native Minecraft full-day times are **different**.
6. Attach the *restored canonical* A/B `CheckpointedCognitiveOwner`
   objects to the single original resident cognitive owner, with original
   `PhysicalIssueAdmission(observation_only=True)`, final-stdin native
   effect admission and historical native denylist.
7. Spawn real independent Mineflayer A/B native processes via the existing
   `OwnedResidentPhysicalBridge.login()` and verify their original
   spawn/request-bound probe. Persist their raw JSONL stdout. A real Paper
   JOIN/PRESENT log with distinct actors + post-JOIN main-thread nonce ACK
   is required to link each original Self's new WorldBody.
8. Original A/B retained identity, Schema and memory are preserved.
   **No L1/Gemma POST, new Skill, MOVE/EAT/ATTACK/REST, Peer send,
   original Action replay or physical authorization** is allowed.
9. Independently retire both natives, verify canonical WAL and no old
   cognitive writers, observe Paper QUIT, stop/save the owned Paper
   process and record its exit code. Preserve raw logs and receipts.
10. First runner returns
    `REAL_REJOIN_CAPTURED_INDEPENDENT_AUDIT_PENDING`, **not success**.
    A separate-process verifier rechecks original source manifests,
    original native stdout request-bound probe, Paper log
    JOIN/PRESENT/QUIT, main-thread ACK, historical session exclusion,
    restored persistent cognition, WAL clear and Paper clean exit.
    Only that independent audit may classify
    `REAL_RESTORED_WORLD_ORIGINAL_A_B_NATIVE_REJOIN_WORLDBODY_DEV`.

On any error: HOLD, preserve evidence, never retry automatically or kill
foreign processes. Owned native/Paper process termination is bounded.
If ownership or cleanup is uncertain, leave visible HOLD and report
the exact dedicated PID/source to the operator. Do not upgrade from an
unverified success-only summary.

## LocalCodex commands

Use a clean worktree based on this PR's exact HEAD and verify GitHub CI
before one real attempt. Resolve the true typed generation directory from
the original Stage28b manifest; do not invent its path.

Inspect-only (does not start Paper or create a World):

```bash
PYTHONPATH=src:. python3 -m experiments.stage28c2b_real_recovered_rejoin_dev \
  --generation "$EXACT_STAGE28B_TYPED_GENERATION" \
  --restored /home/rinsa/stage28c1-restored-575198-20261118 \
  --stage28b-evidence /home/rinsa/evidence/stage28b-1dcd48-20261118 \
  --paper-jar "$STAGE24G_PAPER_JAR" \
  --plugin-jar "$STAGE24G_PLUGIN_JAR" \
  --eula-accepted --inspect-only \
  --java "$JAVA21_BIN" --node "$NODE22_BIN"
```

One live attempt **only** after all offline contracts + preflight pass:

```bash
PYTHONPATH=src:. python3 -m experiments.stage28c2b_real_recovered_rejoin_dev \
  --generation "$EXACT_STAGE28B_TYPED_GENERATION" \
  --restored /home/rinsa/stage28c1-restored-575198-20261118 \
  --stage28b-evidence /home/rinsa/evidence/stage28b-1dcd48-20261118 \
  --paper-jar "$STAGE24G_PAPER_JAR" \
  --plugin-jar "$STAGE24G_PLUGIN_JAR" \
  --execution-dir "$ONE_NEVER_EXISTED_EXECUTION_COPY" \
  --evidence-dir "$ONE_NEVER_EXISTED_EVIDENCE_DIR" \
  --eula-accepted --real-world-dev-grant --execute-once \
  --java "$JAVA21_BIN" --node "$NODE22_BIN" --timeout-s 120
```

The user has permanently approved Minecraft EULA and isolated real World
DEV for RelaySelf; do not ask for reconfirmation. The explicit CLI flags
express that approval. Never use or modify another server's processes.

After the owned Paper/Node processes are **confirmed terminated**, launch
an independent, separate Python process to audit the raw source:

```bash
PYTHONPATH=src:. python3 -m experiments.stage28c2b_independent_rejoin_audit_dev \
  --result "$ONE_NEVER_EXISTED_EVIDENCE_DIR/stage28c2b-recovered-world-result.json" \
  --generation "$EXACT_STAGE28B_TYPED_GENERATION" \
  --restored /home/rinsa/stage28c1-restored-575198-20261118 \
  --stage28b-evidence /home/rinsa/evidence/stage28b-1dcd48-20261118 \
  --execution-dir "$ONE_NEVER_EXISTED_EXECUTION_COPY"
```

Preserve *all* original bytes and compile an independent SHA256SUMS
manifest with full readback. Report code HEAD, CI, actual Paper+native PID
and session, separate tick domains, source+fork identity, A/B Identity,
old/new session provenance, actual log/Paper event IDs, native request
IDs/seq, action/WAL status, exit receipts, evidence digest and HOLD
reasons to parent #966 and the relevant stacked PRs.

## Classification boundary

Until a real trial and independent audit have actually occurred,
classification **remains**

`STAGE28C2B_OWNED_REJOIN_RUNNER_OFFLINE_ONLY /
REAL_REJOIN_HOLD / FRESH_L1_NOT_RUN /
60S_AUTOSAVE_NOT_ATTESTED / QUAL_NO_GO / SCIENCE_NOT_RUN`.

Stage28c2c new Gemma L1 and online 60s autosave are separate.
