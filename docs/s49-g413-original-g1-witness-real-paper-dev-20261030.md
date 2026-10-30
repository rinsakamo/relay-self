# RelaySelf G4.13 DEV — source-bound G1 stable-kind and post-control witness placement (2026-10-30 JST)

## Mission and provenance

Parent G4.12 final report SHA: `48ad95f7836e3ec66464356b82fd7fc8e204690d`. G4.12 identified original S49 / G44 ACK-bound Node generation segments of 1–4 already captured Paper WorldTicks in its real World. G4.13 **does not alter those segments, the G1 gait observation classifier, the original S49 motor, or T2/P1/M0**. It checks where an original G1 stable gait *candidate kind* and the original G46 `g46_challenge_after_control_dev` indicator occurred inside each exact prior G412 contiguous Node action/effect/generation/phase segment.

New module `adapters/mineflayer/g413_original_g1_generation_witness_dev.py` exposes `join_g413_original_g1_generation_witness_dev(...)`; it **recomputes and checks the entire G412 audit from unchanged original G411/G410/G49/G48/Paper/T2/Action ACK/CLEAR/G44 ACK inputs** before inspecting an existing Paper frame. It fails closed on changed G412 rows, source SHA/identity, altered G1 classifications, nonboolean challenge, missing/duplicate Paper WorldTicks or mismatched counts. Every selected G413 row binds its original G412/G411/G49/T2 row SHA, exact first/last generation tick and per-original-Paper-frame SHA, recorded G1 kind sequence, recorded challenge boolean sequence, first stable-kind position and first post-control-challenge position. It counts stable-kind and challenge on the *same* original frame separately from observations on different frames.

Default OFF until `--g413-original-g1-generation-witness-dev` **and** `S49_G413_G1_GENERATION_WITNESS_DEV_ONLY=1`, requires G412 opt-in, and derives `g413_original_g1_generation_witness_dev.json` **after** original S49/G412 read-only postrun stages. Sidecar and report SHA-bind existing original G412/G411/G49/T2 whole files. No additional Paper sensor, native read, motor/trace event, input duration, original tick ledger owner or P1/M0 posting; no physical WAIT inference, G1 status reclassification, gait qualification or physics-tick packet causality. Source classifications explicitly include `NOT_CAUSAL_GAIT` when an original G1 stable kind and original post-control indicator coexist.

## Validated implementation and DEV gates

