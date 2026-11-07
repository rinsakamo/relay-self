# D7-C — genuine pickup-anchored Paper quiet source (DEV only)

> **No actual STOP certificate; EAT still fenced.** Child of [D7-B #782](https://github.com/rinsakamo/relay-self/pull/782), which adds a default-off Paper tick source, and [D7-A #781](https://github.com/rinsakamo/relay-self/pull/781), which reads actual client S50 seven controls. [D6 #780](https://github.com/rinsakamo/relay-self/pull/780) already proved in a single real World: zero natural food → 600-tick respawn → fresh S49 kill → natural food → real S49 MOVE/PICKUP.

## Current implementation slice

The independent Paper tick reader `tools/bug0_d7_paper_server_tick_post.py` previously measured a quiet streak over the **entire World**, which could include long idle periods *before* the first MOVE. D7-C narrows this diagnostic to **server ticks after the independently audited real natural item pickup**:

- Requires the original D6 independent auditor's exact `natural_item_uuid` and `original_move_count`.
- Requires exactly one matching **Paper server** `RSELF_NATURAL_DROP_PICKUP` event for the same Item UUID, Paper player UUID, World UUID and bounded tick.
- Uses the original Paper tick stream's contiguous main-thread rows to measure current inputs (seven), current actual position, velocity and on-ground conditions **after that event**.
- Distinguishes 0 MOVE/0 PICKUP as `NOT_EXERCISED`; mismatches, duplicate or fabricated Paper pickups are rejected. Quiet prior to pickup does not contribute to the post-pickup count.
- Strict offline negative tests cover missing/duplicate/wrong item and future pickup tick, plus inherited native/Paper source negatives.
- An optional eight-or-more quiet Paper server tick streak is labeled **observed diagnostic only**, not `S49_STOP_AUTHORIZED` or proof of Paper-effective original S49 clear tick.

## Owner handoff remains

This source window still does not identify the S49 original clear's **causal Paper-effective tick**, nor attest no other motor issuer and fresh post-window EAT Intent. The original `_post_move_settling_unqualified` cannot be cleared by this report or by synthetic/offline observations. The next S-owner step is one live, independently attested action-bound end-to-end boundary:

**original S49 MOVE physical terminal + original native clear ↔ actual Paper effective input-off ↔ continuous post-clear & post-pickup quiescence ↔ S49 current food/health/inventory/hazard/Intent/probe ↔ once-only EAT PROPOSE/ISSUE and S51 consume native outcome.**

The first DEV EAT after MOVE must preserve an exact original source World/session, fresh S49/S51 original grants and irreversible pre-ISSUE physical journal; never derive new authority from a reviewed Python dict alone. Keep R/QUAL/SCIENCE separate and do not replay old Actions.

**Classification: `DEV_ONLY / D7_C_POST_REAL_PICKUP_SERVER_QUIET_SOURCE_ONLY / STOP_NOT_CERTIFIED / EAT0 / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.**
