# Bug-0 D2 — Real zombie death loot provenance (source-only)

Unified v0.5 #717; Bug-0 survival #742; exact R1 respawn parent #745
and exact D1 pickup parent #747.

- D1 establishes **operator-staged** pickup Paper EntityPickupItemEvent and
  native Mineflayer rotten_flesh inventory +1, not natural loot.
- D2 adds a **new, independently disabled-by-default Paper plugin with no
  commands**. It listens to genuine Zombie EntityDeathEvent and records the
  unmodified `event.getDrops()` rotten_flesh count. It then records a matching
  nearby actual ItemSpawnEvent (same world and <=3 ticks after that death),
  UUID and Player EntityPickupItemEvent if the item is fully collected.
  This does not mutate loot rates, spawn timers, health or physical fatigue.
- The original **separate** #745 zombie respawn plugin still owns one live
  zombie and schedules death tick +600 source ticks. Independent original
  server death UUID/time must match drop witness zombie UUID and time.
  Actual Item entity generation and item pickup IDs must match in the same
  source event chain; observations are operator-only until an independent
  native inventory snapshot shows a corresponding rotten-flesh gain.
- D2 first World grants **operator-controlled** position and kill to connect
  server death->natural loot->pickup. This is explicitly NOT Self-attacked or
  Self-directed MOVE/PICKUP Skill. No replay of any original failed attempt.
- Ordinary drops are random (may be 0), and failed/no-drop Worlds remain
  evidentiary FAIL/NO_LOOT. No guaranteed loot and no forced item spawn.
- Later D3 must replace operator kill with repeated original S49-authorized
  ATTACK and solve lethal-attack target disappearance without manufacturing
  a normal Action outcome. D4 adds genuine S49 MOVE-based loot approach,
  repeated S51 EAT with source-qualified post-motion settling, and the
  next generation for >=2 cycles. All require unique isolated DEV gates.
- No fake learned or qualified autonomous survival. World/WorldBody true
  fatigue/recovery coefficients remain private and immutable.

`DEV_ONLY / D2_OFFLINE_PENDING / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
