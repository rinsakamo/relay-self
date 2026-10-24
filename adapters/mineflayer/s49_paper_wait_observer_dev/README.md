# RelaySelf S49 Paper WAIT observer — isolated DEV source producer

**Status: SOURCE_STAGED / DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.**
This is source code only. The Java 21 / Paper 1.21.8 plugin has **not**
been built, loaded, or exercised in a real World by this DEV step.

This is an independent Paper plugin, not a patch to the protected
`RelayMetabolismPlugin`, `normal_action.py`, or S49 `qualify()` runner.

### Claimed S16 closure → Paper callback correlation

The plug-in is disabled by default. Only a primary-thread server console
operator can call `/relays49observe <action_id> <session_id> <player_uuid>`
after the operator has separately observed a closed S49
`NormalActionClosedReadback`. The action and session strings are **not**
independently authenticated by Paper; this command is a claim, **not a
handshake**. The player UUID and configured expected name merely select the
observed local Minecraft player, not the S49 session/owner identity.

A single command is consumed once per plugin lifetime. With a valid online,
living player, Paper logs an `S49_OBSERVER_SUBJECT` context row, an
`S49_DEV_BACK_WAIT_BEGIN` row, and then at most eight
`S49_DEV_BACK_WAIT_TICK` rows (indexes 1–8) from **sync Paper callbacks**.
Each row includes the asserted `marker_id=action_id-session_id`,
`action_id`, `session_id`, World UUID and `World.getFullTime()` value.
Any tick gap, disconnect, World switch, plugin shutdown or callback error
aborts the candidate with `S49_DEV_BACK_WAIT_ABORT`. No restart, partial
seal, automatic retry, command dispatch or World mutation is allowed.
Other mobs/entities are not a reason to reject the Self's physical rest.

The existing Python `s49_paper_backward_wait_dev.py` offline reviewer can
parse the BEGIN + eight-TICK rows. Context and provenance still require an
independent review. It does **not** prove native command release takes effect
before the first tick, full-tick inactivity, no other issuers, or R original
custody; neither record is a P1 recovery witness.

### Build gate (not performed in this source-only step)

A future **authorized isolated DEV environment** may run
`mvn -f adapters/mineflayer/s49_paper_wait_observer_dev/pom.xml verify`
using Java 21 and Paper API 1.21.8, with explicit source/JAR hashes recorded.
Installation into any real World, command execution, or integration with
the protected S49 process requires a separately governed run. No Java or
Minecraft is started by the Python-only source-contract checks.
