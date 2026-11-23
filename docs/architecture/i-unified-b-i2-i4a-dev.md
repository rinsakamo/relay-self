# I Unified U0: B Original Owner anchored integration (DEV)

## Exact source pins
- B #1119: f43d6f1a14b20f041794bdb0b820a33ebf513f5c (base, original owner retained)
- I2 #1080: d8d7f1d9337d4a4e1937009ce9230f386f0e4716
- I4a #1076: 9f3d6f73af1f4d0e16e212f9cb0ff2564c0137fd
- C #1108: 0dcba713f79ffa5f3850ca99f99c77e2b409c470
- E2→I2 #1111: 7b317fb0040ba4d367271d28a8419cd39129fdd7 (not yet ported)
- R0 #1118: fcceaa8ac359b891550f2cbc021d85337c4a1da5 (already in B)
- Q #1089: d310b91b6c25c3abc0351a8dc67d75d660df2fbb (external audit, not integrated)

## Authority map
B alone: Original Owner, Scheduler, GPU lane, Schema3, PersistentCognition,
Question/Goal/Intent, checkpoint and Source qualification.
I: read-only R0-to-I2 original source ingress; I2 L1/L2 bounded handoff;
I4a S1/S2 run-boundary, WAL/native source readback and original issuer adapter.
C: retained C1/C3 API; I never writes Memory itself.
E: owner-source Native SENSE/continuity; E2 continuous queue fence still HOLD.
Q: independently pinned source/provenance; source-content SHA alone is not custody.

## Migration safety
All selected code files were absent from B tree. Existing B original owner,
Native Dispatcher, Physical ActionPort, Physical WAL, checkpoint, R0,
GPU scheduler, Paper witness, and Bridge source files are byte-for-byte
unchanged. Historic stage27/C dependencies imported only by name and not
made an independent runtime. I4a S2 scripted issuer is synthetic/DEV,
PREPARED_UNRESOLVED remains unrecoverable by automatic replay.

The ingress helper pairs Schema-qualified R0 CURRENT with I2's original
Need/Goal/L1 request on matching same-source native session, seq, request ID,
Paper session/hash, Self and resident epoch. Then it rechecks B's R0 CURRENT,
I2's frozen request and original owner identity without making any selection
or writing Memory or physical journal. The source hash only guards change.

## Qualification
- U0 code/source composition: requires final exact-HEAD CI.
- Genuine B-adopted Question/Goal/Intent: HOLD until original issuer evidence.
- E2 queue-loss / blocked-reader fence: HOLD until reviewed implementation port.
- I4a S1/S2 real continuity and pre-S2 external WAL root: HOLD.
- C1 real owner Memory retention and C3 learned reuse: HOLD.
- Original model/Gemma, World/Paper/S2, Q independent custody: NOT RUN/HOLD.
- R1_SHADOW_ADMISSION: HOLD. QUAL_NO_GO. SCIENCE_NOT_RUN.

No cloud-side simulation is evidence that the user's WSL2 RTX 3060/Paper
or the real Self issued any physical actions.


## Incompatibility audit (first exact-head run)

