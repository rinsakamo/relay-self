# RelaySelf Unified v0.5 — Original S49 ATTACK/EAT pre-ISSUE durability (DEV)

## Scope / parent evidence

Stacked child of **Draft PR #765**, which integrated D5 [#764](https://github.com/rinsakamo/relay-self/pull/764) and C1 [#763](https://github.com/rinsakamo/relay-self/pull/763) under one original `NormalSessionActionExecutor` and passed original [joint offline #42327316909](https://github.com/rinsakamo/relay-self/actions/runs/42327316909). No change to either protected real-World original or general Persistent Cognition Self identity / MySelf / SelfWorld / SelfBody owner.

C1's existing `OriginalS49PhysicalFence` remains **MOVE_BACKWARD only**. The new sibling `OriginalS49NonmotionFence` is one original S49 ATTACK/EAT nonmotion ledger. It has no Action authority and cannot issue native commands. No new S49 executor/ActionSupervisor, no new external authority/grants or World physics changes.

## Exact original boundaries

The same original S49 `NormalSessionActionExecutor.execute_attack/execute_eat` accepts **paired optional callbacks**, `pre_issue_reservation` and `post_outcome_commit`, disabled by default. Both must be callable together. The pre-ISSUE callback runs only after original native source/authorization and `ActionLifecycle.authorize` but **before** `ActionSupervisor.issue`, S49 delegate and *any* Mineflayer non-idempotent IO. If synchronous durable write fails, it emits no physical Action. Nothing automatically retries a PREPARED Action.

The source-bound PREPARED record fsyncs Self ID, source session, current original Intent ID, original Action ID, *kind*, exact native decision seq/request/provenance, and either:
- **ATTACK:** original observed target zombie entity ID. After native ATTACK ACK, a genuinely fresh correlated after-probe and exact original supervisor-held S16 OUTCOME are required. The resulting S16 seal says **only the ATTACK command was applied**; it is *not* evidence of physical damage, death, true killer, drop or independent Paper causation.
- **EAT:** original food name/slot and food-before from the native EatChoice. The original S51 now retains **both** applied `equip_item` and `consume_held` child receipts, plus the actual before and after native probes in the existing typed `EatingActionReceipt` (backwards-compatible optional fields). S49 seals only if the existing S51 `verify_eating_subactions` rechecks separate child IDs/chronological seq, food increase and observed inventory decrease. Missing result/consume ACK or an unqualified after-probe leaves PREPARED.

The ledger enforces strictly increasing original native action source seq per session, unique source and Action IDs, type-specific immutable fields, canonical body SHA256, atomic fsync write / atomic replace / parent fsync, file lock + CAS against stale writers, foreign-Self refusal, and corruption refusal. It has **no automatic crash reconciliation** and does not infer an absent physical effect.

Even when S49's in-memory Action terminal has reached OUTCOME, a failed *durable closure* keeps PREPARED, so the next automatic issuance or newly provisioned World is **blocked**. The same guard applies if a process crashed between PREPARED and ISSUE, or between ISSUE and native result. A later human/original audit may examine immutable Paper/native evidence, but this code grants no implicit automatic recovery.

## Real D4/D5 entrypoint / limits

D5's existing `tools/bug0_d5_oneworld.py` gains separate `--nonmotion-fence-dev` opt-in. It requires the unchanged original D4 one-World grants **and** `BUG0_S49_NONMOTION_FENCE_DEV_ONLY=1`. The original D4 runner creates/restores `report_path.parent/s49_nonmotion_physical_fence.json` and requires no pending PREPARED **before** inspecting server JAR or starting Paper. Each original D4 ATTACK, optional D4 rotten-flesh EAT and one D5 fresh-Intent ATTACK uses the same fence object. The completed World reloads the ledger and matches all exact original Action IDs and S16 closure counts.

A World with **zero authentic natural rotten flesh** has **no EAT record**, not a fabricated zero-consumption event. Genuine Paper 600tick respawn, operator-staged melee location and zombie kill witness remain World-owned evidence unrelated to ATTACK command ACK. If physical fence callback fails after an effect, the D4/D5 run fails and preserves unresolved state; no automatic next-gen Action.

The **D5 live World with the new fence has NOT yet been executed**. Source, offline tests and prior parent live evidence are separate. The new physical ledger neither writes C1 `motion_decimeters` nor reclassifies ATTACK/EAT as MOVE. The C1 motion pre-ISSUE fence and S10 journal remain separate atomic storage; no single cross-kind/global transaction or long-running autonomous survival has been proven.

## DEV tests and further gates

1. Focused `tests/test_s49_nonmotion_physical_fence.py`: real S49 Python owner with *synthetic* source-specific native frame streams; ATTACK ACK-only vs EAT nutrition, source/terminal custody, rejected consume/attack, pre-ISSUE fsync failures (no physical command), forged/corrupt outcomes, stale writer, foreign Self, pre-World UNKNOWN STOP and single original S49 D5 next-Intent epoch with two ATTACKs.
2. Two offline workflows on the child branch (source/grant regression), no World and no LLM.
3. **Only after offline success**: separately source-pinned single-use DEV World verification of first D4 true kill/loot/EAT/600tick respawn and second D5 original ATTACK *with the new nonmotion ledger enabled*. Preserve natural zero-loot as a valid stochastic outcome. Verify original Paper log and native S16 against durable records in a fresh Python process; failure does not allow an automatic retry.
4. Future D6 Self-driven MOVE-to-loot, continuous two hunt/food cycles, cognition/energy & physical settling still separate. Neither a single stochastic trial nor improving performance is required to prove the *architecture*.

Classification: `DEV_ONLY / S49_ATTACK_EAT_PREISSUE_FENCE_OFFLINE_GATE / JOINT_WORLD_NOT_RUN / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
