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


### Controlled-pose packet World-tick source (prospective S DEV)

Only `--v7-controlled-calibration-dev` requires the complete native
`M02_DEV_MOTION` packet sequence including server `world_full_time`,
from/to XYZ, packet ID and cumulative source totals. The S reader checks
finite values, monotone World ticks, sequential IDs, coordinate-derived
distance, packet continuity and running distance/charge totals. Its
`v7_source.native_motion_tick_trace` records the actual packet count and
per-World-tick histogram; partial or contradictory source fails DEV.

**This is not S50 control-on/off tick attestation.** The client-side
`set_control` / `clear_controls` acknowledgements have native session
sequence but no independently matched Paper server-tick acknowledgement.
The trace therefore explicitly reports both control boundaries and
cross-arm equal-duration claims as `false`. It cannot yet promote
fixed-pose DEV calibration to a matched-duration V trial. Next engineering
step is a prospective cross-source control-phase handshake with source
World-tick boundaries that does not replace the S50 issuer. Existing
5-arm V7 science roster remains 0/20; the earlier failed path gate is frozen.


### S50 control phase / Paper World tick handshake (controlled DEV)

The existing S50 issued Action is still the **only** movement issuer.
`execute_seek_step(..., phase_hook=...)` makes four observation callbacks,
strictly ordered around the pre-existing client control commands:
`PRE_FORWARD` before `set_control(forward)`,
`POST_FORWARD` after its native applied ACK,
`PRE_CLEAR` before `clear_controls`, and
`POST_CLEAR` after its applied ACK. On errors *after* forward was sent,
the S50 path attempts the original clear in `finally`; it does not
invent an Action OUTCOME.

The DEV-only Paper plugin now exposes console-only `relaydevphase`
(received on Paper main server thread). The player cannot issue it.
Each phase records the requested source Action/session-scoped marker ID,
actual World full-time, plugin player-tick counter and current XYZ to the
original `paper_server.log`. S waits for each unique original before
proceeding. Only the controlled-pose `--v7-controlled-calibration-dev`
path opts in; default Paper/forage/S50 runs do **not** issue any marker.

`v7_source.s50_server_phase_brackets` verifies the four unique phase
sources, matching ID, original order, nondecreasing World and player
tick clocks, and finite XYZ. It includes the World tick intervals when
**client command issuance/ACK** was bracketed by server callbacks, not
exact server-effective forward-on/off ticks. The server-effective start
and stop, cross-arm fixed-duration, whole-motion observation interval,
and physical matched-path gate all remain **NOT_ATTESTED**.
Differences in server task latency, packet submission, and coast after
clear are not silently normalized. No V7 original or science roster is
reclassified. A changed Paper plugin/JAR needs fresh R owner admission.


### Prospective six-Paper-tick clear-decision calibration (DEV only)

The separate `--v7-controlled-calibration-dev --v7-server-clock-calibration-dev`
mode retains the same disposable fixed-pose World, native S50 Action issuer,
and console-only four source phase markers. At the server's
`POST_FORWARD` callback, Paper schedules **one observation gate after six
server ticks** (not a movement command), writing
`M02_DEV_S50_CLOCK_GATE` with the action/session-scoped marker, original
callback `world_full_time`, player tick and XYZ. S50 awaits that **actual
source line instead of sleeping 0.30 host seconds**, then uses its existing
native Mineflayer `clear_controls` issuer; failures still attempt clear.

The original report's `s50_paper_scheduled_clock_gate` must show the
unique callback `reached_full_time - base_full_time == 6`, the bound
`POST_FORWARD` original and `POST_FORWARD <= gate <= PRE_CLEAR`.
Duplicate, missing, wrong source, bad clock, foreign session or nonfinite
XYZ is rejected. This attests the **server-observed decision gate**, *not*
the exact server-effective forward-on/off motor control ticks. Client
transmission delay, post-clear coasting and actual World packet path must
still be recorded without exclusion. No result counts in V7's historical
science roster, and changed plugin bytes cannot inherit an R qualification.
The previously observed five-arm paired-path failures remain frozen.