- Isolated branch: `self/dev-g413-g1-generation-witness-20261030`. No main merge or protected Draft PR #545/#634 update.
- Original G413 implementation + original 3-World workflow SHA: `1d9a5c8221582e43c929dc3a9150fef96ba6cf82`.
- **Exact successful physical 2-World code/workflow SHA:** `55f5f7c6f2e483ceb6bcb9d692c02b1dcf751e24`. Only the isolated G413 DEV workflow was changed after initial code: read-only source witness physical gate now verifies baseline + controlled Goal Worlds and does not require a particular RUN→JOG→WALK sequence. Original G44 effect ACK identity/integrity validations are retained. Full 3-World challenge workflow remains unchanged and failed.
- **[G413 focused Python3.12 #40995391457 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40995391457)**: 82 focused pytest PASS including G412/G411/G410/G49 regressions, Ruff and compileall PASS.
- **[G413 baseline + controlled real Paper 2-World #40997098497 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40997098497)**: existing Java21 / pinned Paper1.21.8 plugins, Node22, Python3.12 scoped checks and two disposable real Worlds. [Original artifact #12952335343](https://github.com/rinsakamo/relay-self/actions/runs/40997098497/artifacts/12952335343), including SHA-bound original original G1/G49/T2/G412 and derived G413 source.

### Real observations from successful G413 2-World gate

| World | Original S49 result | Source observations |
| --- | --- | --- |
| Baseline G4, G413 OFF | Goal REACHED, **5** original S49 Actions, final error **0.402786908m** | **49** original T2/P1/M0 WorldTick receipts |
| Controlled G413 ON | Goal REACHED, **6** original S49 Actions, final error **0.447752852m** | **133/133** original T2/P1/M0 WorldTick receipts SHA-bound. Original G49/G47/G48 **10 bounded candidate ticks / 123 UNKNOWN**, unchanged. G410/G411 **16** original in-Action G1-nonstable rows, all adjacent observed Paper WorldTick pairs. G412: **10** source-bound Node generation boundaries, **6** original S49 effects / **4** original G44 same-parent-Action subeffects. G413: **10** original contiguous-generation witness segments, source identities and SHA exact. |

G413 actual mutually exclusive evidence classes over 10 selected source segments:

| Original source witness | Number of generation segments |
| --- | ---: |
| G1 stable-kind candidate **and** post-control indicator on at least one same original Paper frame — not gait causality | **6** |
| Only one original Paper frame in that generation; cannot form an extended observed segment | **3** |
| Multiple original Paper frames and post-control indicator, but original G1 remains nonstable | **1** |
| **Total** | **10** |

Across those source segments, **10** original G1 stable-kind candidate frames, **16** original post-control-indicator frames, and **10** same-frame intersections were recorded (counts of **frames**, not segments). G412 generation WorldTick lengths `[4,3,1,3,1,1,2,2,5,4]` (1–5 in **this** fresh World; different from G4.12's own 1–4 World). Original G49 **123 UNKNOWN remain 123**, no new P1/M0 debits and **no physical motor acceptance/latency proof**. Independent baseline vs controlled errors are **not** a causal speed comparison.

### Preserved failed DEV originals (not called SUCCESS)

The original **3-World workflow did not pass** across four isolated same-SHA disposable-World attempts: [run #40995474637](https://github.com/rinsakamo/relay-self/actions/runs/40995474637). Original artifact IDs: [attempt 1 #12951276512](https://github.com/rinsakamo/relay-self/actions/runs/40995474637/artifacts/12951276512), [attempt 2 #12951172611](https://github.com/rinsakamo/relay-self/actions/runs/40995474637/artifacts/12951172611), [attempt 3 #12950939539](https://github.com/rinsakamo/relay-self/actions/runs/40995474637/artifacts/12950939539), [attempt 4 #12951700764](https://github.com/rinsakamo/relay-self/actions/runs/40995474637/artifacts/12951700764). Attempt 1: controlled G413 source successfully generated, but existing motor protocol did not exhibit mandatory RUN→JOG→WALK in one Action. Attempt 2: existing Goal L0 reached original **MOTOR_ACTION_BUDGET** before Goal tolerance. Attempt 3: controlled Goal World passed but separate hazard G4.5 original fail-closed evidence check rejected. Attempt 4: controlled Goal World passed but separate hazard World first original S49 DASH Action lacked real S16 terminal before hazard stimulation. All failures and associated original Paper/T2 files retained; no retroactive reinterpretation.

An initial **2-World witness-only workflow** [#40996615256 FAILED](https://github.com/rinsakamo/relay-self/actions/runs/40996615256), [artifact #12952021025](https://github.com/rinsakamo/relay-self/actions/runs/40996615256/artifacts/12952021025), because it still incorrectly required the same optional G44 two-stage trajectory unrelated to this source witness; only this particular DEV gate requirement was relaxed, **not** original S49/G44 action/motor policy or ACK verification. Subsequent #40997098497 SUCCESS is independently physically observed and scoped exactly to G413's read-only Goal-world claim. No **G413 3-World full hazard qualification** is asserted. Prior **G4.12 hazard 3-World SUCCESS** [#40992856461](https://github.com/rinsakamo/relay-self/actions/runs/40992856461) is historical independent evidence, not re-used as a new G413 hazard pass.

## Final classification

**`DEV_ONLY / G413_REAL_PAPER_TWO_WORLDS_PASS / ORIGINAL_G1_WITNESS_SHA_BOUND / ORIGINAL_G49_UNKNOWN_PRESERVED / T2_P1_M0_SINGLE_OWNER / G413_HAZARD_NOT_QUALIFIED_THIS_RUN / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`**.

No FULL, native motor qualification, exact per-tick gait proof, physics packet timing, new physical test input, additional readers, WAIT, new learning, L2 calls, force push, protected PR merges or SCIENCE.

**Next engineering priority:** stop expanding G4.x evidence taxonomy solely to chase gait qualification; G4.13 already explains stable-kind/challenge placement. Continue integrated L Lane / SelfWorld-SelfBody interfaces and only open new gait investigation on an actual behavior regression or targeted L0 action-control need.
