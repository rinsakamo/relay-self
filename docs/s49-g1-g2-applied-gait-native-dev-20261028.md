# RelaySelf — G1 original-Paper gait observation / G2 initial sprint calibration

2026-10-28 (JST). **DEV_ONLY / SAME_WORLD_G1_OBSERVED / G2_ORDINARY_VS_SPRINT_CANDIDATE / NATIVE_FULL_TICK_GAIT_UNVERIFIED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**

## Frozen real-run evidence and custody

- Base L1/S49/T2 physical integration: [#40705499396](https://github.com/rinsakamo/relay-self/actions/runs/40705499396), 2 Paper Worlds PASS.
- G1 native read-only observation, 2 Worlds: [#40711576242](https://github.com/rinsakamo/relay-self/actions/runs/40711576242), **SUCCESS**, exact code HEAD `b71877803489df31a242ffb3e1fe9f8f2ef4d305`, [artifact #12826266974](https://github.com/rinsakamo/relay-self/actions/runs/40711576242/artifacts/12826266974).
- G2 sprint-vs-ordinary initial real trial, 3 Worlds: [#40712523440](https://github.com/rinsakamo/relay-self/actions/runs/40712523440), **SUCCESS**, exact physical code HEAD `3d35c20f188ce143ed79e71c819153e839396631`, [artifact #12825474100](https://github.com/rinsakamo/relay-self/actions/runs/40712523440/artifacts/12825474100).
- Python 3.12 focused [#40712523580](https://github.com/rinsakamo/relay-self/actions/runs/40712523580): **SUCCESS, 54 PASS**, Ruff, Python compile, Node syntax. No FULL.
- Server: pinned Paper 1.21.8 build 60 SHA256 `8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e`. Java plugin built, unchanged, from T1w `2672d0a1fe15584d16c2426540c528410bbb8c27`.
- Original same-session T1f `ADMITTED` Paper result, Node `applied_controls_dev`, and Paper `gait_dev` go through ONE MineflayerProcessSession.receive. The existing T2 processes every admitted Paper snapshot before passive G1 observes that frame. No additional Motor, issuer, native reader, P1 state or M0 charge exists in G1.
- Archived G1 `g1_applied_gait_observation_dev.json` and T2 `l1_t2_ledger_dev.json` are derived per-World artifacts with independent SHA256 checks in workflow. Full raw Node stdout, complete World folder, independent packet acceptance traces are **not** among these artifacts.

## G1 real World classification

The distinct candidate types have semantics **narrower** than `GaitTickDev`. In particular, `STABLE_ORDINARY_FORWARD_CANDIDATE` is not automatically WALK/JOG, and `STABLE_SPRINT_FORWARD_CANDIDATE` is not automatically RUN/DASH.

| Classified Paper interval | G1 World1 | G1 World2 |
|---|---:|---:|
| Original T2 consecutive ledger | 162 ticks | 193 ticks |
| G1 source snapshots (including initial) | 163 | 194 |
| STABLE_ORDINARY_FORWARD_CANDIDATE | 30 | 34 |
| STABLE_PHYSICAL_IDLE_CANDIDATE | 66 | 78 |
| BLOCKED_OR_STALLED_CONTROL_UNDETERMINED | 7 | 8 |
| TRANSITION_OR_UNDETERMINED | 59 | 73 |
| INITIAL_NO_INTERVAL | 1 | 1 |

The 30/34 ordinary-forward candidate intervals yielded **mean XZ displacement 0.16561 / 0.16008 block per Paper WorldTick** (3.3123 / 3.2017 reference block/s if multiplied by 20). These are empirical filtered means, **not** the motor's theoretical terminal speed or authoritative wall-second speed. Idle candidates had 0 horizontal displacement. Blocked/stalled controls retained their own classification: zero displacement **does not prove** WALK or WAIT.

## G2 one explicitly authorized original sprint Action

WORLD3 of #40712523440 retains the SAME original S49 ActionSupervisor, S16 clear, T2 source, and G1 passive witness. Only the **first** S49 Action has the exact existing `MOVE_FORWARD_SPRINT_DEV` binding, with `S49_GOAL_G2_SPRINT_FIRST_DEV_ONLY=1` and `S49_SPRINT_MOTOR_DEV_ONLY=1` explicit. There is no direct unowned `bot.setControlState` from Self and no extra Action issuer. Subsequent Actions revert to normal S49 forward movement.

- WORLD1/2 unchanged comparison PASS (final errors 0.0609774m / 0.2085780m; original Action→T2 receipts 11/13; T2 rows 162/192).
- WORLD3: **Goal reached**, original first sprint dispatch `set_forward_sprint_dev` **APPLIED**, S16 terminal **OUTCOME**, 4 original Action→T2 receipts, 44 T2 ledger rows, T2 owner failed false, Node/Java exit 0.
- In original Paper+Node G1 evidence, **one stable sprint-forward candidate** was separately identified: Paper speed base `0.10000000149011612`, speed value `0.13000000312924387`, one speed modifier, Paper `sprinting=true`, original Node forward+sprint controls, measured horizontal chord `0.220354` block for that ONE candidate WorldTick.
- During the same World there were **11 stable ordinary forward candidate** ticks, mean XZ chord `0.165555` block per tick, Paper speed base/value both `~0.1`, zero modifiers, Paper `sprinting=false`.
- It would be **wrong** to call the one sprint sample a validated 1.33x physical movement speed. It verifies a real applied **attribute** of 1.30x and a compatible candidate output, but acceleration and sampling window remain unresolved.
- The `g2_first_original_motor_dev.paper_sprint_seen=false` boolean emitted by tested HEAD `3d35c20` was a **pre-finalization placeholder** at the instant the first Action closed, *not* a Paper observation or a denial of sprint. Use the G1 source row to assess observed sprint. The subsequent source-only bookkeeping fix `3a512abace219aa787e3306837ba65aa58195cab` computes this field from the G1 source at the end of the World and marks `same_packet_paper_tick_attested=false`; **that later commit was not part of the successful physical run**.

## Bounded evidence/remaining work

- A Paper snapshot and a Node local control observation are sampled on the same original callback transport, but there is **no causally authenticated client physics step → emitted movement packet → Paper acceptance → WorldTick**. Clock coincidence and equal coordinates cannot fill that gap.
- The optional G1 observer writes **no P1 transition** and **no extra M0 charge**. Existing T2 virtual legacy P1/M0 continues untouched. Neither the G2 sprint request nor this single candidate authorizes `advance_gait_dev`.
- Initial/clear/acceleration/residual tick boundaries remain `TRANSITION_OR_UNDETERMINED`. No fake recovery on blocked motor. Stable idle is a physical candidate, not qualified WAIT; original T2 WAIT_DEV still uses causal clear and independent source.
- WALK (sneak), JOG, RUN, DASH output mapping needs **explicit applied mode signals and a bounded motor contract**, rather than assigning categories from displacement. The Paper speed modifier 0.13 is the vanilla sprint attribute, **not** proof of an extra DASH multiplier. A 20s fatigue-limited DASH cannot be inferred from this test.
- Next G2 increment: increase stable-state counts by repeating already-authorized Action epochs with appropriate L0 observation and source, introduce separate read-only observed-mode and requested-mode columns, then test sneak and configured DASH output without bypassing existing S49 S15/S16. Do not widen action durations beyond L0's accepted envelope just to get more frames.
- After repeatability, use T1w passive client-side physics/packet-return witness only as **diagnostic** until Paper packet acceptance is proven; then consider G3 single-P1 gait with atomic M0 DASH spending. R/V separate authorizations.

No main, #545, #634 or historical protected evidence is modified. All changes are isolated DEV and source-conscious.
