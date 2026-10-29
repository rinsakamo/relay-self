# RelaySelf G4.2 DEV — native brake ACK latency and postclear drift

Baseline: G4.1 real Minecraft 2026-10-29, exact source HEAD `d9e3b0596a45ddcc06ae442cb15b75f6627187b2`.

- G4.2 is explicit DEV-only opt-in `--g42-brake-timing-dev` plus `S49_G42_BRAKE_TIMING_DEV_ONLY=1` and all inherited G4/G4.1 gates. One existing S49 S15/S16 action owner and T2 P1/M0 owner, no new packet consumer, no new motor issuer.
- A host `perf_counter_ns` is captured in the existing G4.1 native brake callback; the original S15 ACK observer captures the **applied** CLEAR ACK source sequence and host time. The difference is **host callback-to-ACK-received interval**, not sensor-time, wire-time, WorldTick, or physical stopping time.
- The original S16 after-CLEAR native position and the **next original Goal loop probe before the next Action** are joined by source order and session; their distance is **postclear native drift candidate**, not a causal proof of inertia. No synthetic position or inferred collision.
- All source sequences and host monotonic clocks are verified. Missing/mismatched source fails closed. If a short WALK is UNKNOWN, it is never transformed into success.
- The DEV workflow runs Python 3.12 focused, Ruff, Node, and two fresh Paper 1.21.8 Worlds (G4 baseline, G4+G4.1+G4.2) with a matched relative +Z 4.0m target. Absolute spawns can differ. Confirm brake to ACK joins and post-CLEAR drift observations plus single T2 accounting. Retain original failures.
- This is a **measurement phase**, not a within-Action gait switch; no guaranteed per-WorldTick control, no R qualification or V science. Follow-on speed switching needs same-Action typed applied ACK, single owner ledger, and measured interruption semantics.
