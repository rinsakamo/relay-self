# RelaySelf — original sole S49 Action owner causal Paper stillness subwindow DEV

2026-10-27 · branch `self/dev-s49-forward-motor-admission-20261026`  
**DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**

**Exact successfully tested source HEAD:** `db505cd0ad28fecd8327fc163b4bf77076375ad0`.  
**[Real disposable Paper Minecraft 1.21.8 World run #40438046090 — SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40438046090).**

## Purpose and minimal implementation

Prior DEV real Minecraft established 217 continuous Paper fullTime samples,
roughly 174 low-motion candidate ticks, 186 consecutive Mineflayer
physics callbacks with all seven controls OFF, and an original **sole S49
NormalSessionActionExecutor** 1→1→2 issued-Action count. The host owner
and Node input-OFF elapsed durations agreed to within ~100ms, but their
clocks were not calibrated to Paper fullTime. **None of those alone
proved the low-motion Paper interval was inside the original owner's
no-new-issue interval.**

This implementation uses two *causal fences*, not a fictitious
Node↔Paper tick offset:

1. The **same original S49** first native S16 Action reaches terminal
   OUTCOME, the original S15 sole receiver has already read the
   `clear_controls` APPLIED ACK, and the original Paper DASH modifier
   was disarmed. Only THEN the original S49 Action owner calls a
   narrowly scoped, DEV-opt-in asynchronous observer
   `dev_inter_action_owner_paper_fence("START", first_action_id, "NONE")`.
   The observer writes the Paper console command
   `relays49dashownerfence` and **awaits the actual Paper log receipt**.
   Its receipt is stored in the pending original owner state until the
   second Action is requested.
2. At the second original `on_action(step)` entrance, the existing
   original owner checks that its original dispatched Action set is
   still one (the first closed Action), with zero open ActionSupervisor
   actions. The owner sends an **END** Paper console command with the
   exact second requested Action ID and **awaits its Paper receipt
   before continuing to S14 admission / S15 native Action ISSUE**.
   The original second native `set_forward_sprint_dev` therefore
   cannot precede the Paper END delivery in this DEV test.
3. Paper's plugin accepts exactly one START then one END, only for
   the same first original action/session/player UUID/world, requiring
   the first native APPLIED+CLEARED markers, the first Paper motor
   fully disarmed, second motor/ACK not active, and a bounded World-tick
   interval. It records Paper `getFullTime()` only: **no motor control,
   P1 update, M0 transaction or new Action authority**. Invalid
   sender, identity, replay, missing release, short interval and
   phase reordering fail closed.
4. An offline reviewer joins the two Paper producer-local fence log
   entries with the original Action-owner receipt flags and count
   bookends, independent Node-local all-inputs-OFF snapshots, and
   8+-tick Paper static-body candidate from the original session.
   It discards both fence ticks and **two Paper ticks at each fence
   side** because scheduler/console ordering within one `fullTime`
   tick is unknown; the returned contiguous static subwindow must
   have at least eight sampled Paper fullTime ticks.

All new behavior is opt-in
`S49_CAUSAL_OWNER_PAPER_FENCE_DEV_ONLY=1` /
`--causal-owner-fence-dev` and depends on existing first native
owner/Node control/two-Action Paper DEV gates. It has **no second
native receiver, no second Action issuer**, no special World pause,
no L0 bypass, no change to original P1 movement computation and no
new M0 ledger owner. The Paper observer only reads and logs World
ticks. The asynchronous owner callback is called only after the
first original S16 terminal and before the second original S15 issue.

## Actual real Minecraft readback

| Observation | Real result from #40438046090 |
| --- | --- |
| First original S49 Action | `s49-native-move-21` · S16 OUTCOME |
| Second original S49 Action | `s49-native-move-59` · S16 OUTCOME |
| First original owner START Paper delivery | **tick 258** |
| Second original owner END Paper delivery | **tick 442** |
| Existing second original S15 ACK APPLIED delivery | tick **443**, after END |
| Native second S15 ACK CLEARED Paper delivery | tick **455** |
| Paper stillness candidate | **264–437**, **174 consecutive** ticks |
| Conservative Paper static subwindow after intersecting owner fence | **264–437 inclusive, 174 ticks** |
| Paper body horizontal motion in candidate | <= **0.002m** each tick |
| Original Node producer-local input OFF | **187 physicsTick** callback samples |
| All Node controls checked | forward, sprint, back, left, right, jump, sneak all OFF |
| Original host first S16 outcome → next issue request | **9,191.294728ms** on host monotonic |
| Original Node between first native clear and second SET | **9,310ms** on Node monotonic |
| Difference of source-local *durations* | **−118.705272ms**; within explicit 1,000ms bound |
| Original S49 Action issued counts (first/second request/final) | **1 / 1 / 2**; open Action count 0/0/0 |
| Full continuous Paper World sample range | **243–460 = 218/218 ticks** |
| Original first Action Paper motor callbacks | 13 |
| Paper bridge / second native ACK window / second tail | 188 / 12 / 5 ticks |
| Illustrative basal M0 shadow (0.5 energy / 20 World tick) | 5.450 energy, **UNPOSTED** |
| Original real B0 owner energy | **12 → 10.413667611509306**, unchanged |
| Original first P1-verified DASH energy extra | 0.08633238849069515 |
| Physical WAIT qualified, P1 recovered, new M0 posted | **NO / NO / NO** |

The extra causal-fence observer shifted the exact Paper trace relative
to an earlier 217-tick run: the actual source shows **218** continuous
Paper callbacks. It is inappropriate to force replayed quantities
to match a previous physical run. Both original S16 terminal outcomes
and the full original B0 M0 accounting remained valid.

## What is proved and what is not

**Causal ordering achieved:** Paper START delivery happened *after*
first native clear, first original S16 terminal and Paper motor
disarm. Paper END delivery happened *before* the second original
S49 S15 native Action issue. Consequently, the **conservatively
trimmed Paper fullTime static tick IDs inside the two accepted
fences** occurred while the same original S49 executor had not yet
issued its second native Action. This is a stronger, clock-offset-free
causal inclusion than comparing three independently sampled durations.

**Remaining limits:** original S49 executor is not globally
attested as the only conceivable issuer of all World actions,
the Node controls are sampled at physicsTick boundaries rather than
cryptographically proved continuous packet custody, the Paper
subject's stillness is not proof of World-wide inactivity, and
host/Node/Paper monotonic clocks and individual ticks remain
unsynchronized. Thus, this is a **causally fenced, source-local
body-stillness / no-issued-original-Action candidate**, not a
production-certified global `WAIT` event. Both actual P1 WAIT
fatigue recovery and additional M0 World-tick debit remain **zero**.
Any P1 recovery needs a separate explicit owner policy and restricted
source-bound WAIT admission; no inferred recoveries are minted here.

### Negative controls and DEV failures

Focused Python 3.12 tests include 31 fence faults: missing or
duplicated START/END, swapped phase, foreign actor/session/world/
second Action, fabricated authority/clock/effect claims, Paper
motor/energy writes, owner already issued second Action, missing
original terminal receipt, stale/broken Paper fullTime and missing
static body. All rejected; Java 21 plugin compilation, Node 22
checks, Ruff and original 2/2 S16 native physical World passed.

Pre-success DEV failures were intentionally fail-closed:
- [#40436747638](https://github.com/rinsakamo/relay-self/actions/runs/40436747638): unit fixture supplied raw owner rather than prior independently audited owner.
- [#40437154821](https://github.com/rinsakamo/relay-self/actions/runs/40437154821): adversarial already-issued-second-Action case exposed a missing owner count check in causal reviewer, added.
- [#40437315303](https://github.com/rinsakamo/relay-self/actions/runs/40437315303): real Paper START accepted but first original owner callback tried to write a report not yet assembled, and original S49 aborted.
- [#40437795706](https://github.com/rinsakamo/relay-self/actions/runs/40437795706): diagnostic re-run identified that original `KeyError` and prevented the misleading secondary missing-END error from masking it.
- Fixed START receipt storage in original owner pending state, later merged when second original Action request arrived. Re-tested source exact HEAD: [#40438046090 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40438046090).

**No main merge/FULL, Draft PR #545/#634 updates, R qualification or SCI execution.**
