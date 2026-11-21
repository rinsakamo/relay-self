# P0-D #860 — Disposable real Paper 1.21.8 main-thread tick/save smoke (stage 12 DEV)

Stacked on Draft PR #871, keeping 60-second committed World + all-Self generations, discard everything after last full generation and **no replay**. This is a distinct **single-World, zero-Self** source attestation precursor, not the final multi-Self experiment.

## Preconditions

- Java 21 and Maven available; Python 3.12+ (same development environment as the repository).
- Obtain the genuine **Paper 1.21.8** server jar from PaperMC's official Fill v3 downloads service with a non-generic User-Agent. Do not use the sunset v2 API or a latest-Minecraft-version jar. A stable known build is **1.21.8 build 60**, whose published SHA256 is `8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e`. Verify the API metadata or checksum rather than trusting an unauthenticated mirror.
- Build the repo's existing `experiments/p0b_paper_recorder` plugin from the exact branch HEAD with Java 21 Maven; the jar must include both Recorder.class and TickWitness.class.
- Read the Minecraft server EULA yourself; the smoke harness does not accept it by default. `--eula-accepted` is the operator's **explicit** affirmation for a brand-new disposable test server, never an existing World. Do not run against a production/interactive server.
- Prepare an existing empty or dedicated writable `--scratch-parent` directory. The harness creates a fresh randomly named child; it never opens an existing Paper process, overwrites a World, uses Mineflayer, or launches Self.

## Reproducible operator commands (from repo root)

```bash
# Inspect the official metadata, pin build 60 and its checksum.
export PAPER_USER_AGENT='RelaySelf-dev/0.1 (https://github.com/rinsakamo/relay-self)'
curl -fsSL -H "User-Agent: $PAPER_USER_AGENT" \
  'https://fill.papermc.io/v3/projects/paper/versions/1.21.8/builds' \
  | jq '.[0] | {id,channel,downloads}'

# Only after verifying official build metadata:
curl -fL -H "User-Agent: $PAPER_USER_AGENT" \
  'https://fill-data.papermc.io/v1/objects/8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e/paper-1.21.8-60.jar' \
  -o /tmp/p0d-paper-1.21.8-60.jar
printf '%s  %s\n' \
  '8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e' \
  /tmp/p0d-paper-1.21.8-60.jar | sha256sum -c -

mvn -B -f experiments/p0b_paper_recorder/pom.xml -DskipTests package
mkdir -p "$HOME/relay-self-disposable-only"
export PAPER_JAR=/tmp/p0d-paper-1.21.8-60.jar
export PLUGIN_JAR=experiments/p0b_paper_recorder/target/p0b-recorder-0.1-dev.jar

# Read https://www.minecraft.net/eula yourself first.
# Add --eula-accepted ONLY if you agree and explicitly authorize this test.
PYTHONPATH=src:. python -m experiments.p0d_real_paper_smoke_dev \
  --paper-jar "$PAPER_JAR" \
  --paper-sha256 "$(sha256sum "$PAPER_JAR" | awk '{print $1}')" \
  --plugin-jar "$PLUGIN_JAR" \
  --plugin-sha256 "$(sha256sum "$PLUGIN_JAR" | awk '{print $1}')" \
  --scratch-parent "$HOME/relay-self-disposable-only" \
  --eula-accepted
```

## Evidence and safe behavior

1. Hash-verify exact Paper/plugin jar inputs, ensure the passive P0BRecorder+TickWitness classes are present; refuse missing EULA confirmation **before creating anything**. Copy jars into a brand-new `p0d-real-paper-only-*` directory with localhost-only TCP binding, no RCON/Query and low simulation radius.
2. Bootstrap Paper *once* with a new World, wait for actual `Done (` and `P0D_TICK_READY` lines, save-all flush and stop, then read `world/uid.dat` (Bukkit's 16-byte World UUID) to bind the P0D source.
3. Use the **existing** OwnedPaperWorld and the newly implemented PaperMainThreadTickReader. Start that same disposable World, receive main-thread tick ACK with exact UUID, fresh boot and nonce **joined to the same owned server process log**. Issue `save-all flush`, wait for a new `Saved the game` completion line, then stop. Hash and copy every file in the generated World/dimension directories and verify the copy before restarting.
4. Start a fresh Paper process with the same World and plugin. Repeat the exact source-qualified tick + save/stop; require **distinct owned Paper sessions and boot/nonce tick receipt identities**.
5. Write the complete SHA256 manifest, source receipt references, exact executable and plugin checksums, world UUID and server-log references to an audit JSON within the scratch evidence directory. Preserve all input files and logs. On failed readback, missing markers or uncertain exit, return **HOLD**, do not overwrite evidence, and do not attempt to restart a failed process. The operator must inspect whether their specifically owned disposable server is still running.

## Interpretation

- If the script actually runs against genuine Paper 1.21.8, with logs/jars/receipts preserved, the maximum claim is `REAL_PAPER_SINGLE_WORLD_TICK_SAVE_SMOKE_DEV`. This is **not** proof of every dimension's atomicity, not a qualified 60-second recurring autosave, and not a real two-Self snapshot or crash/restore.
- CI only runs preflight unit tests against synthetic jar structures, plus the existing owned-fake-server and real plugin **compile** tests. The actual Paper executable is not downloaded, launched, or EULA-accepted in default CI.
- The script uses `level.dat` and `uid.dat` as initial World identity and computes a post-stop file manifest. Neither these nor clean log lines alone certify complete persisted Paper state.
- In order to graduate the full project, a distinct approved real experiment must connect actual A/B native sessions, both owner's complete cognition and WAL, STOP evidence, tick witnesses, 60-second timer and crash rollback **without history replay**. External processes/Node native writers must be inventoried and fenced first.

## Classification while the real script has not been executed

`REAL_PAPER_SMOKE_HARNESS_OFFLINE_DEV_PASS / REAL_PAPER_1_21_8_SMOKE_NOT_RUN / REAL_TWO_SELF_60S_AUTOSAVE_NOT_RUN / QUAL_NO_GO / SCIENCE_NOT_RUN` (only after CI success).


## Next DEV slice: coherent Paper dimensions and multi-Self generations

The single-World smoke copied all **present** standard Paper folders (`world`, `world_nether`, `world_the_end`). An ordinary World+Self generation previously only captured `source_world`, which would omit sibling dimensions when the server uses Paper's folder layout. Stage 13 introduces an **opt-in** `paper_layout=True` in the existing generation and synchronous autosave contracts. It captures each present standard sibling World into the *same* generation before writing `COMMITTED.json`, includes checksummed per-dimension manifests, requires source World/branch/tick/stop receipts to match, and restores all World roots on one **new fork branch** before `RESTORE_PREPARED.json`. A canonical `world` folder with companion siblings fails closed if the option is not used. Unknown `world_*` siblings also fail closed instead of being silently dropped.

Tests remain filesystem-only and never launch Paper or Self. This does not demonstrate live 60-second A/B autosave, atomic World+WAL attestation, or full cognitive-owner resurrection. A real next-stage runner must opt in to `paper_layout`, provide verified A/B owned native sessions, and verify each restored dimension and the entire Self roster before any new action.

During a 60-second multi-generation run, the synchronous runtime pins the list of present Paper dimension roots from the first successful cut. A removed/added dimension at a later cut blocks the next commit and holds the admission gate for operator review. This does not authenticate the Paper source at runtime, or stop arbitrary direct native issuers.
