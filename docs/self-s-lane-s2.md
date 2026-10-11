# Self 1.0 — S Lane S2: source-qualified candidate flow (offline)

Product owner: #537. S2 is stacked ONLY on S1 Draft #592 exact
`75054188f1c7e8141690697794b6e705495de205`. S1, parent
#590, Golden #588, main and sibling R/L/V/A/B/C branches remain unchanged.
Current L Lane #594 is a separate sibling on #590; it is **not** merged.

## What is connected

- **Hard L0:** the unchanged S49 `NormalWorldL0` decision and original
  S14/S15/S16 execution/authority pipeline still own all real Actions.
- **Cheap L1 read-only candidate:** original `relay_self.habit.select_habit`
  examines the same S49-admitted native `WorldConditionedChoice`. Only
  an explicitly **preconfigured, not learned** far-threat WAIT rule is
  considered. Near-threat results in `no_match`. The output never supplies
  an Action grant, changes the L0 selection, authorizes a Skill, or qualifies
  an S11 learned Habit. This is a bounded integration example, not evidence
  that a sophisticated L1 has been learned.
- **Existing L2 observer seam:** `BoundedSessionDriver.run` accepts an
  optional already-owned `LiveL2Observer.observe`, which receives an exact
  source-correlated S49 probe **after native S49 validation**. L2 callback
  is bounded and may be absent/failed; the L0/grant/executor path continues
  unchanged. Any supplied L2 adapter uses original S60-A/B1 lifecycle.
  Client cancellation/sidecar are not STOP ACK or GPU release.
- **Operator entry:** `self_s1_runtime.run_physical` wires the L1 view on
  each World decision and accepts an optional already constructed, exact
  `LiveL2Observer` supplied by an independently qualified owner. An L2
  report is saved only if that owner is explicitly supplied. The existing
  CLI does **not** construct or start a model; it remains dry-run by
  default and physical opt-in still requires separate permission.
- **RelayUI evidence:** the original exclusive fsync JSONL has
  `l1_candidate_review`, `l1_candidate_unavailable`,
  `l2_probe_observed` and `l2_probe_unavailable`, always with
  same-session World/probe identity, explicit effective L0 choice and
  **zero L1/L2 Action authority**. If an actual S60 observer was injected,
  its original final report is retained as a separate exclusive
  `s2_l2_advisory.jsonl`. No S10/S11 update is made.

The native process has **one sequential `session.receive()` ownership
chain**, not parallel S49/Model consumers. A live L2 transport has its own
HTTP task and never consumes World frames. The one foreground S49 Action
owner cannot obtain an authorization from L1/L2 text or candidate data.
An invalid or failing read-only suggestion stays unavailable rather than
being treated as a new effective choice. No arbitrary model text parser,
new World model, Executive, custom Memory DB or A/B/C research merge.

## Offline validation only

```bash
BASE=/home/rinsa/.local/share/relay-self/rsee-1.0-20261011
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD"
export PYTHONDONTWRITEBYTECODE=1
"$BASE/venv/bin/python" -m adapters.mineflayer.self_s1_runtime
"$BASE/venv/bin/python" -m pytest -q \
  tests/test_self_s2_integration.py tests/test_self_s1_runtime.py \
  tests/test_self_continuous_host.py tests/test_self_live_think.py
```

The existing S1 explicit physical runbook is unchanged; no opt-in physical
run, GPU L2 request, model POST, Minecraft server or real native Action was
performed or authorized for S2. Tests are source-shaped fixtures. The old
third Golden authorization is consumed. Physical S2 behavior and RSEE
model-binding/lease ownership are **NOT_RUN**, and S2 **does not yet
demonstrate an L1/L2 candidate changing real World behavior**.

Next S3 adds governed S17/S10 feedback and owner-local subsequent-epoch
reuse only when validated independent feedback/learning authority exists.
S4 adds RelayUI observation. Neither is implemented here.
