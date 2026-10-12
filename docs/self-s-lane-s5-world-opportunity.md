# Self S Lane S5 — frozen RSEE World natural-threat opportunity diagnosis

Authority: product Issue #537, S4 original physical receipt #6115446794,
S4 observational integration Draft #599 exact
`7c2818c940f94f0112035dadc88101bee84c8cc7`.
This **offline-only** Draft is stacked on #599 without changing that Draft,
#598/#597, #592/#590, original Golden #588, shared RSEE 1.0, L/R/V, main or
the original local World/JAR/GGUF.

## Source of the 0-entity physical result

Two successive explicitly authorized *natural* RSEE sessions finished with
181 outer observations and 0 L0 decisions/Actions. S4's actual admitted source
histogram was `move=180, time=1, entities=0`, and none of those original
snapshots showed a zombie within the exposed Mineflayer 16-block entity
registry scope. Thus S49's `entities`-only zombie-trigger condition was never
satisfied; this proves neither global World safety nor a generic protocol
failure.

The static RSEE/bootstrap **eligibility mismatch** is now concrete:

1. `experiments/standard_env/world_bootstrap.py` explicitly executes
   `gamerule doMobSpawning false` when creating #583. Its existing
   `_saved_state` independently checks this saved rule as `false` in
   the stopped `level.dat` NBT.
2. `experiments/standard_env/world_binding.py` copies that same sealed
   snapshot (with a pinned manifest) to a disposable root. Original
   `verify_qualified_world` rejects substitute manifests.
3. `adapters/mineflayer/bridge.mjs` emits `entities` on native
   Mineflayer `entitySpawn` / `entityGone`, not on continuous bot `move`
   or `time` events. The bridge has no spontaneous hostile-mob generator.
4. The older `s31a_real_server_ci.py` used an explicit controlled server
   `summon minecraft:zombie` *after* disabling Mob spawning. That
   controlled World Action was a separately qualified test fixture, NOT
   proof that #583 naturally spawns hostile mobs.

This is **a demonstrated experimental mismatch**, not yet definitive proof
that this was the only cause of S4's zero-entity observation. A previously
present or externally summoned mob could still be visible even when natural
Mob spawning is disabled; bot spawn-position, 16-block geometry, chunks,
server settings, Mineflayer `entitySpawn` emission and source filters still
matter. Adding an `entityMoved` bridge listener is a separate enhancement,
but cannot establish an original target that the World snapshot did not
contain and must not be sold as the root cause.

## What S5 does

`adapters.mineflayer.self_s5_world_opportunity` is a strictly **read-only**
preflight diagnosis:

- Uses original `verify_qualified_world` and pinned #583
  jar/manifest/initial-receipt identity; rejects an unqualified replacement
  World, symlink root or malformed native NBT.
- Parses original stored `level.dat` with existing bounded native NBT parser.
  The original recorded `doMobSpawning=false` leads to
  `FROZEN_WORLD_NATURAL_MOB_SPAWNING_DISABLED`.
- `doMobSpawning=true` in a hypothetical separately qualified World would
  still produce `NATURAL_MOB_SPAWNING_RULE_ENABLED_TARGET_UNPROVEN`;
  it is **not** a guarantee a zombie will exist/arrive.
- Both outcomes explicitly set
  `natural_zombie_spawn_opportunity_qualified=false`,
  `physical_execution_authorized=false`,
  `minecraft_sessions_started=0`, `action_authority=false`.
  No new authority to start a real World exists in either case.

### Operator diagnosis only

From a fresh checkout of the exact S5 HEAD on the operator WSL2 host:

```bash
BASE=/home/rinsa/.local/share/relay-self/rsee-1.0-20261011
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD"
export PYTHONDONTWRITEBYTECODE=1
"$BASE/venv/bin/python" -m adapters.mineflayer.self_s5_world_opportunity
"$BASE/venv/bin/python" -m pytest -q tests/test_self_s5_world_opportunity.py
```

No Java, Node, Minecraft, World copy, install, new output directory, model,
Action or Model POST. Existing original #583 RSEE is **never modified** by
this check. If the original RSEE bytes are absent, it reports
`S5_WORLD_OPPORTUNITY_UNKNOWN_BLOCKED`; never substitutes a new World.

## Next physical gate (NOT authorized or implemented here)

A product test of **natural** threatening-entity arrival needs independently
qualified, non-frozen experimental World assets permitting the intended
natural spawn mechanism and a predeclared opportunity/visibility protocol.
It must independently check spawn opportunity and source-event delivery,
while retaining separate Action authority, EULA, no-replay, cleanup and
scientific evaluation gates. Do **not** flip a gamerule inside #583's
sealed snapshot or pass it off as the same Golden World. Alternatively,
if the aim is specifically the S49 physical integration with a controlled
known target, that is a different **intervention** experiment and needs its
own explicit one-shot permission, controlled input/evidence and a
non-natural classification.

No new physical trials are authorized by a generic continuation. The S2
and S4 grants are consumed; #544 scientific discrimination remains NO-GO.
Terminal ceiling: `S5_OFFLINE_WORLD_OPPORTUNITY_MISMATCH_IDENTIFIED /
FROZEN_WORLD_UNCHANGED / NO_NEW_PHYSICAL_RUN / NO_PRODUCTION_GO`.
