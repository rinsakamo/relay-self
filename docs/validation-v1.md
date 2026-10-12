# RelaySelf V Lane V1 — independent evidence & evaluation baseline

**Authority:** #544 scientific discrimination; #537 Self 1.0 product; #426 hypotheses. Frozen #46 / #415. S #590/#592, L #421/#431/#432, R #575/#593. R1 source base `7c9a013f10e55172f6415deb9002ce7d4417f504`, stacked on Golden #588 exact `34820f6bf391c77f325d7c29d3b779a33e3ca835`. All sibling S/L implementations remain **read-only references**, not merged. No modifications to R1, the Golden, or protected main.

## Scope and independent classification

Three distinct independent questions (never promote one into another):

1. **Engineering validity** — typed owner authority, source/receipt identity, execution continuity, fail-closed Action/LLM/Memory, original data integrity. A green source-shaped CI is an engineering contract result, **not a physical execution**.
2. **Behavioral validity** — one owned Minecraft session achieves observable **task-goal success**, with actual terminal S49/S16 Action receipts; an executed move without a goal label is not verified success.
3. **Scientific validity** — a prospective, held-out, source-matched cheap-baseline comparison shows measurable **incremental World outcome benefit**, then resource-adjusted benefit and independent transfer. Merely changed decisions, more observations or tokens are not gains.

`experiments/validation/v1_baseline.json` inventories 18 claims with origin, exact HEAD if known, original source session if known, reported digest if known, status and authority. `null` means UNKNOWN; it is **not** a zero or proof of absence. Origin `GITHUB_ISSUE_RECEIPT` or `GITHUB_CI_REPORT` **never** means that the original WSL2 bytes were independently opened. No row in the inventory has an independently validated local-source qualification. All claims are bounded to their actual lane/branch; unmerged sibling features do not exist merely because they are documented.

| Qualification family | Present bounded evidence | Missing proof / V1 conclusion |
| --- | --- | --- |
| Offline source/contract test | R1 #593 3/3 CI; S1 #592 twice 3/3 CI; S0 #590 3/3 CI | PASS as **offline only** |
| Source-shaped Action simulation | #590/#592 mocked typed S49 outcomes and denial tests | PASS **source-shaped**, not World |
| Physical World observation | #588 original report: three observations and three L0 decisions | **Reported physical**; optional three-original-file audit below |
| Physical Action terminal | #588 WAIT 1 / MOVE_AWAY 2; two terminal executed movements ~0.627m | **Reported physical**, goal UNKNOWN |
| Verified task-goal | No independent signed positive goal receipt | UNDETERMINED / product incomplete |
| Observational Memory | #588 two source-linked observation episodes; no promotion | **Reported physical retention**, not S10 |
| Qualified S10 learning | #588 in-World updates 0; offline S10 structure elsewhere | **NOT_RUN** for in-World learned improvement |
| Qualified S11 Habit | #588 grants 0; no physical learned reuse | **NOT_RUN** for in-World Habit |
| Real L2 / stale result | #588 one attempted backend task, `EXPIRED_WORLD_ADVANCED`, no Action authority | **Reported**, no verified generative advantage |
| Predictive/adaptive advantage | #544 D1–D4 cheap exact optimum, C11 majority dominates expensive; some toy ADAPT_GROUP improvements | **G3 SCIENCE NO-GO** on current family; transfer/generalization unverified |
| STOP/cleanup/UI | PIDs/bind/VRAM reported; #589 replay contract tests | NO independent STOP ACK; physical RelayUI inspection NOT_RUN |

### Golden independent audit (read only)

First three Golden runs were one-shot. **All three permissions are consumed**. The third source reports exactly one native S49 session, 3 observations and decisions, 2 Action OUTCOMEs, 2 observational Memories, 1 expired L2, 0 learning/Habit/goal grants, missing raw original L2 HTTP, STOP ACK unproven. #537 reports original 69-file index digest `57f0f55079943f8a9c714f166213917ca625ab5e143c4102a927fa4de7195fb0`. An index digest in a GitHub comment **is not** a recomputation.

Default:
```bash
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD"
python -m experiments.validation.v1
```
Reports `GITHUB_REPORTED_ONLY`, original bytes `NOT_RUN`. Uses no native host probes/POSTs.

