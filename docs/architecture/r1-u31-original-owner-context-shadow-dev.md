# R1 Shadow — U31-preserving Owner / 3Self / Present responsibility separation

Status: **R1 read-only, opt-in CPU shadow under verification**. R2 product L1 prompt
or normal Present switching is **NOT** part of this PR. `QUAL_NO_GO` and
`SCIENCE_NOT_RUN` remain invariant.

## Immutable baseline read before implementation

| Evidence | Pinned identity | Scope |
|---|---|---|
| Unified I PR #1124 (R1 branch parent) | `d3034026a8eea3d2d4927527f5bc0d6ad0455457` | U31 source-bearing Original Owner and complete S1→S2 implementation |
| Q PR #1089 | `450734c54e1432ec70a8206952779b5ad82796d8` | Independent U31 original-world audit tooling; not imported to the R branch |
| U31 original evidence | `/home/rinsa/evidence/i-u31/` | **Only LocalCodex WSL has byte custody**; GitHub CI cannot inspect this path |
| Earlier R0.6 PR #1128 | `00229bd2e68257a4ef5e26608cdf075904c18820` | Older U4 read-only context contract, *not merged wholesale* |
| Schema/3Self #833 | original `three_self_present.py` + §15 | Semantics: CURRENT=Schema; RECENT=subjective accepted; RETRIEVED=existing Memory |

Independent U31 report: fresh isolated World once, zero reruns; two real Gemma
HTTP 200 selections, one Original B and one Native session. S1 terminal
WAL; Original Owner reviewed cancellation/Intent release, WAL anchor and
rearm; new S2 L1 request and separate Intent/Skill, START/STOP; two settled
canonical WAL rows, zero unresolved. Q6/Q7/Q8/Q11 original read-only audit
reported PASS for this bounded DEV run. **This R1 branch neither reads the
local original files nor redoes/certifies the real World**. It does not
claim that synthetic Shadow tests replay actual U31 source bytes.

## Responsibility map — avoid the false two-Owner refactor

| Contract / state | Original authority | R1 decision |
|---|---|---|
| Durable Identity / Memory / Question / pattern / retained cognition | original `CheckpointedCognitiveOwner.retained` and `cognition.json` | Only read under its existing resident lock and canonical disk snapshot |
| Owner live session/epoch, quarantine, registered Schema, tasks, concurrency | `ResidentCognitiveWorkOwner` for the *same* original B owner | Reuse lock and source validator, no new lifecycle manager |
| Native/Paper first-source, U31 physical issuer, S1/S2 WAL/ACK/STOP | Original I owned Native/Paper/WAL path | **No code changes**, shadow never calls ActionPort or model |
| Legacy `PresentFrame.three_self` Native OBSERVED LensClaims | Current legacy B reader | Read only for comparison; native Body OBSERVED is **expected** to be absent from schema CURRENT |
| `CognitiveContext.current` | B's original source+current `SchemaSnapshot` and `CognitiveSignal` | Read-only schema-qualified CURRENT; maintain exact Self/epoch/session/source/Need refs |
| `CognitiveContext.recent` | Already accepted original B `ExplorationContinuity.questions` | Project only persisted OPEN `issuer-adopt` Questions as **MYSELF HYPOTHETICAL**; not a fake L1 result or full RecentEpisodeBuffer |
| `CognitiveContext.retrieved` | Original B `PersistentCognition.memories` | Existing R0 digest-pinned Memory refs; `REMEMBERED` and applicability `UNKNOWN` only |
| L1/L2 inference, Scheduler, Skill/Intent and Physical Action | Existing unified I original Owner path | Not switched, adapted, registered, or called |

## Shadow implementation and diagnostics

`compare_original_owner_r1_shadow` is an *opt-in function* in
`src/relay_self/r1_owner_context_shadow_dev.py`. Its only direct runtime
calls are original B resident `read_present_cpu`, existing
`read_original_owner_current`, `retrieve_original_owner_memory`, canonical
`load_persistent_cognition` and `context_is_live`. All run with the
**existing** `resident.lock` (RLock).

