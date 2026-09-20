# RelaySelf Mineflayer MVP adapter

This directory is the first concrete target-local Minecraft adapter for RelaySelf.

It is intentionally **not** a generic Self/World protocol. The JSONL shapes here are
Mineflayer-specific implementation details and may change with this adapter.

## Qualified implementation surface

The first slice is based on the Mineflayer API inspected at:

- package: mineflayer 4.39.0
- upstream master observed at: 2084d0e6e0224fac30ba55d9cae7cfcd17cc9d65
- Node requirement: >=22
- adapter dependency pin: exactly 4.39.0

The older 91204b2a034f0663b39814771e236bcb7c8f26c8 revision used by
synthetic RelaySelf experiments remains historical experiment evidence rather
than product execution authority.

## Scope

Current inbound observations:

- spawn
- health
- time, emitted only on first valid sync, day-number change, or day/night phase change
- inventory
- entities
- move
- forcedMove
- explicit `probe` snapshots requested by the target-local `observe` command
- death
- respawn
- connection end
- adapter/command errors

Each ordinary observation carries a bounded survival snapshot:

- health, food, food saturation, oxygen level, and position;
- time-of-day/day/is-day when Mineflayer has received server time;
- inventory item name/count/slot facts;
- up to 16 nearest entity facts within 16 blocks: id, name, Mineflayer type,
  distance, and position;
- explicit bounded-sensor coverage for that entity projection:
  `source_scope=mineflayer_entity_registry`, fixed `max_distance=16`,
  fixed `max_entities=16`, the number of in-radius candidates before the cap,
  and whether the returned list was truncated. The Python boundary rejects
  changed distance/entity bounds instead of accepting a per-run sensor scope.

An empty or short `nearby_entities` list therefore does not silently imply
unbounded World coverage. The coverage metadata says what Mineflayer source
surface and bounds were actually projected. A consumer must preserve the
difference between “no entity in this bounded projection” and “no entity exists
in the World.”

Entity facts deliberately contain no `hostile`, `danger`, `fear`, or
equivalent appraisal label. Those are Self-side interpretations, not target
facts.

Current outbound primitive effects:

- set_control
- clear_controls
- equip_item
- consume_held
- look

The adapter also accepts the non-Action target-local command `observe`, which
emits one current `probe` observation. It exists for explicit evidence
sampling/qualification and does not issue a World effect, authorize an Action,
or imply a decision epoch. Probe observations remain outside automatic
high-level epoch admission.

Item selection and consumption are separate primitive effects. The adapter does
not choose which food is desirable, combine the pair into EAT success, or infer
Skill completion.

`look(yaw, pitch)` is only a target-local heading primitive, using Mineflayer's
documented radian convention. The mechanical mapping from a target position to
that Mineflayer yaw is likewise adapter-owned
(`mineflayer_yaw_to_target` on the Python adapter surface); Skill/controller
code must not encode Mineflayer's x/z axis or yaw convention itself. An applied
look result means Mineflayer completed the orientation request. It does not
mean movement occurred, a destination was reached, or FLEE succeeded.

Current controlled experiments still pass target-native `MineflayerObservation`
objects directly through their Minecraft-specific vertical slice. That is an
experiment-local dependency, not the intended production Self boundary. Before
production integration, Minecraft evidence should cross a
**Mineflayer-specific Present projection** that translates target-native
observation/coverage facts into the existing RelaySelf Present/Situation
surface. Do not infer a generic cross-World Observation API from this one
adapter; #231 owns the cross-World substitution test for any later shared
extraction.

Duration, destination choice, Skill success, threat appraisal, pathfinding,
and higher-level policy are deliberately not encoded in the adapter.

The bridge uses offline Minecraft authentication only for this controlled MVP
slice. Microsoft-account authentication is deferred.

Mineflayer creates `bot.inventory` during its internal plugin-injection phase,
not synchronously at the initial `createBot()` return boundary. The adapter
therefore attaches its inventory `updateSlot` listener only after Mineflayer's
`inject_allowed` event. This is startup ordering only; inventory observations
still come from Mineflayer's player inventory surface and are emitted only after
the bot has spawned.

Mineflayer 4.39.0 also emits its first `spawn` event from the initial
`update_health` packet before the same packet's ordinary health listener assigns
`bot.health` and `bot.food`. The bridge therefore records spawn as pending and
emits the first RelaySelf `spawn` observation on the following Mineflayer
`health` event, after health/food are initialized.

On Minecraft 26.1, `bot.oxygenLevel` is initialized separately only when
Mineflayer receives player entity metadata containing `air_supply`. Vanilla
startup may not provide that metadata before ordinary play begins. RelaySelf
therefore represents oxygen as `null` until Mineflayer has actually reported a
finite value rather than fabricating a default or blocking spawn indefinitely.
Once observed, snapshots carry the finite oxygen value. Invalid non-null oxygen
values still fail closed.

## Transport

The adapter reserves stdout for one JSON object per line. Diagnostics go to
stderr. stdin accepts one JSON command per line.

Every outbound JSON object carries:

