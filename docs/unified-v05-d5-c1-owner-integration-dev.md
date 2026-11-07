# RelaySelf Unified v0.5 — Bug-0 D5 × C1/S10 single-owner integration (DEV)

## Source and merge provenance

This branch is a **true two-parent Git merge** of:
- Bug-0 D5 [#764](https://github.com/rinsakamo/relay-self/pull/764), R3 final `f510ab895056a2c30b1126ce85e848dbed54ffa8`. R3 real Paper/Mineflayer World [#42244551668](https://github.com/rinsakamo/relay-self/actions/runs/42244551668) and independent original [#42245679703](https://github.com/rinsakamo/relay-self/actions/runs/42245679703) PASS: first kill/pickup/EAT, new zombie 600 server ticks later, second original S49 Intent physically ATTACKs once. Second kill/EAT is NOT demonstrated.
- C1 physical-fence [#763](https://github.com/rinsakamo/relay-self/pull/763), final `13791c31b9cf24397f5b251df8a0fcc45863c487`. Original [#42229071113](https://github.com/rinsakamo/relay-self/actions/runs/42229071113) PASS: two sequential original MOVE Intents, 3 S16 OUTCOMEs, 2 C1 motion experiences, S10 7/rev0→8/rev1→7/rev2, durable C1 and pre-ISSUE MOVE physical fences.

Merge base `fa17b9eddc00c58a85b91af64bf34bacef868c1a`. C1 contains 26 modified/new source paths relative to that base; only one overlaps D5, `adapters/mineflayer/normal_action.py`. All other C1 paths are carried over by Git blob SHA (no independent rewrites).

## Sole genuine S49 physical issuer

The one manual merge resolution in `normal_action.py` retains:
1. D5 `NormalSessionActionExecutor(..., max_intent_epochs=1..4)`, exact original supervisor and Action ID retention, and explicit `advance_intent_epoch` source-qualified rearm after an existing completed Intent with a different authentic zombie; original ATTACK/EAT authorization still applies.
2. C1 opt-in `execute(..., pre_issue_reservation=...)` for `MOVE_BACKWARD`, called immediately before **the same** `ActionSupervisor.issue()`, after original authorization but before Mineflayer physical IO.
3. Default paths remain unchanged when the DEV callback is absent. No duplicate ActionSupervisor, new Minecraft adapter, new central Self controller, or independent action-grant authority is added.

Separate C1 `S49C1MotionDevJoin`, `C1MotionJournal` and `OriginalS49PhysicalFence` can now be constructed against the same D5 epoch-capable original `NormalSessionActionExecutor`, as an offline owner-reference bridge. This does NOT yet imply D5's combat/EAT receipts are converted into C1 motion-training examples. The current C1 training target is only `motion_decimeters`; D5's ATTACK/EAT target outcomes are different experiences.

### Hard safety / unknown boundaries

- The C1 durable physical Action fence **currently supports MOVE_BACKWARD only**. A real ATTACK/EAT may not borrow its S16 sealing criteria and must not be reported as durably pre-ISSUE protected. Next change must introduce typed, action-kind-specific pre-ISSUE and outcome evidence before claiming combat/food crash safety.
- D5's explicit epoch rearm does NOT certify post-MOVE settling; physically insufficient quiescence still fences subsequent EAT/ATTACK. The C1 MOVE fixture does not silently advance or bypass D5 epoch boundaries.
- Current C1 S10 is **motor prediction**, not evidence of a learned S49 L0 choice policy or cognitive crystallization.
- Existing Persistent Cognition / MySelf / SelfWorld / SelfBody design contracts B/C remain open in #717. C1's fsynced sidecar is not a new identity owner.
- Both parent real-world PASS results were **different World/session experiments**, not a single full D5+C1 live World. The newly merged branch is initially **offline-only** and must not inherit a claim of integrated physical success.
- Model calls, physical Actions and World creation in this merge/test are zero. Protected original World evidence and both parent Draft PRs are unchanged.

## DEV qualification sequence

1. Commit the true two-parent merge with explicit one-file conflict resolution and publish to a separate integration branch; keep main and both parent branches unchanged.
2. Run `tests/test_unified_d5_c1_owner_integration.py` and both sets of existing parent-lane original-S49 regression tests under the same Git commit, including stale/foreign Intent, duplicate Action, UNKNOWN, C1 S10 journal and physical pre-ISSUE pending restart.
3. If offline success, a **later separately gated** one-World integration test can progressively evaluate D5 ATTACK→D5 rearm and a fresh C1 MOVE experience with the same original supervisor, after each action-kind-specific physical ledger contract exists. No auto-retry, no inferred grant.
4. Only after an entire first and second genuine hunt/pickup/EAT/REST episode should D6 or long-term continuous autonomous survival be considered integrated.

**Classification before joint CI:** `DEV_ONLY / D5_C1_TWO_PARENT_CODE_MERGED / JOINT_WORLD_NOT_RUN / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
