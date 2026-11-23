# Q6 independent audit — U16 original raw evidence manifest and U17 World execution gap

**Date:** 2026-11-22. Q independent lane [Issue #1088](https://github.com/rinsakamo/relay-self/issues/1088), [Draft #1089](https://github.com/rinsakamo/relay-self/pull/1089); original I [Draft #1124](https://github.com/rinsakamo/relay-self/pull/1124).

## Pinned source and CI

- I **U16** immutable HEAD `f1d0258eef83acc134645a1f20c721e2e0f60122`. [Exact-head Actions #45022943095](https://github.com/rinsakamo/relay-self/actions/runs/45022943095) **5/5 SUCCESS**, original pytest job log **2,972 passed in 114.65s**, including U16 custody tests; Node/Mineflayer, Paper witness, Ruff and repository contracts succeeded. This is a source/CPU result, **not a real World observation**.
- I **U17** immutable HEAD `059cf52a61d381a189e62275f850a4fa45942a8c` is U16 + **one documentation-only commit**; its [`i-unified-u17-q4-execution-hold.md`](https://github.com/rinsakamo/relay-self/blob/059cf52a61d381a189e62275f850a4fa45942a8c/docs/architecture/i-unified-u17-q4-execution-hold.md) explicitly reports no live call-site chain to the existing U15 real S2 runner, no real original S1→terminal→fresh L1→S2 rearm sequence, no complete continuous original stdout+stdin/Paper/host timing recording and no World run. The existing Stage24b live L1 MOVE runner is **not** a two-PLACE real runner. Do not treat U17 as World authorized.
- Q source inspected at I U16: `experiments/i_unified_q4_raw_evidence_manifest_dev.py` Git blob `647ba7a3c3829fd620491b66f9c6336a862f60b8`; U16 documentation/runbook Git blob `3c4e06cc3e462015d3260ba955cd61f753b9050b`. I's own manifest is a 7-role inventory: stdout/stin, Paper, canonical WAL, Owner cognition, original host monotonic timing, and process exit. Its output contains `real_world_dev_pass=false` and `independent_q_audited=false`. An inventory does **not** certify the original producer or prove an experiment occurred.

## Q-owned implementation and hostile regression

Created independent read-only `experiments/q_lane_q6_u16_manifest_audit_dev.py` and `tests/test_q_lane_q6_u16_manifest_audit_dev.py`, **without copying U16's author-side validator**:

- Independently reopens each of seven immutable files from the same absolute non-symlink root and compares source SHA256 to the I manifest, plus filename, inode/device, byte length and mtime; rejects changed/read-raced, missing, symlinked, hardlinked or aliased evidence and duplicate JSON keys.
- Requires exact manifest schema/mode/status and false all-success flags. Distinct trial mode `two_moves` vs `stop_failure` prevents reclassification of fault evidence as a nominal success.
- Optional `--check-two-moves` passes the **original** Native stdout and WAL into the already independent Q5 two-MOVE read-only structural verifier, and continues to label success as `CPU_PASS_ONLY` with `world_dev_pass=false`. Fault-mode evidence is **not** passed to that positive two-MOVE checker.
- Independent synthetic tests include a clean 7-role inventory, 14 hostile mutations (modified same-size/mtime raw bytes, missing source/role, foreign path, symlink, hardlink, duplicate/alias role, checksum change, spoofed success or auditor flag, duplicate JSON key, empty source), isolated stop-fault mode, and rejection of fake Native/WAL two-move evidence. These tests make **no claim** of real producer origin.
- Q exact source `6314aa4179af551d43e35537dbb88d3fd49a3aa9` [Actions #45024432925](https://github.com/rinsakamo/relay-self/actions/runs/45024432925): **4/4 SUCCESS, 1,198 pytest PASS** read from original job log; Ruff, repository contracts, Mineflayer adapter SUCCESS.

When the original operator/owner-runner actually produces an archive, run read-only verification:

```bash
python experiments/q_lane_q6_u16_manifest_audit_dev.py \
  --root /absolute/trial-root \
  --manifest /absolute/trial-root/raw-manifest.json \
  --trial two_moves --check-two-moves
```

A separate aborted run uses its own original directory, `--trial stop_failure`, **without** `--check-two-moves`. Further Q review of actual original Paper witness vs Native, independent motor time, terminal WAL, host abort and original process exit remains required before genuine DEV PASS. No real output is invented or replayed.

## Minimal honest decision

- **`Q6_I_U16_EXACT_HEAD_CI_AND_MANIFEST_CODE_REVIEW_PASS`** (CPU only).
- **`Q6_INDEPENDENT_RAW_MANIFEST_RECHECK_CPU_PASS`** (synthetic adversarial coverage only).
- **`Q4_REAL_MOVE_STOP_REPEAT_NOT_RUN / Q4_REAL_STOP_FAULT_NOT_RUN / PRE_WORLD_HOLD`** until a *real* original B one-Self S1→first STOP+8+8→fresh L1 Action→S2 rearm + original process-backed runner, then a separate abort trial, truly executes in an isolated World. Q can inspect raw artifacts but does not have access to the operator's local WSL/Minecraft environment.
- **`QUAL_NO_GO / SCIENCE_NOT_RUN`**. Keep both PRs Draft. Original historical cryptographic S1 authentication, extended cognitive qualification, and long-horizon science remain out of scope for the agreed narrow DEV proof, not gratuitous new preconditions.

**Owner lane next smallest change:** build the one actual isolated-World call chain and source capture path; do not add more CPU abstractions or turn synthetic fixture transcripts into World evidence.
