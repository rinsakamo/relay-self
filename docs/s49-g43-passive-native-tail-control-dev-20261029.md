# RelaySelf G4.3 DEV — post-CLEAR native passive tail and late quiet reference

Starts from G4.2 documented HEAD `fe1f1002ab125daf73be26095ccec3ed47b86a25`; separate branch `self/dev-g43-passive-native-tail-control-20261029`.

- Opt-in `--g43-passive-tail-control-dev` requires `--g42-brake-timing-dev` and environment `S49_G43_PASSIVE_TAIL_DEV_ONLY=1` plus inherited G4/G4.1 gates. No extra issued Action, motor writer, packet reader, P1/M0/T2 debit or assumed gait change.
- After **original applied CLEAR ACK and completed native S16**, the sole session reader collects 5 request-ID-bound observations with cumulative sleep targets ~40, 120, 300, 550, 800 ms after S16. Actual source sequence and host timestamps, rather than fake WorldTick stamps, order samples. There is NO new S49 motor issued until measurement ends.
- Each sample must be native source `mineflayer`, session-matched, with expected request ID, strictly increasing seq and host clock, finite XZ, and complete entity coverage. Failure is fatal to DEV run; no guessed success.
- Compare movement from S16 to nominal 120ms, nominal 120→300ms, and **quiet reference** nominal 550→800ms on the same World/body. The late interval is **not independently randomized**. No proof that physical input was OFF at every WorldTick, no causal attribution to inertia, no guaranteed separation of server tick jitter. All limits are reported.
- Existing G4.2 native after-S16→next original Goal probe is still evaluated (now with a longer observational interval). L0's next Action remains tied to its original Goal probe and the same S49 single owner.
- Verification: Python 3.12 focused, Ruff, compileall, Node, Java and two disposable Paper 1.21.8 Worlds (G4 baseline, G4.3) at relative +Z 4.0m and L1 tolerance 0.55m. Different absolute spawn/World clocks prevent causal speed comparisons. Keep DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.

**Next G4.4 only when source evidence warrants it:** same-issued-Action typed ACK motor gait changes, no secondary executor/ledger. Do not infer a physical speed mode from a requested gait.
