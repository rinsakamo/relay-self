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
- move
- forcedMove
- death
- respawn
- connection end
- adapter/command errors

Each ordinary observation carries the current Mineflayer health, food,
oxygenLevel, and bot position.

Current outbound primitive effects:

- set_control
- clear_controls

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
