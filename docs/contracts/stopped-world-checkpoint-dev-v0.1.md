# P0-A #853 — stopped Minecraft World checkpoint DEV contract

Parent #851 / Draft PR #852 contains a separate causal-cut evaluator.
This change adds offline *filesystem* capture, exact inventory/hash
verification and non-destructive restore into a newly generated fork.
It never starts/stops a server, issues an Action or changes a Self WAL,
Intent, Skill, Goal, memory or L0 program counter.

## Operator CLI

Only run after the designated isolated dedicated Minecraft 1.21.8 server
was stopped normally, saved all dimensions and exited. The program
cannot check the stop event independently; supplied references are
OPERATOR CLAIMS and may be false.

    python -m experiments.cognitive_world_checkpoint_dev capture \
      --source-world /ABS/server/world \
      --archive-dir /ABS/checkpoints/W100 \
      --world-id world-dev-1 \
      --branch-id branch-alpha \
      --checkpoint-id W100 \
      --logical-tick 204 \
      --tick-source-ref server-log:gametime204 \
      --stopped-server-ref server-log:clean-exit0-save

    python -m experiments.cognitive_world_checkpoint_dev verify \
      --archive-dir /ABS/checkpoints/W100

    python -m experiments.cognitive_world_checkpoint_dev restore \
      --archive-dir /ABS/checkpoints/W100 \
      --new-world-dir /ABS/other-isolated-server/world \
      --restore-id restore-W100-1

    python -m experiments.cognitive_world_checkpoint_dev verify-restored \
      --archive-dir /ABS/checkpoints/W100 \
      --restored-world-dir /ABS/other-isolated-server/world

Run verify-restored BEFORE starting the restored server, while its
files are expected to be byte-identical. This also validates the
separate fork receipt and explicitly rejects forged permission flags.
After Minecraft starts, World files naturally change and a byte-identical
prelaunch check may no longer be valid.

Source and archive must never overlap. Output directories must NOT
already exist. After restore, the world.restore.json sidecar is written
in the new World directory's parent and contains both the inherited
branch ID and a fresh fork UUID. The Minecraft server will not see
that branch automatically: actual World history custody is still
an external responsibility, not a changed level.dat or native clock.

## DEV metadata-trust policy (2026-11-15)

For isolated development, checking that the World files match the Manifest
is sufficient to investigate whether Minecraft can restore a saved World.
Independent metadata authenticity (e.g., proving a recorded tick is not
forged) is **NOT a prerequisite for DEV experiments** and must not
automatically block P0-A work.

- Normal `verify`, `restore` and `verify-restored` commands are unchanged.
- To investigate Manifest metadata tampering, optionally pass
  `--expected-manifest-sha256 <64 lowercase hex>` to any of these
  commands. Obtain this pin *independently at capture time*, e.g. from
  the prior evidence record, never from the same mutable archive being
  checked. The provided pin is checked before trusting the Manifest.
- Without a pin, syntactically valid modified Manifest metadata such as
  tick 476→477 **can still pass**. This is deliberate DEV behavior and
  should be classified as `MANIFEST_METADATA_UNPINNED` in the DEV report,
  not authenticated truth; the API does not emit that classification.
- The restore receipt records the source Manifest digest to make
  internal comparisons possible, but does NOT establish external
  authenticity without independent custody.
- Keep actual file-level mismatch, unsafe overwrite, foreign World
  path and unresolved physical Action/WAL replay protections intact.

This mode does not itself change a `P0-A` file restore observation into
a causal reconstruction proof. QUAL/production requirements may impose
trusted metadata pins and verified server event clocks later.

## Integrity and limitations

- Capture includes all regular files recursively, including level.dat,
  region, entities, poi, playerdata (when it exists), DIM-1, DIM1,
  session.lock and any other World subtrees.
- No symlinks/special files. Exclusive new checkpoint directory and
  file creation, source drift detection during copying, fsync of target
  files, exact re-scan and rehash after copying.
- The complete manifest records world ID, branch ID, checkpoint ID,
  *declared* tick, tick source reference, stop reference, exact file
  size and sha256. SHA256SUMS and manifest.json are written last;
  if capture fails, the partial directory is intentionally retained
  for investigation and is not accepted as a complete checkpoint.
- Verify demands exact inventory, canonical file entry types, sha256
  and size, matching SHA256SUMS, and zero extra root entries.
- Restore checks all source files BEFORE creating the output directory;
  creates a NEW World, verifies copied bytes and writes a new sidecar
  receipt LAST. It never overwrites an existing World or receipt.
- A modified/missing/extra/symlinked file, stale/invalid manifest,
  missing level.dat, destination collision or source drift causes refusal.

Hashes are byte integrity only, NOT authentication of a real stopped
server, proof of a coherent live World tick, or an atomic distributed
cut across World/JVM/network/physical WAL and Self cognition. A
complete file copy is not proof that arbitrary future Minecraft
behavior will be bitwise replayable.

In particular level.dat Time / DayTime / time query gametime is NOT a
branch-invariant monotonic causal history. The capture stores an
explicitly *declared* logical tick and source reference. It does not
authorize claiming real world atomic_capture_attested or independent
event_coverage_through_tick in the #851 assessor.

## LocalCodex controlled real World qualification

1. Read repo, #851, #853, PR #852 and this PR's latest exact HEAD and CI.
   Use an isolated worktree and disposable vanilla 1.21.8 dedicated
   server, not an unrelated or existing player's World.
2. Stop the server cleanly and verify it has exited. Record server.jar
   hash, saved-dimensions and process exit logs. Do not assume an old
   session.lock file alone proves a server is stopped.
3. Use CLI capture + verify, preserve manifest and SHA256SUMS in
   independent evidence directory. Validate presence of actual
   playerdata if a player was connected and saved; if absent report
   player/inventory NOT_ATTESTED.
4. Fault-inject a changed/missing/symlink/extra file **only into distinct
   copied test archives**, verify fail-closed. Never corrupt original
   evidence; never delete files to make a test succeed.
5. Restore into a *new empty destination path* under a separate
   isolated server. Preserve fork receipt and report the new branch.
   Rehash all restored bytes before starting server.
6. Start ONLY the restored server; independently reobserve block at
   known coords, exact zombie UUID/health, player position/health and
   player inventory; fresh Mineflayer session native Entity ID vs UUID.
   If no player is present, do not invent playerdata coverage.
7. Record pre-stop and post-start game time and exact observation
   sequences. A matching integer Entity ID across processes does not
   make the old native ID reference current.
8. No automatic native Action replay, Semantic owner restore, #851
   physical causal attribution, or multi-Self autonomy is qualified
   by this test. Failure leaves unknown physical/state dimensions
   explicitly NOT_ATTESTED.

Report exact HEAD, CI, native/server versions, model if used, evidence
SHA256, what was physically read back, branch receipts, tested negative
cases, unverified World state and unresolved P0/P1 to PR/Issue.
Keep QUAL_NO_GO / SCIENCE_NOT_RUN.
