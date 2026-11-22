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
