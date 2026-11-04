# Bug-0 Paper source correction — DEV

The first original Paper World (#41835442063) stopped before ATTACK
(0 issued Actions) because source monitoring started before operator-only
`time set night`. World full time jumped, which was correctly rejected
by the consecutive-tick guard but was not an actual missing scheduler
callback. The original Paper log, S49 FAIL report and SHA256 manifest
were retained as artifact #13325421416.

Changes on this child Draft:
- Native read-only plugin timestamps by `Bukkit.getCurrentTick()`,
  not modifiable `World.getFullTime()`.
- ATTACK authorization and server-side pre-attack Health check complete
  **before** the source is started by a hook on the original S49 owner;
  the original one-shot ATTACK issuer and supervisor are unchanged.
- REST observation is then marked on the same Paper/server-source clock.
- Pre-World source faults still fail closed; no automatic replay or
  unqualified P1 recovery admission.

This exact commit authorizes one new disposable DEV attempt, without
reusing the previous source or claiming a scientific/qualification pass.
P1 is still a virtual model evaluated on candidate Paper callback-tick
activity; it is not a Minecraft-native Fatigue sensor. Source coverage
is explicitly not independently certified whole-tick inactivity.
