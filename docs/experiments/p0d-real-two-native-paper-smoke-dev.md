# P0-D #860 — Stage 15: real Paper + A/B native-body smoke (DEV)

Stacked on #876 (which is stacked on #874). The new runner
`experiments/p0d_real_two_native_smoke_dev.py` is a **separate disposable
two-player Paper harness**, not an amendment to the previously qualified
single-World/zero-Self smoke. It has no fake success mode: ordinary CI only
tests pure configuration, safety negatives and injected fake ownership
protocols; it does not download or launch Paper, spawn a real bot, or accept
Minecraft EULA on the operator's behalf.

## Exact restricted experiment

1. Operator checks the Minecraft server EULA, passes `--eula-accepted` only
   if they affirm it and supply genuine pinned Paper 1.21.8 build 60 and the
   locally built P0BRecorder+TickWitness plugin with explicit matching SHA256.
   Java 21, Node 22 and locked Mineflayer 4.39.0 must already be installed.
   The runner refuses any mismatch *before* creating a Paper World.
2. Create a new `0700` scratch child. Never use an existing World, server or
   game port. Bootstrap the **new** World through existing
   `_bootstrap_paper` source witness. Bind `server-ip=127.0.0.1` and choose
   a random loopback port; disable RCON/Query and use `max-players=2`,
   peaceful/creative, no Action-issue actors. `online-mode=false` and
   `enforce-secure-profile=false` are permitted **only** for this dedicated
   localhost trial, because Mineflayer's native bridge uses offline auth.
   Do not expose, port-forward or copy this server config to shared networks.
3. Start an `OwnedPaperWorld` process, then two **real** existing
   `MineflayerProcessSession.launch` processes, usernames `RelayA` and
   `RelayB`, the same explicit local port, Minecraft version 1.21.8.
   Require real `adapter_started`, distinct native session IDs, `spawn`
   and individually request-ID-correlated `probe` observations, plus
   **both join messages in that exact owned Paper process log**.
4. Install the existing `PhysicalIssueAdmission` in
   `require_neutral_stop=True` mode with the same two native identities.
   For each cycle, `prepare_stop_before_autosave` submits one supervised
   `clear_controls` per native Self and validates the actual ACK, unique
   same-source probes, two 8-tick World-clock windows and <=0.06m 3D drift.
   Preserve PREPARED and VERIFIED STOP audit files; no retroactive
   reconstruction of a missing PREPARED receipt.
5. Close the *same* physical gate, read the existing passive Paper
   main-thread tick witness, issue `save-all flush`, wait for a fresh
   completion line and exit 0. SHA256 inventory the stopped overworld, Nether
   and End folders, copy them without following symlinks, then re-inventory
   to verify each copy. This is a **native-only** World snapshot, not a
   coordinated World+Self generation.
6. Restart the same World as a *new owned Paper process*. For A and B,
   terminate the former owned Node bridge, launch a new real bridge, require
   spawn and correlated probe, cross-check the joined native player names
   in the **new** Paper log, and rotate the existing physical gate for each
   owner. Re-open it only after both have fresh IDs; no MOVE/EAT/ATTACK
   or LLM communication is performed after the native-only rejoin.
7. Run STOP/save a **second** time with the new pair, then leave the
   second Paper process cleanly stopped and the physical fence closed.
   Record both distinct Paper sessions, native IDs, STOP receipts, tick refs,
   dimension file hashes and copied stopped-World files in a JSON audit.
   On any crash/uncertainty, HOLD and preserve evidence; no blind Paper
   restart, server kill, Action replay or forgotten-source retry. Native
   child cleanup is owned, bounded, and audited separately.

## Operator command

From an exact checked-out repository branch containing #876 and this stage:

```bash
# Paper and plugin jar provenance should be reviewed against previous real
# single-World smoke; do not download unpinned build replacements here.
npm ci --omit=dev --no-audit --no-fund --prefix adapters/mineflayer
mvn -B -f experiments/p0b_paper_recorder/pom.xml -DskipTests package
mkdir -p "$HOME/relay-self-two-native-disposable"

# PAPER_JAR: actual PaperMC build 60 from the previously verified source.
# PLUGIN_JAR: jar built from this exact repo HEAD.
# Read https://www.minecraft.net/eula before adding --eula-accepted.
PYTHONPATH=src:. python -m experiments.p0d_real_two_native_smoke_dev \
  --paper-jar "$PAPER_JAR" \
  --paper-sha256 "$(sha256sum "$PAPER_JAR" | awk '{print $1}')" \
  --plugin-jar "$PLUGIN_JAR" \
  --plugin-sha256 "$(sha256sum "$PLUGIN_JAR" | awk '{print $1}')" \
  --scratch-parent "$HOME/relay-self-two-native-disposable" \
  --eula-accepted
```

No existing `localhost:25565` or a production Minecraft World is ever
attached; the runner selects its own random 127.0.0.1 TCP port. The operator
must check the output `P0D_TWO_NATIVE_AUDIT=...` and independently verify
the process PIDs and preserved files. A failed run returns nonzero. Inspect
the **exact owned** Paper PID/log before any manual shutdown. Never interpret
a mere printed JSON field as a scientific certificate.

## Qualification boundary

Only after the operator actually runs this script and verifies source logs,
jar digests and preserved audit originals may the result be classified
`REAL_PAPER_TWO_NATIVE_STOP_SAVE_REJOIN_SMOKE_DEV`.

**No Self cognitive process was run.** The smoke does not save full
Goal/Intent/LogMemory/StructuredMemory/Skill/peer messages, WAL or GPU state.
The local native gate release between smoke cycles is **not**
`CognitionOwnerCohort` release and must never become physical grant in the
real product. The smoke does not execute a 60-second periodic autosave and
does not crash and restore a jointly committed World+A/B generation.

For full #860 acceptance, connect #876's async native preparer to a
*real* two-Self cognition owner and frozen state/GPU/transport fencing, fix
any Paper dimension archive layout mismatch using actual stopped World
evidence, then separately run >=60s periodic joint World+Self cuts, a
post-cut crash, the latest verified generation rollback, and whole-cohort
fresh rejoin without replay. QUAL/SCIENCE remain NO GO.

## Current evidence

This stage's GitHub CI can establish only
`REAL_TWO_NATIVE_HARNESS_OFFLINE_DEV_PASS`. Unless actual native Paper
evidence has been supplied in this PR's comments, the physical test is
`REAL_TWO_NATIVE_PAPER_NOT_RUN`.


## Paper companion checkpoint layout correction (Stage 15)

During repo-first review, a compatibility blocker was found in #874:
`world_checkpoint_dev._scan` required `level.dat` in **every** archive
folder, but the existing Paper-only World hashing helper explicitly allows
`world_nether` and `world_the_end` folders without `level.dat`.
Those are not standalone overworld World roots.

The default `capture_stopped_world` still **requires** `level.dat` and emits
the original schema 1. For opt-in standard Paper sibling dimensions only,
`capture_stopped_world(..., paper_companion=True)` now records an explicit
schema-2 `world_file_role=PAPER_COMPANION`, requires at least one real file,
and hash-verifies the entire directory without inventing a `level.dat`.
`capture_generation(..., paper_layout=True)` opts into it only for its two
approved sibling names. The verifier rejects an untyped companion, a
companion swapped into the main overworld slot, missing or altered files,
corrupted role metadata and symlinks; restored companions share the same
new fork branch but never receive physical authority. Existing standalone
`level.dat` qualification remains unchanged.

This is synthetic layout coverage, **not** a claim of observing the precise
contents of a newly generated genuine Paper 1.21.8 sibling directory.
