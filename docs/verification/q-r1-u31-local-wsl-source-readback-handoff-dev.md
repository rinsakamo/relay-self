# Q R1 / U31 — local WSL original-source readback handoff (one bounded operation)

**Status:** instructions for a LocalCodex-only original readback, **NOT RUN** by GitHub / ChatGPT. This is *not* a new World experiment, an R1 production runtime integration or a QUAL proof. Do not add further verifier frameworks or rerun expensive real workloads.

## Immutable review anchors

- Original I U31: `d3034026a8eea3d2d4927527f5bc0d6ad0455457` ([I Draft #1124](https://github.com/rinsakamo/relay-self/pull/1124)).
- R1 read-only Shadow: `06349c7a216b042511a90e05ad0196f4a7164378` ([R Draft #1129](https://github.com/rinsakamo/relay-self/pull/1129)); original I U31 remains **unchanged**, including Owner/Physical/Native/Paper/WAL.
- Independent Q static+runtime: `57ae1899c1ea7f61596e4f46ec5c462192d7dc24` ([Q Draft #1130](https://github.com/rinsakamo/relay-self/pull/1130)).
- Existing independent Q original source code: `450734c54e1432ec70a8206952779b5ad82796d8` ([Q Draft #1089](https://github.com/rinsakamo/relay-self/pull/1089)).
- Historical real original source root: `/home/rinsa/evidence/i-u31/`. Earlier #1088 U31 report records Q6/Q7/Q8/Q11 PASS, two settled WAL rows, zero unresolved, original B one Native session, two real L1 HTTP 200 choices. **Never replace historical original files with synthetic fixtures.**

## Safe local source-only procedure

1. In an authorized WSL Q checkout, independently fetch/check the **exact Q and R and I commit IDs**, using a detached/read-only worktree for the auditor. Do not alter `main`, I, R, or Q Draft sources; never merge older R PRs. Refuse SHA drift.
2. Inspect the original root and identify the sealed U31 `original-u17-two-moves-manifest.json` (the existing I runner generated that basename) and the seven original role files:
   - `original-native-stdout.jsonl`
   - `original-native-stdin.jsonl`
   - `original-paper-process.log`
   - `original-owner-wal.json`
   - `original-owner-persistent-cognition.json`
   - `original-host-monotonic.json`
   - `original-node-process-exit.json`
   A nested directory is allowed only after locating the *existing* original sealed manifest and matching its seven original role paths; never fabricate or rewrite a missing manifest.
3. Snapshot original root's regular-file identities + SHA-256 (size, device, inode, mtime_ns) **before** inspection, keep any temporary receipts outside original evidence root. Refuse symlink/hardlink/role alias, missing/incomplete/log-replaced bytes or duplicate/nonfinite JSON as implemented by Q6. Avoid uploading original private logs or LLM content.
4. From the **pinned Q code** execute exactly the existing read-only validators on original U31 files (without overriding them):
   ```bash
   E=/home/rinsa/evidence/i-u31
   M="$E/original-u17-two-moves-manifest.json"
   test -f "$M" || { echo "U31_MANIFEST_MISSING_HOLD"; exit 2; }
   python -m experiments.q_lane_q6_u16_manifest_audit_dev \
     --root "$E" --manifest "$M" --trial two_moves --check-two-moves
   python -m experiments.q_lane_q7_native_three_way_audit_dev \
     --wal "$E/original-owner-wal.json" \
     --native-stdout "$E/original-native-stdout.jsonl" \
     --native-stdin "$E/original-native-stdin.jsonl"
   python -m experiments.q_lane_q8_paper_native_two_move_audit_dev \
     --wal "$E/original-owner-wal.json" \
     --native-stdout "$E/original-native-stdout.jsonl" \
     --native-stdin "$E/original-native-stdin.jsonl" \
     --paper-log "$E/original-paper-process.log"
   ```
   If the original manifest is under a subordinate root, substitute **only** the verified original manifest parent for `E`, not an invented archive. A previous run's results are not fresh readback.
5. Independently reread **existing** `owner-boundary.jsonl` and `q11-original-readback.json` at their actual paths (may be sibling of the seven-file archive). Check U31 original Owner explicit S1 `CANCELLED` then Intent release, WAL prefix+Anchor, original Source rearm, fresh seq 80→86 / S2 distinct Intent/Skill, final two settled rows zero unresolved; keep Native world-age ticks separate from Paper main-thread ticks. Use already implemented Q11/original artifact contract; if its verifier is only represented as a prior logged Q result, report readback provenance as `HOLD` rather than invent a fresh Q11 pass.
6. Compare all original file digests and stat identities **after** the read-only audit against step 3. If anything changed, classify `Q_R1_U31_WSL_REINSPECTION_HOLD`. Do not write results inside the evidence root.
7. Record in Q Issue #1088 and R Issue #1117 (and Q Draft #1130 / R Draft #1129): original root used (without copying private log content), full pinned I/R/Q SHA, Q6/Q7/Q8/Q11 per-check outcome, before/after identity stability, whether original U31 evidence was actually read, precise limitation, and `QUAL_NO_GO / SCIENCE_NOT_RUN`. Add a **minimal** Q-only report commit if warranted; rerun exact-HEAD CI only if repository code/docs change.

## What a source PASS means

`Q_R1_U31_WSL_ORIGINAL_READBACK_DEV_PASS` may be reported only when U31 original bytes were truly reread in authorized WSL, Q6/Q7/Q8 validations and any claimed Q11/source-boundary checks explicitly succeeded, and no originals changed. This preserves the existing *original U31 experiment's* DEV evidence, **not** independent real-world execution of the R1 Shadow. R1 is still an **opt-in, Stage28 initial A/B** read-only comparator (first-login epoch 1); U31's original one-B native sequence does not directly run that R1 Shadow. Do not claim R1 Shadow measured in actual U31 World.

The **only remaining R1 gate** after its pinned Git/Q CPU PASS is the deliberately bounded WSL source handoff, if the project requires fresh byte reinspection. This is not permission to start R2, to rerun World/Gemma/Physical, to introduce a new Owner/Memory/Issuer, or to create new QUAL gates. Keep `R2_HOLD / QUAL_NO_GO / SCIENCE_NOT_RUN`.

**Local execution boundary:** ChatGPT's remote execution container was checked and does not mount `/home/rinsa/evidence/i-u31/`; therefore this handoff is deliberately marked **NOT RUN**, regardless of GitHub Actions success. The readback must be performed by LocalCodex in the original WSL environment, with a separately identified Q review result.