- session_id: unique to one Node bridge process
- seq: monotonic integer beginning at 0

The Python decoder converts session_id:seq into a RelaySelf Provenance pointer.
That pointer records source/reference only; it does not make Mineflayer
infallible or promote a message directly into belief, Action success, or World
truth.

The first message must be adapter_started with seq 0. Sequence gaps, session
changes, unknown fields, unsupported message types, and version mismatch fail
closed.


## Decision-epoch admission

The adapter-local Python runtime seam admits only the first message classes that
have a concrete reason to wake high-level Self coordination:

- effect_result: always material because it closes one supervised primitive Action
- spawn / health / filtered time transition / inventory / entities / forcedMove / death / respawn:
  material body/session/survival observations
- move: not automatically admitted because it is a high-frequency controller signal

An admitted message enters the existing RelaySelf decision-epoch coordinator;
the adapter does not implement a second runtime loop.

For an effect_result, the matching Action is first closed as OUTCOME using the
message provenance. Both applied and rejected are known target results:

    effect_result(applied | rejected)
      -> Action OUTCOME
      != Skill success/failure

Caller-owned deterministic or Present/reprojection work runs after ordinary
Action supervision. Only an unresolved result from that work may request the
supplied RelayEngine seam.

Adapter-startup messages and ordinary move events remain outside this high-level
decision path by default. Future concrete Skill controllers may consume movement
feedback locally without turning every movement update into model cognition.


## Process ownership

The Python side can now own exactly one Node bridge process through an
adapter-local asynchronous process session.

The process session:

- launches bridge.mjs with explicit host/port/username/version arguments;
- inherits stderr for diagnostics while reserving stdout for JSONL;
- requires adapter_started as the first decoded message;
- exposes explicit set_control / clear_controls / equip_item / consume_held / look send operations plus a non-Action observe probe;
- decodes one stdout message at a time through the same strict stream decoder;
- treats unexpected stdout EOF as an explicit process error;
- performs no automatic reconnect, retry, replay, or replacement launch;
- supports one clean shutdown request with a bounded terminate fallback.

This is process lifecycle only. It does not create a runtime Scheduler, classify
Minecraft meaning, authorize Actions, or decide when a Skill has succeeded.

## Install

From this directory:

    npm install --omit=dev

The package manifest pins Mineflayer exactly. A later live qualification should
record the actual Node version and npm-resolved dependency tree used for that
run.


## Live qualification transaction

The repository includes a reusable external-qualification harness that uses the
same process session, adapter protocol, Action lifecycle, ActionSupervisor, and
Mineflayer runtime-admission path as the MVP.

It requires a real local/offline Minecraft server and does not run in CI.

Prepare the adapter dependency from the repository root:

    cd adapters/mineflayer
    npm install --omit=dev
    cd ../..

Start an offline/local Minecraft server with a spawn area where the bot can move
forward safely, then run the source-checkout launcher:

    bash adapters/mineflayer/run_live_qualification.sh \
      --host 127.0.0.1 \
      --port 25565 \
      --username RelaySelf

The launcher derives the repository root from its own path, owns the `src/`
Python import path, changes to the repository root for the top-level
`adapters` namespace, and then executes the canonical Python module with
bytecode disabled. No operator-side `PYTHONPATH` setup is required.

Add `--version <minecraft-version>` when the server protocol should be pinned.

The transaction qualifies only when all of the following are observed in one
actual session:

    spawn observation with body/resource facts
      -> supervised forward Action ISSUED
      -> set_control(forward=true)
      -> Mineflayer effect_result(applied)
      -> Action OUTCOME
      -> post-ack horizontal position delta >= 0.05 blocks
      -> separately supervised clear_controls Action
      -> Mineflayer effect_result(applied)
      -> second Action OUTCOME

The harness prints one JSON report only after these conditions hold. An
`applied` control acknowledgement without observed movement is not a pass.

The report is external/physical qualification evidence for the exact recorded
repository revision, Node/Mineflayer install, server version/configuration, and
host conditions. It is not automatically portable evidence for later revisions
or different Minecraft servers.

The qualification transaction deliberately does not mark the associated Skill
successful, release Current Intent, infer threat, choose food, or write durable
Memory.

## Run against a local/offline server

Example:

    node bridge.mjs --host 127.0.0.1 --port 25565 --username RelaySelf

Optionally pin the Minecraft protocol version:

    node bridge.mjs --host 127.0.0.1 --port 25565 --username RelaySelf --version 1.21.8

The bridge does not reconnect or retry automatically.

## Example commands

Enable forward control:

    {"type":"effect","action_id":"action-forward-on","effect":"set_control","control":"forward","state":true}

Clear all movement controls:

    {"type":"effect","action_id":"action-stop","effect":"clear_controls"}

Change heading without destination semantics:

    {"type":"effect","action_id":"action-look","effect":"look","yaw":1.5707963267948966,"pitch":0}

Shutdown:

    {"type":"shutdown"}

An applied control-state result means that Mineflayer accepted/applied that
primitive control operation. It does **not** mean the bot reached a destination
or that a Skill succeeded. Movement/consequence observations remain separate.
