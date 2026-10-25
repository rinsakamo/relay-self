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

DASH is **forward only**. Other directions must not receive a DASH speed
modifier. Maximal speed is 1.5 × RUN. Actual Minecraft server/client speeds,
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

Validation is restricted to Python 3.12 focused pytest, Ruff, and syntax.
No FULL / new World / science / PR merge / main update is requested here.
