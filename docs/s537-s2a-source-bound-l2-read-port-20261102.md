# S #537 / S2-A — source-bound read-only input for future L2 (DEV)

2026-11-02 follow-up: a new disposable World passed the S2-A source join.
See [実World検証・実測seq・S2-B境界](s537-s2a-real-world-dev-20261102.md).
The offline-only classification below records the pre-World stage.

S2-A builds on S1 **actual DEV** source proof at exact
`125c7fbfe5f96bf8db394412365c29775761d6af` (Draft #690).
It does **not** call Gemma, issue another Action, add a native reader, grant
S60 acceptance, persist memory, learn a rule, or debit energy.

## Why the S1 postowner receipt alone is insufficient

S1 `completed_l0` is invoked only after all three S49 decisions and their
Actions completed. Joining that finished batch *after* the World ended does
not mean the next decision had access to previous S16 at decision time.

The original `NormalSessionActionExecutor` already supplies a context-local,
exception-isolated `observe_closed_native_actions` callback immediately
after a **real** S16 closure. S2-A uses that pre-existing hook together with
the existing `live_probe` projection already proven by S1.

The S2-A candidate at original probe N thus contains only:

- exact native S49 session/self/epoch/probe seq/request;
- the same bounded WB L1 SelfWorld/Body source refs and observed cue fields;
- **at most one** already-closed preceding Action ID, source probe seq, and
  S16 after seq, and only if the closure callback preceded N in host order,
  belonged to the same original session and source, and S16 after seq < N.

Previous S16 is **not guaranteed** to exist for the first two source probes.
If it is absent, the input explicitly marks it null; it cannot fabricate
a completion. Next native source invalidates current presentation for future
L2 acceptance: **that stale/lease rule belongs to existing S60-A/B1 owners,
not to S2-A**. S2-A has no S60 result to accept or reject.

## Implementation

- `adapters/mineflayer/s537_s2a_l2_read_port.py`: S1-derived observer;
  original source/WB L1 projection plus the post-S16 typed callback.
  A bounded immutable `S2AReadOnlyInput` is recorded at each original
  predecision probe, never created later by reading S1's final report.
  Native action, model and learning authority are always absent.
- `tools/s537_s2a_original_readonly_dev.py`: optional **single-call**
  original S49 `qualify` runner through existing S1/M/WB pinned owners.
  Additional context-local closure observer is read-only, default OFF.
- `tests/test_s537_s2a_source_bound_read_port.py`: uses original
  pinned WB #669 and M #676 code with synthetic original S49/S16 shapes;
  tests two-phase host order, source provenance, duplicate/foreign/future
  closure rejection, disabled-run CLI, zero S60 calls. Offline fixtures
  are NOT physical native samples.

## WSL disposable DEV verification (separate from CI)

When explicitly authorized under S #537 DEV operator policy, use new clean
S2-A worktree and clean M/WB owner worktrees pinned exactly at:

- M #676 `9afce6bde1079f8a42aaf3c4e515ef35fc6b0396`
- WB #669 `944db858186a4d9449946b6acdcb8c8e5998e071`

Fresh evidence destinations and distinct DEV gates:

```bash
export PYTHONPATH=src:.:tests
export S49_REAL_SERVER_CI=1
export S49_COMPLETED_L0_DEV_ONLY=1
export S537_S2A_LIVE_DEV_ONLY=1

python -m tools.s537_s2a_original_readonly_dev \
  --m-owner-dir "$M_OWNER_DIR" \
  --wb-owner-dir "$WB_OWNER_DIR" \
  --report "$EVIDENCE_DIR/s49.json" \
  --server-log "$EVIDENCE_DIR/server.log" \
  --s2a-report "$EVIDENCE_DIR/s2a.json" \
  --live-world-dev
```

Before calling this on local WSL: check executable owner pins, closed ports,
World dependencies, Java21/Node22, no NODE_OPTIONS shim, available new
evidence paths, explicit DEV grant and process ownership.

The expected original World is S49's established
WAIT → MOVE_AWAY → MOVE_AWAY / Action2 / S16 OUTCOME2 and the last probe
must carry prior Action1 / after seq < probe seq, not a future result.
Independent full native/Paper chronology, model benefit, learning,
human-like energy or R/V certification are not established.

Classification before the next real World:
`DEV_ONLY / S2A_OFFLINE_ONLY / S2B_LIVE_GEMMA_NOT_RUN /
SOURCE_UNATTESTED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.

## S2-B boundary (not implemented here)

Only after source ID/host-order readout is validated in a new DEV World,
adapt a **single** S2A typed input into the existing S60-B1 request; let
S60-A retain the deadline/stale-fence/typed acceptance decision. A
late response may be past-epoch review only; foreign, replayed or
future-source input must not be admitted as current. Do not stall L0
to wait for L2 or grant L2 World/Action/Memory/Learning/Habit authority.
