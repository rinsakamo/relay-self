# RelaySelf M0.2 Paper DEV plugin — experimental server-side exhaustion

**Status:** Code compiles against Paper **1.21.8**; **NOT** a qualification or
scientific finding. Plugin is **DISABLED by default** and is not loaded by the
existing Mojang-vanilla S49/S51 product runner. Java/Paper live validation is
NOT_RUN until a disposable Paper World is separately created and executed.

## Why this plugin exists

- The **Minecraft World** is the *only physical source of truth* for hunger,
  saturation, health, eating and exhaustion.
- One universal configuration contains `standard`, `multiplier`,
  `additional`, `unit`, `enabled` for all 14 Paper
  `EntityExhaustionEvent.ExhaustionReason` types, plus BASAL and COGNITION.
- Per action: `q × (standard × multiplier + additional)`.
- The EventListener calls `event.setExhaustion(...)` (**replaces**, does not
  add on top of the Vanilla pending charge). Movement reasons are **1 cm per
  event**, so for a per-block numeric standard `q=1/100`.
- Some sources (`REGEN`, `HUNGER_EFFECT`, `UNKNOWN`, underwater/water-surface)
  use explicit `standard: native`; the original event amount is the source.
  For native movement the multiplier is applied to the source event amount,
  and `additional` is still per block. Do not make up HP healed from REGEN.
- Once per actual scheduled server tick, the plugin adds the BASAL rate via
  `Player.setExhaustion`; it does **not** bill a second energy ledger.
- COGNITION is disabled and unqualified. It is a configuration extension
  placeholder, not a working physical-meter hook.
- **Single isolated bot:** only the exact player `RelaySelf`; a wrong player
  name or invalid config refuses plugin activation. Do not use personal,
  public or existing qualification Worlds.

## Action size vs. physiological integration resolution

Approved abstraction: **one MOVE/SEEK planning step is up to one block
(nominally one meter), never one centimeter**. Existing S50
`SeekWaypoint.max_step_m=1.0` already provides the default local steering
cap; actual motion can be partial/blocked. No attempt is made to change
the existing Action authorization, motor timing or source receipts.

This Paper plugin charges native movement exhaustion events at their
own **1cm source granularity**. The per-block editable standard and
additional are divided by 100 per actual centimeter event. A typical
one-block walk costs about 100 events × 0.0001 = 0.01 exhaustion under the
uncalibrated candidate; a partial 0.4-block walk should cost 0.004 for 40
admitted WALK centimeter events. Do not charge the full requested meter
separately. Basal billing is still by World tick, and nothing bills by
number of Self decisions. Live original event attestation is NOT_RUN.

## Build the plugin, no World starts

Install **JDK 21 + Maven 3**; build explicitly:

```bash
mvn -B -ntp -f adapters/mineflayer/m02_paper_dev/pom.xml -DskipTests package
```

Expected:
`adapters/mineflayer/m02_paper_dev/target/relay-metabolism-paper-dev-0.2.0-dev.jar`

No jar is committed. This build obtains a **Paper API dependency** over
the network; it does not fetch/launch a Minecraft server, install EULA,
create a World, or run a player. A dedicated GitHub compile workflow is
part of S's owner Draft #545 and MUST actually complete before claiming it
builds.

## Separate, manual disposable Paper DEV World (not S51 integration)

1. Obtain a separately downloaded and SHA-recorded **Paper 1.21.8 server
   jar** from the official PaperMC source. Never replace an existing RSEE
   Golden or someone's personal World. Reserve a new empty directory/port,
   seed, and strict localhost-only `server.properties`. This is deliberately
   **not** an S51 drop-in replacement. Accept EULA only for the isolated
   disposable World if the operator agrees.
2. Put the built plugin jar in **that new World's** `plugins/` folder.
   Start Paper with normal explicit Java 21 operator controls once, then stop
   it cleanly. The plugin writes `plugins/RelayMetabolismDev/config.yml`
   whose `dev-enabled` is **false**.
3. For a separate explicit DEV run, edit that copied config to
   `dev-enabled: true`. Verify `target-player: RelaySelf`,
   `minecraft-version: 1.21.8`, and all 16 complete rate sections. Capture
   profile and plugin SHA256 BEFORE server start. Never let Self change them.
4. Operate only a single owned offline Mineflayer player named `RelaySelf`,
   not a user's survival World. Run staged WAIT, WALK, SPRINT and optionally
   consume `cooked_beef` using only the existing authorized S-owner Action
   path once the S51 integration is separately modified and tested.
5. Preserve the complete Paper console log, `M02_DEV_BODY` snapshots each
   100 billed ticks, independent Mineflayer snapshots (health/food/saturation),
   World identity, bot observations, plugin jar/config hashes, shutdown ACK,
   owned Java/Node PID exit and port rebind checks. If any native causal input
   is unavailable, report UNKNOWN and do not infer success.
6. Close and delete only the explicitly owned disposable World; report
   DEV_ONLY. R must independently qualify a **new** run; V scientists must
   preregister a comparison. No historical B0 run becomes M0.2 proof.

The plugin only logs periodic body state; it does **not** yet record every
original action/exhaustion frame in a cryptographically attested JSONL stream,
nor independently prove walking displacement, food consumed or native
saturation deltas. These are requirements for the NEXT S/R integration stage.
Paper plugin build success alone does not show any Minecraft physiology.

## Why source constraints matter

The standard settings are **candidate values**, not calibrated biological
parameters: BASAL 0.001 exhaustion per World tick, WALK 0.01/block, the
Vanilla-like reference costs for other actions, and standard food
`cooked_beef` (Vanilla restores 8 food and up to 12.8 saturation).
A body with insufficient hunger cannot always consume steak, and capped
saturation makes nominal 20.8-point recovery an upper bound.

Do not run the legacy M0/M0.1 virtual energy debits simultaneously against
this World. The present S51 DEV entrypoint still hardcodes the old rotten-flesh
fixture and Mojang server and **must not** be described as Paper-compatible.
RSEE Golden is **Mojang vanilla**; its original receipts, hashes and permits
are protected. The plugin currently does not implement historical arena
respawn-without-free-energy or starvation-only lineage death.

Authority: M #616 / Draft #617; S #537 / Draft #545; R #575 / Draft #610;
V #544 / #619. Design/API sources:
- https://jd.papermc.io/paper/1.21.8/org/bukkit/event/entity/EntityExhaustionEvent.html
- https://jd.papermc.io/paper/1.21.8/org/bukkit/event/entity/EntityExhaustionEvent.ExhaustionReason.html
- https://docs.papermc.io/paper/dev/project-setup/
