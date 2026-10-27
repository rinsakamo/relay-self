# RelaySelf — original S49 sole Action owner gap + Node input-OFF + Paper stillness DEV

2026-10-27 JST. Isolated branch:
`self/dev-s49-forward-motor-admission-20261026`.

**DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.**

## Verified original-owner integration (actual Paper Minecraft)

**Source-tested HEAD:** `e456bd3d3f320c701e1a3b4d16122fcc3f181fb9`.

**[Real disposable Minecraft Paper 1.21.8 run #40434152476 — SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40434152476)**. Python3.12 focused, malicious-negative tests, Ruff, Java21 Paper plugin compilation, Node22 check/native effect, original S49 2/2 native S16 OUTCOME, Java/Node complete cleanup PASS.

This step directly instruments the **existing, original**
`adapters/mineflayer/s49_normal_session_real_ci.py`
`qualify()` Action owner, only when explicitly opted into
`dev_inter_action_owner_gap` under
`S49_INTER_ACTION_OWNER_GAP_DEV_ONLY=1`. No synthetic or independent
Action issuer is created. The original
`NormalSessionActionExecutor` is checked when the first original S16
OUTCOME finishes, and again at the entrance to the **second original**
`on_action(step)`, before the original executor's next native issue:

- first closed original S16 Action: exactly one dispatched original
  action, `_count=1`, no `ActionSupervisor.open_actions`;
- second Action request entrance: **still one** dispatched original
  action, `_count=1`, no open Action, correct original first ID and
  distinct original second ID;
- final second native S16 Action terminal: exactly two dispatched
  original Action IDs and zero open Actions.

The original host uses `time.monotonic_ns()` for the two bookends.
The default code path, original Action issuance, native effect reader,
L0 owner, P1 motor, B0/M0 energy and legacy status remain unchanged.
The original report contains an optional DEV-only
`dev_inter_action_original_owner_gap` section. It can never
authenticate non-S49 issuers or an unsampled World-wide state.

### Actual one-World result

| Source/view | Source-observed value |
|---|---|
| Original native Action 1 | `s49-native-move-19`, S16 OUTCOME |
| Original native Action 2 | `s49-native-move-55`, S16 OUTCOME |
| Original S49 first terminal → next original issue-request bookends | **9,192.920917ms** (host monotonic) |
| Original S49 Action counts at first terminal / next request / final terminal | **1 / 1 / 2** |
| Original ActionSupervisor open Actions at each bookend | **0 / 0 / 0** |
| Original Node input-off callbacks after first native clear, before second original SET | **186 continuous physicsTick ordinals** |
| Node locally observed source timestamps | **210,?** not asserted as host/Paper aligned |
| Paper original World fullTime samples | **217/217 consecutive** |
| Paper stillness candidate | **173 consecutive ticks, 259–431**, <=0.002m XZ per tick |
| Second Action Paper ACK marker | original native S15 APPLIED delivery tick 437 |
| M0 per-original-Action logical ticks | 2 (0→1→2), never 217 |
| P1 source-verified first Action DASH extra energy | **0.07867623703453769** |
| Original B0 M0 energy | **12 → 10.421323762965462** |
| Any new physical WAIT admission | **NO** |
| Any P1 WAIT recovery / new M0 world-time debit | **NO / NO** |

Note that the DASH extra energy in this run differs from prior
Minecraft runs (~0.08633) because real source/P1 input differed.
**Never rewrite or force a prior run's energy**: the actual M0 ledger
at the above tested HEAD has first 0.5 basal+0.25 MOVE+0.078676 DASH
extra, then 0.5 basal+0.25 MOVE. This is the measured and independently
read-back real result.

The simultaneous presence of a host Action-owner no-new-issue
**bookend interval**, original Node input-off local interval, and
Paper body-static interval is stronger than the earlier two-source
candidate. But owner count equality is an **original-executor**
observation, not proof that all possible real-world actors issued no
Action. Python monotonic, Node process.hrtime and Paper fullTime
are separate clock interfaces with no attested mapping.
This DEV prototype **does NOT admit** the candidate to P1 WAIT or M0
billing. The 173 Paper callbacks are a candidate only.

### Bounded elapsed-duration consistency

A further isolated DEV improvement compares the owner-local
elapsed **duration** with the original Node-local input-off elapsed
**duration**, checking a conservative <=1,000ms discrepancy to reject
gross source mismatch. This never sets host↔Node epoch calibration,
or assumes individual Paper tick = Node physicsTick. Review the
latest [isolated stillness workflow](https://github.com/rinsakamo/relay-self/actions/workflows/self-s49-inter-action-stillness-dev.yml)
for exact post-change test status, independently of source-tested
#40434152476.

### Negative controls and interpretation

Focused tests cover foreign original Action/session, spoofed counts,
already-open Action, forged executor identity, wrong dispatched ID
sets, monotonic reversal/replay or fake elapsed time, node input
control-OFF forgery, missing/foreign Paper body-static observations,
false clock equivalence, false global World/no-Action admission and
premature P1/M0 credits.

**Remaining unqualified chain:** only an independently grounded
one-direction owner-terminal/no-issue proof, Node input-OFF, Paper
contiguous XZ samples, and source-bound time correspondence can
justify *exact* physical WAIT World ticks. Even after that, P1 WAIT
recovery is a separate decision on the authorized owner; it is not
implicit in this DEV log. The basal shadow model assumes 20 Paper
World ticks per normalized World-second and remains unposted.
Keep canonical original M0 one charge per native MOVE Action until
rate/authority migration is expressly accepted.

No FULL regression/main merge, no original #545/#634 Draft changes,
no R Qualification/SCI Science.
