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
- death
- respawn
- connection end
- adapter/command errors

Each ordinary observation carries a bounded survival snapshot:

- health, food, oxygen level, and position;
- time-of-day/day/is-day when Mineflayer has received server time;
- inventory item name/count/slot facts;
- up to 16 nearest entity facts within 16 blocks: id, name, Mineflayer type,
  distance, and position.

Entity facts deliberately contain no `hostile`, `danger`, `fear`, or
equivalent appraisal label. Those are Self-side interpretations, not target
facts.

Current outbound primitive effects:

- set_control
- clear_controls
- equip_item
- consume_held

Item selection and consumption are separate primitive effects. The adapter does
not choose which food is desirable, combine the pair into EAT success, or infer
Skill completion.

Duration, destination choice, Skill success, threat appraisal, pathfinding,
and higher-level policy are deliberately not encoded in the adapter.

The bridge uses offline Minecraft authentication only for this controlled MVP
slice. Microsoft-account authentication is deferred.

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
- exposes explicit set_control / clear_controls / equip_item / consume_held send operations;
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

Shutdown:

    {"type":"shutdown"}

An applied control-state result means that Mineflayer accepted/applied that
primitive control operation. It does **not** mean the bot reached a destination
or that a Skill succeeded. Movement/consequence observations remain separate.
