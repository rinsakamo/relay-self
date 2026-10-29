# RelaySelf G4.2 DEV — native brake ACK latency and postclear drift

Baseline: G4.1 real Minecraft 2026-10-29, exact source HEAD `d9e3b0596a45ddcc06ae442cb15b75f6627187b2`.

- G4.2 is explicit DEV-only opt-in `--g42-brake-timing-dev` plus `S49_G42_BRAKE_TIMING_DEV_ONLY=1` and all inherited G4/G4.1 gates. One existing S49 S15/S16 action owner and T2 P1/M0 owner, no new packet consumer, no new motor issuer.
- A host `perf_counter_ns` is captured in the existing G4.1 native brake callback; the original S15 ACK observer captures the **applied** CLEAR ACK source sequence and host time. The difference is **host callback-to-ACK-received interval**, not sensor-time, wire-time, WorldTick, or physical stopping time.
- The original S16 after-CLEAR native position and the **next original Goal loop probe before the next Action** are joined by source order and session; their distance is **postclear native drift candidate**, not a causal proof of inertia. No synthetic position or inferred collision.
- All source sequences and host monotonic clocks are verified. Missing/mismatched source fails closed. If a short WALK is UNKNOWN, it is never transformed into success.
- The DEV workflow runs Python 3.12 focused, Ruff, Node, and two fresh Paper 1.21.8 Worlds (G4 baseline, G4+G4.1+G4.2) with a matched relative +Z 4.0m target. Absolute spawns can differ. Confirm brake to ACK joins and post-CLEAR drift observations plus single T2 accounting. Retain original failures.
- This is a **measurement phase**, not a within-Action gait switch; no guaranteed per-WorldTick control, no R qualification or V science. Follow-on speed switching needs same-Action typed applied ACK, single owner ledger, and measured interruption semantics.

## Actual Paper 1.21.8 DEV results, 2026-10-29 JST

- Exact **physically tested code HEAD**: `ffdd3cb3a7af8632c166c15230f31f923998a63c`.
- [G4 baseline / G4.2 source-focused two-World workflow #40832332789 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40832332789). [Original saved artifact #12879625063](https://github.com/rinsakamo/relay-self/actions/runs/40832332789/artifacts/12879625063). Focused Python 3.12, Ruff, Node, Java Paper build passed. Both World simulations were disposable DEV and reached the original Goal.
- Baseline G4: 3 original S49 Action OUTCOMEs, 39 original T2/P1/M0 WorldTicks, final native Goal error `0.5207522378637011m`.
- G4.1+G4.2: 6 original S49 Action OUTCOMEs, **6 strict source-ordered after-CLEAR→next-probe windows**, 58 original T2/P1/M0 WorldTicks, final native Goal error `0.49526855477631937m`. Exactly 2 early brake requests/qualified host ACK pairs, no second action issuer, no T2 owner failure.
- RUN Action step 2: native early brake probe → applied native CLEAR ACK host callback delta `1.623352 ms`. RUN Action step 3: `0.330289 ms`. Both are source-ordered host process readings; **not physical latency or full packet→Paper WorldTick attestation**. Measurement is bounded by Python callback scheduling and receipt arrival.
- After-S16 to the next original native Goal probe, the six position delta magnitudes were **0.258907479, 0.280731930, 0.153222385, 0.216718951, 0.066364361, 0.064652620m**. Their host inter-probe gaps were approximately **307.965, 202.107, 202.380, 202.927, 203.603, 202.440ms**. Label these as *postclear drift candidates*, **not inertia causality**; there is no closed no-motor or zero-velocity control that isolates causal inertia.
- The two disposable Worlds share relative +Z 4.0m Goal and L1 tolerance 0.55m but do not share absolute spawn coordinates or exactly matched wall/World timing. Baseline's three Actions vs G4.2's six do **not** license comparative speed/efficiency causal claims. An action's original S16 OUTCOME is not proof of a continuous gait class.
- DEV_ONLY / G42_NATIVE_BRAKE_ACK_TIMING_POSTCLEAR_DRIFT_REAL_WORLD_PASS / INERTIA_NOT_CAUSALLY_ATTESTED / PER_TICK_GAIT_NOT_IMPLEMENTED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.

## Next engineering gate (G4.3)

Introduce a no-motor, matched native post-CLEAR observation window to separate motion tail from the original 200ms observation delay and server jitter; measure the clear ACK → Paper tick boundary where available. Only then consider a **single issued S49 Action with typed in-place gait-change ACKs**. Never create another executor or duplicate T2 source, and do not count requested gait as actual physical tick mode.
