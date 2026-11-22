# P0-D #860 — Shared physical EAT/ATTACK issuer admission (stage 6 DEV)

Parent stack: PR #865 → #864 → #863 → #862 → #861 → #859. This slice adds a **guarded path for existing physical issuer functions**, not a new native Action issuer, a global hook into all call sites, or live Paper/Gemma evidence.

## Issue that this closes

Earlier CognitionOwnerCohort used an externally asserted `ExternalPhysicalFence` with no implementation of the physical issuer admission side. Therefore it could not prove that an EAT/ATTACK async task wasn't still sending native effects or awaiting a native ACK when the World snapshot started.

## Implemented

- `PhysicalIssueAdmission` stores the fixed Self→native-session roster and owns a synchronized, per-Self `IssueLease` around **the entire existing** `issue_selected_eat_dev` or `issue_selected_attack_dev` async call. Existing preissue WAL, ActionSupervisor, grants, Mineflayer sends, ACKs and after-probes are unchanged. No extra physical issuer exists.
- `close` atomically refuses new physical leases **before** checking active issues; if any action is still active, the checkpoint is refused and the gate stays closed. No snapshot is allowed under a dirty physical state. A settled action does not automatically release an unsuccessful checkpoint.
- A `close` attempt that observes any in-flight action poisons the gate permanently for the current process; even if the asynchronous Action later settles, no token rotation/release makes that rejected generation valid. Operator-managed recovery is required.
- `run_l1_eat` and `run_l1_attack` guard the **entire existing L1 selected EAT/ATTACK runner**, including Intent/Skill construction and the lower WAL/native issue sequence, using a caller-provided per-attempt `admission_ref` (not the eventual Action ID). This is the recommended opt-in autosave route.
- On an accepted cut, `rotate_native_session` refuses stale/same/duplicate sessions; `release` requires the exact fence token and **every** registered Self to have a fresh native session. New requests using the old session are rejected.
- `CognitionOwnerCohort` already accepts `external_close_physical`, `external_release_physical`, and externally attested native rejoin callbacks. Tests wire this new gate into those real cohort hooks to prove a physical lease blocks even a synthetic World/A+B save and that new session IDs replace old ones.
- `issue_eat` and `issue_attack` explicitly dispatch to the current existing native DEV issuer functions while the lease is held. Wrapper tests monkeypatch only those functions to prove the lease extends across an async await; they do **not** send actual native Minecraft IO.
- Async cancellation returns the in-process lease to zero, but does **not** imply the persisted WAL is resolved. Actual `freeze` still reloads the canonical WAL and requires clear; PREPARED_UNRESOLVED must HOLD forever until independently reconciled.

## Deterministic tests

- One Self cannot have two concurrent physical issue leases; Action IDs unique across Self.
- Closing with in-flight work fails closed and skips World snapshot; a completion after refusal does not silently commit or un-fence.
- No new native issue during a checkpoint; neither A nor B can resume before both sessions rotate; old session cannot send even if all native tasks finished.
- Existing EAT/ATTACK guarded wrappers call the real module entrypoint under lease; no Action is issued after fence closes.
- Existing A/B actual cognition owner fixture uses the shared physical gate for close/rebind/release; in-flight A attack causes HOLD before saving any World generation.

## Explicit limits / follow-up

**Critical:** The two legacy direct `issue_selected_eat_dev` / `issue_selected_attack_dev` Python functions are still callable without this gate. Every deployed caller must be migrated to the guarded entrypoints and tested before claiming full physical issuer closure. Also L0 movement, any old S49 physical owner, Mineflayer bridge/direct effects, non-Python issuers and concurrent processes are outside this in-process lock.

The admission token is an in-process receipt, not an authenticated distributed authority. An external real Mineflayer rejoin adapter still has to prove the new native session and cancel stale GPU/transport queues, not merely return booleans. Paper 1.21.8, real 60s unattended autosave and two real Self crash/restore remain untested.

**Policy fixed:** 60s autosave, whole-World-and-cohort rollback, discard everything between snapshots, tolerate minor save-time skew, no replay, no UUID reconstruction.

Classification after exact HEAD green CI: `IN_PROCESS_PHYSICAL_ISSUER_FENCE_OFFLINE_DEV_PASS / ALL_NATIVE_CALLERS_NOT_MIGRATED / REAL_PAPER_AUTOSAVE_NOT_RUN / QUAL_NO_GO / SCIENCE_NOT_RUN`.
