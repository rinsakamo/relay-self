# D7-A — original S49 physical MOVE → same native bot S50 direct controls evidence

Parent [#780](https://github.com/rinsakamo/relay-self/pull/780), original real vanilla World [CI #42362496990](https://github.com/rinsakamo/relay-self/actions/runs/42362496990): genuine random rotten_flesh0→World-owned 600tick new zombie→new original S49 ATTACK→real positive meat1→same-original-supervisor S49 C1 MOVE→Paper same-item-UUID pickup/native inventory0→1. **Post-MOVE EAT not authorized** because mere S15 clear ACK and sampled position cannot establish server-effective STOP.

## Source owner and absolute boundary

Reuse the *existing S-owned* S50 direct control wrapper `adapters/mineflayer/m02_paper_dev/s50_p1_readback_bridge.mjs` and its true `bot.getControlState()` on every Mineflayer `physicsTick` for all seven controls: forward, back, left, right, jump, sprint, sneak. The wrapper imports the original unchanged `bridge.mjs`; it does **not create a second bot, second S49 ActionSupervisor, another physical issuer, network controller, packet sender or Action**. `MineflayerProcessSession.launch` gains an **opt-in DEV-only** fresh absolute sidecar file argument. Default launches follow the unmodified bridge. The original S34 session helper and D4 World driver forward the file only under **separate grant `D7_PASSIVE_CONTROLS_WORLD_ONLY=1`**, strictly in the same original World evidence directory. No inherited S50 tracing/packet path is permitted. The S50 wrapper direct raw original is written as `s50_native_direct_controls_original.jsonl`, SHA-sealed with the Paper/native/ATTACK/MOVE evidence.

The independent after-World read-only `tools/bug0_d7_postmove_native_controls_post.py` joins:
- SAME original S49 World/session ID and original S49 immutable physical ATTACK/MOVE journals already independently audited by D6-D6.
- Last actual original S49 S15 `MOVE_BACKWARD` action ID, `clear_controls` effect result native sequence, original S16 OUTCOME.
- The original S50 callback `EFFECT_ACK(native_action_id=original_move_id+'-clear')`, complete direct held-control snapshot of all seven controls, consecutively numbered client physicsTick events including at least eight after that clear, and no client control reactivation until clean native shutdown. Only already recorded original native client callbacks are read; no new observation, physical effect or issuer is created.
- Missing/foreign session, duplicate JSON keys, missing/partial controls, native source rows, lost client ticks, postclear reactivation or another motor ACK result in fail-closed rejection. No previous World/Action retry on source uncertainty.

## Critical prohibition

**Even if every seven-control S50 client snapshot is OFF, this does NOT prove physical stop**: these are Mineflayer CLIENT physicsTicks. Paper's server-effective release tick, contiguous Paper tick positions/velocities and all-source physical occupancy are *not* authenticated. The S49 original `_post_move_settling_unqualified` remains TRUE. The D7 reviewer must output `body_physically_stopped_proven=false`, `server_effective_release_tick=NOT_ATTESTED`, `authenticated_S_owner_EAT_resume_grant=false`, `original_EAT_issued=false`. It creates NO EAT permission object. An all-true natural-zero World with no physical MOVE classifies `D7_A_NO_MOVE_STOP_SOURCE_NOT_EXERCISED`, not STOP success.

D7-A is one fresh **bounded real Paper World** DEV experiment with unchanged normal loot RNG and unchanged original D6 owner, same native session, original S49 physical ATTACK/MOVE journal, same S50 wrapper observer. A new docs-only one-use exact-source-HEAD trigger runs offline negative tests, pinned Paper 1.21.8 build60 + both Paper plugins, Mineflayer 4.39, real bounded original World, independent D6 and D7 read-only audits, full original SHA256 and Node/Java cleanup. Existing #780 or other old World is NEVER replayed. No autonomous AI hunting/learning or endless runtime claimed.

**Next only after evidence:** S owner must separately integrate Paper server-effective input-clear tick, full-gap-free Paper per-tick controls/position/velocity, and authenticated S-owner EAT resume grant before allowing the original S49→S51 EAT. A passive client quiet streak is a diagnostic, not that grant.

`DEV_ONLY / D7_A_PASSIVE_S50_CLIENT_CONTROLS_SOURCE_PROBE / PHYSICAL_STOP_UNPROVEN / EAT_NOT_ISSUED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
