# P0M — Paper main-thread MOVE/STOP XYZ witness (DEV-only)

**Independent scope:** This read-only sidecar is deliberately located on the
initial Skill PR #882 branch. It does not modify Checkpoint PR #878 or its
P0D tick witness. It neither issues MOVE nor clears/recovers a motor WAL.

## What the Paper plugin actually measures

`experiments/p0m_paper_move_observer/` is a Java 21 / Paper 1.21.8 plugin.
During `onEnable`, it schedules one recurring task on Paper's main thread.
It has no slash commands and never mutates World, ticks, player controls, or
checkpoint state. The plugin stores its spool under its own data folder:

```text
<Paper server>/plugins/P0MMoveWitness/p0m/
  requests/<nonce>.arm  # host publishes atomically before native LOOK
  requests/<nonce>.mark # host publishes only AFTER native STOP/applied ACK
  handled/...            # Paper retains consumed requests (nonce replay fence)
  acks/<nonce>.armed     # Paper's first main-thread position-tick admission
  complete/<nonce>.trace # immutable single completed 16-post-STOP-tick trace
```

The plugin validates a **live, online player UUID** in the supplied **World
UUID**, allows at most one active observer for an actor, and samples exact
Paper `Bukkit.getCurrentTick()` and `player.getLocation()` XYZ once per
tick. It logs `P0M_READY`, `P0M_ARM`, `P0M_STOP_MARK` and
`P0M_COMPLETE`; a failed observer produces `P0M_ABORT` and no terminal
trace. The STOP marker is a host-produced signal **after** a Mineflayer
`clear_controls/applied` ACK, not a server-authenticated Action ID
acknowledgement or proof that the actor ceased motion at that tick.
The completed trace contains:
`boot_id`, `nonce`, `world_uuid`, `actor_uuid`, `action_id`,
`native_session_id`, `arm_tick`, `stop_mark_tick`,
`source=PAPER_MAIN_THREAD`, and consecutive `sample=tick,x,y,z` rows.

The Python `PaperMoveWitnessSession` uses distinct UUID nonce, native
session+Action scope, atomic fsynced request files, exact arm ACK, and
matches the same recorded native MOVE parent. Arm occurs **after the
Self-owned WAL `PREPARED_UNRESOLVED` is durable, before native LOOK**;
mark occurs **after** native STOP applied ACK. Native MOVE alone never
confers permission to emit an unowned Paper request.

Strict `qualify_paper_move_trace` requires all provenance fields to
match the original request, a monotonic **unbroken tick sequence** from
arm through **STOP+16**, an arm tick before the STOP marker, Paper start
position within 0.20m (3D) of the native start, at least 0.25m targetward
Paper horizontal progress by STOP marker, and **≤0.06m 3D maximum drift
over every sample during ticks STOP+8..STOP+16**. The `P0M_*` sequence
must appear, in order, in the exact operator-provided process log.
These windows deliberately allow transient post-STOP displacement during
the first 8 ticks. Records are immutable after publication; the
SHA256 of the raw trace is returned for audit.

**Important limits:** This is a DEV independent position stability
witness, **not** verified physics settling forever, causal Paper STOP
action acknowledgement, collision freedom, destination arrival, QUAL,
World checkpoint consistency, or multi-Self arbitration. Paper actor and
World UUIDs, and the purported owned process log, are *operator inputs*;
this design has not independently authenticated them to the Mineflayer
session or the actual Paper process. In particular the raw file and a
manually supplied log are not cryptographic remote attestation. Do not
promote to QUAL or infer another Self's action causality from this trace.

## Build (no server launch)

```sh
mvn -B -ntp -f experiments/p0m_paper_move_observer/pom.xml -DskipTests package
sha256sum experiments/p0m_paper_move_observer/target/p0m-paper-move-observer-0.1-dev.jar
```

