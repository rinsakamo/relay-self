# RelaySelf I Unified — R0.6 and Q Schema3 hardening handoff (2026-11-22)

**DEV/CPU only; not a real Native, Paper, GPU or World attestation.**
This is an integration record, not a new R authority, Owner, WAL writer,
physical issuer or a replacement for Q independent verification.

## Independently preserved source commits

| Source | SHA | Result |
| --- | --- | --- |
| I U5b reviewed parent #1124 | `82ac3bced9da7ee3175627bd745811b664608348` | 5/5 CI, 2,831 scoped pytest PASS, physical source/STOP HOLD |
| R0.6 source PR #1128 | `00229bd2e68257a4ef5e26608cdf075904c18820` | R0.5+R0.6 read-only Stage28/Owner comparison; source based on I U4 |
| R selective I commit | `2ca64e1c5816bf505586ce75cb038cbd872b1d79` | 7 R files only; 618→624 tracked blobs, no file loss; exact-HEAD 5/5 CI, 2,860 PASS |
| Q/B strict Schema3 source child #1126 | `38243d4cd15f30453eacd3e17df4c80bd664a0ed` | Original B source JSON duplicate-key/nonfinite rejection and five hostile tests; child 5/5 CI |
| Q/B selective I commit | `474086e8e0ec01127bdf61f0e52b780849d79660` | Only 2 previously unchanged B files modified, same 624 tracked blobs |

The source PRs remain Draft and unmerged. The I branch is the only
consumer; the exact source blobs were selected without a wholesale merge
or overwrite of the original U5b Physical/WAL changes. R0.6's source
document remains intentionally pinned to its former U4 parent; this
document records the newer U5b+R0.6+Q/B integration lineage.

## R compatibility (no promotion)

R0.5 adds cross-Paper RECENT and qualified Need-reference RETRIEVED
fences; R0.6 compares the existing I `read_i_unified_b_current` with
the original B Present/Schema reader, using the original resident lock.
It performs reread consistency checks and exposes an immutable
`r1_shadow_allowed=False` diagnostic. No turn registration, alternate
owner, Memory adoption, GPU ticket, Action grant or physical effect.
Initial synthetic Stage28 only; reJOIN Composite and R1 Shadow HOLD.

## Source JSON (no authentication)

Q/B #1126 replaces Python default last-wins JSON loading in
`bd1b_schema3_source_readback_dev.py` with nested duplicate-key and
NaN/Infinity refusal. The five hostile tests recalculate available SHA
pins for producer report, prelogin, initial Native/Paper and logout
receipt. Successful rejection demonstrates an improved *structural
source gate*, not possession of an authentic prior producer witness.
The Q owner branch and its independent evidence remain untouched.

## U5b physical and Q qualification boundary

The original B recovered gate remains observation-only with MOVE_PLACE
disabled. The in-process S1 snapshot/Canonical WAL prefix/physical lease
are local consistency evidence, not independently immutable custody.
A forged prefix before first capture, forged PREPARED before binding,
Native stdin check-to-write races, quarantine emergency STOP and actual
settling remain unqualified. Abandoned PREPARED must remain unresolved,
without replay. Legacy I2/I4a test suites not ported into this branch
are **not** certified by this branch's scoped pytest.

**PRE_WORLD_HOLD / QUAL_NO_GO / SCIENCE_NOT_RUN**.

## Required next steps

1. Exact-HEAD 5/5 CI of the integrated I branch and Source+R+U5b
   hostile test subsets; report failed runs without retroactive edits.
2. Q #1088 independently audit actual original S1/prefix custody,
   schema source completeness, Native stdin ownership and STOP safety
   on the pinned integrated HEAD; passing local hashes never suffice.
3. Preserve R0.6 as CPU read-only; reJOIN qualified R1 Shadow,
   R2 runtime migration and real World S2 require separate evidence.
