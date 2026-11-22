# B Lane B+D → B and R0 consolidation (DEV/offline)

Status: **INTEGRATION UNDER TEST / R1_HOLD / REAL_OWNER_SELF_ADOPTION_HOLD / QUAL_NO_GO / SCIENCE_NOT_RUN**.

## Pinned source and topology

| Source | Exact immutable commit | Role |
|---|---|---|
| B Normal Runtime PR #1114 | `76b1a98f5b84b7a9184bae1345005802cba62bee` | Integration parent; original A/B Bridge, 2nd A reJOIN, generation-specific CPU work |
| B+D PR #1050 | `6e4e17909c6c2e1db5c1759ccf9c0cd000a1a5f4` | Selective source for original Owner admission, Schema3, source audit |
| R0 PR #1118 | `fcceaa8ac359b891550f2cbc021d85337c4a1da5` | Three immutable CURRENT/RECENT/RETRIEVED files |
| B/B+D merge base | `7dadab3688d59ea2da6aeec53ee382907ce4d6c5` | Historical common source; branches diverged |
| First transplant commit | `79ccd6ba9ba5cab883785a8e5d662db5942832ca` | 37 selected Git blobs; no full merge |

**These are distinct concurrent development histories.** R0's 3-file diff is based on B+D;
this integration reuses its exact blobs but is based on B. Never merge all of #1050
or #1118 into B #1114 indiscriminately.

## Original ownership map

| Responsibility | Canonical authority | This integration |
|---|---|---|
| Persistent Memory, exploration continuity/Question, Intent, skill, pattern registry | `CheckpointedCognitiveOwner`, its `PersistentCognition` and its canonical cognition file | Preserve; adopt only under original resident lock and disk readback |
| Live Self epoch, original mutation gate, CPU tasks, retirement/quarantine, Schema registration | `ResidentCognitiveWorkOwner` bound to the *same* owners | Preserve B's implementation verbatim |
| Native/Paper evidence, physical issuer, login/logout/reJOIN | Existing `OwnedResidentPhysicalBridge` | Preserve B's implementation verbatim |
| A/B normal Present and per-Self CPU scheduling | Existing B normal scheduler and paired Composite readback | Preserve B's implementation verbatim |
| R0 read-only context | `r0_cognitive_context_dev.py` only | New immutable facade, no owner/DB/scheduler |

These are **not** two autonomous cognitive Owners. In particular R0 is not a Memory
store, an ActionPort or an L1 decision maker. No second Native dispatcher/GPU lane
is introduced.

## Selected transfer boundaries

- B+D: new original issuer readback/commit/audit, original initial-source binding,
  Schema3 pre-login producer and source readback, recorded Schema codec, and the
  corresponding hostile tests and DEV documentation.
- B+D: replace the B-common-base implementations of Question store, typed
  checkpoint, Schema bootstrap, typed Stage28 cut/recovery and scoped original
  inference safeguards. **Do not replace** B's post-fork Resident, Bridge,
  real World runner or normal CPU scheduling code.
- R0: exact upstream read-only `r0_cognitive_context_dev.py`,
  `test_r0_cognitive_context_dev.py` and architecture audit.
- This integration: `test_b_bd_r0_consolidation_dev.py` checks shared original
  A/B owner identities, source-bound Question proposal against schema-qualified
  CURRENT, mutation-free readout and source drift failure.

**Potential unresolved compatibility:** B normal reJOIN has fresher source composite
types than the initial B+D issuer/Schema3 original admission chain. Transferring
a helper file does not prove that the older issuer may commit after B's reJOIN;
such a claim requires a new end-to-end original-source attestation and typed
generation proof. R0's current reader is an original *initial-source* adapter,
not an R1 migration or authorization to transplant outdated Present fields.

## Epistemic contract

- `CURRENT`: only valid `CognitiveSignal` from original source/epoch and the
  presently registered `SchemaSnapshot`. Raw Native WorldBody or a `LensClaim`
  cannot become CURRENT simply by traversing legacy 3Self.
- `RECENT`: optional, read-only subjective entries; no source-independent
  `OBSERVED` promotion. No automatic append of L2, timeout, cancelled or partial
  receipts and no new canonical RecentEpisodeBuffer.
- `RETRIEVED`: references and digest to **existing** Original Owner memories;
  `REMEMBERED` only, applicability `UNKNOWN`. It is not a C3 installer or new
  Memory database.
- Context use must recheck original source, registry revision, owner epoch and
  Memory digest. The old Present and source readers remain in place.

## Fail-closed / qualification matrix

| Claim | Required independent evidence | Decision |
|---|---|---|
| BD_HANDOFF_CPU_OFFLINE | Integrated original question/Schema3/issuer tests and exact-HEAD CI | Pending |
| B_R0_CONTEXT_ALIGNMENT_CPU_OFFLINE | R0 tests plus original B/B+D cross tests; no Context mutation | Pending |
| B_NORMAL_RUNTIME_REGRESSION | B's original A/B scheduler, 2nd reJOIN, stale token, typed source/Checkpoint | Pending |
| R1_SHADOW_ADMISSION | Single qualified B/I exact HEAD and Q independent source audit | **HOLD** |
| REAL_OWNER_SELF_ADOPTION | Authenticated original L1 choice, ticket/readback, single CAS adoption under current source | **HOLD** |
| REAL_WORLD / GEMMA | Original WSL/Paper/Native/GPU process witness and bounded test | **NOT RUN** |
| 3rd+ A reJOIN | Fresh independent source and generation-bound task qualification | **HOLD** |
| QUAL / SCIENCE | Independent qualified evidence | **NO_GO / NOT_RUN** |

The preexisting BD1b ADOPT synthetic bundle checks only structure and specified
source pins. Recomputed local SHA is **not** independent external authentication.
Do not promote a caller-supplied ADOPT value or a synthetic model response to a
real Self decision. PREPARED_UNRESOLVED must never be silently completed.

## Next owners and Q audit handoff

I #1061 may consume the branch **only after** the exact-head test matrix is
recorded. Q #1088 should independently compare Git blob identities, source
and session paths, original lock/epoch/currentness, Schema3 restore, reJOIN
Task tokens, WAL external anchoring, and verify that read-only R0 cannot trigger
Memory/Intent/Action effects. Q does not mutate this implementation branch.

No live Minecraft server, native Mineflayer process or real GGUF execution is
claimed by this document. All synthetic tests remain DEV-only.