Only with an independently authorized, already-owned local Paper
**1.21.8** process should the built jar be installed under its
`plugins/` directory, and plugin enable/`P0M_READY` verified in the
**same process's raw log**. Installing or launching Paper is a separate
explicit operator action; this code does not perform it.

## One-shot real DEV command (operator-supplied values, not pre-approved)

Use an **existing world**, isolated DEV Self, bounded and near-level
destination 0.4..4m from the current native position, and both separately
authorized World and LLM runtimes. Fill in actual session-owned paths and
UUIDs; never reuse a previous Self's or World generation's WAL:

```sh
python -m experiments.run_cognitive_minimal_world \
  --grant-real-world --grant-real-llm \
  --model "$LLM_MODEL" \
  --pre-l1-native-probe \
  --physical-move-dev --exploration-need \
  --move-destination "chosen-point,$X,$Y,$Z" \
  --physical-journal-path "$SELF_WAL" --physical-create-journal \
  --physical-propose-authority "$PROPOSE_AUTHORITY" \
  --physical-issue-authority "$ISSUE_AUTHORITY" \
  --acknowledge-physical-dev-unverified-grants \
  --paper-move-spool "$PAPER_PLUGINS/P0MMoveWitness/p0m" \
  --paper-move-owned-log "$OWNED_PAPER_PROCESS_LOG" \
  --paper-move-world-uuid "$WORLD_UUID" \
  --paper-move-actor-uuid "$ACTOR_UUID" \
  --evidence-path "$AUDIT_JSON"
```

The model must select the MOVE option. It can instead select L2
escalation/DEFER, or refuse stale Target; neither outcome is a physical
MOVE success. If no native issue was authorized, no Paper observation
request should be treated as physical permission. The CLI flags
`--physical-eat-dev`, `--physical-attack-dev`,
`--physical-move-dev`, legacy `--execute-native` and explicit
`--s49-readonly-shadow` are exclusive.

## Classification and recovery

Only if the original native WAL Action has been fsynced, the native
LOOK/forward/STOP ACKs + progress + native STOP readbacks close, **and**
a valid independently logged Paper 16-tick trace joins that original
Action does the CLI expose `paper_move_position_stable_8_ticks=true`
and the digest/ticks/positions in `paper_move_tick_proof`.
`native_move_paper_settled_attested` and
`native_move_arrival_attested` remain **false**. The skill still yields
`YIELD_EVALUATION`, not Goal completion.

Any incomplete/mismatched Paper trace after physical issuance is a
`PREPARED_UNRESOLVED` WAL and STOP/UNKNOWN, **not** a soft fallback
to the native-only path. Do not reuse the WAL or retry the motor command
after restart until a separate operator-owned causal reconciliation
exists. Missing source snapshots, a different Paper boot, world UUID,
actor UUID or native session are all refusals. Clock comparisons across
Paper and Mineflayer are not invented; only the explicit ordered
host-side ACK→marker handoff and main-thread tick sequence are asserted.

## Test and evidence boundary

- Offline Python contracts: good and adversarial UUID/action/world/start,
  missing/repeated/regressed ticks, native/Paper position mismatch,
  unexpected source, no before-STOP progress, vertical/horizontal STOP
  drift and foreign/out-of-order Paper logs.
- Scripted native/Paper observer contracts: observer armed **before**
  native LOOK; host STOP marker only after observed ACK; no Paper
  evidence/foreign Paper Action leaves native parent UNKNOWN and
  retains persistent WAL.
- CI compiles the Java plugin against Paper API on Java 21. This is
  **not** an actual Paper runtime/World/persistent physics test.

For real qualification, independently obtain original plugin trace,
original process log, Paper jar/hash, session identity, native ACK and
WAL originals, plugin enable evidence, and World/actor UUID linkage.
A matched trace demonstrates a bounded Paper-observed **position
stability interval**, not full STOP semantics or real-world skill
success. Checkpoint #878's P0D main-thread witness and STOP recovery
remain separate.
