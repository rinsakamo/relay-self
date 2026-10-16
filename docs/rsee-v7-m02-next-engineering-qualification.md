# R V7 M0.2 — new BASAL-write plugin: prospective engineering-qualification handoff

2026-10-16. Authority R #575 / Draft #610, S #537 / Draft #545, V #619 / Draft #625.
**Status: DEV ORIGINAL SOURCE VERIFIED, NEW-JAR/CHANGED-PROFILE ENGINEERING QUALIFICATION NOT_RUN.**
No old grant may be reused, and this document authorizes no World execution.

## Distinct forms of evidence now in hand

- S producer new 5 disposable Worlds: [run #38850179491](https://github.com/rinsakamo/relay-self/actions/runs/38850179491), exact S HEAD `5defe85f55068b34d4ddae0ebe93afc892c09c2c`, plugin SHA256 `af911877133f54e6a3f4ab2f5a9416daf75259af53cb7b4226f8730da9a8b1fc`, Paper build 60 SHA `8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e`.
- R independently retrieved all five original S DEV artifacts, original Java plugin JARs and config source, native STOP, 200 Paper player `setExhaustion` BASAL writes and actual-coordinate WALK billing. Run [#38850421003](https://github.com/rinsakamo/relay-self/actions/runs/38850421003): SUCCESS, independent 90-day archive #12024688755.
- Independently read **original `level.dat` NBT bytes** using bounded decompression and structured NBT parser (not the claimed `server.properties` seed alone). [R run #38868318233](https://github.com/rinsakamo/relay-self/actions/runs/38868318233): 5/5 seed=61021, saved NBT SpawnX/Y/Z=(0,-60,0), different five `level.dat` hashes. **Saved world spawn point != actual bot spawn point.** The Level NBT alone does not prove equal generated terrain/chunks, World start state or a shared S50 MOVE phase.
- Independently reconstructed each true Paper motion packet from `from_xyz`, `to_xyz`, `world_full_time` and native billed exhaustion in [R #38868635492](https://github.com/rinsakamo/relay-self/actions/runs/38868635492). The actual first native horizontal move coordinates differ:
  - BASE_ON: (-9.5,-60,10.5), 7 packets, 1.0390903428873646 blocks
  - SHAM_ON: (-4.5,-60,-9.5), 7 packets, 1.0390903428873624 blocks
  - BASAL_ZERO: (6.5,-60,3.5), 9 packets, 1.2828913533098643 blocks
  - WALK_ZERO: (8.5,-60,-7.5), 7 packets, 1.0390903428873646 blocks
  - BOTH_ZERO: (8.5,-60,-0.5), 9 packets, 1.2828913533098643 blocks
  Each horizontal packet-summed path equals net horizontal displacement in this run; no loop or detour is present in the observed horizontal trace. **Collision is not independently diagnosed**, and the different packet counts/step lengths remain unexplained.
- Separate archive `r-v7-new-world-nbt-review.json` and `r-v7-new-motion-pose-review.json` are collected alongside the original five fresh DEV bundles. Read-only source-shape status only.

## Engineering qualification is NOT V7 scientific path matching

For qualifying **the new plugin's M0.2 accounting** per configured arm, the normative within-arm checks are: source integrity, direct Paper BASAL writes per actual player tick and cumulative request (not unqualified native hunger effect), WALK request per *actually measured positive horizontal block* (zero distance -> NO_RATE_OBSERVABLE), no native-event double bill, real MOVE/OUTCOME and native STOP/host cleanup. A World collision or different walking distance does **not** by itself disqualify source accounting.

**Separate requirement for cross-arm scientific causality:** clone the entire relevant initial World region/chunks with identical initial bot XYZ/yaw/pitch, timing, food/hunger and resource layout. Same `level.dat` seed alone is not sufficient. Under ecological conditions, true failed MOVE and obstacle effects are legitimate outcome variables and shall not be filtered to force equal paths. Under the frozen V7 matched-path study, the 0.005-block entry requirement still FAILS and cannot be post-hoc changed.

## Next qualification must be a genuinely new run

1. Issue a **fresh explicitly scoped** R engineering-qualification run identity/grant for the new JAR **and each altered profile**; the old 2026-10-15 third Paper qualification grant was consumed, and a DEV source cannot be retroactively promoted.
2. Independent R preworld gate: exact new S HEAD, new compiled JAR/Paper binary/config SHA256s, owned new disposable World and source seed. Validate World serialized NBT and/or chunk snapshot as actually required for the precise claim.
3. S or dedicated qualification producer: new unique original evidence root, no edited originals or borrowed producer run. Capture native timeline/Action IDs, first-player-tick/MOVE phase, new BASAL and WALK writes, food readback, real STOP, Java/Node/PID/port cleanup. Emit producer source status with **qualification claimed=false**.
4. R independent post-run reviewer: authenticate exact original bytes and GitHub run/attempt/authorization, verify plugin JAR and per-arm full config, native sequencing and World/host witnesses, reconstruct actual BASAL and WALK source charges and publish **one new immutable verdict**. Neither S's `PASS` nor R's earlier DEV REVIEW_ONLY is an engineering qualification.
5. If run is invalid, retain it and start any corrected qualification only under its own newly scoped grant/identity. Never reuse the previous physical authorization.

**Current legal output:** `RSEE_V7_NEW_FIVE_DEV_BASAL_WRITE_ORIGINAL_REVIEW_ONLY`.
**Not legal:** `M02_RSEE_NEW_PLUGIN_ENGINEERING_QUALIFIED`, V7 scientific success or R G3 promotion.
V7=0/20, V6=0/48, production=NO_GO.

The V8 natural-map survival design is separately a future **offline candidate**. No SCIENCE execution may begin from this document.
