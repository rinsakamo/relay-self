# RSEE 1.0 — Minecraft-only one-shot World bootstrap

Authority: #575 / #537, host evidence #580, byte-binding Draft #581.
Child branch: `self/rsee-world-bootstrap-20261011`, stacked directly on
#581 exact `6860ce46230bf1bbf5002e9233f2f930276c53d8`.
No modifications to main, sibling Lane A/B/C, S49 L0 Action ownership,
S60 L2 ownership, or the default S31A/S49 runs.

**Current status: OFFLINE_BOOTSTRAP_IMPLEMENTED / LIVE_BOOTSTRAP_NOT_RUN /
GOLDEN_RUN_BLOCKED.** Do not represent a green CI as a physical run.

## Why this separate bootstrap exists

#581 correctly refuses any RSEE Self/LLM Golden Run without an existing
Mojang-jar-bound, stopped-World manifest and initial native evidence. This
module creates those artifacts through **a separate Minecraft-only one-shot**:
one vanilla Minecraft 1.21.8 server, one Mineflayer 4.39.0 observer,
zero LLM inference, zero S49 autonomous/agent Actions.

The module reuses S31A's existing `_write_config`, `_ready_server`,
`_await_spawn`, `_correlated_observe`, `_shutdown_server`, the
original unmodified Mineflayer bridge and #581's World verifier. It never
calls native S49 Action/execution code.

### Before physical execution: two independent approvals

The following flags are *explicit requests for new permissions*; this
document and any earlier issue/PR are NOT permissions:

- `--authorize-world-bootstrap-once`: explicit one-shot disposable World
  process permission for this exact HEAD, jar, and new output directory.
- `--minecraft-eula-accepted`: independent user assent to Minecraft Java
  Edition server EULA, not inferred from previous experiments.

Do NOT set either flag without the human operator's actual affirmative grant.
Merely saying `進めて` or performing offline tests is not proof of EULA assent.
The program itself cannot check authorization provenance; preserve the human
approval and exact CLI argv in a separate operator receipt.

### Runtime preflight and physical stages

- Expected jar exact SHA256:
  `2349d9a8f0d4be2c40e7692890ef46a4b07015e7955b075460d02793be7fbbe7`.
  Original host #580 verified its Mojang identity and version; this run
  rechecks the *bytes*, not the online publisher response.
- New output directory must NOT exist; its parent must already exist and
  not be a symlink. No overwrite and no auto-retry. Existing local
  Minecraft listener on loopback25565 is refused.
- NODE_OPTIONS substitution refused; Java+Node+native Mineflayer imports
  checked before launch. Explicitly preserve #580 host Python environment.
- Copy jar into `<new-output>/server/minecraft.jar`, exact SHA check.
  Existing S31A properties + `level-seed=575` and world name
  `s31a-ephemeral`. EULA file is scoped to the new disposable World.
- Start server once. Before connecting Mineflayer, issue frozen setup:
  `gamerule doDaylightCycle false`,
  `gamerule doWeatherCycle false`,
  `gamerule doMobSpawning false`,
  `time set midnight`, `weather clear 1000000`.
  No mob attacks, forced movement, inventory writes, or Self Actions.
- Start one Mineflayer observer and consume native `spawn` and exactly
  one correlated `probe`, retaining session IDs and source sequences.
  Any mismatch, missing native response, startup timeout or exit anomaly
  fails closed.
- Request Mineflayer clean shutdown and Minecraft `stop`, wait for
  process exit 0. **Exit 0 alone is not an independent STOP_ACK.** If a
  timeout/fallback kill or missing clean exit occurs, mark unqualified
  and retain the failed run untouched.
- Only when both processes have reported clean exit, read vanilla stopped
  `level.dat`: native `DayTime`, `raining`, `thundering`,
  complete stored GameRules, and required fixed rules. Read the only
  native playerdata NBT for saved position, yaw, pitch, health, food and
  Inventory. **No fabricated orientation or weather placeholders.**
- Copy stopped World into `<new-output>/snapshot`, hash all files and
  confirm byte equality with the stopped original. Create
  `initial_native_observation.json` and
  `snapshot_manifest.json` with exact byte hashes. Re-run #581
  `verify_world_binding` against the original jar and saved bytes.
- Receipt is `bootstrap_receipt.json`. Any nonzero/uncertain cleanup,
  missing native fields, file drift or manifest failure is non-qualified
  and prevents snapshot admission. No retry, no fallback, no failed-run
  reset. Preserve original logs/World for analysis.

### Physical command template (not an approval)

Only after **explicit new one-shot World permission AND separately
recorded Minecraft EULA assent**, in an isolated HEAD #582 worktree:

```bash
export PATH=/home/rinsa/.nvm/versions/node/v22.22.2/bin:$PATH
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD"
export PYTHONDONTWRITEBYTECODE=1

# NEVER run before the separate grants. OUTPUT_DIR must not yet exist.
/home/rinsa/.local/share/relay-self/rsee-1.0-20261011/venv/bin/python \
  -m experiments.standard_env.world_bootstrap \
  --jar /home/rinsa/.local/share/relay-self/rsee-1.0-20261011/minecraft-1.21.8.jar \
  --output-dir /home/rinsa/.local/share/relay-self/rsee-1.0-20261011/bootstrap-UNIQUE_RUN_ID \
  --authorize-world-bootstrap-once \
  --minecraft-eula-accepted
```

Do not use this command against real World installations. This is a single
disposable instance. Test the exact HEAD's synthetic CI first.

### What is and is not qualified

Success classification intentionally remains
`STOPPED_WORLD_BYTES_SEALED_PHYSICAL_AUDIT_PENDING`. Even then, an
independent read-back of all logs, world/player NBT, source jar bytes,
process IDs, listener cleanup, and evidence hashes is needed before
`WORLD_SNAPSHOT_QUALIFIED` may be claimed. A physical observation
during bootstrap cannot prove identical future timing or physics.
No stop acknowledgment can be inferred from simply seeing process exit0.

The *separate* Golden Run still requires new explicit authorization
for model/GPU, L2 POST, disposable World and S49 actions, and must use a
different fresh evidence directory. There is NO delegation from
bootstrap permission into Self operation.

### Offline tests

`tests/test_rsee_world_bootstrap.py` covers missing permissions,
native NBT time/weather/rules, saved player yaw/pitch/health/food,
one synthetic launch pair + clean stop + sealed manifest, and failure
with unclean stop retaining World but no admitted manifest. Tests only
use mocks and synthetic NBT; no Java, Minecraft, Node or LLM process.
