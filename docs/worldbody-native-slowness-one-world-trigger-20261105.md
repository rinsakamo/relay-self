# WorldBody v1: second independent DEV World, native Slowness V correction

This is an **explicit one-time, new World trial**, not replay or retry
of the original failed Paper World #41999248107.

Prior original World (exact execution HEAD
e7e2965d3600d8f06e3b91d691cdc8a7943da6b5) completed
WAIT/MOVE/MOVE and both S16 MOVEs at 0.6269065734210617 m. The
server-only walk speed changed to 0.08, but the native Mineflayer
movement was unaffected. It was classified FAIL; original raw
Paper/S16 evidence preserved under artifact #13401363197.

The frozen fixed WorldBody internal laws are **unchanged**:
- MOVE_FATIGUE_PER_METRE=2.0
- STILL_RECOVERY_PER_SERVER_TICK=0.003
- SLOW_AT=0.25
- NORMAL_AGAIN_AT=0.05

The authoritative Paper server now also applies genuine vanilla
Slowness V (amplifier 4, 12000 ticks) when WorldBody enters the
degraded state and removes it when it recovers. This is part of the
World's physical constraints, not a Self-selected fatigue coefficient,
sensor, or authority. Rates and mechanics are compiled into server
code and cannot be written by Self.

The independent second trial is allowed ONLY on this one exact
commit-message trigger; the first trial must remain unchanged:
`run-worldbody-fixed-native-slowness-once-20261105`.

Before creating the disposable World:
- offline CI at HEAD 9165d7466ddfd009c86edbe9f0fca997d91e97fc
  was SUCCESS;
- pinned Paper 1.21.8 STABLE #60 SHA verified;
- isolated physical plugin compiled from exact same HEAD and SHA recorded;
- S49 sole original issuer unchanged, no Action retries, no L2;
- explicit WorldBody mode and opt-in, no competing DEV lane mode.

Success must be contingent on **actual** second original native S16
movement distance shrinking below 0.8 times first; native L0 must
choose REST from direct SelfBody S16/Present, not the server's
private fatigue number, and zero new Action after REST. The private
Paper operator-only log must also show native Slowness V applied and
later removed by fixed recovery, with actual server walk speed
restored. If the client does not physically slow, the trial is FAIL
even if the Paper potion log says Slowness V is active.

Source original paper.log, S49 World report, post-audit and SHA256
manifest preserved even on failure. No automatic rerun/cleanup bypass.
DEV_ONLY; QUALIFICATION_NO_GO; SCIENCE_NOT_RUN. No learning or
feeling/emotion compression; no physiology claims.
