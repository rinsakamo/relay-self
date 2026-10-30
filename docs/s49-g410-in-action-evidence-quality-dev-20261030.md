# RelaySelf G4.10 DEV — in-Action UNKNOWN source evidence quality (read-only)

Parent: G4.9 final report HEAD `7183f2436663aa7dfbd766daf170e672353b4882` and physically tested exact code `24b526c7a0f52faa988f7aed836f5a7427e9fb94`. Parent 3 disposable Paper Worlds PASS; original controlled World 133 T2 rows with 9 bounded stable candidates and 124 UNKNOWN. Source-gap groups: 105 no T2-active Action, 5 pre-APPLIED ACK, **14 inside the original APPLIED→CLEAR Action** (DASH 4 / RUN 3 / JOG 2 / WALK 5). These are existing G4.9 physical observations, **not new G4.10 World results**.

G4.10 adds pure `join_g410_in_action_evidence_dev` to inspect the **14** original in-Action UNKNOWN candidates only, while validating 1:1 correspondence of **every** original G49/G48/T2 WorldTick and exact per-row T2 SHA and G48 SHA. It checks existing G1 original Paper frames by session/source_seq/world_tick, original T2 applied gait and G3 extra debit, Node G46 Action/effect generation, original post-control challenge, G1 already-computed stable two-frame kind and, for DASH, actual exact Paper modifier key/operation/amount and speed from the original captured snapshot. Missing axes stay explicit; a single DASH modifier snapshot, even exact, is **not** causal proof or a paired G3 debit. The original RUN Action may enter G44 JOG/WALK subeffects; the original S49 parent mode is intentionally kept separate from the Node callback mode.

Original G48/G49 UNKNOWN statuses, unchanged original G47 stable candidates and exact T2/P1/M0 receipts are preserved. The new after-run `g410_in_action_evidence_quality_dev.json` is generated **only when** both the original G49 gate and new explicit `--g410-in-action-evidence-quality-dev` plus `S49_G410_IN_ACTION_EVIDENCE_DEV_ONLY=1` are active. The file carries parent G49/G48/T2 whole-file SHA from original report, and each diagnostic row carries the original G49/G48/T2 per-row SHA. It records missing-axis counts, without modifying any source. Default remains OFF.

Scope: no motor command, longer input pulse, Paper callback, native reader, synchronous trace, T2 tick source, P1/M0 posting, WAIT recovery, R qualification or V science. Initial check is a small **Python 3.12 offline focused** workflow, not a new physical Minecraft run. Unsafe/mixed/altered source is rejected, not reclassified. A G1 stable kind is recorded as a source observation, **not an independent per-physics-tick acceptance proof**. The evidence-quality matrix is descriptive, not a new decision policy.

## Completed DEV implementation and physical evidence (2026-10-30 JST)

**Final result:** `DEV_ONLY / G410_REAL_PAPER_THREE_WORLDS_PASS / ORIGINAL_G49_UNKNOWN_PRESERVED / IN_ACTION_EVIDENCE_QUALITY_SHA_BOUND / HAZARD_T2_FAIL_CLOSED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.

- Isolated branch `self/dev-g410-in-action-evidence-quality-20261030`.
- **Exactly physically tested implementation/workflow SHA:** `f5365383976b91e755e84152be92035f6d0a0a56`.
- [GitHub Actions run #40983814098, attempt **2**, SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40983814098/attempts/2); [original Paper/Node/T2/artifact #12946780109](https://github.com/rinsakamo/relay-self/actions/runs/40983814098/artifacts/12946780109).
- Python3.12 focused including G4.10 tests, Ruff and compileall, original Node22 tests, Java21/Paper1.21.8 plugins and **three disposable real Worlds** all pass. Separate [G4.10 lightweight CI #40983625109 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40983625109), 24 Python focused tests.
- **Prior attempt 1 FAILED and retained:** [#40983814098 attempt 1](https://github.com/rinsakamo/relay-self/actions/runs/40983814098/attempts/1), artifact #12946376088. Controlled World stopped at first DASH Action because **no original S16 terminal** was observed, before G4.10 postrun diagnostic. G49 consequently refused absent CLEAR/terminal. Not reclassified as physical PASS; attempt 2 was a fresh disposable World at exactly the same SHA.

### Three-World source report

| Independent disposable World | Physical outcome | Original S49 / original T2 rows | Original G49 and G410 results |
|---|---|---|---|
| Non-opt-in G4 baseline | Goal reached, final error **0.402777597m** | 5 Actions / 51 T2 | G410 OFF |
| G410 controlled | Goal reached, final error **0.319681351m** | 6 Actions / **136 T2** SHA bound | Existing G47/G48 **10** bounded candidate / **126 UNKNOWN**; G410 diagnoses **15** in-Action UNKNOWN without changing 126 |
| Genuine zombie hazard | Original L0 INTERRUPT → S15 CLEAR → S16 UNKNOWN/FAILED; no following S49 Action | **33/33 pre-refusal original T2** SHA bound, T2 owner_failed=true | G410 diagnoses **5** in-Action UNKNOWN; original T2 refuses unsafe S16; P1 credit 0 |

Original controlled G49 gap census: **108** no T2-active Action, **3** before original applied ACK, **15** inside applied original Action (DASH **4**, RUN **3**, JOG **1**, WALK **7**), plus **10** existing stable candidates. The counts total exactly **136** original rows. The original **126 UNKNOWN remain UNKNOWN**. G410 in-Action diagnostics for this World report missing evidence axes:

| Missing axis over selected 15 original in-Action UNKNOWN ticks | Count |
|---|---:|
| Original G1 stable two-sample kind unavailable | **15** |
| Original T2 applied gait unavailable | **15** |
| Post-control challenge not observed | **8** |
| Exact DASH Paper modifier identity unavailable | **4** |
| Original G3 DASH debit proof unavailable | **4** |

These axes overlap; they are **not** additional WorldTicks or separate P1/M0 debits. A failed or missing modifier proof does not mean a physically failed DASH. The 108 non-Action T2 WorldTicks are neither counted as Action evidence nor declared physically WAIT/idle. Independent baseline vs controlled goal errors are not a causal performance comparison.

Original hazard: the genuine zombie was observed by the native reader at **seq68**, distance **0.681723m**, following RUN→JOG ACK **seq64**. Original CLEAR ACK **seq69**, S16 **seq70** terminal UNKNOWN/FAILED. No next Action, no P1 award, no second T2 owner. G410 keeps all original **33** T2 source rows and audits its five in-Action UNKNOWN rows read-only.

Workflow checks exact original G49 whole-file SHA, original G48 whole-file SHA, original T2 ledger SHA, original G49 per-row SHA and T2 per-row SHA for every G410 diagnostic, plus each produced sidecar's SHA. No independent packet-level causal input acceptance, calibrated motor speed/energy, complete per-tick gait or original G3 DASH debit is newly qualified. Unchanged G4.9 failure records and qualified source boundaries are retained.

No main, protected Draft #545/#634 merge, FULL, R QUAL or V SCIENCE run. This is a **DEV observability improvement**, not an upgrade to motor policy or accounting. Next G4.11 if useful: discriminate the 15 missing-G1 pairs between transition, stalled/blocked control and observation cadence using already captured Paper interval facts, without increasing physical motor holds or creating extra readers.