Operator WSL2 optional, only when the sealed originals **already exist**, using shared Python 3.12:
```bash
BASE=/home/rinsa/.local/share/relay-self/rsee-1.0-20261011
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD"
export PYTHONDONTWRITEBYTECODE=1
"$BASE/venv/bin/python" -m experiments.validation.v1 \
  --golden-dir "$BASE/golden-third-20261011-authorized-once"
```

This command never writes evidence, installs dependencies, starts Java/Node/Minecraft/llama, acquires a lease or issues an Action. Only three known source files are verified with R1 `read_only_receipt_index` and `validate_evidence(..., verify_receipts=True)`, then existing `self_timeline.timeline` replays S49/Memory/L2 typed source constraints; all digests **must** exactly match the #537 archived report. No fallback, raw reconstruction or repair. It does **not** independently verify the full 69-file index, all HTTP request/response bytes, contemporaneous process authenticity, native STOP ACK or a signed World goal. If any original is missing/symlinked/tampered, stop `V1_EVIDENCE_BLOCKED` without reattempting physical work. The local-path command has **not been run by this GitHub lane**; the actual WSL2 directory is inaccessible here.

### Self 1.0 product acceptance (#537)

Each criterion needs **its own** authentic source and receipt; UNKNOWN is not success:

| Criterion | Admission witness | Current V1 status |
| --- | --- | --- |
| Same-session Observe → Decide → Action → terminal | exact S49 session, correlated request, Action ID/OUTCOME, native before/after | Golden **bounded reported yes**, new #592 path NOT_RUN physically |
| L0 while L2 active | actual concurrent timestamps/World L0 callback; not UI order | Separate #412 history reported; **not verified for new S1** |
| Stale L2, invalid Action prevented | original authorized-action ledger and stale decision proof | Golden stale no-Action; #592 CI test only |
| Action UNKNOWN never success | fail-closed typed UNKNOWN; no invented outcome | contract PASS; new real runtime NOT_RUN |
| Memory provenance | original S49 action/session/frame digest -> retained episode | Golden two linked reported, new S1 owner NOT_RUN |
| Progress into next epoch | real one-session epoch n -> epoch n+1, not test fixture | Golden 3 decisions; **autonomous repeated session** not proved |
| Shutdown/resource release | independently observed owned PIDs/ports/VRAM and separate STOP ACK | process/port/VRAM reported; STOP ACK UNDETERMINED |
| RelayUI mirrors original | independent source-to-view identity and no operator-invented event | #589 read-only contract CI; host rendered UI NOT_RUN |

**Product decision:** `SELF1_PRODUCT_ACCEPTANCE_UNDETERMINED`. #592 offline success neither means new World launch was tested nor completes goal-directed autonomous reuse. Product development continues under S owner; no science gate blocks routine code integration.

### Learning contract (L owner, V evaluator)

Compare **Retention OFF**, **exact episode/tags lookup**, **cheapest source-matched deterministic rule** (including finite decoder, lookup, degree-2/one-bit as appropriate), **qualified retained reuse**, and an additional cognitive mechanism only if genuinely qualified. Fix the original input source receipts/session/heldout lineage, feasible action set, stopping rule and same cognitive budget **before** comparing. No oracle truth, hidden evaluator rule, unexecuted future or counterworld may enter a chooser's Present/Memory.

Track separately: next decision changed; original subsequent *executed* World outcome; novel context transfer; mismatch response; distribution-shift recovery; actual retrieval+learning CPU time/bytes/tokens/energy when observed; provenance/authorization violations. Learning from a dictionary alone is not evidence of new cognitive advantage. B24/B25/B29 contain concrete **cheap equal-performing** counterexamples; native production S11 success remains unproven.

### Prediction & epistemic-value contract (A/#544)

Four truth classes must be explicitly typed: (i) actual observed future after the chosen Action, (ii) action-conditioned hypothesis before intervention, (iii) unexecuted counterfactual **hypothesis**, (iv) evaluator-only potential outcome after independent reset. Never train/score an agent using class (iv) as input. Held-out lineage must be disjoint by World mechanism, not only by permutation; equal initial states need independently qualified intervention/reset equivalence. Fix candidate mapping/order controls. Report proper predictive score/calibration (G1), discrimination/change of chosen Action (G2), independent actual World benefit (G3), and observation/resource cost (G4) **separately**. If independent counterfactuals are unavailable, label `UNDETERMINED`. More observing/token generation is not itself positive epistemic value. D1–D4 cheap exact optimum remains a scientific **NO-GO** for expensive G3.

### Resource-value contract (C/#544)

