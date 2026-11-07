# Unified v0.5 C1/S10: original S49 owner DEV wiring (#758)

## Parent/ownership
- Parent Draft #757, exact base HEAD `3080ce771e7d4be4d2f82534c25f6088b742f59c`. Separate child #758.
- The original S49 runner's `IntentCommitment`, `NormalWorldL0` and `NormalSessionActionExecutor` remain the real owners of Intent/L0/action. `S49C1MotionDevJoin` is a local synchronous coordinator referring to the **same** Intent and executor instances. It has no Action issuance capability.
- Separate S10 motion-retained `LearningPreferenceState("motion_decimeters", value=7, revision=0)` is an experimental *seed*, distinct from existing L0 `risk_weight=4/revision1`. It is not a learned policy nor an L0 behavior modification.

## Original runner wiring — opt-in only
The `qualify(..., unified_c1_dev=True)` / `--unified-c1-dev` branch additionally requires `S49_UNIFIED_C1_DEV_ONLY=1` alongside the runner's existing real server gate. It is exclusive with other S49 feature branches and **is not itself a World grant**. The user/operator must verify an unconsumed DEV World authorization for the **exact branch, HEAD and purpose** before any physical run. No such grant has been verified in this development turn.

1. On the original `on_action(step)` path *after* S14 admission, *before* the unchanged `executor.execute(...)`, the coordinator reads the original correlated decision `probe` and exact S10 owner revision.
2. S15 obtains its own distinct internal before observation. The original S49 executor, not this coordinator, issues the Action and produces its original S16 terminal. The coordinator accepts that receipt only if `executor.supervisor.get(action_id) is receipt.terminal` and `receipt.source == original_decision_probe.provenance`.
3. Once the established WAIT→MOVE_AWAY→MOVE_AWAY original run successfully returns and supervisor has no open Actions, the original `IntentCommitment` is explicitly terminalized as an **attempt assessed**, not an independently verified Goal success.
4. C1 composes the two original MOVE receipts into one attempted Intent motion experience, structurally compares the seeded forecast against observed movement, and updates the existing S10 scalar by its revision-checked commit. UNKNOWN does not train.
5. A **fresh native correlated original-session probe** is read (no new Action). The same Intent owner commits a distinct successor Intent; its forecast reads the exact revised S10 retained object and revision. The next L0 action/selection is **not** issued/attested.

## Replay and provenance
In-process duplicate terminal, duplicated/old decision probe, mismatched session, copied S16 terminal, foreign supervisor, stale next-source and repeated successor are rejected. The native probe's provenance is computed by the Mineflayer protocol from session and sequence; S15 before is never relabeled as the L0-selected source. The same-object terminal custody protects against detached receipt replay in this bounded DEV process.

**Boundary:** the replay journal is process-local. A restart/persistent duplicate experience is not yet blocked by a durable owner journal; no B 60-second autosave or long-term experience store is included. The source is native adapter-level evidence, not independent World/Paper proof.

## CI and tests
- `tests/test_s49_c1_motion_owner_dev.py`: synthetic original-shaped supervisor, exact S16 object custody, single attempt → one experience, revision 0→1, next original Intent forecast 0.7→0.6m and negative/replay cases.
- Earlier #756/#757 C1/S10 source-join and owner regressions remain selected.
- Workflow is offline: no World creation, Minecraft Action, GPU or LLM. A successful GitHub Actions result is **not** a real-world qualification.

Classification remains `DEV_PARTIAL / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`. Actual World one-session integration, independent source attestation, next original L0 policy change, habit/L0 crystallization and learning advantage remain unproved.
