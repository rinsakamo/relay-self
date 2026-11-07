# D6-A — Source-qualified ground-item approach (DEV, offline first)

Parent: [#768](https://github.com/rinsakamo/relay-self/pull/768), exact source HEAD `c87381fcdab6be605635950c0c94ab3d384ad6bd`. Evidence for its one-World D5 original ATTACK→natural item pickup→conditional EAT→600tick next-Intent ATTACK is retained; it is **not** proof of a second survival cycle.

## Repo-first blocker analysis

- `NormalSessionActionExecutor.require_authorizations` currently accepts original S49 `MOVE_AWAY` with a **zombie** target. An item-entity target is correctly rejected, so reusing that path without a reviewed new source/authority branch would disguise a loot pursuit as evasive motion.
- S15 knows only `MOVE_BACKWARD` for 0.20s. Its physical direction depends on actual Mineflayer yaw. Current default probes have no yaw: W4's opt-in `MineflayerOrientedSnapshot` is the only existing source for this cue. We cannot silently assume direction or operator orientation.
- `_post_move_settling_unqualified` intentionally forbids EAT after any S49 MOVE. S15's `clear_controls` ACK + S16 OUTCOME is not final 8-tick stationary WorldBody proof. This existing barrier is preserved, not bypassed.

## This child

`adapters/mineflayer/d6_loot_approach.py` defines `source_qualified_loot_approach(previous,current,item_entity_id)`. It refuses any stale, foreign, uncorrelated, truncated or ambiguous native item/probe; it requires two steady same-session probes with the same one item and no zombie or other entity; validates bounded item geometry and **actual** optional native yaw; and admits a **read-only** `MOVE_BACKWARD` approach candidate only if stepping backward is physically aimed toward that item. Candidate contains native provenance and remains `action_issued=False`, `authority_granted=False`, `pickup_verified=False`. Neither Mineflayer's `name=item` nor the geometry proves that the entity contains `rotten_flesh`: independent Paper natural-drop identity and fresh inventory gain must be joined later.

This pure source decision does NOT fabricate S14/S49 authorization, does not introduce a second physical issuer, send `look`, alter `S15`, reduce WorldBody physical gates, write C1/S10, or change D5/default S49 behavior. Negatives cover wrong entity, zombie, extra item, truncated coverage, stale source, foreign session, missing W4 orientation, bad yaw, moving item/body, health/oxygen and distance boundaries.

## Next bounded D6 slices

1. Obtain W4 native orientation through an **explicit** D6 opt-in and add reviewed `COLLECT_LOOT` skill admission inside the **same** original S49 ActionSupervisor, with C1's existing MOVE-only pre-ISSUE journal and strict typed S15 before/clear/after. Do not re-label a zombie escape as loot collection.
2. In a one-use disposable real World, make an item originate from a genuine Paper `EntityDeathEvent`, and require a **native item observed before MOVE**, original S49 MOVE performed, authentic Paper pickup and exact fresh `rotten_flesh` inventory increase. If the item is already passively picked up, record that as a genuine outcome but **not** Self MOVE-to-loot success.
3. Only after independent post-clear settling and next source epoch qualification, let original S51/S49 select EAT. A second kill→pickup→EAT cycle and sustained survival need a further one-use physical DEV experiment, not inferred from #768.

Classification: `DEV_ONLY / D6_A_LOOT_APPROACH_READ_ONLY / WORLD_NOT_RUN_D6 / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
