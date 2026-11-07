# D7-F R3: true vanilla zombie natural food after S49 ATTACK/MOVE/STOP/S51 EAT — DEV PASS

## Evidence

- Run: https://github.com/rinsakamo/relay-self/actions/runs/42387610107 — SUCCESS including independent post-audit.
- Exact source parent: 9ce4a22108422d4f8b156e7104a926355b006e2c; offline CI: https://github.com/rinsakamo/relay-self/actions/runs/42387209093 (SUCCESS).
- Single-use physical trigger: 6b576e3cf7de4957640d810a179348ecb39c8912. No old R1/R2 physical Action replay.
- Original artifact: https://github.com/rinsakamo/relay-self/actions/runs/42387610107/artifacts/13579984650. SHA256SUMS.txt independently read back: 8/8 exact source/derivative files match.
- One disposable Paper 1.21.8 World, one Mineflayer 4.39 bot, one original S49 ActionSupervisor/Intent/session.

## Physical events — all from the same World

- Actual World UUID a0b7b62d-b9ba-41ef-96cf-26805dec586d; original managed zombie UUID c5004dad-38e7-450c-9755-f25ba8e251ab.
- Paper natural witness READY: d7f_managed_world_witness=true. Scope restricted to online RelaySelf current World and tagged DEV target, unlike the earlier unrelated World event in failed R2.
- Original S49 issued one real ATTACK; S16 OUTCOME; Paper EntityDeath tick 524 independently attests killer_is_relay_self=true.
- Unmodified vanilla doMobLoot natural ItemSpawn tick 524, rotten flesh **2 items** in one actual Paper Item UUID 7fc60a44-37f4-4de4-a622-871d8238ad4a.
- Same original S49 issued one direction-qualified MOVE_BACKWARD, 0.6269065734210615m, native clear seq 132, S16 OUTCOME, preserved original C1 physical pre-ISSUE journal.
- Same Paper ItemPickupEvent, same original item UUID, tick 568, owned player UUID dcae346d-e66f-331a-b459-a5a5370e9738; native inventory rotten_flesh=2.
- Current-world original S49 owner STOP readout: same S49 MOVE/S15 clear and S50 same-client 7-input OFF after clear for 22 physics ticks. Paper main-thread **17 consecutive last quiet ticks**, live readback through tick 589 (pickup tick 568). This is DEV body-quiet evidence, not direct server-effective S49 clear causality.
- Original S49 L0 food decision admitted once from fresh native probes and actual vanilla hunger effect. Same original S49 emitted EAT once, delegated to existing S51 equip_item + consume_held with physical pre-ISSUE persistent nonmotion record.
- Native Food 11.0 -> 15.0 and native rotten_flesh 2 -> 1. EAT S16 OUTCOME, no unresolved physical Action. Original S49 total physical Actions 3 = ATTACK1 + MOVE1 + EAT1.
- Original nonmotion physical ledger: ATTACK + EAT (both S16_OUTCOME), SHA256 506c9a8d89052a3d93a33a6b81a9dcfe9744592c19f06780293cfcb70ed77254; original MOVE physical ledger: 1 S16_OUTCOME SHA256 c2d8fb6759eb8b90ea60a8906206ad0a0d145f5bbe458708277071d55e29dd60.
- Independent audit file: d7f_independent_natural_food_audit.json; classification D7_F_ONE_REAL_NATURAL_ZOMBIE_ATTACK_MOVE_STOP_S51_EAT / status PASS_DEV.
- Paper World-controlled zombie respawn from death tick 524 to next-generation tick 1124 = exactly 600 ticks, fresh zombie UUID. Node exit0, Java exit0, cleanup PASS.

## Claim boundary

- This **is the first verified DEV one-cycle with real natural zombie-sourced food**, not an operator-created item. The operator still staged the *zombie* (NoAI/low HP) and applied normal vanilla hunger effect before attack: therefore not an entirely autonomous fight or spontaneous self-sustenance.
- No separate alternate S49 issuer and no L0 authority expansion; source-bound engineering DEV STOP/food admission retains strict fresh native hazard checks. The exact server-effective original S15 clear tick remains NOT_CAUSALLY_ATTESTED.
- This has **one** original natural-food cycle and **one** World next-generation respawn, but the next-generation zombie has NOT yet been attacked/picked/eaten in the same session. Full two-cycle survival, unrestricted long-run, learning, QUAL and SCIENCE remain unproven.
- Classification: DEV_ONLY / D7_F_ONE_NATURAL_FOOD_CYCLE_PASS / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
