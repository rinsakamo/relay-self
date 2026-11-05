# R1 native-witness follow-up: unique second disposable Paper World

Only this document is changed in trigger commit.
Unique commit message: `run-bug0-zombie-r1-native-witness-once-20261105`.

Original first R1 physical World [#42051052687](https://github.com/rinsakamo/relay-self/actions/runs/42051052687) is **FAIL** and never replayed. Its real Paper initial spawn tick35 was observed; the very first Mineflayer zombie probe did not qualify. Original independent read-only audit [#42051530649](https://github.com/rinsakamo/relay-self/actions/runs/42051530649), artifact #13427326461, sha256 63ff6af41e25100e825c6223cd2db37385407f1c968a38d7bcb0e96710577a94 are retained.

New preflight at exact source HEAD `3239db3610985caa4edf4aec0b33ce8fee66e515` is [#42052129379 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/42052129379).
It adds only bounded 10 new read-only native probes and a negative test; no changed World-owned 600tick physical rule or additional S49 issue surface.

Authorize exactly ONE new disposable Paper 1.21.8 World using pinned server/plugin/node sources:
- generate initial real Paper-managed AI zombie;
- operator-only kill **not S49 ATTACK**;
- confirm real EntityDeathEvent, due_tick, and >=600 observed actual server ticks;
- observe genuinely new Paper and native entity in same World/session;
- ensure Java/Node cleanup and SHA256 original evidence.

If any source check fails, stop without automatic retries. World truth not fed to Self. This is not PICKUP/EAT/learning/endless survival.

`DEV_ONLY / R1_NEW_WORLD_ONCE / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