The first broad historical source+fixture transplant was actually run on
\`888bac537b51751d2fb8d1f9deda4a1b8bc681ab\`. Full pytest collected and
executed, with **2,977 PASS / 538 FAIL**. Five-job CI was 4/5:
repository contracts, Ruff, Mineflayer, Paper succeeded, pytest failed.
Real defects were API incompatibilities, not merely missing fixture imports:

- B schema refuses the old I2 legacy exploration mapping/activation (114 fails).
- I2's \`read_i0_owner_cpu\` signatures and B's current legacy Source no longer
  match (\`i2b_read_attached_lane\` and follow-on SENSE).
- Old I4a Stage27 fixture \`allow_resident_move\` and provider
  \`enable_stage26_raw_audit\` are not B original interfaces (216+ fails).
- At U0, B Journal lacked I4a's \`certified_prefix_digest\`. U2 adds
  **only the read-only v1 canonical prefix function**. A digest is not an
  original-custody trust root, and I4a's **v2 MOVE_PLACE schema is still
  incompatible** with B's v1 EAT/ATTACK/relative-MOVE writer.
- E2 Native receive-queue pressure fence assumes a different dispatcher
  than B's existing original Mineflayer session. It is NOT transplanted.
- Older Option/target/registry assumptions conflict with present B Schema3.

Those historical tests and real-World runners have therefore NOT been added
to final test discovery. Historical PR evidence and test files remain in
#1080 and #1076; **not passing them is a HOLD, not a silent PASS**.

The final branch retains the selected code as deliberately non-authoritative
DEV modules, and uses **new compatibility tests** around B Original Owner:
- \`read_i_unified_b_current\` positively reads B's R0 CURRENT and rejects
  a mutated Paper session without Memory/physical authority.
- I2 handoff pairing requires B original owner/source and current Schema,
  and remains HOLD if old I2 exploration/source API cannot qualify.
- \`capture_i_unified_s1_cpu\` / \`audit_i_unified_s2_cpu\` use B's
  existing \`PhysicalActionJournal.restore\` (read-only) and compare S1
  prefix, Self, Owner identity, native session, generation, distinct S2
  Intent/Skill/Action and terminal status. CPU local content equality
  **is not authenticated source custody**; no physical S2 is issued.
- Reuse of C modules is staged; no C1 real adoption or next-epoch claim.
- Q remains external and must inspect original source and WAL independently.

The final exact HEAD's CI verdict must be recorded independently after this
change. No claim of complete I2/I4a runtime integration is permitted merely
because B-only regression and the newly scoped negative tests pass.


## U1/U2 follow-on (2026-11-22)

U1 source-qualified B original exploration is now wired to the actual B
registered CoverageAdoptionTurn and B original bounded-L1 issuer. The
U1 exact HEAD `23461613a4d051c225b887b9c2357fecdb4fdd50` passed
2,739 scoped tests and all 5 CI jobs. Only **B** can issue the Question
ADOPT and persist it to its original cognition file. This path neither
activates legacy I2 L2 Intent/Goal/Skill issuance nor runs real Gemma.

U2 adds `PhysicalActionJournal.certified_prefix_digest(count)` in B v1,
with no schema/writer/physical grant changes. It allows a previously
retained S1 digest to be compared against the *canonical v1* prefix after
S2 appended. The `i_unified_physical_source_dev.py` CPU-only adapters
now pair the original Owner's own WAL path, original resident/native/World
epoch, and saved prefix SHA with a reread of B's canonical WAL. The
positive synthetic test appends valid v1 EAT outcome-shaped rows, **not**
a genuine Native/Paper/Physical Action, and verifies a distinct second
Intent/Skill/Action is read back. The negative tests reject an S1 action
rewrite with recalculated full checksum, a foreign cloned WAL file,
replaced Owner/epoch/session, replay, drifting journal and unresolved
PREPARED. Test fixtures directly write canonical *synthetic* rows; this
cannot qualify their provenance or ActionSupervisor.

This U2 comparison **does not lock the original physical admission lease**
through Native/World operations or establish an independently authenticated
S1 anchor across restart. I4a's original source branch uses WAL schema 2
(`MOVE_PLACE`, `NATIVE_PLACE_MOVE_SETTLED`) while current integrated B
WAL supports schema 1 only; those paths must not be invoked or treated as
qualified by this v1 read-only prefix helper. To reach real I4a S1→S2,
a future scoped migration/compatibility implementation must retain v1
reader/writer behavior, add v2 support with adversarial tests, reconcile
B's original physical lease and Q's independently held original evidence,
then perform new PRE_WORLD and DEV qualification. No actual real World,
GPU/model, S2 Native effect, C1 experience or Q audit was run here.


## U3 — original B WAL v2 MOVE_PLACE compatibility (2026-11-22)

The upstream I4a source `9f3d6f73af1f4d0e16e212f9cb0ff2564c0137fd`
includes v2 exact-row validation, `prepare_place_move` and `close_place_move`.
U3 ports these ORIGINAL canonical WAL operations into B's single
`PhysicalActionJournal`, **without copying I4a's alternative owner,
issuer or separate file**. B's existing v1 EAT/ATTACK/relative MOVE
operations are preserved; schema v1 remains the default for `create`,
`restore` accepts schema 1 or 2, v2 upgrades are explicit and use
the same canonical CAS/fsync mechanism. Unknown versions and incomplete
PLACE gait pairs fail closed.

A pre-existing v1 S1 prefix needs explicit `source_schema=1` when
calling `certified_prefix_digest` on a later v2 journal. Rehashing
the old rows under schema 2 would yield the wrong historic digest and
can never prove source custody. `i_unified_physical_source_dev.py`
records the original snapshot schema and matches a separately held
original SHA and Owner/world/native scope, including after a v2 append.
This remains CPU readback only: it cannot authenticate a witness
which was forged before its first capture or prove post-restart custody.

The new U3 source-shaped synthetic tests exercise:
- v1 old rows + v2 PREPARED refusing S2 completion until closed
- v1 digest equality across a v2 append, and v2→v2 S1/S2 readback
- PLACE settled/no-progress/overshoot and optional WALK/SNEAK gait ACK formats
- hostile v2 row mutation with recomputed full-file checksum, bad
  Action/source/skill/budget/tick/position, partial gait data and downgrade
- default v1 writer unchanged, mixed-format stale/duplicate rejection.

**Remaining U3 HOLD gates:** The U3 positive WAL fixtures use internal
canonical `_commit` with synthetic rows. They do *not* exercise the
full upstream typed `prepare_place_move/close_place_move` issuer chain,
PhysicalIssueAdmission lease, Native ACK/Paper original custody,
fresh B Owner L1 Skill selection, C1 success retention or a real World.
Adding v2 parser/writer methods is not an S2 authorization.
Q must independently inspect v1→v2 on-disk migration, original S1
source authentication, concurrent physical leases, and all runtime
commands before PRE_WORLD. U2's earlier claim that schema v2 was
absent is historical; v2 is now present in U3, but its live issuer is
still **HOLD**.


## U4 — PLACE PhysicalIssueAdmission opt-in and typed WAL (2026-11-22)

The **existing** `PhysicalIssueAdmission` class now recognizes a distinct
`MOVE_PLACE` effect family, exact original child IDs for `look`,
`set_control` and `clear_controls`, and a **separate explicit**
`allow_resident_place_move=True` constructor opt-in. The opt-in can
only be set together with `resident_mode=True` and
`allow_resident_move=True`; the default is False. The lease requires
the original native session and single-action ownership. No child is
admitted before original `PhysicalActionJournal` fsync PREPARED
readback and `bind_native_children` correlation. Selected Native
IDs are one-shot, and releasing/ending the lease removes admission.
`MOVE_PLACE` requires v2 PREPARED rows. A `SNEAK` gait is **refused**
at child binding because it requires an additional, separately
accounted-for `set_control` ID; this U4 minimal route covers only
walking without that gait. It is deliberately not permissive fallback.

The new `tests/test_i_unified_i4a_place_lease_dev.py` uses a separate
*synthetic* opt-in instance of the **original PhysicalIssueAdmission
class**, original typed `PhysicalActionBinding`, original
`SkillInvocation` and `Stage27PlaceMotionPlan`, and the original
canonical WAL `prepare_place_move`/ `close_place_move` methods.
Synthetic source-shaped MineflayerObservations / EffectResults and
original `ActionSupervisor` lifecycle allow a complete v2
PREPARED->terminal **contract test**, with no actual Native IO.
Denied cases include missing opt-in, wrong child IDs, cross-Self,
pre-PREPARED, replay, missing Native lease, forged source/target,
unresolved PREPARED and SNEAK. The *real B restored instance* is
separately tested for explicit refusal: it is **observation-only**
and has `allow_resident_move=False`, so its physical gate rejects
even before U4 PLACE-specific opt-in evaluation.

U4 **does not** migrate B's restored original Owner to a physically
enabled mode or install any real PLACE/L0 motor runner. The synthetic
opt-in PhysicalIssueAdmission test object is NOT the B restored actor;
there is no original B actor/World-backed issued S2 evidence.
Particularly, PLACE `bind_native_children` currently trusts the
provided canonical WAL path and a matching local session/Action row;
it does **not** independently authenticate the physical journal's
original custody against Paper/Native process evidence or a long-lived
original-B-held source witness. That must be separately fenced in
a future stage before any real opt-in is considered. Explicit
`PRE_WORLD_HOLD`, `QUAL_NO_GO`, `SCIENCE_NOT_RUN` remain.

Historical I2/I4a test discovery is still incomplete: scoped U4 CI
cannot imply blanket legacy regressions or real S2 source certification.


## U5 — B original S1 physical custody gate (2026-11-22)

U5 adds an **in-process, volatile** S1 history anchor to the **existing**
`PhysicalIssueAdmission` object, and a dedicated
`arm_original_place_s1`→`bind_original_place_children` path. This
does **not** create another Owner, external WAL, process or native issuer.

The anchor is created only from the current Original B
`bridge.cognitive_work`/ `bridge.owners[self_id]` identity, the
owner's exact canonical `physical_wal_file`, a nonempty terminal
S1 `PhysicalActionJournal` readback, and original live
resident/native/World epoch. It stores original `IUnifiedS1Witness`
under the existing physical gate, not a caller-provided SHA or
persistent/new file. The anchor may be armed only once in the original
resident session; restart loses it and must fail closed.

The generic `bind_native_children` intentionally **rejects**
`MOVE_PLACE`; otherwise the U4 path could bypass custody binding.
The dedicated path needs a current original PLACE lease, same
PhysicalIssueAdmission, Owner, Self/Native/World/physical epochs, the
same exact canonical original WAL path, and a **single new v2
PREPARED_UNRESOLVED** with distinct Action/Intent/Skill following the
unchanged S1 historical prefix. It verifies the S1 canonical digest
under the historical schema (including v1→v2), the caller journal's
current digest, and WAL file metadata. S1 is never silently rearmed,
and one action's child binding may not be reused.

At each `require_native_effect` under a bound PLACE lease,
`resident.lock → physical._lock → canonical WAL restore` rechecks
original scope, saved S1 prefix digest, PREPARED row and the
`(device,inode,size,ctime_ns)` of the bound canonical WAL file
**before** consuming an exact native child ID. A byte-identical
file replacement after binding is refused even when its checksum
still matches; independently rewritten old S1 history, action
substitution, symlink swap and stale or fenced epochs are also
rejected. No awaiting occurs while these locks are held, and the
same original gate remains the sole consumer of child IDs.

The U4 typed `prepare_place_move`→`close_place_move` CPU test now
uses this U5 anchored binding path (on an isolated explicit-opt-in
`PhysicalIssueAdmission` instance injected into a **synthetic** B
bridge). New U5 adversarial tests cover cloned WAL path, stale
histories with recomputed checksums, duplicate S1 arm, stale/foreign
scope and Owner, pre-Native inode replacement and rejoin fences,
and one consumed child before later WAL replacement. No actual
Mineflayer/Paper/GPU/World process was run.

**Unqualified boundary and safety caveats (HOLD):**

- The S1 anchor is **volatile within the same process** and captures
  the currently visible canonical data; it is **not a cryptographic or
  independent Native/Paper source-custody root**. A malicious
  replacement of the canonical path *before the first S1 capture*,
  or a valid but forged PREPARED row written before the first binding,
  cannot be attributed solely from checksums or inode inspection.
- The WAL check and native IO are not one indivisible cross-process
  transaction: the current code checks immediately before
  `require_native_effect` consumes a child ID, **not** through a
  complete Native/Paper roundtrip. A host process or external writer
  can still race between child admission and the actual stdin write.
  Q and a fresh original-source/issuer transport verifier are needed.
- Live `MOVE_PLACE` emergency STOP after quarantine is **not
  qualified**: the U5 fail-closed source fence refuses post-quarantine
  child admissions, including an ordinary STOP. Before any real
  PLACE motion can be enabled, the original Physical issuer must
  provide a separately audited emergency STOP/settling path that
  cannot be blocked by this custody guard.
- Original B restored `PhysicalIssueAdmission` still has
  `observation_only=True`, `allow_resident_move=False`, and
  `allow_resident_place_move=False`; U5 positive tests use a distinct
  *synthetic* opt-in instance of the original class and forged
  native ACK/probes. They are not real action qualification.
- This U5 pass does not qualify old I2/I4a historical runner tests
  omitted from the integrated branch, L2/Gemma, Memory adoption,
  independent Q Source, C3 or World. Maintain
  **PRE_WORLD_HOLD / QUAL_NO_GO / SCIENCE_NOT_RUN**.

The next gate for R0.5 is exact-head compatibility and Q read-only
shadow audit, not R2 runtime migration or enabling physical PLACE.

### U5b — abandoned PREPARED and lease reacquisition guard

A new lease is **not** a new issuance authority for a previously prepared
PLACE action. The original `PhysicalIssueAdmission` now performs a
read-only canonical-WAL/saved-S1 comparison when acquiring a PLACE lease
after an S1 anchor exists. It demands exactly the unchanged terminal
Owner-held S1 rows, historical schema, source digest, canonical file path
and a non-unresolved WAL; a leftover PREPARED or rewritten S1 refuses the
new lease **before** any Native child is registered. This uses the existing
physical lock followed by the original WAL lock. The subsequent
`resident.lock → physical._lock → WAL` check still verifies the Owner,
session, World and action identity. No new writer, issuer or permission.

`tests/test_i_unified_u5_abandoned_place_lease_dev.py` adds hostile
interruption-before-binding, abandoned LOOK, forged PREPARED before lease,
rechecksummed S1 before lease, same-Self and real-thread lease contention,
and cross-Self nonauthorization coverage. The negative quarantine-after-
START example explicitly records **STOP SAFETY HOLD**: refusing STOP
proves fail-closed admission, not safe physical neutralization.

This is an **additional CPU/synthetic regression only**. It does not seal
an S1 prefix independently, authenticate real Native/Paper source, remove
the final-check-to-stdin race, qualify STOP settling, authorize original
B production PLACE, or discharge Q/PRE_WORLD/QUAL/SCIENCE HOLD.
