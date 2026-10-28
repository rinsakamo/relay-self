# RelaySelf S49 — observed L0 micro WALK / genuine WAIT DEV

**DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**

Starting source: `445796b3e63966eb873f31f63a3b00336be33e5c`; prior `S49_L0_THREE_REAL_S16_DEV_PASS` tested original Minecraft 1.21.8 S16 movements 3.030m → 0.815m → 0.324m. Second/third scalar travel 1.139m versus relative 1.0m target (overshoot +0.139m). No Paper/Node forced synchronization.

## Choice/action separation

Both arms run separate fresh vanilla Mojang Minecraft 1.21.8 disposable Worlds with original `NormalWorldL0`, existing NativeObservationOnly `session.receive()`, unchanged S14→S15→S16 issuer and independent grants. Each real World receives a far zombie event (original WAIT), two near zombies (original MOVE_AWAY) and a fourth fresh native zombie event. No extra action issuer, observer, replay, model call or S10/P1 authority.

**WALK**: after second native S16, original L0 independently chooses third MOVE_AWAY on fourth zombie; DEV bound S14 action ref for third Action is `MOVE_FORWARD` instead of `MOVE_FORWARD_SPRINT_DEV`, with same existing Mineflayer `set_control('forward', true)` effect. The third input duration is `clamp(residual / observed second-action speed, 0.10..0.60s)`; World physics/latency determine the actual movement. Original S16 reports the third WALK horizontal distance. This does **not** implement global WALK/JOG/RUN/DASH controller.

**WAIT**: original second S16 residual within explicit 0.20m deadband and no immediate threat (<1.5m) allows the **same** NormalWorldL0 to arm a source-identified stop criterion. On fourth independent real zombie/probe pair it chooses `WAIT` itself. `ReactiveL0.run_session` passes **no Action grant**, does not invoke Action request callback, and its Action budget stays at two real actions. Source carries the previous second closed S16 ID; no observer simulates the WAIT event. Outside deadband, mismatched session, stale Action, immediate danger or missing owner gates fail closed or preserve native threat MOVE. In this DEV, the 0.20m stop criterion concerns **relative 1.0m step scalar distance**, not absolute World coordinates. A real MOVE request cannot be secretly converted to WAIT in an action callback.

## Source gates / safety

Only when separately opted in: `S49_L0_OBSERVED_FEEDBACK_DEV_ONLY`, `S49_L0_RESIDUAL_THIRD_DEV_ONLY` (WALK), `S49_L0_WALK_THIRD_DEV_ONLY` (WALK), `S49_L0_GOAL_WAIT_DEV_ONLY` (WAIT), original `S49_NEXT_EPOCH_DEV_ONLY`, original S49/Mineflayer owners. No forced tick count, no always-on synchronous trace. The WALK and WAIT flags are mutually exclusive; all result receipts remain original S49 typed S16.

Workflow `.github/workflows/self-l0-walk-wait-two-worlds-dev.yml` performs Python 3.12 focused tests and Ruff, Node22 bridge syntax, original Mineflayer install, then two fresh real Worlds; archives raw source even on failure. A wrong Action count, missing S16 / STOP evidence, or a third Action in WAIT arm rejects the run. main and Draft #545/#634 remain unchanged.

### Limits

The WALK and WAIT World instances are distinct and their threat event timing is not phase matched. The near-target WAIT policy could choose to wait despite a zombie 2m away, but only in this explicit step-calibration DEV gate; real escape safety and integrated intent prioritization need separate real testing. This exercise is not QUAL/SCIENCE evidence or proof of actual absolute target position.
