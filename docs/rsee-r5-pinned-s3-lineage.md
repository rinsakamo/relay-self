# RSEE R5 — exact S3→S6→S7 lineage for R2/V read-only review

Authority #575, Self product #537, V #595. Parent R4 [#602](https://github.com/rinsakamo/relay-self/pull/602) exact `07eb6fd91dcb038ae1846705d865520c19f261c5`. This R5 is one R-only child; S3 #598, S6 #604, S7 #605, L, V, main and original WSL2 evidence are **not changed**.

## Material bug fixed

R4 requires `expected_head == S3_HEAD` even though the **actual** S6 controlled NoAI physical run emitted from exact `a6ed8ed6b99dd09edcaa6cc9e5cefc08778aec8f` and S7's prospective source emitter runs only from exact `d23378d0c2d8271997389f6296a9bd018e488327`. Substituting S3's HEAD to make R4 accept S6 would be **false source identity**.

Independently checked Git ancestry:

| Source | Frozen exact HEAD | Qualification scope |
| --- | --- | --- |
| S3 #598 | `6f493b7a559dd72ea365998b9eadbd35fd7eb9b4` | Offline source-shaped original S3 contract |
| S6 #604 | `a6ed8ed6b99dd09edcaa6cc9e5cefc08778aec8f` | One consumed controlled physical trial; **derived output only; raw bridge originals were not archived** |
| S7 #605 | `d23378d0c2d8271997389f6296a9bd018e488327` | Prospective predecode Mineflayer JSONL source producer; actual physical S7 run **NOT_RUN** |

`S3→S6` = 20 commits ahead/0 behind; `S6→S7` = 11 ahead/0 behind, verified by GitHub compare; CI asserts exact independent git ancestry again. These are **three explicit allowlisted exact HEADs only**. A later S8+ or unrelated sibling must be independently audited and added deliberately, not admitted via arbitrary ancestry or a user-provided SHA.

## Fail-closed semantics

R5 updates only the inherited R4 read-only adapter and its tests.

1. Unknown exact source HEAD => `RSEE_R4_EVIDENCE_CHAIN_BLOCKED`, even if otherwise plausible envelope. S3 head remains a valid source-shaped fixture.
2. **Historical S6:** S3-derived Memory/events can be compared for source/session consistency, but a retained Action leads to `RSEE_R5_S6_DERIVED_ONLY_RAW_NOT_ARCHIVED` (CLI exit **2**, R2 not run). Even a synthetic valid R1 envelope does not retroactively create Mineflayer stdout originals. One reported controlled Action and 0 learning/Habit remain factual **operator reports**, not R2/V-qualified byte history.
3. **Prospective S7:** require original predecode `native_bridge_received_original.jsonl` in the independently supplied R1 envelope's original-receipt set, plus separate explicit original Action/OUTCOME evidence; treat `native_bridge_sent_original.jsonl` and `native_bridge_source_receipt.json` as **outbound attempt and derived index**, never Action outcome. R2 independently hashes every referenced existing original file, matching exact S7 HEAD, RSEE profile SHA and session. Missing/drifted/foreign original => BLOCKED.
4. Any positive return stays `RSEE_R4_DERIVED_MEMORY_MATCH_R2_BYTES_REVIEW_ONLY`, with `native_source_semantics_attested=false`, `action_correlation_attested=false`, `v_admission_granted=false` and `science_qualified=false`. It is **not** a signed World success, full S49/S16 semantic verification, or model/learning/behavioral advantage.

No S6 historical stdout archive exists to inspect retroactively. S7's archival code is qualified **only offline**, so R5 does not have an actual S7 source directory or independent envelope to run against. R4's existing CLI remains unchanged and pure by default.

## Existing S6 index identities are not interchangeable

The original host operator later reported an independently read-back **32-entry original index** and **39-entry final index**. The user's SHA starting `baa0e633...` and earlier GitHub index starting `b22598cc...` referred to **different index artifacts**, not known corruption. This was reported to V #595 / #544, but not reread by this GitHub code-only R lane; neither index is the missing original Mineflayer bridge byte stream. Do not overwrite, normalize or fabricate the historical S6 index.

## Offline qualification

R5 runs new negatives for no-retroactive S6, expected-head mismatch, S7 missing/fake original, outbound attempt mislabeled as OUTCOME, and byte tampering, while retaining R1–R4 tests. Independent checkout S7 #605 runs its genuine predecode source tests and dry-run in addition to S3/S4/L1/V1 frozen owner tests. No cross-branch merges. The user-host WSL2 shared Python/npm root, Minecraft, Java, GPU, LLM, World, physical native actions and archived original receipts are untouched.

A genuine **S7** R2/V review still requires a **separately authorized future one-shot S7 physical trial**, complete immutable predecode originals, separate S-owned real S49/S16 Action evidence, an independently qualified R1 envelope and an independent V audit. An S7 permission is **not** created here. R5 grants no production or G3 science GO.
