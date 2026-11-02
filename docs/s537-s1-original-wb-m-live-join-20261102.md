# S #537 S1: original single-World S49 → WB L1 and M passive admission

## Architecture and source ownership

Base: S0 Draft #688 exact `c939dce957c946c0eba7bc1d3f163c6159703cd0`.
This S-only descendant never vendors the M/WB owner code; operator must provide
**read-only clean original worktrees pinned to exact SHA**:

- M #676 `9afce6bde1079f8a42aaf3c4e515ef35fc6b0396`
- WB #669 `944db858186a4d9449946b6acdcb8c8e5998e071`
- Original S49/S16 #674 remains the only native reader / Action issuer.

A S49 `live_probe` callback projects *already received* native Present into
original SelfBody + SelfWorld and the original pinned WB L1 `CognitionSlice`.
After the original S49 L0 loop and genuine S16 closure, original
`completed_l0` calls the S-only observer; pinned M original
`S49MAdmissionLease` consumes the SAME `S49OriginalCompletedBatch`.
S0's typed join verifies original S49/M; S1 independently matches each
WB projection with **the identical native probe Python object**, native
sequence, request and session, plus an original S16 after-seq preceding
a later original S49 probe. This does **not** create the missing original
S42/B0/L8 epochs, measure Gemma costs, mutate learning or Action.

No WB L2 / Gemma call occurs in S1. WB L1 is an information presentation,
not a learned policy, physical fact beyond native evidence, or new Action.

## Runtime command (user's actual WSL dev workspace only)

Use existing S49 #688 descendant checkout with clean approved M and WB
checkout at the two pinned revisions. Fresh unique output files under
an existing disposable evidence directory, never historical evidence.

```bash
export PYTHONPATH=src:.:tests
export S49_REAL_SERVER_CI=1
export S49_COMPLETED_L0_DEV_ONLY=1
export S537_S1_LIVE_DEV_ONLY=1

python -m tools.s537_s1_live_wb_m_dev \
  --m-owner-dir /absolute/clean/m676-worktree \
  --wb-owner-dir /absolute/clean/wb669-worktree \
  --report /absolute/new/evidence/s49.json \
  --server-log /absolute/new/evidence/server.log \
  --s1-report /absolute/new/evidence/s1.json \
  --live-world-dev
```

This is **not** an instruction to rerun any consumed QUALIFICATION/SCIENCE
one-shot. S #537 authorizes isolated, explicitly opted-in disposable DEV
Worlds under existing safe owner controls. Before running, verify Java21,
Node22, required game files, ports, original S49 owner gates, evidence
root, and ownership of Java/Node process. No inference about an external
running World or retained grant from successful GitHub CI.

## Offline success and physical gate

CI checks the real pinned M/WB source modules in one process using
synthetic original S49-shaped fixture inputs. A positive fixture is
not a physical Minecraft execution or source-independent verification.
Existing owner code rejects foreign, stale, replayed or malformed sources;
the new S1 code does not loosen either owner.

Physical S1 qualifies **only** when original S49 report PASS,
original callback returned after S16, original decision/source trace
matches S1 L1 WB sources, M same-Python original typed admission RECORDED,
and at least one S16 after→next genuine native probe is ordered in
the same World. Any missing/foreign/observer callback is DEFERRED.
Original physical Action itself cannot be retroactively vetoed.

Scope remains `DEV_ONLY / SOURCE_UNATTESTED /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`; STOP ACK, independent Paper
chronology, L2 behavioral benefit, genuine learning, crystallization,
R qualification, and V causal science are not claimed.

## Next boundary

After *actual* S1 same-World DEV source join, S2 can optionally attach
the single existing S60 nonblocking L2 shadow and carry source-limited
prior cognition into the next epoch, without stalling L0. Separate
Learning owner #431 must still prove usable numeric prediction errors;
L #686 H1/H2's null forecast does not count as model revision.
