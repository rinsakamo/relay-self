# RelaySelf G4.7 DEV — original T2 WorldTick x G46 stable gait candidate x P1/M0

Parent G4.6 isolated DEV final HEAD `ce47a0e755af7fce1cedff93523b09e8678fbebf`. G4.7 new branch `self/dev-g47-original-t2-gait-join-20261029`; main/protected Draft unchanged.

## DEV contract

Under `S49_G47_ORIGINAL_T2_GAIT_JOIN_DEV_ONLY=1` and `--g47-original-t2-gait-join-dev` (requires G46/G45/G44), post-run join uses the **existing original** Paper/T1u/G1 frame, G46 native Action/effect generation and the **single original T2 per-WorldTick owner row**. It does not add a session reader, motor issuer, T2/P1/M0 posting, synchronous trace, or periodic callback. Every original T2 row gets one immutable hash-linked audit row including exact original `m0` and `p1` receipts, same-session Paper source seq and WorldTick, G1 kind, Node generation/Action effect and evidence status. No original row is modified.

A WorldTick may be marked `SOURCE_BOUND_STABLE_GAIT_CANDIDATE_DEV` ONLY when original T2's already-posted `applied_gait` agrees with a two-sample G1 stable Paper gait candidate, native Node generation matches original same Action/effect ACK, Paper challenge was issued after Node control modification, and original T2 action remains active for that interval. Even this is a **bounded candidate**, not exact physics-tick command acceptance or R qualification. All other cases are differentiated UNKNOWN (no effect window, missing owner, stale challenge, unstable Paper gait, original T2 fallback). G4.7 never fills unknown with motor intent or credits P1/M0 a second time.

Source invariants: all original T2 WorldTicks contiguous, exact G1/T2 source-seq/world-tick join, one original T2 G3 owner, `qualification=false`, `full_tick_R_attested=false`, original P1 and M0 receipts present, no unexpected extra energy debit inside G4.7 RUN/JOG/WALK sourced periods. Any forged source, lost Paper/T2 frame, duplicate tick, invalid receipt or forged QUAL fails closed and is test-covered. A derived JSON contains all WorldTicks, SHA of original G1 and T2 derived ledgers, SHA per original T2 row and explicit source-status counts. Original source files remain immutable.

DEV CI uses focused Python3.12/Ruff, Node22, unchanged Java21/Paper1.21.8 and three disposable real Worlds: G4 baseline, G4.7 3.5m L0 target, and real zombie injection during in-place JOG. Hazard must retain existing original CLEAR→S16 UNKNOWN and single T2 safe refusal with no P1 credit and no next S49 Action. No grant or promotion to R QUAL or V SCIENCE.
