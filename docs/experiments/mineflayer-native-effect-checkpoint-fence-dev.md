# P0-D #860 — Mineflayer process native effect admission (stage 8 DEV)

Stacked on Draft PR #867, itself stacked on #866 → #865 → #864 → #863 → #862 → #861 → #859. User policy unchanged: 60s committed whole-World/all-Self generation, no replay, discard every post-generation state, permit small save-time skew.

## Gap closed

Previous physical issue guard prevented an EAT/ATTACK coroutine from entering through its selected guarded wrapper when a checkpoint was closed, but the same Python MineflayerProcessSession still provided public `send_set_control`, `send_look`, `send_equip_item`, `send_consume_held`, and `send_attack_entity` methods. A direct native effect send could bypass the guarded runner.

## New opt-in final-stdin gate

- Existing `MineflayerProcessSession.install_effect_admission(check_effect)` registers a one-way callback on an **already started, owned** native process session. A second installation is refused. This is not a cryptographic authority and does not fence other processes or direct Node-bridge writes.
- With the callback installed, the central `_send` checks every outgoing JSONL command. `type=effect` requires the callback to accept the **actual started session ID and effect name** before stdin write/drain. Malformed, unknown, and direct `_send` effect-bypass attempts refuse. Read-only `observe` and clean `shutdown` remain available even while the physical gate is closed.
- Existing shared `PhysicalIssueAdmission` now binds each active lease to one typed effect family: `EAT` may send only `equip_item` + `consume_held`, and `ATTACK` may send only `attack_entity`. A default unqualified lease permits no effects. The gate refuses unrelated movement, look, or clear-controls effects even if some other Skill currently has an active lease.
- `run_cognitive_minimal_world.py` installs this gate immediately after the owned Mineflayer launch when explicit coordinated checkpoint mode and externally supplied shared gate are present. Selected EAT/ATTACK runners retain their existing ActionPort, WAL and native consequence checks. The outer coordinator still owns the **same gate across every registered Self**.
- The new tests instantiate the actual `MineflayerProcessSession` with fake stdin/stdout rather than monkeypatching the send methods. They verify no bytes are sent for unleased EAT/ATTACK, direct `_send` bypass, MOVE/LOOK/CLEAR in coordinated mode, malformed commands or stale sessions; only EAT/ATTACK's matching effects and observation go out.

## Important STOP limitation

`clear_controls` is also a native effect and is intentionally refused in the coordinated mode here. Therefore this mode **must only be installed on a newly launched neutral-control session**, or after a separately qualified emergency-stop/readback transition. It does not solve stopping a body whose previous `set_control(state=true)` remains active. Before live multi-Self qualification, implement one supervised STOP/neutralization path and a reliable WorldBody confirmation; otherwise HOLD.

## Remaining unqualified edges

- The adapter's effect admission callback is an in-process Python callback. An external process writing directly to the Node bridge, legacy S49 owner with an unguarded session, or a second MineflayerProcessSession created outside the coordinator remains outside the gate. All running sessions must be inventoried and guarded before a global World cut.
- Effect-family checking alone is not physical Action identity authorization: immutable intent/skill/native binding, two-probe source, operator permission and WAL reservation are still checked by existing issuers; do not promote the gate into another physical issuer.
- Real Paper 1.21.8, L0 MOVE/STOP, native rejoin attestations and true 60-second periodic multi-Self crash recovery remain untested. Offline deterministic CI is the only evidence for this PR.

After exact-HEAD green CI: `MINEFLAYER_PROCESS_EFFECT_FENCE_OFFLINE_DEV_PASS / L0_MOVE_STOP_NOT_QUALIFIED / ALL_NATIVE_SESSIONS_NOT_INVENTORIED / REAL_LIVE_60S_AUTOSAVE_NOT_RUN / QUAL_NO_GO / SCIENCE_NOT_RUN`.