Record actual wall latency (p50/p95 across valid repetitions when authorized), CPU process time, counted tokens, GPU utilization/VRAM, and **measured power only if calibrated hardware provides it**, separately from symbolic work. Distinguish actual GPU joules from Minecraft hunger/health and experimenter-defined virtual fatigue; any mapping is a prospectively specified bridge, not physical identity. A selected costly mechanism must improve real World utility after same-source cheapest viable rule and end-to-end retrieval/parser/LLM cost. C11 fixed Majority was better than expensive selector in its synthetic utility; ADAPT_GROUP has bounded synthetic positive evidence, not LLM/Minecraft transfer.

### G0–G5 prospective science admission

- **G0 Source validity:** exact runtime/model/World/Action/OUTCOME/Memory identity and independently attested source; forbid leaks, stale/success laundering. Same input evidence + candidate set for all arms.
- **G1 Measurement validity:** fixed metrics, evaluator truth isolation, independent heldout, negative controls, explicit UNKNOWN/missing/error, uncertainty.
- **G2 Cheap baseline:** at least matching tags/lookup/exact cheap rule, measured at the actual device class. If baseline dominates within budget, G3 NO-GO.
- **G3 Incremental behavioral benefit:** independent real goal/outcome benefit from intervention, not just a choice change or synthetic test. Otherwise NO-GO or UNDETERMINED.
- **G4 Resource adjustment:** genuine end-to-end measured cognitive cost minus measured World gain. Nonpositive gain means NO-GO.
- **G5 Independent reuse/transfer:** later lineage and distribution shift evaluated without source leakage. Any adaptation requires fresh original World data.

V1 `admission` only parses *proposed* comparison claims and makes fail-closed GO candidate screening; it **never** authenticates caller-supplied booleans, declares science-qualified, grants execution, or invokes a simulator. A matched positive proposal returns `UNDETERMINED_INDEPENDENT_REVIEW_REQUIRED`, not GO. Unequal source fingerprints/session/actions, oracle leakage, stale L2 Action or UNKNOWN promoted to success fail G0. Nonpositive matched outcome gain fails G3; resource nonpositive fails G4. At present: G0 real-world science attestation incomplete, G1 model forecast unmeasured, G2 cheap dominance exists, G3 **NO-GO**, G4–G5 **UNDETERMINED**. A new LLM/GPU/Minecraft science trial requires separately qualified source/controls and explicit one-time authorization.

## Handoffs and execution boundaries

- **S → #537:** original new S1 physical session with 3+ natural decisions, goal witness (or explicitly UNKNOWN), source-correlated Action/Memory, independent cleanup STOP ACK when actually available, UI source match. No fourth trial implied.
- **L → #431 / #426:** authentic source-qualified learning update and later S11 reuse; strong same-experience cheap tags/one-bit/finite rule comparator; unseen context + mismatch trials. Do not promote B29's schema CI to a valid real L2 forecast.
- **R → #575:** optional *read-only* operator attestation of the three sealed Golden originals, R1 source index and profile at audit; observe that an R1 preflight is **not** Golden launch authority. Do not silently fill absent raw L2 wire or STOP ACK.
- **V → #544:** preserve #46 NON_DISCRIMINATING and #415 36 valid/18 matched unchanged; record cheap dominance and positive synthetic counterexamples without merging them into real World claims.

## CI and operational ceiling

Tests: `python -m pytest -q tests/test_validation_v1.py tests/test_rsee_shared_runtime.py`; full regression: `python -m pytest -q`; lint: `ruff check src tests experiments adapters observability`; repository contracts: `python tools/check_repository.py`; Mineflayer protocol: `npm run check --prefix adapters/mineflayer`. GitHub workflow uses only mocked offline checks, no actual model/World launch. No per-worktree runtime environment on the user's WSL2 should be created. Source operations use the R1 code and existing shared RSEE Python/Node roots when on the actual operator host.

**All current V1 results remain source/issue/CI-audited only until separate original-byte and physical host evidence is provided.** Draft PR remains open and unmerged. No new small research Issues or PRs are required for this baseline.

## V1 continuation — L1 independent cheap comparator / S1 isolated dry-run

