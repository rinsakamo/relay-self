# RelaySelf P1 single-state gait / DASH — DEV 2026-10-25

Status: **DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.
This is an offline evaluator prototype, **not native Minecraft control**, fatigue
interoception, M0 posting, real Paper ticks, or evidence for physiological fitness.

## Agreed design

Minecraft is a compressed World. Do not introduce high-intensity fatigue
reservoirs, independent stamina bars, cooldown timers, or an imitation of human
metabolic pathways. Keep **one P1 fatigue state**.

| Self mode | Vanilla input (proposed) | Nominal forward m/s |
| --- | --- | ---: |
| WALK | sneak | 1.30 |
| JOG | regular movement | 4.32 |
| RUN | vanilla sprint | 5.61 |
| DASH | forward sprint + temporary speed modifier | up to 8.415 |

DASH's **boost is forward only**, but DASH *stance* is retained while
strafing or retreating. For the first DEV model, side/back cap is set to
JOG's 4.32 m/s (design ceiling, **not** an observed Minecraft velocity).
Side/back consume no additional DASH M0 charge and use ordinary RUN fatigue;
a transition back to forward movement may use DASH again if its P1/M0 budget
permits it. Maximal forward speed is 1.5 × RUN. This avoids toggling off the
DASH stance at every directional change. Paper's global MOVEMENT_SPEED
attribute does **not** impose a hard direction-dependent cap. A physical
motor-mode controller must apply the forward modifier only where supported,
and must validate authoritative directional input or displacement to rule
out unintended sideways/backward acceleration. Previous Paper InputEvent
probes did not establish reliable control edges; fail closed on ambiguity.
Do not claim that this offline model enforces the in-World directional cap. Actual Minecraft server/client speeds,
especially acceleration, stopping, and effects in other directions, must be
measured rather than inferred from these nominal numbers.

A tick-local externally validated applied gait powers the DEV P1 function:

\[
d(F/C)/dt = L(g,p) - k(g)\,(F/C)
\]

where C is the existing P1 capacity, g is the applied gait, and p∈(0,1]
is DASH output. Both terms operate *during every gait*, including DASH.
Rates are scenario design parameters, not biological measured coefficients.

Illustrative rates:
- WAIT: no movement load, recovery k=0.12/s.
- WALK: zero load, k=0.10/s.
- JOG: load 0.002/s, k=0.06/s (equilibrium F/C≈0.033).
- RUN: load 0.004/s, k=0.025/s (equilibrium F/C=0.16).
- DASH: load interpolates between RUN load and full-DASH load with p^1.2;
  k=0.02/s. Full-DASH load is derived analytically so that starting from
  F=0 and applying power 100% continuously reaches F=C after 20 seconds.
  The full output limit is a *game design calibration*, not a literal
  physiological time-to-exhaustion measurement.

The analytical per-tick transition (0.05s) avoids integrating differently
when the runner is slow. At F=C, DASH admission fails; RUN/WALK can continue
and recover. Partial DASH outputs impose smaller loads. No separate DASH
recovery or timer exists. The current demonstration uses cutoff rather
than output taper near exhaustion.

## M0 boundary

The DEV transition proposes an **additional** M0 cost for DASH power,
0.20 M0 units per second at full output, so 20 seconds adds 4 M0 units.
Ordinary basal/MOVE energy expenditure still belongs to the *existing M0
ledger*, and **this new receipt does not post anything to M0**.

The preflight caller must supply *extra* M0 energy available **after** normal
basal/MOVE obligations. Both available energy and elapsed/applied output need
World/evaluator evidence; intentions, Python sleep duration, and Mineflayer
physicsTick alone are insufficient. Do not run
metabolism_viability.metabolism_step() on every World tick: its current tick
is an M0 action accounting step, not established as 20Hz Minecraft time.

## Boundaries / next integration

- New module: experiments/p1_gait_dev.py (pure, alternative transition).
- Existing experiments/fatigue_p1.py remains bit-for-bit unchanged.
- Existing S49 original Action issuance, Mineflayer control, Paper observer,
  protected historical evidence and P1 boundary remain unchanged.
- A passed-through GaitTickDev object is **not** source attestation; callers
  must authenticate and bind a tick and applied direction/output before use.
- SelfBody must treat P1 model outputs as hypotheses until real native
  interoception exists. Do not attribute Mineflayer ↔ Paper timing
  uncertainty to intrinsic physical fatigue.
- The earlier 0.10m SelfBody Motion Uncertainty DEV damping heuristic is
  **not adopted** as bodily uncertainty.
