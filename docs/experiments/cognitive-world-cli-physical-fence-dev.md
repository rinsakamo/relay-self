# P0-D #860 — Cognitive World CLI call-site migration to shared physical fence (stage 7 DEV)

Base: Draft PR #866. Preserves the user decision of one 60-second whole-World + all-Self checkpoint, throwing away all future events and **no replay**. This slice does not create the live autosave daemon.

## Why

Stage 6 provided `PhysicalIssueAdmission.run_l1_eat` and `run_l1_attack`, but the actual existing execution composition in `experiments/run_cognitive_minimal_world.py` still called `issue_eat_from_selected_l1_dev` and `issue_attack_from_selected_l1_dev` directly. Those direct calls bypassed the new admission gate.

## Implemented opt-in call-site migration

- `run(args, *, physical_issue_admission=...)` accepts a **shared instance provided by an outer coordinator**, rather than allocating an ephemeral one per physical Action. This is essential: an isolated gate cannot represent a World + all-Self admission cut.
- `--require-coordinated-physical-fence` explicitly opts the CLI composition into the external shared gate. When enabled, it requires exclusive WAL-backed EAT or ATTACK mode, a typed preexisting `PhysicalIssueAdmission`, and refuses the legacy `--execute-native` route **before launching** Mineflayer or making model requests. Passing a gate without the explicit mode is also refused.
- Under the flag, the actual EAT and ATTACK call sites dispatch via `gate.run_l1_eat` / `gate.run_l1_attack`, retaining the entire existing L1-selected Skill/Intent, WAL-before-native, Mineflayer ACK and consequence inspection paths. The `admission_ref` is scoped to the selected Self/world-session/intent; it is an invocation identity **not a grant or physical Action ID**.
- In normal unflagged DEV, existing one-shot CLI behavior is unchanged and still unqualified for coordinated autosave. `main()` does not manufacture a gate, so the CLI alone **cannot** enable qualified coordinated checkpoint execution. The enclosing live owner must supply one in-process shared gate and qualify its roster and session provenance.
- Report `coordinated_physical_issuer_fence=IN_PROCESS_SHARED_ISSUE_LEASE_DEV` for the guarded path and `coordinated_checkpoint_committed=false` for this one-turn attempt; **no assertion of a completed 60-second or multi-Self save**.
- Strict mode fails closed when the gate is closed, uses a stale/foreign native session, or attempts legacy physical issue. The original disk WAL must still independently reject unresolved reservations after failures.

## Deterministic tests

- Uninjected gate in coordinated mode refuses before launching Mineflayer.
- Injected gate without explicit flag refuses (no implicit authority).
- Coordinated flag + old `--execute-native` route refuses before launching.
- Existing scripted Mineflayer *real CLI composition* sends exactly one EAT or ATTACK via the guarded, original issuer, checking WAL consequence and audit record.
- Closed gate and stale session each refuse before any native Action or WAL reservation.

## Strict remaining gaps

`run_cognitive_minimal_world.py` remains **one Self per invocation**; it cannot by itself prove 2 Self running in one Paper World. An external multi-Self coordinator needs to create and retain exactly one shared PhysicalIssueAdmission across both Self and connect its `close`/`rotate_native_session`/`release` to P0-D. Direct legacy EAT/ATTACK function imports, L0 movement, old S49 and native Mineflayer direct commands are still bypass routes. No process-wide/in-bridge fence is installed, no authenticated native session rebind, no real Paper 1.21.8 live 60-second checkpoint or real A/B crash/recovery has been run.

Classification after CI: `COGNITIVE_WORLD_CLI_GUARDED_ISSUER_DEV_PASS / GLOBAL_NATIVE_CUT_NOT_ATTESTED / REAL_LIVE_60S_AUTOSAVE_NOT_RUN / REAL_TWO_SELF_RECOVERY_NOT_RUN / QUAL_NO_GO / SCIENCE_NOT_RUN`.
