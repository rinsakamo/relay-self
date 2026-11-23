# RelaySelf Unified I U7 — PLACE emergency STOP / Native stdin buffer boundary

**Scope:** CPU/offline hostile tests on original B physical issuer and synthetic
Native adapter. Q2 audited original I U6 `4b08384dfd928f0e5788038ec721064df6353bff`
(https://github.com/rinsakamo/relay-self/issues/1088).
Original real Native/Paper/World producer custody was NOT attested.

## Owner-preserving implementation

- `PhysicalIssueAdmission` remains the ONLY existing original B physical
  issuer. A new `submit_native_effect(..., write)` does not select actions,
  bind a different Owner, create a WAL writer, or bypass original Source.
- For a normal PLACE native child, lock order is:
  **Original resident lock → original PhysicalIssueAdmission lock →
  original canonical WAL flock**. The gate validates original B S1, physical
  and cognitive scope, v2 PREPARED WAL digest/identity/lease and one-shot child
  while the existing canonical WAL lock is held. It then synchronously calls
  the original adapter's `stdin.write` *before releasing any of those locks*.
  This closes the in-process quarantine/WAL-lock **check-to-buffer-write** gap
  in the opt-in original owned native route. There is no await in the critical
  section; `drain`, Node reception, Paper ACK and physics remain outside.
- `MineflayerProcessSession` serializes full frames through an asyncio lock.
  The owner-controlled bridge installs one permanent `atomic_effect_sender`
  after its existing original admission hook, before any native observe. An
  effect with MOVE_PLACE active is **denied** by the legacy check-only API:
  missing the atomic hook fails closed rather than reverting to old check +
  later write. EAT/ATTACK and legacy MOVE keep their old capabilities.
- Quarantine emergency STOP is narrowly admitted for the same original
  bound PLACE lease/session/parent/child, only when its START child was already
  consumed, the original physical resident epoch advanced exactly once into
  QUARANTINED, the one-shot STOP remains unused, and no global close/poison
  occurred. No LOOK/START/forged ID/foreign session/replay is allowed.
  Cognition may have been fenced and WAL history changed after START; requiring
  a fresh cognition or WAL read here would withhold the last safe STOP.
  Emergency STOP is **not** an admission to resolve, adopt, or replay the WAL.
- A failed write or drain can leave physical PREPARED_UNRESOLVED. A callback
  error does not refund the consumed child. Synthetic STOP admission is not
  proof of native acceptance, speed settling or actual safety.

## Adversarial CPU regression plan

`tests/test_i_unified_u7_place_stop_atomic_native_dev.py`:
quarantine before START; missing pre-submitted START; after-START cognition
fence and corrupted WAL STOP; wrong native and child identities; duplicate
STOP; simulated process-backed Native stdin LOOK/START/STOP; missing atomic
hook; legacy check-only bypass; physical lock contest at final byte write;
canonical WAL flock contest; write-failure replay denial; post-bind rehashed
WAL denial. Retain the original I4a typed WAL/settling tests and legacy
EAT/ATTACK/MOVE test suites. All fixtures are synthetic.

## Qualifications that remain HOLD

- Original pre-S1 producer witness custody and independently authenticated
  Native/Paper/World: **HOLD**. Internally recomputable hashes do not suffice.
- Process boundary: original synchronized `stdin.write` buffer insertion is
  protected, but an IPC drain is async and *cannot* prove atomic arrival or
  native execution across processes. A killed process or interrupted drain
  leaves UNKNOWN. Native ACK and Paper tick corroboration: **NOT RUN**.
- STOP motor outcome: STOP could be enqueued but there is no real ACK or
  post-STOP 8+8 tick settling evidence. **EMERGENCY_PLACE_STOP_REAL_HOLD**.
  Explicit host-side STOP dispatch and termination behavior under real
  quarantines still require isolated DEV qualification.
- The original restored B resident is observation-only, MOVE_PLACE opt-in OFF
  by default. No practical physical grant or PRE_WORLD elevation.
- R1 Shadow, R2 migration, post-reJOIN Composite, real L1/L2 GPU, C/E
  independent admission and historical non-integrated I2/I4a suites remain
  separately unqualified.

**PRE_WORLD_HOLD / QUAL_NO_GO / SCIENCE_NOT_RUN**. Keep PR #1124 Draft,
and request independent Q #1088 regression review on this exact U7 HEAD.
