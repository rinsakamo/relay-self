# RelaySelf M0.2 Paper DEV plugin — experimental server-side exhaustion

**Status:** An isolated Paper **1.21.8** real-World **DEV-only** run
completed in [S CI #38668633950](https://github.com/rinsakamo/relay-self/actions/runs/38668633950),
with corrected coordinate-based walking cost and governed S50 MOVE/S51 steak EAT.
This is **not R qualification**, calibrated ecology, V science, or a production
finding. The plugin is **DISABLED by default** and is not loaded by the
existing Mojang-vanilla S49/S51 product runner.

## Why this plugin exists

- The **Minecraft World** is the *only physical source of truth* for hunger,
  saturation, health, eating and exhaustion.
- One universal configuration contains `standard`, `multiplier`,
  `additional`, `unit`, `enabled` for all 14 Paper
  `EntityExhaustionEvent.ExhaustionReason` types, plus BASAL and COGNITION.
- Per action: `q × (standard × multiplier + additional)`.
- The plugin replaces native exhaustion using `event.setExhaustion(...)`.
  For land WALK/CROUCH/SPRINT the original movement-event charge is set to
  zero and `PlayerMoveEvent` gives the **actual distance in blocks**.
  Charge that distance once via `Player.setExhaustion`, not a second
  independent ledger. Native nonmovement events retain replacement rules.
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

**Corrected from real 2026-10-15 Paper DEV evidence:** 1.042431 blocks
of executed S50 motion emitted only **12 WALK exhaustion events**. Therefore
one event is NOT necessarily one centimeter of physical displacement;
billing 12 × 0.0001 would undercharge by about 8.7×. The corrected plugin
observes `PlayerMoveEvent` horizontal block displacement and bills
`observed_blocks × (standard × multiplier + additional)` once, without
charging the requested Action distance. At WALK standard 0.01/block,
a fully observed 1.042431-block step should bill about 0.0104243;
a genuine observed 0.4-block step should bill 0.004.
The corrected coordinate-path rate **has a separate real DEV confirmation**:
9 movement packets covered 1.2828913533 observed blocks and charged
0.01282891353 exhaustion (WALK=0.01/block); this is not the same quantity
as S50's net goal-direction progress of 1.0424312164 blocks. The earlier
12 native WALK exhaustion callbacks must not be used as a centimeter counter.
The result is still **DEV_ONLY / NOT R-QUALIFIED**. Water, sprint and
unclassified locomotion are outside this bounded land-walk result. Basal
still charges once per actual World tick.

## S-owned disposable physical DEV executable

`python -m adapters.mineflayer.m02_paper_dev.s51_paper_physics_dev`
is an opt-in DEV-only physical characterization runner that **reuses** the
existing S31A World lifecycle, S50 governed SEEK movement, S51 native
`IssuedEatingExecutor`, recording Mineflayer session, and Java cleanup.
It does not change the old S51 Mojang/rotten-flesh path, and it deliberately
does **not** construct an M0/0.1 virtual energy ledger.

The runner requires fresh absolute output directory, an explicit DEV confirmation
string, full SHA256 hashes of a specific Paper 1.21.8 official jar and the
compiled plugin jar, and an unused loopback 25565 port. It creates/removes
only its owned disposable World; evidence in the separate output directory
is kept after cleanup. It stages steak and hunger as **operator fixtures**,
not autonomous food procurement.

New source files:
`s51_paper_physics_dev.py` and
`tests/test_m02_paper_dev.py`.
The **existing** `m02-paper-dev-build.yml` GitHub workflow now has
`paper-world-dev` in addition to compile-only. It looks up an official
stable Paper 1.21.8 build, checks the official SHA256 and runs a fresh
ephemeral Paper server and one native Mineflayer connection. DEV evidence,
including the plugin log, raw native JSONL and owner commands, is uploaded
whether success or failure; historical World receipts and Golden cannot
be reused. A successful compile is not a physical PASS. A physical run
must independently close and pass its own cause/food/session checks.

**Always maintain DEV_ONLY:** this path is a controlled source
characterization, not proof of learned Self locomotion, ecology calibration,
precise pickup causality, starvation-respawn behavior, scientific
discrimination or production integration.

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

## Optional manual Paper DEV exploration (not a second qualification)

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
   not a user's survival World. For the **already implemented** S-owned
   disposable runner, use the existing S50 governed MOVE and S51 governed
   `cooked_beef` EAT path; staged SPRINT or additional movement modes require
   separate DEV source checks and cannot inherit the WALK result.
5. Preserve the complete Paper console log, `M02_DEV_BODY` snapshots each
   100 billed ticks, independent Mineflayer snapshots (health/food/saturation),
   World identity, bot observations, plugin jar/config hashes, shutdown ACK,
   owned Java/Node PID exit and port rebind checks. If any native causal input
   is unavailable, report UNKNOWN and do not infer success.
6. Close and delete only the explicitly owned disposable World; report
   DEV_ONLY. R must independently qualify a **new** run; V scientists must
   preregister a comparison. No historical B0 run becomes M0.2 proof.

The plugin logs sampled body state **and per-event/per-coordinate-motion
diagnostics**; the existing S DEV runner independently preserves native
Mineflayer JSONL and S50/S51 owner commands. These streams are not yet a
cryptographically attested, source-joined R qualification receipt. R must
review their identity, ordering, motion/food evidence and terminal separately.
A compile-only result is never a live physiology result.

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

## S qualification source preparation (offline only)

The **same** S-owned `s51_paper_physics_dev` CLI now exposes a read-only
`--qualification-preflight` mode. This is **NOT a qualification runner**:
there is no Java/Node/Minecraft process, World mutation, run grant, S51 Action,
R acceptance, or V admission. It does not reclassify the historical real DEV run.

Stage exactly the four original **R-pinned candidate** assets in a *new*
absolute directory (no extra files, symlinks, or shared Golden World) under the
names `paper-1.21.8.jar`, `relay-metabolism-paper-dev.jar`, `config.yml`,
`server.properties`. Then run:

```bash
PYTHONPATH="$PWD/src:$PWD/tests:$PWD" \
python -m adapters.mineflayer.m02_paper_dev.s51_paper_physics_dev \
  --qualification-preflight \
  --asset-root /ABSOLUTE/FRESH/FOUR-PAPER-ASSETS
```

S independently checks four byte SHA256s against the unchanged R #610
`RSEE_M02_PAPER_PREWORLD_PROFILE_V1` and validates intended test player
and survival/loopback settings. A successful response is strictly
`S_M02_PAPER_QUALIFICATION_ASSET_PREFLIGHT_ONLY`; `qualified=false`,
`physical_world_launches=0`, `new_world_snapshot_seed=NOT_BOUND`.
Any mismatch fails closed, including missing or mixed DEV launch parameters.

**Not provided by asset matching:** a new fixed Paper World snapshot/seed,
fresh per-run QUALIFICATION permission, exact code HEAD and runtime attestation,
live original receipts, independent STOP/PID/port witness, ecological calibration
or V science. R remains the independent owner; the historical 2026-10-15
DEV result and protected Mojang Golden/B0 evidence are immutable.
The preflight is not a mechanism to bypass the new explicit physical grant.


## Native hunger L0 product bridge (future Paper B0/B1)

The Paper-specific `native_l0.py` now provides a *small cheap, designed*
L0 decision based on real correlated Mineflayer food/inventory/item-entity
observations: `WAIT` when not hungry or food source absent, `EAT` for an
observed edible inventory candidate, and `SEEK` for a single observed nearby
item only while hungry. The item's stack contents are **UNKNOWN**, so SEEK
is a tentative candidate, never proof of edible pickup. Decisions do not
issue S15/S16 Actions and do not alter M0.2's Paper exhaustion or build a
separate M0/M0.1 virtual energy ledger.

The existing S-owned Paper DEV `_native_steak` now requires this explicit
`EAT` decision before S51's governed food Action. Its appetite trace records
the L0 kind for each truly observed World probe. Other action, physics and
source qualification ownership remains unchanged. In particular, the frozen
R-qualified third one-shot at S HEAD
`50d3dfe96a37d18cc8fec68334cfc2e0204a996b` remains immutable;
this **new future-only product bridge** is not automatically R-qualified.
The full Paper B0/B1 `SEEK → MOVE → pickup → EAT` loop is a subsequent DEV
integration, not claimed here.
\n## Paper native ground forage — new isolated DEV scenario\n\nRun the existing Paper DEV CLI with `--forage-dev` and a fresh root to test\n`native World hunger → L0 SEEK → S50 governed MOVE → source-consistent pickup → L0 EAT → S51 governed EAT`.\nThe operator transparently stages one cooked_beef dropped item and induced Hunger,\nnot an autonomous food source. Paper-native physiology is the only actual\nmetabolic source; no B0EnergyLedger, virtual M0 energy or M0/M0.1 credit.\nThe source only proves an item disappearance with a one-item cooked_beef\ninventory increase, **not** playerCollect strict causality or unknown item\nmetadata. If eight bounded MOVE Actions cannot get there, the run fails and\nretains partial outcomes. Default original steak DEV and frozen third R\nqualification issuer are unchanged. New Paper forage remains **DEV_ONLY**.\n\n### Real Paper forage diagnostic correction\n\nA first fresh Paper forage DEV successfully recorded actual L0 SEEK, two\ngoverned S50 MOVE OUTCOMEs, a native inventory+item-disappearance pickup\ncontrast, and one S51 steak EAT. Its final Paper receipt **correctly failed**\nbecause the original one-block check required an `EntityExhaustionEvent(WALK)`\ncallback even when **14 real `PlayerMoveEvent` packets** had metered\n2.1462877746 observed blocks / 0.02146287775 exhaustion and emitted **zero**\nnative WALK callbacks. Native WALK callback count is not a distance or an\nexhaustion source and can genuinely be zero over bounded movement.\n\nOnly the isolated `--forage-dev` multi-MOVE diagnostic now allows zero\nnative WALK callbacks **when** real coordinate packets, bounded positive\ndistance, basal samples, exact 0.01/block billed ratio and plugin activation\nare independently present. Any *observed* native WALK event must still\nbe replacement-zero; missing packets or incorrect billing fails closed.\nThe pre-existing one-step Paper physical verification keeps its original\nstrict callback requirement. This is DEV source acceptance, **not** a\nretrospective upgrade of that failed run or any prior R qualification.\n\n## Paper B1 local adaptation (isolated ON/OFF disposable DEV)\n\nRun `--forage-dev --paper-b1 on` or `--forage-dev --paper-b1 off`,\nwith new, separate absolute output roots and the same explicit disposable DEV\nconfirmation as the Paper-only B0 fixture. A direct 2-block-high stone obstacle\nis requested between an operator-staged single cooked_beef item and the player.\nOnly an actual governed native S50 `SeekConsequence(BLOCKED)`, **not**\nthe operator's `fill` write, counts as evidence. Existing source-scoped\n`B1LocalCandidate` retains and reads a single Memory for ON to select -Z;\nOFF retains no Memory and chooses fixed +Z. Lateral movement and later pickup\ncontinue through the original S50/S51 owners, Paper-native BASAL/WALK rates;\nno virtual M0/M0.1 ledger is involved. Eight total MOVE attempts bounded.\n\nEach run independently requires exactly one authentic BLOCKED, at least one\nprogressing lateral Action, a native source-consistent inventory pickup and\nissued EAT. Without this it is a **failed DEV run**, not a proof by request.\nOFF is a cheaper fixed reflex baseline, not a counterfactual proof: different\nspawn/seed states cannot establish retained Memory's causal advantage.\nThe new DEV artifact remains outside the frozen third R-QUALIFIED scope;\nstrict playerCollect causal evidence, behavior benefit, V science and\nproduction are not implied. The Paper workflow preserves failed-run originals\nfor both retention switches and marks the job FAIL if either is unsuccessful.\n

## Prospective Paper B1 Memory original journal

New disposable `--forage-dev --paper-b1 on|off` runs now create
`paper_b1_memory_original.jsonl` with **exclusive create** before World
starts. At the first genuinely governed native BLOCKED the S producer
immediately persists the actual retained Memory object (id, verbatim content,
source/integration provenance) or an explicit null for OFF, using append,
flush, and fsync **before the next MOVE**. Each subsequent lateral Action
ISSUED also saves the session/native source seq, chosen waypoint, Action id,
and SHA256 of the retained content (or null for OFF) before executing it.
A failed run retains partial entries; absent/malformed journal is not
a qualification. The producer report hashes the journal original alongside
native, command, and Paper originals, without promoting or rewriting any
historic R-qualified source. `Memory` is an S/L-owned retained observation,
not a new Paper physics currency or an automatic science benefit.

This is a **new prospective DEV source emitter**. It cannot retroactively add
Memory bytes to previous Paper B1 ON/OFF originals, replace strict pickup
provenance, certify identical World starts, or qualify independent R/V claims.
R must separately inspect new original bytes, Action provenance, and host
termination before any new scoped qualification.
\n## Prospective V7 direct BASAL write source — S DEV only\n\nThe new Paper plugin emits bounded `M02_DEV_BASAL_WRITE` source lines at\neach **actual** target-player `setExhaustion` write (id/world full time,\nprevious exhaustion, requested debit, input write target, API readback,\ncumulative requested debit, and native pose/yaw). Genuine `PlayerMoveEvent`\nrecords now also include native from/to coordinates and World time. S validates\nfirst 200 consecutive player callbacks and 200 corresponding consecutive\nWorld full-time ticks, with direct request/rate/cumulative checks; failures\nremain DEV fail-closed. This is **direct write-input evidence**, not the\nindependent downstream effect on hunger/saturation and **not** an exact\nMOVE-bracketed 200-tick trial. S also saves pre/post MOVE native positions\nwith identity-bound probe seq; the Mineflayer snapshot has no yaw and\nWorld geometry/collision coverage is still UNKNOWN.\n\n**No retrospective reinterpretation**: historic V7 five-arm seed61021 DEV\nhas source-review PASS but 0.2438-block paired-path spread vs preregistered\n0.005; comparison FAIL remains unchanged. Newly built plugin JAR SHA differs\nfrom historically R-qualified 0.2 plugin: no R transfer or science admission.\n
## Prospective V7 native World seed and bounded local terrain

The Paper plugin now emits one `M02_DEV_WORLD_V7_FIRST_TICK` original
line at the first living-player BASAL callback. It includes the actual
Paper `World.getSeed()`, full World time, player xyz/yaw/pitch and a
four-column +X ground/feet/head Bukkit material and passability probe.
The S V7 reader checks this exact source instead of assuming the
`level-seed` setting proves World identity. Motion packet sources also
contain actual from/to coordinates and World time. This is a first-tick
local sample, **not** guaranteed to be a pre-MOVE snapshot, verified
collision attribution, matched spawn/pose, identical path, or a
flat controlled corridor. Old V7 preregistered path gate stays FAIL;
new DEV plugin is not automatically R qualified or V science.
