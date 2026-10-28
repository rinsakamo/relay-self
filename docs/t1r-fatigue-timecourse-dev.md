# T1r — real-world passive fatigue timecourse in SelfBody (2026-10-28)

Baseline T1q real Minecraft DEV: `4c82333e6015db423ce631674dc6907081a2ba30`
(1 PASS/0 FAIL; 2 native MOVE/OUTCOME/clear; 61 consecutive accounted ticks).
**DEV_ONLY / OFFLINE_IMPL_ADDED / T1R_NATIVE_UNVERIFIED /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.**

## Why this change is needed

The previous T1q `SelfBodyView` was read only at the **next Action** decision,
after S49 clear, native Paper input/pose settling, and 12 more World ticks.
T1q reported the same 12.0 energy perception at both decisions despite the
actual evaluator ledger declining, which is correct with the .25 sensor quantum.
P1 was already recovered to zero in both decisions. In the unchanged physical
P1 model, normal short 0.2s backward movement generated about 0.03 fatigue,
while each qualified DEV callback WAIT tick can recover as much as 0.10.
A sensing interface sampled only after long settling can miss the nonzero
fatigue state entirely. **Do not modify P1 physiology, boost fatigue, insert
artificial conditions or weaken the safety boundary to manufacture a signal.**

## Minimal code path

```text
Existing Paper1.21.8 tick --> Original T1e single Mineflayer receiver
    --> Existing T2 TickAccounting.observe() / M0 / P1 state advance
    --> T1r optional PASSIVE observer on that same admitted frame
    --> original #634 SelfBodyView with M0/P1 quantized INTEROCEPTION
    --> sensed-rest *preference* timeline (never Motor authorization)
    --> Existing T1q L0 Action decisions, original T1p/S51/S49/S16
    --> original WAIT_DEV accounting; no new native IO or Action writer
```

The T1r callback is installed only inside the `run_t1r_body_recovery_dev`
scope and always removed even on error. It ignores the T2 initial anchor
which has not yet produced any accounted row. When the original T2 is
accounting and an original S49 Action remains open, T1r requests
`project_t1q_selfbody(..., passive_during_action=True)`:
this is a **read-only signal**, not a motor decision. The original T1q
action policy still rejects an active Action and cannot grant a new issue
while it is open. Session/Paper tick/M0 tick/P1 owner state and
native provenance are rechecked for every sample.

Each recorded sample is a small SelfBody cognition record containing
source seq, Paper WorldTick, M0 tick, observed health/food and
quantized `m0_energy_sensor` / `p1_fatigue_sensor`; the state used
to compute the projection remains evaluator-local. Original Action
open state and activity are *audit context*, not self-declared authority.
The source native / Python / ledger are written by existing owners only.
No separate reader, full-precision cognition leak, per-tick new Node sync trace,
LLM, extra physical motor effects, new metabolic debit or P1 recovery.

Designed DEV **perceptual preferences**, not unambiguous physical Actions:
fatigue sensor >=0.02 -> REST_PREFERRED; otherwise READY_FEELING
(unless energy sensing <=3.0 or unavailable, when resting/unknown remains
the conservative choice). This 0.02 boundary is only a short-lived local
demonstration of a different SelfBody *perception*, not a medical/physical
calibration. In the normal T1q/t1p loop, only the independent ordinary
L0 decision can authorize the next bounded action. Do **not** equate
REST_PREFERRED during an already running Action to a STOP command or to
a proved change in Motor duration. A real new Action delay due to sensing
would require separate owner-reviewed integration.

The T1r external, read-only audit reconstructs the **original** per-tick
M0/P1 sensor values from original `t2_ticks` owner rows. It requires one
new passive record per accounted WorldTick, all matching native seq/session,
sensor origins and quantization. The auditor alone may inspect exact ledger
values; those values are not copied to the SelfBody cognition trace. It
records presence/absence of sensed-rest and sensed-ready states
separately from original P1 fatigue accumulation and WAIT_DEV recovery.
It does not certify a P1-qualified WAIT or any new independence.

## Next physical DEV — LocalCodex

First verify isolated branch and original baseline SHA and clean
separate worktree; use verified existing assets, Python3.12, Node22,
Java21/Paper1.21.8/Mineflayer4.39.0. Focused:

```bash
PYTHONPATH=src:tests:. python3.12 -m pytest -q \
  tests/test_t1r_fatigue_timecourse_dev.py \
  tests/test_t1q_interoception_dev.py \
  tests/test_t1p_body_runtime_dev.py \
  tests/test_t1f_t2_dev.py \
  tests/test_t1e_native_dev.py
```

Then existing Python3.12 FAST/Ruff/repository contracts. Test fixture
and Python import failures should be fixed narrowly; preserve first
FAIL evidence. No Node/Java rebuild if source unchanged. No FULL/SCIENCE.

After offline PASS, **one new disposable DEV World** `T1R-001`, fresh
absolute output root, original assets and command:

```bash
PYTHONPATH=src:tests:. python3.12 -m adapters.mineflayer.t1e_native_dev \
  --cases t1r_body_recovery --loop-moves 2 --node-trace off \
  --output /NEW/ABSOLUTE/T1R-001 \
  --paper /VERIFIED/PAPER.jar \
  --plugin /VERIFIED/PLUGIN.jar \
  --bootstrap /VERIFIED/BOOTSTRAP \
  --confirm T1E-DISPOSABLE-DEV-ONLY
```

Acceptance: 2 original MOVE/OUTCOME/clear, one canonical T1e source
reader, uninterrupted source/admission, original T2 M0/P1 accounting,
positive nonzero P1 fatigue during native movement and zero after
sufficient WAIT_DEV, at least one source-linked REST_PREFERRED and one
later READY_FEELING; no extra Action, no false Action/WAIT qualification,
zero food/LLM/TPS actuation, Node sync trace OFF, original exit/shutdown
ACK/PID cleanup/port rebind, exact SHA256 evidence readback.

If natural motion does not give an observable nonzero **quantized**
P1 signal, do not silently inject a stimulus or falsify a trace.
Retain FAIL/UNKNOWN with its raw source and report observed bounds;
correct bugs and rerun as a new disposable World where reasonable.

Report to existing #537/#627/#632/#616 after actually running,
commit/push nonforce and read back. Do not touch main, Draft
#545/#634/#626, frozen S18, or any R/V owner. Do not convert source
passive callback into independent full-tick verification.
