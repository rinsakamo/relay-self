# RelaySelf — Two original S49 Actions, continuous Paper World time, M0 shadow DEV

Date 2026-10-26 · **DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.
Branch: `self/dev-s49-forward-motor-admission-20261026`.

**First full physical success, exact source HEAD `4954895ef57ec72614b4e0c5b46ab85b35864c67`:**
[GitHub Actions real Paper 1.21.8 World #40335084843 — SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40335084843).

**Final workflow/readback verification, tested HEAD `ca25e43866b4367cc2615c4f0c483eab62b68172`:**
[Real two-Action Paper World run #40335184537 — SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40335184537).
The final run independently reproduced **217 contiguous ticks**
(tick 248–464), first DASH callback count 13, bridge 187,
second native ACK-delivery window 12 (APPLIED tick 447,
CLEARED tick 459), and final passive tail 5. Source Action IDs
`s49-native-move-19` and `s49-native-move-57` both achieved
S16 OUTCOME. It also reproduced shadow basal 5.425 without
posting, geometric MOVE shadow 0.1625+0.1500 without posting,
original B0 M0 energy 12→10.413667611509306, and
original Node/Paper consecutive motion fingerprint matching 2 samples.
Python3.12 focused, Ruff, Node22 syntax/bridge,
Java21 plugin compile and physical World all SUCCESS.

## New DEV engineering scope

Prior original S49 native Action/Paper/P1/M0 integration already showed:
1. one physical forward DASH Action with native S15 typed APPLIED/CLEARED ACK,
   Paper P1 motor speed modifier and verified S16 OUTCOME;
2. one original non-DASH MOVE Action with verified S16 OUTCOME;
3. native forward/sprint false after clear-controls, plus Paper
   position updates after modifier removal;
4. original B0 M0 one logical MOVE step for EACH native Action,
   with P1-verified DASH extra cost only in the first Action;
5. an expressly assumed **0.5 energy per normalized World-second**
   basal shadow on 13+5 bounded Paper callback ticks, while excluding
   unsampled World tick 261.

The missing integration was **the long interval between the two
original native Actions**. This DEV change adds a second, read-only
Paper producer-local timeline, independent of the one-shot existing
DASH motor. The timeline samples consecutive `World.getFullTime()`
ticks from the original *first* ARM through second native control
CLEAR plus five Paper ticks. It captures entity horizontal XZ, same
original session, player/world UUID, exact consecutive tick indices,
and whether native second original S15 effect ACK delivery markers
have been received. A short-lived, strictly gated console command
`relays49dashtrailmark` accepts only the original actor, second Action
ID, APPLIED/CLEARED in order with native sequence numbers. It has
**no motor, Action, L0, M0, P1 or S10 mutation powers** and adds no
native listener/reader. Native ACK markers mark *Paper delivery after
an already-received original native ACK*, not exact physical effect
onset or stop World tick. A bounded five-tick second tail is captured.

Paper-side observer maximum 1,200 World tick callbacks, fixed
original subject and World, monotonic `fullTime`, same-World-tick
callback discarded, fail-closed on gaps/changed actor, and stop
after five Paper callbacks following the second ACK delivery.
Original plugin DASH is still physically active only for the first
Action and is removed on original owner RELEASE.

Offline reviewer `s49_two_action_world_timeline_dev.py` replays the
full Paper log; joins both original issued S16 Action outcomes, first
Paper arm/release/callback bracket, passive post-release records,
typed native second Action dispatch and cleanup S15 ACK seq, exact
second Paper console delivery marker source, and original B0 M0
owner post-Action ledger. It denies missing/repeated/reordered World
ticks, forged actor/session, duplicated or swapped native ACK,
missing terminal, invented WAIT/P1/M0 posting, residual first DASH
modifier, nonfinite or teleported location, insufficient measured
second-window geometry, and fraudulent energy owner balances.

## Actual observed World: read-only normalized time

At exact source tested HEAD `4954895ef57ec72614b4e0c5b46ab85b35864c67`:

| Item | Direct physical/ledger observation |
|---|---|
| Original first native Action | `s49-native-move-20`, OUTCOME |
| Original second native Action | `s49-native-move-58`, OUTCOME |
| Paper timeline first/last tick | **244 through 460**, inclusive |
| Consecutive World ticks captured | **217/217, no gap/duplication** |
| Original first DASH motor Action observed | **13 ticks** |
| First release → second APPLIED-marker bridge | **187 ticks** |
| Second original native ACK APPLIED delivery | **Paper tick 443** |
| Second original native ACK CLEARED delivery | **Paper tick 455** |
| Second native ACK-delivery window | **12 ticks**, 12 geometric movement proxies |
| Post-second-clear observation tail | **5 ticks** |
| All 4 buckets exactly partitioned | 13 + 187 + 12 + 5 = **217** |
| Explicit normalized time | **10.85 World-seconds** (217 / 20) |
| Assumed DEV basal rate | 0.5 energy / normalized World-second |
| Basal energy shadow | **5.425, NOT POSTED** |
| Assumed DEV MOVE rate | 0.25 energy / normalized World-second |
| First Action window MOVE shadow | **0.1625, NOT POSTED** |
| Second marker-window geometric MOVE proxy | **0.1500, NOT POSTED** |
| Old M0 original Action charges | 2 × (0.5 basal + 0.25 MOVE) |
| Old M0 original DASH extra | 0.08633238849069515 for first Action |
| Original real ledger final energy | **12 → 10.413667611509306**, unchanged |
| Single P1 first Action | fatigue 0.6 → 0.6177122410202606 |
| Original Action native movement distances | 3.892684618m / 3.030157205m |

These bucket labels are *paper observations and ACK-delivery marker
boundaries*. The **187-tick bridge is NOT attested as inactivity or
qualified WAIT**. It may contain pending movement, control changes and
unobserved activity; it is a counted Paper World-time interval only.
The **second 12-tick ACK-delivery window is NOT a source-certified
precise physical second Action onset/offset interval**. Moving XZ
samples (>0.02m) are an explicitly labeled geometric proxy, not a
packet-certified forward-only movement control. No tick is classified
as both bridge and second ACK-window, so no double-counting in the
read-only shadow. Existing M0 Action debits still occupy their
legacy logical units and are not added to the new World-time shadow.

### Observer effect and ambiguity

The new per-tick Paper logger increases passive instrumentation
relative to the earlier 13+5-only probe. An earlier real trial
[#40334377136](https://github.com/rinsakamo/relay-self/actions/runs/40334377136)
recorded the **full second Action trace and original S49 PASS**,
but the previous extremely tight Node/Paper consecutive motion
fingerprint (1µm tolerance) failed. It was correctly **FAIL_CLOSED**,
not re-labeled successful. In the new **two-Action-only DEV mode**,
the 1µm fingerprint is a distinct diagnostic:
when it matches, the prior single-Action 13+5 shadow is also
calculated; when it doesn't, the result is explicit
`NODE_PAPER_GEOMETRIC_FINGERPRINT_UNDETERMINED`, with
`exact_match_confirmed=false` and no prior 13+5 shadow
invented. The **new two-Action timeline still independently requires
the full Paper producer-local tick series and native S15 ACK joins**.
The original single-Action fingerprint workflow remains strictly
fail-closed without this new mode. In the full successful World above,
the two producer-local motion traces *also matched* on two adjacent
nonzero deltas.

Earlier DEV implementation failures are preserved: a misplaced
first-DASH ARM branch temporarily denied the old workflows;
restored original first-Action arm and left the second Action
read-only. Unit tests identified that the reviewer initially matched
second-Action EDGE rows against the *first* Action ID, and that
one negative test never actually inserted NaN. Both bugs were
corrected and then a real World test reached SUCCESS.

## What is / is not achieved

**Achieved:** source-joined original S49 2/2 native Action outcomes,
one continuous Paper producer-local World time range spanning both
original Actions, proof of 217 unique original World clock ordinals
captured with no duplicate callback/gap, a separately delimited
second Action's native-ACK-delivery marker window, and explicit
per-normalized-World-second **shadow-only** basal and MOVE proxies.
Original physical motor, P1 first Action replay, and canonical
original B0 M0 energy balances stay intact.

**NOT achieved:** independent World tick issuer source
authentication; synchronized Mineflayer physics ticks versus Paper
World tick; physically exact second Action onset/offset World tick;
a global observation covering all World activity before first ARM
or after second tail; stationary/no-Action SourceBoundTick;
P1 WAIT recovery; real biologically grounded energy per second;
an authorized new World-time M0 charge or migration from original
per-Action M0 accounting. The observed 217 World ticks should not be
misstated as **10.85 seconds of actual host wall time** or "187 ticks
of idle WAIT".

All changes are isolated DEV branch. **main, Draft PR #545 and #634
unchanged. No R qualification, SCI, FULL regression or main merge**.