After the V1 baseline froze, L1 [Draft #594](https://github.com/rinsakamo/relay-self/pull/594) became available at exact `40db58d548ea31c4a70acabcc71b0954c7b6ce42` with source `src/relay_self/experience_bridge.py` blob `326d4f14e2addc465f97ff452572865f3494325d`. L1 intentionally implements `cheap_tag_baseline` by calling `retrieve_experience` itself; its built-in parity check therefore cannot serve as an *independent* discriminator.

V1's `experiments/validation/l1_independent_audit.py` uses eight **V-owned source-shaped typed-Action** cases and an independently implemented elementary episode/tag lookup on exactly the same retained Memory and query (Retention OFF, recall, foreign session, stale revision, unadmitted digest, cue mismatch, Action UNKNOWN, contradictory original outcome). L1 code and V oracle run as two distinct implementations against matching episodes and identical query budgets. Pinned sibling L1 HEAD/blob/clean tree and actual imported source path are checked first. The observed Action reference is not treated as a goal, learning update, Action grant, or success claim. This check **does not** measure physical World benefit, retrieval CPU costs, cross-lineage generalization or model-generated predictions. Matching all source-shaped cases is engineering parity only; if source and independent oracle disagree, fail closed; never relax expected negative outcomes to obtain PASS.

The exact S1 #592 sibling HEAD `75054188f1c7e8141690697794b6e705495de205` is checked separately in an isolated read-only checkout. Only the default `S1_DRY_RUN_NO_EFFECTS` CLI is invoked (no physical opt-in). This is a **compatibility smoke**, not a merged S1/L1 end-to-end test and not native Minecraft.

Both sibling branches are checked out at immutable full SHAs *inside ephemeral GitHub CI only*. The parent #595 branch, L1 #594, S1 #592, original Golden #588, main and shared physical RSEE assets are not modified. There is no new World simulator, machine-learning mechanism or model call. On the actual WSL2 host, no new interpreter/npm root is provisioned.

**Provisional V outcome:** cheap reference cannot presently be beaten by L1's equivalent full scan on those bounded source-shaped cases. V records equality, not science positive. `G3_SCIENCE_NO_GO` remains for the present prior family; physical S1↔L1 integration/Goal/S10/S11 is still `NOT_RUN`. A future claim needs *independent real World-source* evidence and actual resource-benefit measurements.

## V1 follow-up — real S1 event schema ↔ L1 authority handoff audit

The **unchanged actual S1 emitter** [#592](https://github.com/rinsakamo/relay-self/pull/592), exact `75054188f1c7e8141690697794b6e705495de205`, produces `SELF1_BOUNDED_WORLD_EVENT_V1` JSONL. Its `action_outcome` includes typed decoded Mineflayer before/dispatch/clear/after source frames and their canonical SHA256, but its top-level log is a **projection**: `source=S49_OWNER_EXPLICIT_REAL_OR_SYNTHETIC`, not an independent attestation of actual physical origin. S1 `retained_revision` is the existing learning-preference revision, **NOT a World state revision**.

The **unchanged actual L1 input** [#594](https://github.com/rinsakamo/relay-self/pull/594), exact `40db58d548ea31c4a70acabcc71b0954c7b6ce42`, requires a **current original S16 `ActionLifecycle`**, source-matched `ActionOutcomeInterpretation`, **S-owner-supplied World revision**, and **S-owner-admitted source digest** before `qualify_episode` and a later `retrieve_experience`. These original typed authority fields are **not** reconstructed from an event feed. L1 hint is not Action authority.

V now performs a **source-based boundary test**: `experiments/validation/emit_s1_fixture.py` executes #592's own offline `test_self_continuous_host._fixture` via one pinned sibling checkout to generate actual S1 emitter JSONL with a synthetic WAIT→MOVE_AWAY→one typed original-source-shaped terminal outcome, *without* Minecraft/Java/Node/LLM/GPU, while `experiments/validation/s1_l1_boundary.py` independently checks stream origin fields, indices/session, decision/request/outcome ordering, same-source decoded native receipt SHA256, original frame/provenance/dispatch/clear order, independently recomputed 2D movement, terminal counts and explicit no-learning/no-goal flags. There are V-owned negative controls for unknown, replay, missing terminal, stale index, forged source, goal promotion, tampered retained state, and missing L1 admission. The checker **never** manufactures ActionLifecycle, World revision, source authorization, L1 Memory, S10 update or S11 Habit.

A structurally correct synthetic stream returns `S1_LOG_CONSISTENT_NO_L1_ADMISSION`; an uncertain/incomplete Action fails closed or returns `S1_FAILURE_NO_L1_PROMOTION`; an invalid stream rejects. **Even with one synthetically observed move, S1's event feed alone is insufficient to independently qualify L1 experience retention**.

**S owner-specific next product interface**: expose or separately record *the already existing source-qualified* S16 current typed Action/Outcome owner records, exact World state revision and independently admitted original digest **without reissuing Action**; only then may L validate `qualify_episode` and return a read-only memory reference. R's verified original receipts and post-stop ownership remain separate. V will not infer them from L0 `epoch` or `retained_revision`. This is a measured **S↔L handoff gap**, not new experimental research. No hidden LLM/model target, no scientifically qualified improvement, no new physical grant.

Original Golden #588 remains **operator reported**, WSL2 raw original bytes **NOT_RUN** in GitHub; G3 science **NO-GO** and product acceptance **UNDETERMINED**.

## V1 follow-up — independently bounded S6 reported physical trial and R5 source ceiling

S6 controlled trial [#537 #6116683016](https://github.com/rinsakamo/relay-self/issues/537#issuecomment-6116683016) was **one real operator-run Minecraft session** at exact S6 [#604](https://github.com/rinsakamo/relay-self/pull/604) HEAD `a6ed8ed6b99dd09edcaa6cc9e5cefc08778aec8f`. Its original host-only operator report gives session `a5cdc400-572a-41ee-b411-e7399bbb80fd`: 187 outer observations, 1 controlled stationary NoAI zombie entity frame, L0 MOVE_AWAY, 1 original S49/S16 terminal `executed` reported, movement 0.6269065734210617m, one S3 observational Memory, zero learned S10 updates/S11 Habit grants, no L2 model calls and no physically attested independent goal. This is **bounded controlled target behavior**, not natural spawning, hostile survival or an autonomous learned policy. S6 authorisation was consumed and cannot be replayed.

S7 host-local [#537 #6117549533](https://github.com/rinsakamo/relay-self/issues/537#issuecomment-6117549533) reportedly re-read the two **different existing** index artifacts: `SHA256SUMS` own SHA `b22598cc985d5fce4f8c8ffbb15452a8e6f79578aa18d5326650eaa4143536e7`, 32/32 entries; `FINAL_SHA256SUMS` own SHA `baa0e633a10f2cfd64107d1aee77250e56b4fa56405c826ff27e2f3f3652fd47`, 39/39 entries. The latter contains former 32 unchanged and seven additional post/report/index items. **No collision or corruption follows from the different index digests**, but the GitHub V reviewer has **not independently read these host-local original bytes**. Derived `session_events.jsonl` SHA `6626e94d...` and observed Memory SHA `15440763...` are not original Mineflayer bridge byte archives.

R5 [#607](https://github.com/rinsakamo/relay-self/pull/607) frozen exact `364f4cc66fbe393717d31adce22747be17446dd8` changed the frozen R4 identity gate to **allow only exact pinned S3/S6/S7 source heads**. Crucially: actual physical S6 head is a descendant of S3, not S3 itself; head spoofing would be invalid. For S6 with retained S3 observation, R5 emits `RSEE_R5_S6_DERIVED_ONLY_RAW_NOT_ARCHIVED` and CLI **exit 2**, refusing even a purported retroactively fabricated R1/R2 original-byte envelope. The original predecode bridge JSONL did not exist in archived S6. S7 #605 has future-only original predecode capture, but **S7 physical trial is NOT_RUN**; its own outbound attempts and derived SHA index cannot be Action outcomes.

New V-only `experiments/validation/s6_report_review.py` and frozen `s6_report_claims.json` maintain a separate **reported-source evidence class**, pin exact operator URLs, S6/S7/R5 source identities, Action, counts, SHA identities and absent scientific witnesses, with tampering/false-permission negatives in `tests/test_validation_s6_report.py`. It does **not** read the physical WSL2, fabricate raw S6 receipts or infer a valid source R2 envelope; GitHub assertions only check the fidelity of independently reported *claims*, not actual original bytes. The V sibling CI checks the **unchanged R5 source and tests** from a separate exact-SHA checkout, no merge.

Engineering status: real S6 bounded World/Action cleanup and two-index readback **operator reported**, V byte-level independent physical origin and native STOP ACK **not proven**. Behavioral status: one **controlled intervention** MOVE_AWAY original Action/observational Memory reported, not goal/autonomy or natural danger. Scientific gates: G0 raw source for independent V **BLOCKED**, G1 prospective heldout **NOT_RUN**, G2 strongest same-source cheap control **NOT_RUN**, G3 **NO_GO (no attested goal gain)**, G4 measured net resources **NOT_RUN**, G5 independent later reuse/transfer **NOT_RUN**. S7 **no physical run**; legacy #46/#415/C11 and #544 G3 NO-GO unchanged. This does not request a new physical permission.

## V1 follow-up — S8 exception vs S9 two physical controlled epochs

**S8 one-shot [#537 #6119140571](https://github.com/rinsakamo/relay-self/issues/537#issuecomment-6119140571)** at exact S8 #608 `eac08081d497b11f8386edd1229704c816d1a78d` exited 2 with `ReactiveL0Rejected` after **one** original native Action OUTCOME and one S3 observed Memory; its later source-scoped L1 hint reported `recall`, but both old and new zombie IDs 2 and 4 overlapped. This was a correct fail-closed obstacle to a second Action. Existing S8 grant **consumed**; its failed final S3 snapshot was not generated and shall not be reconstructed.

**S9 one-shot [#537 #6120089028](https://github.com/rinsakamo/relay-self/issues/537#issuecomment-6120089028)** at exact [S9 #609](https://github.com/rinsakamo/relay-self/pull/609) HEAD `916814742567f8ff396b5c078d22f897d8418927`, with S8 as exact parent, reported **one** disposable Minecraft World and shared RSEE preflight success, original S49/S16 executed Action OUTCOMEs **2**, S3 retained observations **2**, L0 decisions **2**, controlled NoAI source targets distinct entity IDs 2/4 and three native correlated clearance probes before second spawn. Two observed movements: 0.792923118 m and 0.944431178 m (operator rounded). Terminal `ACTION_BUDGET_ENDED` / exit 0, retry zero, S9-only permission consumed. This represents *two bounded controlled actions in the same source session*, not free natural hostile survival or successful learned strategy. A read-only Memory recall was also reported; **no controlled Memory-off/Memory-on or source-matched cheap-policy contrast**, therefore its causal effect on the second Action is **NOT_ESTABLISHED**. S10 learning/Habit/LLM posts all zero.

Unlike historical S6, **S9 reportedly archived original Mineflayer bridge predecode receive JSONL**: 39 lines/21,924 bytes SHA256 `614bdb6be1cff97ad598b49be5dd0beaf21bc5a440933d8af91a1f5860703844`; separate outbound command-attempt JSONL: 14 lines/897 bytes SHA256 `23d5feb0ebff8c43c374817bcd1e05f72714dcbf55db9792075ba072a4895000`. Source capture is **Python/Node bridge JSONL, not Minecraft TCP packets**. The stdout-predecode and stdin-before-send roles must never be interchanged with Action execution proof. Pre-posting `SHA256SUMS` own digest `da9858667ab4e3b38a8ab53819f7d55edf2bba14bede8bc364d01709c40ee70e` is not interchangeable with a later final index. S8 predecode receive SHA was `474eb0b...`, a *different session*, not a paired equal-source control. Native STOP ACK unverified even if owned Java/Node exited.

**V new owner-controlled admission:** `s9_two_epoch_report.py` and `s9_two_epoch_review.py` strictly pin the **existing operator source report** and status qualifiers; tests reject changed session/source HEAD, fabricated R9 byte qualification, native ACK/World-absence/learning or Habits, fake S9 causal Memory proof, false cheap comparator, goal/resource/transfer, replay, and S8/S9 head equivalence. This is **evidence-report fidelity checking only**; V **has NOT independently opened WSL2 original bytes**. As of GitHub inspection, R Lane public reference #575 and branch/PR listing expose **R5 #607 only**, not an independently inspectable R9 exact HEAD, so `R9_SOURCE_NOT_CONFIRMED_BY_V`. A user statement that R9 is finished is retained as context, not substituted for a verifiable source/receipt.

**Engineering:** S9 **bounded two-epoch original source retention reported**, producer native byte identity for V **not independently verified**. **Behavioral:** two distinct controlled source-conditioned Actions and two observational Memories **reported**, causal memory-based change/goal not proved. **Science:** G0 original V readback **UNDETERMINED**, G1 prospective heldout outcome not present, G2 strongest cheap matched baseline not run, G3 **NO-GO** no independently attested goal improvement, G4 net resource gain not measured, G5 transfer not demonstrated. #544 D5 scientific NO-GO and #537 product acceptance UNDETERMINED remain. No new physical/LLM/GPU launch authorized or performed.