- Scope: initial Stage28 owner-source shape only (`boot/world/links`). It does
  not claim that the separate post-reJOIN `RejoinedOwnerSource` / continuing
  Composite / U31 later POST model source is qualified by an initial receipt.
- FIRST READ: under lock verify same Original B owner identity, read original
  persisted `cognition.json`, read legacy Present and schema-only CURRENT.
- RECENT: only existing original Owner persisted OPEN Question with
  `issuer-adopt` origin, bounded issuer record keys and actual ADOPT choice
  enters the subjective lens. `generation=0` means **not an L1/L2 model
  generation**; `task_ref=owner-question:...` is explicitly an owner Question
  reference, *not* a fabricated `CognitionResultReceipt`. This is only the
  first justified accepted-cognition subset; no sleeping epoch aggregator, no
  automatic L2 append and **not source-proven GPU admission**.
- RETRIEVED: only original owner Memory ID + digest, not new Memory content
  copies or C2/C3 applicability promotion. Missing/unadopted selectors HOLD.
- SECOND READ: compare source, Schema, epoch, signals, Need/Attention,
  legacy Present stability, retained owner pointer/data and context current
  source+Memory readback. Unexpected differences are collected as stable
  mismatch codes in immutable `R1ShadowComparison`.
- **Cached RECENT/RETRIEVED recheck**: `r1_shadow_is_live` rereads the original
  cognition file and current Owner-retained Questions, recreates subjective
  RECENT, and verifies the original Context/Memory digests. Closing or changing
  an accepted Question invalidates a prior Shadow even if the Native/Paper
  Source revision stays unchanged. It can only return a negative/positive
  read-only *freshness* answer, not an L1/physical permission.
- The Stage28-only adapter requires the original **first-login resident epoch
  1**. Artificially advancing epoch with old Native/Paper boot/links must HOLD;
  reJOIN has an independent composite/revision and is outside this comparison.
- EXPECTED semantic differences: legacy `OBSERVED` SelfBody claims are not
  imported to Schema CURRENT; subjective accepted Question stays HYPOTHETICAL;
  old Memory stays REMEMBERED with UNKNOWN applicability. These do not become
  false incompatibility errors.
- Status `MATCH/MISMATCH/HOLD` is **diagnostic only**; the R1 return object
  has no write/GPU/Physical permission; all three grant flags fixed false.

## R1 adversarial and full CI obligations

Run full exact-head `pytest`, Ruff, repository contracts, Mineflayer
adapter, Paper witness against the **same** U31-parent R1 commit. New tests
cover both A/B, no Question adoption or file changes from a shadow read,
unknown need, already Owner-persisted issuer-adopt Question vs mere proposal,
declined/failed LLM non-adoption, wrong source/epoch/Owner/disk/read drift,
Memory digest/context validity, semantic expected differences, mismatch
diagnostics and frozen non-grant report. Existing U31 owner reviewed
Skill/Intent S1→S2 and physical/WAL regression suites are left unchanged.

## Q independent compatibility gate

Q source HEAD `450734c54e1432ec70a8206952779b5ad82796d8`
must independently confirm no R diff edits original U31 issuing/STOP/ACK/WAL
production files, original B owner lineage, source/epoch recency,
no native 3Self claim promoted into CURRENT, accepted Question provenance not
mistaken for a live original L1 ticket, Memory read-only, and exact-head CI.
The local original `/home/rinsa/evidence/i-u31/` can be read only in
authorized WSL custody; **do not invent a byte-level source check in GitHub**.
If Q has not run on this R HEAD, report `Q_R1_INDEPENDENT_REVIEW_PENDING`,
not Q PASS.

## Exit scope

R1 is considered **CPU/offline read-only SHADOW PASS** only when original B
state, disk bytes, old Present and physical/S1→S2 regression remain unchanged
and new diagnostics/tests pass under one exact commit. This is **not** a
general real-World Shadow certification or R2 migration; Product L1 remains
wired to its existing Original Owner path. Hold R2 separately.
