# R S50/P1 FLAT first BLOCKED original profile — read-only admission

Authority: R #575; S original report #627; S Draft #545 (execution HEAD
`4ba9846f73dc34faf92c315d5304eae587c5d75c`).
R readback implementation: `experiments/standard_env/s50_p1_flat_blocked_original_audit.py`.
This new profile **does not alter** the historical seed61021 / PASS V7 R evaluator.
It admits only the first seed63101 **BLOCKED** source and never upgrades the run.

## Frozen source identity

- LocalCodex original root:
  `/home/rinsa/work/s50-p1-flat-native-evidence-20261017/physical-run-001/`.
- Sealed bundle: `sealed-run-001.tar.gz`, SHA256
  `8f372041c08f5743f3e0c936fd045c112f4d3b6e48f6eb6444c8d8cccd3f27a7`.
- Native session: `be9aa263-afac-4b17-945b-09eef6c47126`.
- S final HEAD: `07ce0899abe309fda1dbcb67152f7443983e24d9`.
- Native bytes: seq0–27, LOOK ACK7, FORWARD ACK8, CLEAR ACK17,
  shutdown ACK26, connection_end27.
- S15/S16: one ISSUED→OUTCOME, consequence **BLOCKED**,
  progress `-0.3363737550662047` block.
- Client callbacks: 30 contiguous, at least 23 after CLEAR all 7 OFF.
- Paper WAIT candidate: tick44–51, **sampled** stationary only.
- P1: no admitted WAIT or recovered fatigue, no science.

The R script pins SHA256 values for each of five original files:
`original_native.jsonl`, `owner_commands.jsonl`, `paper_server.log`,
`s50_action_original.jsonl`, `s50_p1_native_controls_original.jsonl`.
For original SHA references see S #627 report and the constants in the R
reader; do not trust a source-originating status alone.

## Prospective R local invocation (NOT YET RUN HERE)

At a fresh read-only R worktree with the new R code:
```bash
PYTHONPATH='src:tests:.' python -m experiments.standard_env.s50_p1_flat_blocked_original_audit \
  --original-root /home/rinsa/work/s50-p1-flat-native-evidence-20261017/physical-run-001
```

Do not invoke this against a derived receipt instead of original files.
Before execution confirm sealed bundle SHA and `SHA256SUMS` independently;
no physical Java/Node/World, no unsealing overwrite, no qualification or
science run. Preserve all original bytes and write any new R receipt outside
the frozen S original.

An exit code of zero means **the five pinned source files satisfied this
bounded DEV-only independent reader**. It does **not** make R engineering
QUALIFICATION PASS; checks for full World-tick activity, all Action issuers,
server-effective input release tick, and a P1 Body WAIT contract remain
`NOT_ATTESTED`. Exit code 2 is source rejection; do not retry by modifying
the original S receipt.

The current exact first-run state is **R_PENDING** until the actual sealed
original files are read by this R CLI. Synthetic R negative tests alone do
not satisfy that requirement.

The first run's Overworld17 original was preserved, but Nether/End original
World bytes were not. New S-only `s50_p1_world_preservation.py` captures
*all present dimensions* after STOP in future DEV runs; this does not
retroactively fill the original run's missing dimensions.
