# Bug-0 zombie supply — World-owned 600-tick respawn (R0)

Parent Issue #742, v0.5 #717, original fixed WorldBody/S49 source #741
`e280f4cdc4f435720513329212e35959d8eb776a`.

## Implementation boundary

- **Standalone opt-in Paper 1.21.8 plugin**, default disabled. No Self-host command, profile API or second S49 issuer.
- One exact player name `RelaySelf`, one World UUID, one plugin-managed zombie at a time.
- Upon first owner join, spawn one ordinary **AI-enabled, vulnerable adult zombie** at the owner's initial location +6 X (fixed World arena rule). Disable daylight burning for repeatable daylight spawns; ordinary loot is not modified. Initial arena must provide clear headroom and solid ground.
- Only an actual `EntityDeathEvent` matching the managed UUID and server-owned persistent tag creates a future spawn deadline. The `RespawnCycle` pure Java gate requires death+600 server ticks; no background wall-clock timer. Every generation has a new entity UUID.
- Spawn timer, authoritative server UUID, death and generation are **operator-only post-World audit**; no SelfBody/L0/LLM input. Self only gets existing native Mineflayer entity/inventory observations, if genuinely witnessed.
- Logout, player death, World change, plugin disable, invalid/contested spawn point and missing living entity without death fail closed. No duplicate spawn, no timer replay on restart. This plugin does not promise 30 wall-clock seconds when TPS deviates from 20.
- Minecraft default drops remain subject to random zero drops, vanilla death rules, other modifiers and item despawn; no guaranteed rotten flesh.
- Existing #741 fixed WorldBody Java source untouched. #740 P1 law is a **separate** ongoing DEV branch. This does not silently merge #740.

## R0 offline gate

Run `javac`/ `java -ea` on `RespawnCycleTest` for world/identity mismatch, duplicate death, 599/600 tick boundary, new UUID and next generation, cleanup and overflow. Compile the standalone Paper plugin separately. Current evidence is **offline only**; plugin behavior in a real Paper World, zombie killing, loot pickup, EAT repeat and unlimited survival are NOT attested.

## R1 real World plan (separate single-use grant and CI)

Require fresh exact pinned Paper1.21.8 JAR hash, exclusively enabled plugin, one original S49 session with one authorized combat source, original Paper death/respawn server log, 600 contiguous world ticks plus wall duration, next fresh native entity probe, SHA256 immutable artifacts, no retries or hidden self-command. If test-only kill is operator issued, label it **operator-caused** not **Self combat**. A later R2 trial must link genuine S49 kill/death/drop/PICKUP/EAT and second generation in one World. R0 alone neither grants a physical World run nor establishes autonomous survival.

`DEV_ONLY / WORLD_NOT_RUN / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
