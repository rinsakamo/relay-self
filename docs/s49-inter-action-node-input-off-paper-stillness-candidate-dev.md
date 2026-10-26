# RelaySelf — original S49 inter-Action stillness candidate (DEV)

2026-10-27 JST. **DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.
Isolated `self/dev-s49-forward-motor-admission-20261026`.

**Exact source-tested HEAD:** `5b92df227c856447242d2ec08b8c7cbaec82fbd1`.  
**[Actual one disposable Paper 1.21.8 World #40414068146: SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40414068146).**

## Aim

The previous two-native-Action DEV proof observed **217 contiguous Paper
World ticks** and a **187-tick bridge** between first DASH and second
native-effect ACK delivery. The bridge is not automatically WAIT.
This change independently seeks: (a) repeated stationary **Paper body**
samples; (b) the original Mineflayer bot's **actual requested controls**
OFF between its own first clear and second set. Neither source alone
licenses World-wide inactivity, P1 recovery or M0 time-based billing.

## Implementation

- Original `adapters/mineflayer/bridge.mjs` remains **the single
  original S49 process, command recipient, Action owner and native
  effect receiver**. Under explicit
  `S49_INTER_ACTION_CONTROL_DEV_ONLY=1`, bound to existing physical
  S49 DEV gates, it writes one owner-local exclusive-create JSON file.
  This contains first native `clear_controls` and second original
  `set_forward_sprint_dev` identity, Node-local monotonic timing,
  a consecutive ordinal per `physicsTick`, self XZ and *seven*
  requested input control booleans:
  `forward, sprint, back, left, right, jump, sneak`.
- Its buffer is capped at 1,200 physics callbacks, with incomplete /
  overflow flagged and denied. No native observation protocol update,
  extra Action, new reader, movement, energy or P1 write occurs.
- `adapters/mineflayer/s49_inter_action_stillness_dev.py` reads the
  sealed original Node data **after original S49 terminal** and joins
  the already-reviewed producer-local continuous 2-Action Paper
  timeline (same Action IDs/session/world/player). It rejects
  missing/reordered Node physics, active or absent control bits,
  clock rollback, foreign session/Action, incomplete files,
  gaps/duplicates in Paper time, retained first DASH motor or
  invented WAIT/P1/M0 authority.
- Paper local position differences are checked per individual tick.
  A candidate requires **at least eight consecutive Paper World
  callbacks**, each moving **no more than 0.002m horizontally**, after
  skipping first-owner-release boundary/tail and before the second
  original native APPLIED *delivery* marker with a six-tick guard.
  The count is based on explicit consecutive tick IDs; gaps are
  never filled in.
- The two local time axes are **not synchronized**; Paper samples
  have no certified equivalence to Node control samples. There is no
  independent source attestation, no qualified physical WAIT, no
  P1 recovery, no new M0 debit and no change to legacy energy owner.
  Even a long Paper stillness candidate is not proof of a globally
  quiescent World or no ongoing cognition/Action activity.

## Actual Minecraft physical result — run #40414068146

| Observation | Physical/source-local value |
|---|---|
| First original native Action | `s49-native-move-18`, S16 OUTCOME |
| Second original native Action | `s49-native-move-55`, S16 OUTCOME |
| Paper source-contiguous local World ticks | **249–465 inclusive, 217/217** |
| Original first DASH callbacks | 13 |
| Bridge from first release to second ACK delivery | 187 Paper ticks (not qualified WAIT) |
| Second original native APPLIED delivery marker | Paper tick 448 |
| Second original native CLEARED delivery marker | Paper tick 460 |
| Last five Paper callbacks after second clear | 5 |
| Paper static body candidate | **tick 269–442 inclusive; 174 consecutive** |
| Paper per-tick XZ motion maximum inside candidate | **0.002m** |
| Node local input-off physics callbacks before second SET | **186** |
| Node control state throughout those callbacks | All seven controls OFF |
| Native/Paper 1:1 physics/World tick alignment | NOT ATTESTED |
| Qualified WAIT and P1 recovery | **NO / NO** |
| Hypothetical basal M0 over 217 observed World ticks | 5.425 energy, SHADOW only |
| Original legacy M0 energy | **12 → 10.413667611509306** |
| Original legacy B0 MOVE logical steps | Exactly two (0→1→2) |
| P1 first Action single-fatigue replay | 0.600000 → 0.617712241 |
| Original native 1st / 2nd movement distance | 4.105008585m / 3.030157205m |
| Any extra native Action issuer / Paper motor writes | None |

The Node local trace begins when the same original native process
receives the first Action `clear_controls`, and seals **before**
it sets controls for the second issued Action. This establishes
input-OFF in that Node-local interval, not that the Paper candidate
runs are precisely frame-aligned with those input samples.
The Paper candidate may overlap unrecognized physical effects or
other World activity. Consequently, no authentic `WAIT` admission
or P1 recovery is inferred, even though both body-stillness and local
control-OFF are supported by real evidence.

## Tests and failed-closed attempts

Python 3.12 focused negative-controls cover incorrect Action/session
bindings, spoofed input flags (including jump/sneak), missing/replayed
physicsTick ordinals, reversed clock, NaN, incomplete/overflow Node
file, foreign Paper actor, fake M0/P1/WAIT claims, and a nonstationary
synthetic bridge that returns **candidate ABSENT**, not fabricated
WAIT. Ruff, Node22 syntax/bridge checks, Java21 Paper plugin build,
and one disposable real Minecraft World all passed at the above
exact HEAD. Existing original S49 native Action/P1/DASH/energy
readbacks remain sound.

Earlier new-feature CI attempts failed closed in focused tests:
an invalid `Path` class check (rejected legitimate `PosixPath`)
and an incorrect sliding-streak reduction (returned ABSENT on a
known static synthetic input). The reducer was replaced with
explicit stationary World-tick ID collection plus adjacency joining,
without interpolation. All corrections preceded the successful
real-World execution; no failed result was represented as PASS.

## Next DEV boundary

To move a static-body+input-OFF **candidate** into a defensible
source-bound physical WAIT, explicitly join original S49
no-issued-Action state, Node input-control epochs, and Paper World
tick custody under an acceptable cross-clock interval bound.
Paper stillness alone cannot classify no-action World ticks.
Only after the true WAIT owner accepts the interval should P1
physical fatigue recovery run; no provisional recovery is booked.

Canonical M0 basal/MOVE charges remain per original S49 Action
logical steps, not World ticks, until owner migration and explicit
energy-rate approval. main, Draft PR #545/#634 untouched.
FULL, R QUALIFICATION and SCIENCE not executed.
