# U16 — minimal real-World Q4 evidence handoff (code present; PRE_WORLD HOLD)

The source used for this iteration is U15 **`d324e468a86978ce23d4ce649abd01062057187f`** ([CI #45020224540](https://github.com/rinsakamo/relay-self/actions/runs/45020224540), 5/5 SUCCESS, 2,958 pytest). Existing I Draft [#1124](https://github.com/rinsakamo/relay-self/pull/1124), integrated issue [#1061](https://github.com/rinsakamo/relay-self/issues/1061), independent Q [#1088](https://github.com/rinsakamo/relay-self/issues/1088).

## Limited work added

New `experiments/i_unified_q4_raw_evidence_manifest_dev.py` writes a *read-only raw-source inventory and SHA256 manifest*, **not** an externally authenticated World success receipt. Seven mandatory original files come from one isolated disposable Q4 trial:

| Role | Source, never regenerate from the purported success report |
| --- | --- |
| `native_stdout` | One `MineflayerProcessSession.start_raw_source_audit` JSONL, opened before first action, not reopened between moves |
| `native_stdin` | Raw host→Node effect-command stream, exact parent and LOOK/START/STOP IDs |
| `paper_ticks` | Original Paper-side tick/position/actor witness, not recomputed from Native |
| `owner_wal` | Same Original B Owner canonical physical WAL v2 after trial |
| `owner_cognition` | Original B Owner's selected Intent/Skill/Action/source-receipt record |
| `host_monotonic` | Host original START send, STOP ACK, abort, settlement deadlines with clock origin |
| `process_exit` | Original owned Node child PID, session, exit readback, TERM/KILL when injected |

Each file must already exist and be non-empty inside the same absolute, non-symlink trial root, have a distinct single-linked inode, be regular and no larger than 32MiB. Directory symlinks, file alias, missing role, empty file, path escaping root, evidence changing while read, existing manifest output are all **HOLD**. Manifest is created O_EXCL 0600 and fsynced with the directory. It records original byte SHA256/size/inode/mtime and has explicit `real_world_dev_pass: false`, `independent_q_audited: false`. It never edits Native/Paper/WAL files, issues physical effects, or authorizes an experiment.

Two moves and intentional STOP failure **MUST use two different isolated trial directories**. Do not attempt an abort in the qualified two-MOVE run.

## Local invocation, once all seven true original files exist

Example with an operator-created absolute root `/tmp/q4-two-moves` (replace paths with the *actual existing original files*):

```bash
PYTHONPATH=src:. python experiments/i_unified_q4_raw_evidence_manifest_dev.py \
  --root /tmp/q4-two-moves --mode two_moves \
  --native-stdout /tmp/q4-two-moves/native.stdout.jsonl \
  --native-stdin /tmp/q4-two-moves/native.stdin.jsonl \
  --paper-ticks /tmp/q4-two-moves/paper.original.jsonl \
  --owner-wal /tmp/q4-two-moves/owner-wal.json \
  --owner-cognition /tmp/q4-two-moves/owner.json \
  --host-monotonic /tmp/q4-two-moves/host.monotonic.jsonl \
  --process-exit /tmp/q4-two-moves/process-exit.json \
  --out /tmp/q4-two-moves/raw-manifest.json
```

For the separate STOP fault trial, use `--mode stop_failure` and a separate absolute root. Missing an original source is HOLD, **not** an invitation to generate placeholder JSON.

Q's independent, read-only [two-MOVE original Native/WAL auditor](https://github.com/rinsakamo/relay-self/blob/d89347e65299f7a1e9e5f43208d0122f51b91216/experiments/q_lane_q4_raw_native_wal_audit_dev.py) lives in Q Draft #1089, **not** the I branch. Run it independently on the exact archived original `owner_wal` and `native_stdout` from the qualified same-Session two-MOVE run, without copying its source into the I qualification path or mistaking its `CPU_STRUCTURE_PASS` for real World PASS.

## Remaining **real** work (LocalCodex/WSL only)

1. Verify the full original S1 Action source, actual L1 selection, native/Paper-owned Session/World and the first terminal readback; only then rearm S2 under original B Physical Issue and same canonical WAL. No fabricated `LiveWalHistoryAnchor`, synthetic Native ACK or restored B motor authority.
2. Preserve the *single* Native stdout audit FD across both moves. Execute exactly two bounded `MOVE_PLACE` on one original Self and original Node/Paper session. At each Action: WALK pulse around 0.5m; ≤800ms forward, host START→Native applied STOP ≤2s; separately read 8+8 tick STOP settling; actual displacement 0.1–1.0m; verify Paper/Natives/Owner all agree.
3. Use a fresh isolated fault-run World to inject STOP/cancel **after START**. When clean STOP cannot be confirmed, release native controls or TERM/KILL the **owned** Node process, verify exit, leave PREPARED WAL unresolved, forbid replay. Do not claim clean settled STOP from buffered bytes.
4. Archive all seven immutable originals plus SHA manifest and hand to independent Q audit. Preserve exact CI/HEAD, record failed and cancelled trials as HOLD. If original Paper/Native provenance is ambiguous, do not run the second Action.

**Status:** Raw manifest writer and hostile file custody tests are CPU-only. It is a preparation aid, not a real Native/Paper/Paper World test. `I_U16_Q4_RAW_EVIDENCE_MANIFEST_CPU_ONLY`, `Q4_REAL_WORLD_MOVE_STOP_REPEAT_HOLD`, `Q4_REAL_ABORT_FAIL_SAFE_HOLD`, `PRE_WORLD_HOLD / QUAL_NO_GO / SCIENCE_NOT_RUN`; PR must stay Draft.
