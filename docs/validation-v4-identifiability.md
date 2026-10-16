# V4 #619 — G0 information-matched cheap null and challenge feasibility

**V-owned prospective prerequisite.** V3 at exact `063c6581f00c7247346dd4b4bb38c989a65b4dcb` (3/3 CI PASS) demonstrated an operational M0 end-energy metric but only a *hand-coded ON vs masked choice difference*. V3 is retained, immutable. V4 does not add scientific positive evidence or a physical launch. It checks whether sensor information adds a decision that **cannot be reproduced by a simpler policy given the same information**.

## Exact source-shaped conditional policy matrix

Frozen S owner [#545](https://github.com/rinsakamo/relay-self/pull/545) at `28cb0f588192ecfe5d03b12b818508352d1a40a8` (4/4 CI PASS) implements `B0EnergyLedger.decide`: for a single ground item and native Food < 14, `native_only` always SEEK; `sensor_gate` SEEK iff `round(true_E)` ≤ 8, using ties-to-even with quantization 1. ON and sham use genuine E; MASK uses fixed gain0/bias12. This is a **fixed one-threshold function**, not learned.

| Source-shaped first-item phase | E before choice | ON/sham | MASK | native-only cheap | equal-information cheap |
| --- | ---: | --- | --- | --- | --- |
| V3 source mode: E12 after 11 WAIT ticks | 6.5 (reads 6) | SEEK | WAIT | SEEK | SEEK |
| Low E4 after one WAIT | 3.5 (reads 4) | SEEK | WAIT | SEEK | SEEK |
| High E20 after one WAIT | 19.5 (reads 20) | WAIT | WAIT | SEEK | WAIT |

The low/high phases are **not available in S's existing real `groundv2`**; source policy code and M0 can generate these typed synthetic probes, but no runtime owner or experimental authority exists. The table only proves *choice separation* at controlled M0 energies, not useful survival/energy/World advantage. The low-phase masked agent may starve over a longer horizon, but that is a **scripted mask-and-threshold effect**. The high-phase native-only agent can still end with **higher energy** after eating if food intake exceeds movement costs. Do not assume high-E sensor WAIT is more efficient.

## Identifiability and scientific ceiling

The **information-matched cheap comparator**, a bare `quantized_E ≤ 8` function of the exact same signal available to ON, replicates ON **for every possible source probe** in the current ground-only branch (given the native item/inventory/food candidate gates are equally supplied). No task built on this fixed policy can establish incremental cognitive complexity beyond that cheapest equal-information threshold without adding a genuinely different *learnable* policy, retained update, prediction or transfer. A contrived high-energy scenario where ON WAIT and native-only SEEK does not solve equal-information redundancy.

Thus register two different questions and keep the controls distinct:
1. **M0 information utility:** matched LOW/HIGH regimes, ON vs mask/sham/native-only, with actual cost/food hazard/opportunity consequences **independent of policy settings**, same sealed initial World and native time.
2. **Cognitive learned structure value:** train an adaptive candidate from **different** World starts, freeze its learned parameters and the calibrated cheap baselines before heldout source starts; compare to the **same-information cheap** and independent ablations, and account for real CPU/GPU/wall/metabolic costs. If simple threshold matches on heldout, result is **NO incremental cognition**, regardless of ON>mask.

Both require S and L/M owner intervention support; do **not** implement them in V, modify old S/World sources or infer new real permissions. V4 is an eligibility blocker, not a positive V4 experiment. Additional preconditions: externally frozen multi-regime food opportunities not chosen by desired policy outcomes, original-native elapsed World time parity and original-byte Action/EAT/WAIT scope admitted by R, distinct train-vs-holdout World starts, blind scoring and fresh grants per World run.

## Implemented evidence

- New versioned `v4_identifiability_manifest.json` and source-only oracle `v4_identifiability.py` (synthetic policy gates).
- Negative tests reject state/scenario changes, dropped cheap equal-information comparator, fake learned qualification and real-source/SCIENCE admission.
- CI separately reads original S checkout at exact immutable SHA and verifies three S-typed source-shaped policy phases with no Mineflayer startup.

**Classification:** `V4_G0_EQUAL_INFORMATION_CHEAP_REPLICATION_BLOCK`. Native World runs 0, heldout results 0, R original byte qualified 0, `SCIENCE_G3_NO_GO`. Preserve V2/V3 as frozen.