### S50 physical boundary (2026-10-16, new DEV source)

The existing `--v7-server-clock-calibration-dev` now observes a bounded
post-clear quiet window before probing and closing the supervised Action.
Paper emits `S50_DEV_TICK` (native World UUID/full time, actual pose,
monotonic motion count/path/billing) for up to 100 World ticks starting at
PRE_FORWARD. Phase markers and native PlayerMoveEvent rows carry the same
World and Action/session composite marker. This is an observer only: no server
motor command, velocity change, teleport, rollback or new Action grant.

`seek_execution.py` continues to own forward and clear, including clear in
`finally` on lost ACK/gate failure. A clear ACK means Mineflayer
`clearControlStates()` returned; it does not mean velocity is zero or identify
a server-effective control tick. Six World ticks are measured from the
POST_FORWARD console bracket, not from an invented shared clock.
The new settle callback requires six consecutive native snapshots spanning
five quiet intervals (unchanged XYZ, event count, distance and billing).
A source gap, regression, identity mismatch or timeout leaves UNKNOWN;
the original issued/terminal lifecycle is saved in `s50_action_original.jsonl`.
Its `at_ns` values are explicitly synthetic DEV logical ordering, not measured
host nanoseconds or World ticks. Missing connection or release ACK remains
unattested; session termination is separate from successful release.

`s50_boundary.reconcile` independently sums the horizontal native event path,
checks chained XYZ and every snapshot's event prefix, applies the configured
WALK rate to realized blocks, and compares actual target-directed progress
with S50's OUTCOME progress. Path length, endpoint displacement and target
progress are distinct. Overshoot is preserved, including moves away from a
target. `distance_after_post_clear_world_bracket_blocks` is a conservative
subset of release-tail movement, not exact clear-ACK-to-motion causality;
same-tick event ordering cannot be reconstructed from tick numbers alone.
Further movement after the first quiet window fails final reconciliation.
The final raw bridge stream must contain the exact command/ACK lineage and
native shutdown ACK. Raw files and lifecycle are hashed in the final report.
Hashes detect changes against that saved receipt; self-consistent rewriting
of both evidence and hashes is not independent provenance (R still required).

**Nominal 1 block remains a request, not a physical cap.** A finite Paper
clock gate bounds the requested control window, but host scheduling, console
round trips, client packet scheduling, collision, momentum and transport
failure prevent a strict distance or release-latency upper guarantee. There
is no universal distance bound in this implementation. Observed quiet is
bounded evidence, not a permanent physical-stop guarantee. No assertion,
coordinate correction, billing refund or alternate server motor hides this.
The observer is opt-in for this DEV route; legacy S50 consumers have not
acquired native World attestation or live P1 capacity enforcement.

P1 integration seam: retain World-local path by tick with the in-flight
MOVE reference. Zero-distance/blocked MOVE and release settling never become
WAIT recovery. Later no-Action ticks remain UNKNOWN for WAIT: full-tick
motor/combat inactivity and P1/R source admission are additional requirements.
P1 #626 latest correction (0ab76b4) supersedes old REST semantics. No P1
parameters, capability limits, fatigue ownership or M0.2 rates are changed.

Offline controls in `tests/test_s50_physical_boundary.py` cover normal,
zero/short/overshoot path, release-tail movement, native ACK loss/rejection,
connection end, wrong identity, missing/regressed/duplicate ticks/events,
billing/coordinate corruption, missing STOP and unsettled/ended World.
Synthetic controls establish rejection logic only; each new physical run,
including failures, must retain originals. New JAR is not R-qualified;
V7 SCIENCE remains 0/20 and historical V7 comparison failure is unchanged.

#### First native attempt: honest boundary stop, not an engineering pass

