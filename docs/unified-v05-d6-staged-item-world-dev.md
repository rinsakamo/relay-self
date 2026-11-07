# D6-C: one-use staged-item original S49 MOVE→real Paper pickup DEV

Parent [D6-B Draft PR #770](https://github.com/rinsakamo/relay-self/pull/770), exact inherited HEAD `0430d012ab31e95c04df0aab51b6cc414ff3407c`. Old D5 / D6-A/B original reports, source files and branches unchanged.

## Scope

The original Paper D1 operator-created item plugin gains *optional* `rselfstagefood back`: a single real rotten-flesh Item entity appears about 2.2m behind the DEV player's server yaw; default `rselfstagefood` still drops at player location. This is clearly **OPERATOR_FIXTURE_NOT_ZOMBIE_DROP**. Nothing grants the player food directly or creates a PICKUP effect.

`tools/bug0_d6_staged_move_world.py` preserves one same Mineflayer session and one original S49 ActionSupervisor, explicitly opts in to the existing W4 native orientation readback, requires real native `item` entity geometry, uses `D6LootApproach` to select native-yaw-aligned `MOVE_BACKWARD`, and limits sequential physical S15 commands to four. Each original S49 Action is granted separately with native-probe/item-ID scoped PROPOSE/ISSUE authorization; the existing C1 MOVE-only ledger is fsynced `PREPARED_UNRESOLVED` before original supervisor ISSUE/native IO and sealed only upon real original S16 OUTCOME, original S15 set_control/clear_controls/after evidence.

Before provisioning any Paper World, a non-empty preexisting physical journal (unresolved OR terminal) is an unreplayable STOP. Its path is outside the disposable World directory and included in one-use evidence. Failure/UNKNOWN is preserved; no automatic new World, retry, or reset. Once physical movement actually reduces the native item distance, independent Paper `EntityPickupItemEvent` must prove the exact operator-staged Item UUID and a new correlated native inventory probe must show `rotten_flesh` count 0→1.

`tools/bug0_d6_staged_move_post.py` independently restores C1 ledger and checks all action/intent/native seq/dispatch/clear/after IDs plus original Paper item stage/pickup UUID, immutable source classification, original supervisor identity and no additional issuer. A successful S16 MOVE is never proof of pickup by itself; neither the native item `name` nor operator staged food proves a genuine zombie drop.

## Boundaries

The original generic S14 `COLLECT_LOOT` planning/route admission and source qualification are not fully implemented; D6-B's Action-level specialized original S49 DEV grant remains the scope. Existing S15 fixed control 0.20s stays unchanged; this World may fail if the actual physics or native yaw does not permit pickup. No item teleport, no manual player MOVE, no zombie kill or second true cycle is claimed. **Post-MOVE EAT remains fenced** by `_post_move_settling_unqualified`; S15 STOP ACK is not verified physical settling.

Offline first: dedicated workflow with Python regression/preworld refusal tests and Paper pickup plugin Maven build. Real World: only a separate one-use docs-only exact parent HEAD trigger, pinned Paper 1.21.8/Mineflayer 4.39.0, raw logs, independent audit, SHA256 evidence manifest and cleanup. Do not run a World on ordinary push. No main/parent PR modification.

`DEV_ONLY / D6_C_STAGED_MOVE_PREWORLD_PENDING / REAL_WORLD_NOT_RUN_D6 / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
