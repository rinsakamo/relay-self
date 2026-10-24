# RelaySelf S49 Paper WAIT observer — isolated DEV source producer

**Status: JAVA_21_COMPILE_VERIFIED_DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.**
The isolated Java 21 / Paper API 1.21.8 plugin was built and its packaged
class, plugin.yml and default-disabled config.yml inspected in a compile-only
GitHub Actions runner. It has **not** been loaded, run, or tested in a real World.

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

### Java 21 compile result (not real Paper execution)

The isolated build at [GitHub Actions #40100070963](https://github.com/rinsakamo/relay-self/actions/runs/40100070963)
completed successfully for commit `efc6d70ca8fbcb578a15bab0901b58ef88329a7a`.
The packaged DEV JAR measured 6,501 bytes with SHA-256
`987ecc19d3ea999a6186c807d4ca5a51897a3b7ef5446cb736261d3354ed64ea`
for that specific build. The compiled JAR is available as a short-retention
GitHub Actions artifact. Do not treat the artifact ZIP SHA as the JAR SHA.

The workflow compiles only this standalone observer using Java 21, audits the
JAR entries, ensures protected S49/P1 source blob identities, and does not
launch Paper, Minecraft, Mineflayer or any physical World. Installation,
console command execution, native S49 Action integration, or independent R
source qualification is **not approved or evidenced by this build**.