Producer `cf6cfc38651358541707dadf8b60f9c5237065ef`, controlled DEV
[#38890045733](https://github.com/rinsakamo/relay-self/actions/runs/38890045733):
all five arms retained **FAIL**, supervised Action **UNKNOWN**. Every arm
observed endpoint displacement and tick-sampled chord sum **1.9389928412050272
blocks**, versus PlayerMoveEvent-metered path **1.930189272171467 blocks**.
The native post-clear bracket to quiet endpoint displacement was
**0.25474274790455187 blocks**. Six-tick World gate was retained.
The final **0.008803569033560166 block** is native server pose movement not
covered by the event meter. Small moves can update the player location without
a new PlayerMoveEvent; consecutive World samples and event counters expose
this. Strict source reconciliation correctly refused to close OUTCOME.

BASE_ON/SHAM_ON/BASAL_ZERO billed `0.01930189272171467` exhaustion,
WALK_ZERO/BOTH_ZERO billed `0`. For the positive-rate arms the endpoint alone
implies a debit shortfall lower bound `0.0000880356903356`; zero-rate arms
have no missing debit but the same incomplete movement-event coverage.
No costs were adjusted after the run. Tick-sampled chords are not a complete
sub-tick path source and must never be relabeled invented walking events.

All five had native clear + shutdown ACK, Java/Node exit0, port release.
These cleanup facts do not convert UNKNOWN to OUTCOME. Obstacles/zero-MOVE,
ACK loss and disconnect injection have offline controls only; no new physical
fault injection has been claimed. The next physical integration requires a
complete accepted-motion metering source under existing S/M ownership and
independent R review, then a fresh DEV run. This delivery stops the controlled
physical experiment at the demonstrated billing/source inconsistency.

Read-only diagnosis (keeps the original UNKNOWN and validates saved hashes):

```bash
PYTHONPATH=src:. python -m adapters.mineflayer.m02_paper_dev.s50_boundary \
  /absolute/downloaded/arm-output --failed-attempt
```

It reports native endpoint, tick chords, event meter, actual applied billing,
release-tail bracket and the source gap separately. Hashes are checked against
the original report; an independent retained receipt is still needed to attest
the manifest itself. Successful legacy DEV paths do not override this result.



### S50 candidate native World-tick WALK meter (prospective DEV only)

The **new**, explicit `--v7-controlled-calibration-dev
--v7-server-clock-calibration-dev --v7-tick-meter-dev` candidate stages a
disposable Paper config with `s50-tick-meter-dev: true`, **only for this
new DEV run**. The original M0.2 config template, five registered baseline
renderings, former V7 originals, consumed permits and R qualifications remain
unchanged. New plugin JAR and new config SHA require independent R admission.

On `PRE_FORWARD`, the Paper plugin records a native player pose. On every
subsequent living-player World tick it observes the next real Paper pose,
computes the **horizontal chord between two actually sampled XYZ** and
requests `Player.setExhaustion` once using the configured WALK
`standard × multiplier + additional`, multiplied by that chord's blocks.
Each call records before/requested/target/readback and cumulative blocks/debit
in `S50_DEV_TICK_MOTION`. The original `M02_DEV_MOTION` PlayerMoveEvent is
**still recorded**, but its own WALK write is zero to prevent double billing.
Native land exhaustion event replacement remains zero as previously.

The fail-closed reviewer `s50_boundary.reconcile_tick_meter` requires
consecutive original World ticks, one event-independent native writer row per
observed tick, finite continuous XYZ, billed amounts and accumulated readback,
no concurrent event billing, snapshot identity, terminal native position,
genuine S50 issued Action and already-existing native clear/STOP lineage.
In the prospective tick profile, a missing or foreign meter source is
`BLOCKED`, never a synthetic path or after-the-fact debit.

**Claim ceiling:** The charge covers observed tick-to-tick *horizontal
displacement lower bound*, **not** an independently measured full sub-tick
path. World-tick sampling cannot establish loops or turns occurring entirely
inside one server tick. No hard 1-block cap, exact client-control start/end
server tick, permanent quiet, R qualification, science, or P1 WAIT recovery
is asserted. Blocked MOVE and zero-distance MOVE remain MOVE (not WAIT).
Physical rates stay unchanged; only their movement quantity source changes
for the explicitly enabled DEV arm.


### Original-only S50 WALK metering scope screen (after R BASE_ON qualification)

A **read-only**, S-owned metering-scope reviewer is available without a
new Paper build, motor action, expired or reused grant, or extra World run:

```bash
PYTHONPATH=src:. python -m adapters.mineflayer.m02_paper_dev.s50_boundary \
  /absolute/unpacked/BASE_ON/output --tick-meter-original

PYTHONPATH=src:. python -m adapters.mineflayer.m02_paper_dev.s50_boundary \
  --five-tick-meter-originals \
  /absolute/unpacked/BASE_ON/output \
  /absolute/unpacked/SHAM_ON/output \
  /absolute/unpacked/BASAL_ZERO/output \
  /absolute/unpacked/WALK_ZERO/output \
  /absolute/unpacked/BOTH_ZERO/output
```

The checker rejects ordinary old event-only profiles, source-reported
failure/UNKNOWN, changed exact candidate config SHA, broken local evidence
hash, missing source-issued Action/OUTCOME/STOP, nonsequential native ACK,
noncontinuous source-tick writer, source/write mismatch, or missing 200
requested BASAL writes. It independently recomputes source
tick-chord distance and native WALK input rather than accepting S's saved
arithmetic. It treats both source-event WALK charge and post-hoc
reimbursement as forbidden. The five-arm screen requires **all five
distinct sources** and preserves the pre-registered 0.005-block gate,
rather than allowing selection of a favorable subset.

**Scope decision (as of 2026-10-16):**
- *Candidate source quantity:* native observed horizontal tick chords can
  be used to verify lower-bound displacement and direct exhaustion-writer
  *input* in the controlled S50 DEV fixture. They exceed old event-only
  measured distance for the specific observed traces.
- *R qualification:* independent R archival review of all five DEV sources
  is REVIEW_ONLY. A subsequent separate user-authorized, now-consumed
  **one-shot R engineering QUALIFICATION covers BASE_ON only**, exact
  pinned JAR/config/source/World/Action/STOP. See R #575 and the sealed
  verdict in R Draft #610; the S reviewer **never** issues that verdict.
- *Not admitted:* exact continuous within-tick distance, universal
  walking energy ledger for Minecraft, human/animal ecological rate,
  full net hunger/saturation response, full physical WAIT/P1 recovery,
  other four BASAL/WALK arm qualifications, 1-block hard movement cap,
  old/new V7 science, or a causal comparison. Identical tick-chord
  summaries cannot rule out different sub-tick paths or hidden turns.
- *Live / future:* the experimental Paper flag is still opt-in and the
  tick writer is S50-controlled-fixture specific. It is **not a validated
  general metering replacement** for arbitrary mobs, collisions, liquid,
  forced motion, combat, or indefinite runtime. Do not silently promote it
  to P1 Body fitness or world-model feedback.

Original source artifacts expire 2026-11-15; R's independent 90-day
original/verdict archive is the durable independent witness. No new
QUALIFICATION start or fresh SCIENCE grant is authorized by this section.
The 6-world-tick gate and frozen old V7 matched-path FAIL are not revised.

### S50/P1 WAIT same-World loaded-entity separation (DEV source, 2026-10-17)

`s50_p1_scope.review_scope` reads the original eight `S50_DEV_WAIT_SCOPE`,
`S50_DEV_WAIT_TICK` and all explicit `S50_DEV_WAIT_ENTITY` rows. The
sampled subject `PLAYER` UUID and its entity World UUID must remain identical
throughout the bracket; a different subject or World between callbacks now
fails closed, even if each per-tick SHA256 roster is internally consistent.
The reader distinguishes `other_loaded_entities_seen_ticks` (entities across
**all** loaded Paper Worlds) from `same_world_other_loaded_entities_seen_ticks`
and per-tick counts (only subjects in the **same entity World UUID** as Self).
A Strider in a different World or an End Crystal elsewhere is not an actor in
Self's World. The distinction is tested against digest-consistent cross-World
and subject-World-drift negative fixtures.

`same_world_only_self_at_all_samples=true` proves **only** the eight sampled
loaded-chunk rosters and **not** all World ticks, not unloaded chunks, and not
complete entity creation/removal or forced-movement provenance. In particular,
`full_tick_solo_no_agents=NOT_ATTESTED`, `held_motor_control_absence=
NOT_ATTESTED`, `wait_ticks_admitted=0` and `p1_fatigue_recovered=0` remain
non-negotiable. The current native Paper emitter, client-side clear-control
ACK and S50 Action OUTCOME do not span an independent whole-tick no-input/no-
action source. R must independently qualify any prospective broader source
before P1 can consume a `SourceBoundTick(WAIT)`. No new Minecraft run,
physiology change, JAR qualification, P1 grant or V science inference is made
by this offline reader update.

### Prospective S50/P1 Paper entity/chunk lifecycle callback ledger (DEV)

When the existing controlled S50 DEV mode enters its post-OUTCOME
`relaydevwait` source window, the **same** Paper plugin logs
`S50_DEV_WAIT_LIFECYCLE_BEGIN`, bounded
`S50_DEV_WAIT_LIFECYCLE_EVENT` and eight
`S50_DEV_WAIT_LIFECYCLE_SAMPLE` records. Event kinds:
`ENTITY_ADD`, `ENTITY_REMOVE`, `CHUNK_LOAD`, `CHUNK_UNLOAD`.
The entity callbacks come from Paper AddTo/RemoveFromWorld events, not just
creature spawn/death; removal uses the event's source World because the entity's
current World may already have changed. Every callback records the subject
World tick and **separately** its own entity World/tick/UUID/type/chunk identity.
Other dimensions may legitimately contain entities and events.

The new S reader `s50_p1_lifecycle.review_lifecycle` demands an exact
session-scoped begin, eight consecutive server sampling ticks, 1–256
sequential events with exact cumulative original counts, and a consistent
native entity/World identity. Missing, reordered, duplicated, foreign,
over-cap or asynchronous callback observations are rejected. A transient
same-World Mob add/remove is not silently erased by equal start/end
rosters. The existing DEV physical runner attaches this source-only
receipt to the WAIT candidate when it uses a newly compiled plugin.
Historical archives without these new prospective rows remain unchanged
and cannot acquire this claim after the fact.

**Proof limit:** Events are observed from the `relaydevwait` begin
through each scheduler callback; the 8th sampling callback immediately ends
collection. Other Paper event families, unobserved packets, unloaded data,
possible late events in the 8th tick, Mineflayer held controls and every
source of concurrent physical Action remain `NOT_ATTESTED`. This is
`S_P1_PAPER_CALLBACK_PREFIX_SCREEN_ONLY`, **not**
`SourceBoundTick(WAIT)` or P1 fatigue recovery. Even if there are zero
same-World entity callbacks, `wait_ticks_admitted=0`,
`p1_fatigue_recovered=0`, `science_go=false`. R must independently
audit the exact prospective JAR/config, original event scope and source
coverage before any engineering qualifier; V science stays separate.

### Prospective S50/P1 S15/S16 Action and commanded-control source cross-check

The existing S-owned controlled S50 Paper DEV route, when `--v7-p1-wait-evidence-dev`
is explicitly selected, now also verifies after the owned Node shutdown and
source capture:

- Exact one S15/S16 source Action `issued → outcome` in
  `s50_action_original.jsonl` (the journal has **synthetic logical order**,
  never a server World clock).
- One session-scoped, strictly sequential native `look → set_control(forward)
  → clear_controls` effect and applied ACK each; an independently matched
  after-probe and STOP ACK in `original_native.jsonl`, plus the original
  `owner_commands.jsonl` command stream. Extra/unknown effects fail closed.
- Paper `PRE_FORWARD → POST_FORWARD → PRE_CLEAR → POST_CLEAR` brackets,
  then `WAIT_BEGIN`, then eight ordered source tick samples in the same
  action/session marker and Paper World. Paper bracket ordering is proven;
  no client-to-server clock conversion is inferred.

The bounded S reader `s50_p1_control_action.review_control_action` records
`native_commanded_control_after_clear=CLEARED_BY_APPLIED_COMMAND_ACK` **only**.
The Mineflayer bridge has not independently exposed `getControlState()`
for all controls. Therefore `native_held_controls_readback=NOT_ATTESTED`,
`all_other_action_issuers_absent=NOT_ATTESTED`, and
`client_server_effective_tick_mapping=NOT_ATTESTED`. This S50 fixture proves
only its own supervised issued/outcome pair and three observed client commands;
it cannot prove no other owner issued an Action elsewhere. There is no physical
WAIT admission, Body fatigue recovery, new primitive, World launch, R transfer
or V science evidence from this source-only cross-check. Prospective native
held-control readback is a separate adapter/protocol owner change, and must
not be fabricated from a successful clear ACK.

### S50/P1 direct Mineflayer getControlState DEV sidecar

For explicit `--v7-p1-wait-evidence-dev` ONLY, S launches its own
`s50_p1_readback_bridge.mjs` process wrapper instead of modifying the
shared `bridge.mjs` or Python/Node production protocol. The wrapper imports
the **unchanged** standard bridge and reads `bot.getControlState()`
for all seven native controls (`forward/back/left/right/jump/sprint/sneak`).
A private fresh `s50_p1_native_controls_original.jsonl` sidecar is
written synchronously by Node, with the bridge session/seq on
`effect_result`, probe observations, and STOP ACK. It also samples all
seven controls on Mineflayer client `physicsTick` callbacks and has an
8192-record overflow boundary. No `setControlState` or
`clearControlStates` implementation is replaced.

The S-only subprocess uses a child-local environment variable for its
exclusive original sidecar; no process-global environment mutation or
new physical action issuer. After STOP, the S runner reads and SHA256-indexes
the original alongside `owner_commands.jsonl`, `original_native.jsonl`,
`s50_action_original.jsonl`, and the Paper source log.
`review_native_controls` requires direct forward=true after its
source ACK, all seven controls false after the clear ACK and after
the correlated source probe, a subsequent client physics tick showing
all controls false, no later recorded reactivation, and an original STOP.
Missing/malformed/extra/foreign/duplicate/unbounded readbacks fail closed.
The report records these **sampled client states only** under
`s50_p1_native_controls_source`.

**Not a shared clock:** Client `physicsTick` has no established 1:1
mapping to Paper `world_full_time`; a direct `getControlState`
readback does NOT show that input release was effective on the server
at any particular World tick. Nor does it prove physical stillness
between sampled callbacks, unseen packet states, or all Action issuer
registries. `paper_effective_input_release_tick=NOT_ATTESTED`,
`continuous_held_controls_absence=NOT_ATTESTED`,
`all_S15_S16_issuers_absent=NOT_ATTESTED`,
`wait_ticks_admitted=0`, `p1_fatigue_recovered=0`,
`science_go=false`. This is a new DEV source profile requiring
prospective standalone physical test and independent R inspection
before P1 can consider a source-bound physical WAIT interval.

### S50/P1 FLAT seed63101 source DEV (new isolated copy only)

The existing V7 S50→P1 eight-tick evidence collector supports an **explicitly
separate** `--s50-p1-flat-archive <absolute-directory>` input only when ALL
of these are set together:

`--v7-arm BASE_ON --v7-seed 63101 --v7-controlled-calibration-dev
--v7-server-clock-calibration-dev --v7-tick-meter-dev
--v7-p1-wait-evidence-dev`.

Unlike the existing V7 natural seed roster, 63101 is accepted **only** for
this direct held-control DEV source mode. It cannot silently participate in
V7 paired natural conditions or scientific comparisons. The archive must
be the recorded stopped FLAT original from S source
`38989215391` (containing `flat-source/server/world/`,
`flat-source/paper_console.log`,
`flat-source/flat_dev_receipt.json`). The S preflight independently checks
the full stopped-World index, pinned original `level.dat` SHA, original
Paper 25/25 ground+air native markers, receipt, source properties and no
symlinks/overlapping output roots. The original World must remain unmodified;
only an exact byte-for-byte copy may be launched. This is *not* a new
independent World UUID; an original copied World retaining its UUID is
expected. Paper loads `level-name=world`, not the default S31A world. The
controlled Self body pose remains `0.5,-60,0.5` as attested by native
Paper and Mineflayer observations.

After STOP and child cleanup, the runner verifies the frozen source's
unchanged byte index and (in the new prospective runner) preserves every
present Paper dimension at `saved_flat_dimensions_original/{world,world_nether,
world_the_end}/` with independent source/copy SHA256 indices and explicitly
records absent dimensions. The historical first FLAT P1 run preserved only
17 Overworld files; its missing Nether/End bytes are NOT retroactively filled.
The runner also retains
`s50_p1_native_controls_original.jsonl`, original native bridge bytes,
formal S50 Action transitions, Paper lifecycle + eight candidate WAIT tick
samples, plugin/config digests and source identity. The runner may reject a
physical run even if MOVE progressed, if source coverage or control
readback is incomplete. It never retroactively changes original archives
or upgrades DEV results to R QUALIFICATION or V SCIENCE.

**Prospective native→Paper LOOK evidence (S-owned, FLAT only):** The
opt-in `s50_p1_readback_bridge.mjs` now writes
`client_yaw_radians` / `client_pitch_radians` directly from the
Mineflayer entity at its actual native ACK and callback source rows.
`s50_p1_native_pose.py` reads the original sidecar after the existing
LOOK ACK and refuses to proceed if the client yaw/pitch do not match
the governed target. Only then does `s50_p1_flat_look.py` verify
the independently observed Paper yaw, before `PRE_FORWARD` and the
original governed FORWARD. `s50_p1_flat_look_bracket.py` separately
checks the saved Paper log phase order. The runner rereads the native
LOOK sidecar on the success path and compares the immutable ACK
identity and pose, not the naturally growing row count.

The **client yaw is in radians**; the Paper yaw in its snapshot is
**degrees**. Matching both snapshots is evidence at two different
observation points, not proof of a common clock, teleport completion,
uninterrupted orientation, all issuers absent, or whole-tick WAIT.
Native pose is added to **future** S50/P1 FLAT DEV originals only.
The older first-run sidecar has no such readback, is never modified,
and remains BLOCKED. There is no new Action issuer or physics ledger.

The **first** explicit FLAT P1 LocalCodex run completed as
`DEV_ONLY / BLOCKED / R_PENDING / WAIT_NOT_ATTESTED`, rather than a
successful MOVE. S execution HEAD `4ba9846`, final report `07ce089`,
frozen bundle SHA `8f372041c08f5743f3e0c936fd045c112f4d3b6e48f6eb6444c8d8cccd3f27a7`.
Existing native-client `physicsTick` remains distinct from Paper World tick.
The prospective post-STOP all-dimension capture and look readback gate
require **new isolated DEV evidence** before any claim about their live
behavior. Historical report and archive stay immutable. Still
`wait_ticks_admitted=0`, `p1_fatigue_recovered=0`, production NO_GO.