- Follow-up actual World task: separately gate an issued S49 forward DASH
  on the S49 one-owner path, apply and remove a temporary Paper server
  modifier, observe actual motor ticks and forward/side/back negative controls,
  then post each verified net M0/P1 tick once. **Do not claim this occurred
  from the offline model or the present focused CI.**

The initial single-P1 model used Python 3.12 focused pytest, Ruff, and syntax.
A later isolated real Paper negative trial was also run (see below).
No FULL / science / PR merge / main update.


## Implemented Paper motor prototype and measured negative control

DEV plugin: `adapters/mineflayer/s49_paper_dash_dev/`, default OFF.
Its one-shot console claim can be armed only by an external owner; that
claim is **not** cryptographic proof of an issued S49 forward Action.

For an explicitly armed subject, the Paper main-thread motor observer keeps
DASH *stance* through lateral/backward motion; its transient
`MOVEMENT_SPEED` bonus (up to +50%) is applied only on unambiguous
forward-only sprint input, otherwise cleared without dropping stance.
Unexpected/unverified input always gets **no additional DASH bonus**.
This is NOT an independently proven hard cap against other mods,
intra-tick forward-to-side changes, or Mineflayer/Paper clock skew.

**Original S49 backward negative in real disposable Paper 1.21.8:**
GitHub workflow run https://github.com/rinsakamo/relay-self/actions/runs/40205538388
on exact tested commit `ddfef0db6de51ce5d939e073a23f0373abed83b6`.
Original S49 2 Action outcomes, Paper DASH diagnostic 5 ticks,
**forward modifier active 0 ticks**, Java/Node exit 0, cleanup confirmed.
P1 native state and M0 ledger unchanged; original Action/World evidence
preserved. Explicitly **not** a forward-DASH or side-speed qualification.

DEV retries retained: 40204947652 failed pre-DASH due missing sole-session
reference; 40205129465 / 40205349719 failed from same-world-tick
scheduler callback erroneously triggering automatic safety disarm.
The final test allows the *initial* same-tick callback while keeping
subsequent non-increasing World tick checks fail closed.

Remaining live work: add a genuinely authorized forward DASH Action
through the existing S49 single issuer, then test actual forward speed,
side/back cap, release timing, and source-bound M0/P1 settlement
(without inferring elapsed full World ticks from host sleep time).
No main / PR #634 adoption or qualification is implied.

## 2026-10-26 paired Paper / Mineflayer motor DEV

Branch: self/dev-s49-dash-forward-operator-world-20261026

This is an **explicitly operator-owned forward experiment** performed
within the sole original S49 Mineflayer session *after* the two real
S49 MOVE_BACKWARD Actions had each reached original S16 terminal.
It is **NOT** an S49-issued MOVE_FORWARD Action or S16 learning receipt.

| Exact GitHub World run | RUN / 0.9s | DASH / 0.9s | ratio | Paper boosted ticks |
| --- | ---: | ---: | ---: | ---: |
| https://github.com/rinsakamo/relay-self/actions/runs/40241254554 | 4.810m | 5.046m | 1.049 | 0 |
| https://github.com/rinsakamo/relay-self/actions/runs/40241532469 | 4.810m | 5.046m | 1.049 | 23 |
| https://github.com/rinsakamo/relay-self/actions/runs/40242559345 | 4.810m | **7.573m** | **1.574** | 24 |

The third trial used a temporary, single-session Mineflayer bridge
that mirrors the Paper +50% modifier to the missing client self attribute
minecraft:movement_speed while forward+sprint is in effect. The original
bridge.mjs remained unchanged, as did the original one-owner S49 controls.
A separate trace proved that the unmodified Mineflayer client had no
own movement speed attribute and used physics.playerSpeed=0.1:
https://github.com/rinsakamo/relay-self/actions/runs/40242229676.

All trials verified independent Paper modifier cleanup; the paired run
also retained exactly two original S49 closed actions and Java/Node exit 0.

**Important limits**:
- 1.574 is the observed displacement ratio including acceleration and
  stopping time, not certified steady-speed multiplier.
- Paper/Node actual effective motor ticks are not source-aligned.
- The previous real backward negative https://github.com/rinsakamo/relay-self/actions/runs/40205538388
  observed zero forward modifier ticks while DASH stance remained active.
  **Lateral speed cap enforcement is still unverified.**
- No genuine S49 forward Action permission, M0 posting, P1 native state
  settlement, 20-second physical exhaustion, fatigue-induced speed limiting,
  L0 learning or S10 memory update was executed.
- The 4.32 m/s side/back target remains a proposed design cap; Paper's
  transient attribute switching is not a proven hard instantaneous cap.

DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
