# Fresh corrected DEV World: source STOP-after-quit fix

Previous exact HEAD: 71339382d0d9cfc04595f23c1f2312681d76a94d
Original failed run #42032607432 remains immutable: physical S49 Action2
and WorldBody physical post succeeded; same-World source join rejected
the missing S49P1_STOP (console processing occurred after native quit).

Corrections: collector accepts console-only STOP after native disconnect
for the same already-armed nonce and no open action; S49 waits 0.75 sec
for source STOP before native cleanup. Both are source-only changes.

This is a DISTINCT one-use disposable World, not rerun of consumed #738
or #42032607432. Same original S49 owner, same old fixed WorldBody law.
Only DEV source join is tested: no original P1 real physics installation,
no independent R full WAIT witness, no SCIENCE or learning.
Do not retry this specific run ID. Artifact originals and FAIL preserved.
