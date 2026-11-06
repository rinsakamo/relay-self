# D2 corrected World trial after immutable real zero-loot original

Initial one-World original [#42188953900](https://github.com/rinsakamo/relay-self/actions/runs/42188953900) remains **FAIL as a source-complete D2 pickup** (not retried). Paper original entity death at tick36; genuine vanilla rotten_flesh drop count **0**, Paper due tick636, no item spawn or pickup, source runner stopped before respawn. Original artifact #13488448680 SHA zip `12de90dbb0fadd33516089b8f15aedcaaf07761bf557b30c6437cd044de2ed87`; independent [read-only audit #42189178634](https://github.com/rinsakamo/relay-self/actions/runs/42189178634) verified SHA manifest. Node/Java exit0, Self Action0.

This child repairs the *behavioral test loop*: **genuine zero-loot is a valid World outcome**, not an excuse to place food or restart. At zero, retain native inventory count0, wait the **original fixed 600 server ticks** in the same World, verify new Paper and native zombie generation, then close with `D2_REAL_ZERO_VANILLA_ROTTEN_FLESH_WITH_600TICK_RESPAWN_PASS` **without pickup success**. At nonzero (1..2), require actual vanilla ItemSpawn/Paper ItemPickup and matching native count gain plus respawn, as before. Tests separately reject fake positive claims for zero, modified timer, and wrong new entity ID.

No source amendment to original #745 respawn physics, original D1 inventory readback, or S49 Action issuer. A later one-use DEV World may run this source after exact CI; a second new World is not a retry of the failed prior World and preserves it as a separate result. No Self ATTACK/MOVE/PICKUP/EAT or endless survival claim.

`DEV_ONLY / WORLD_NOT_RUN_CHILD / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
