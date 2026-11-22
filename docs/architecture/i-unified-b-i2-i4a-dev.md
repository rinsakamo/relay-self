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
- Old I4a Journal \`certified_prefix_digest\` is absent from B; do NOT
  invent a trust root or backfill a fake certified digest.
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
