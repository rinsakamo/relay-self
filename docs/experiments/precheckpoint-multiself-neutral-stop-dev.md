# P0-D #860 — Multi-Self pre-checkpoint neutral STOP (stage 9 DEV)

Stack: #868 → #867 → #866 → #865 → #864 → #863 → #862 → #861 → #859. This is **offline, fake native-source testing** of a real-source STOP protocol, not live Paper/Mineflayer.

## Rationale

The previous stage protected EAT/ATTACK at the Mineflayer process stdin boundary, but intentionally denied MOVE/LOOK/CLEAR. In a world with a moving Self, an idle Python EAT/ATTACK lease does **not** imply that native movement controls are neutral, because Minecraft keeps applying a previously enabled `set_control(state=true)` until cleared.

We add a **pre-checkpoint**, not an unconditional or replayed STOP. Before `CoordinatedAutosaveRuntime.run_if_due`, a caller explicitly runs `prepare_stop_before_autosave` for the **full enrolled Self cohort**. This step is asynchronous, while the existing checkpoint barrier remains synchronous.

## Protocol

1. The shared `PhysicalIssueAdmission(require_neutral_stop=True)` checks the exact Self roster and closes normal physical admission **before** any asynchronous STOP send. If any EAT/ATTACK lease is active, fail closed; no STOP may overlap ambiguous physical work.
2. Exactly one scoped `stop_lease` per native Self session allows `clear_controls` through the last Python Mineflayer `_send` gate, **only** for that STOP's exact native Action ID. Other effects, old sessions, a second STOP ID and new EAT/ATTACK are refused.
3. Before native STOP send, write/fsync an exclusive per-Self `PREPARED_UNRESOLVED` audit file. On failure, never rewrite or delete the original evidence. STOP is a distinct DEV audit and **not yet a row in the canonical S49/EAT/ATTACK WAL**.
4. Require a native same-session, same-action `clear_controls` **applied** ACK (not a terminal physical outcome).
5. After ACK, allow an initial **8 observed World ticks** for residual motion to settle. Then require a further **8..200 World tick** source-qualified native probe interval with 3D displacement `<=0.06m`; if drift exceeds this, move the baseline forward and check another 8-tick interval within the bounded timeout. All probes use distinct matching request IDs and the same native session, with `day * 24000 + time_of_day` as a **native reported**, not independently authenticated Paper tick clock. A perpetually moving Self never qualifies. This is a bounded settling heuristic; it does not prove a true stopped physicsTick under all server plugins, nor world-wide stasis.
6. Independently verify the STOP proof inside `PhysicalIssueAdmission.confirm_neutral_stop` and fsync the `NEUTRAL_SETTLED_DEV` evidence file. Failure to get any ACK/probe/file for any Self makes the **entire physical gate poisoned and HOLD**; later asynchronous completion cannot unlock it.
7. `PhysicalIssueAdmission.close` in strict mode now refuses bypass if STOP was not prepared. A successful `CognitionOwnerCohort.close` consumes **all** qualified same-generation STOP proofs, then uses the existing full typed World + all-Self checkpoint and fresh-session rebind; release remains blocked until every Self's old session is fenced.

The physical stop and cognition cut are not the same instant: the user explicitly accepts minor save-time skew. The cognitive cut is taken **after** all physical STOP confirmations. During neutralization, normal physical effects cannot start, but cognition/message owners have not yet been frozen: the synchronization boundary starts at the subsequent existing CognitionOwnerCohort.close.

## Tests (offline only)

- Actual owned mutable A/B cognition facade + strict typed generation, two STOP ACKs + 8-tick-spaced probes, successful World/Self snapshot/rebind after both body proofs, no replay.
- B-only drift, stalled clock, wrong ACK/session/request ID, missing World time, rejected STOP, clock regression and forged STOP command: global HOLD; A's valid STOP alone is not enough.
- A in-flight EAT/ATTACK before STOP: refuse before any native STOP emission and keep gate closed.
- Strict mode refuses direct checkpoint without STOP, partial roster or incomplete native evidence.
- Real Python `MineflayerProcessSession` with fake owned child process stdin permits only the exact STOP Action ID during the fenced neutralization phase. No MOVE/ATTACK/direct unscoped native effect passes to Node.

## Important nonclaims and remaining live P0

- **No real Paper 1.21.8 or two real Self actors were run.** Mineflayer time/position checks in this CI are simulated readbacks. The 8-tick interval is derived from a native snapshot clock, not independently authenticated Paper main-thread physics tick evidence. No true automatic 60-second background host driver is installed.
- STOP preissue evidence is a separate, exclusive/fsynced DEV audit. It is **not yet integrated with the canonical physical Action journal/S49 ActionPort** and does not qualify a new native physical authorization.
- The Node/Mineflayer bridge itself has not been upgraded to enforce this shared gate against foreign processes or direct bridge stdin; the gate belongs to the one explicitly owned Python session.
- A native body can move due to collisions, knockback, gravity, moving platforms or other actors even with controls cleared. Two position probes provide a bounded drift check only, not proof that every chunk/entity is quiescent. The safe World cut still depends on Paper clean-stop/save receipts.
- The existing old L0 MOVE/S49 direct execution, external native session inventories and full original Self owners still require migration or shutdown. No true multi-Self crash/rollback qualification. Legacy non-strict tests remain non-qualifying.
- Any strict pre-stop failure, SAVE failure, stale session, or uncertain Action must HOLD and preserve the last verified full generation without historical replay.

Classification after exact-HEAD green CI: `MULTI_SELF_NEUTRAL_STOP_OFFLINE_DEV_PASS / PHYSICAL_STOP_PAPER_TICK_NOT_ATTESTED / FULL_ACTION_ISSUER_ROSTER_NOT_FENCED / REAL_LIVE_60S_AUTOSAVE_NOT_RUN / QUAL_NO_GO / SCIENCE_NOT_RUN`.
