# R Lane R0.5 — Original Owner Context Compatibility & R1 Preflight (DEV/offline)

Status: **R0.5 under CI / R1_SHADOW_ADMISSION_HOLD / R2_HOLD / QUAL_NO_GO / SCIENCE_NOT_RUN**.

## Immutable evidence inspected first (2026-11-22)

| Lane | Review artifact | Observed HEAD | Relationship |
|---|---|---|---|
| B/B+D/R0 | Draft #1119 | `f43d6f1a14b20f041794bdb0b820a33ebf513f5c` | R0.5 branch parent and sole Original Owner lineage |
| R0 upstream | Draft #1118 | `fcceaa8ac359b891550f2cbc021d85337c4a1da5` | R0 context selected into B #1119, not merged wholesale |
| I2 original | Draft #1080 | `d8d7f1d9337d4a4e1937009ce9230f386f0e4716` | Separate history; R0 file absent at this HEAD |
| E1/E2→I2 | Draft #1120 | `def8edb6cc3094f655f1311cb297def23e6ae2c9` | Separate I2-based history; no B scheduler adoption |
| Q independent | Draft #1089 | `b8e5672bbba58829ef0bb968fb9462970a7b293f` | No independently authenticated R0.5 source verdict |

**Do not infer that the B and I histories form one integrated exact-HEAD runtime from this table.**
A green CI run on each branch separately cannot establish cross-branch identity,
original Native/Paper custody or Q independence.

## Scope actually implemented

- Strengthen R0 `CognitiveContext` validation against a foreign Paper world-session in
  `Recent3SelfView` and caller-forged `RetrievedMemoryBundle.query_need_refs`.
  No new mutable store, evidence producer, Memory read path or capability.
- `audit_r05_initial_owner_context` compares the **existing original B**
  `ResidentCognitiveWorkOwner.read_present_cpu` with the R0 schema-only
  `read_original_owner_current` for the same Self, resident lock, initial
  Native/Paper source, registered Schema snapshot, and actual Schema Need.
  Original legacy OBSERVED World/Body claims are never promoted into R0 CURRENT.
- A second original Present read and `context_is_live` revalidation reject
  drift during the synthetic comparison. Neither read is an independent real
  producer witness; this remains a bounded, *non-atomic across real sensors*
  CPU compatibility check.
- `R05CompatibilityAudit` is a frozen non-permitting diagnostic object.
  Its R1 admission flag is always false, and all independent R1 gates remain
  explicit even when the Stage28 synthetic compatibility check passes.
- Adversarial tests cover A/B identity, unchanged owner files and state, old
  Present regression, native/Paper/epoch/registry drift, foreign owner,
  unregistered Schema, retired Self, manipulated legacy source, interleaved
  drift, old World RECENT, fabricated RETRIEVED Need, and attempted R1 promotion.

## Precisely bounded reJOIN / Schema3 / C/I handling

The original Stage28 initial-source `BD1bOwnerSource` is **not**
the newer B reJOIN `RejoinedOwnerSource` or second reJOIN's additional
composite/source-generation proof. The R0.5 reader **does not accept**
`initial_receipts`/`historical_composite` and does not adapt a reJOIN to the
old initial boot/link shape. Such a probe must remain HOLD. Existing B typed
A/B Schema3 and second A reJOIN CPU tests remain unchanged; R0.5 does not
claim to have requalified these for normal R1.

## R1 prerequisites — all external and still HOLD

1. **B/I single immutable integration HEAD** with original Resident, Skill/Intent,
   Native/Paper, Schema3, reJOIN and the R0 read-only contract; no second Owner.
2. **Q independent audited actual original Native/Paper/Owner source custody**
   with externally anchored raw receipts and source revisions, not recomputable
   attacker-controlled SHA or self-reported provenance.
3. **Exact-HEAD combined adversarial CI** including B second reJOIN, typed
   Schema3 restore, old Present, I2, C1/C3, E source and R0.5 tests.
4. **A specifically approved read-only R1 shadow** with zero state mutation,
   no additional Physical action, no new GPU or L1/L2 ownership. This is a
   future action; the R0.5 helper does not launch or approve it.

Until the prerequisites are independently verified, the only valid outcome is
`R0_5_STAGE28_CONTEXT_COMPAT_CPU_OFFLINE_DEV` if tests pass, **not**
`R1_SHADOW_ADMISSION_PASS`. Real World, Gemma, QUAL and SCIENCE remain not run.

## Q audit handoff

At the eventual B/I convergence SHA, independently check:
- Git Blob equality of R0 source, single B original Owner / resident link,
  original B Native/Paper vs R0 context source and Schema, stale/replaced owner
- RECENT historical session/epoch status, cancelled/timeout L2 and no OBSERVED
  promotion or automatic memory append
- RETRIEVED real original Memory digest/readback, query Need identity, no C3
  applicability upgrade
- original Stage28 Source vs reJOIN Composite and second generation token,
  original Schema3 checkpoint generation, C1/I2/E2 regressions, WAL original
  PREPARED_UNRESOLVED preserved
- no additional ActionPort, owner mutation or normal prompt routing from R0.5.

The Q lane must determine qualification independently. This branch changes
only R-owned context/preflight/tests/docs; B, I, C, E, Q branches are untouched.
