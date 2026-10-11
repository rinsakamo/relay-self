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
