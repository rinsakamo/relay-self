# RelaySelf G4.3 DEV — post-CLEAR native passive tail and late quiet reference

Starts from G4.2 documented HEAD `fe1f1002ab125daf73be26095ccec3ed47b86a25`; separate branch `self/dev-g43-passive-native-tail-control-20261029`.

- Opt-in `--g43-passive-tail-control-dev` requires `--g42-brake-timing-dev` and environment `S49_G43_PASSIVE_TAIL_DEV_ONLY=1` plus inherited G4/G4.1 gates. No extra issued Action, motor writer, packet reader, P1/M0/T2 debit or assumed gait change.
- After **original applied CLEAR ACK and completed native S16**, the sole session reader collects 5 request-ID-bound observations with cumulative sleep targets ~40, 120, 300, 550, 800 ms after S16. Actual source sequence and host timestamps, rather than fake WorldTick stamps, order samples. There is NO new S49 motor issued until measurement ends.
- Each sample must be native source `mineflayer`, session-matched, with expected request ID, strictly increasing seq and host clock, finite XZ, and complete entity coverage. Failure is fatal to DEV run; no guessed success.
- Compare movement from S16 to nominal 120ms, nominal 120→300ms, and **quiet reference** nominal 550→800ms on the same World/body. The late interval is **not independently randomized**. No proof that physical input was OFF at every WorldTick, no causal attribution to inertia, no guaranteed separation of server tick jitter. All limits are reported.
- Existing G4.2 native after-S16→next original Goal probe is still evaluated (now with a longer observational interval). L0's next Action remains tied to its original Goal probe and the same S49 single owner.
- Verification: Python 3.12 focused, Ruff, compileall, Node, Java and two disposable Paper 1.21.8 Worlds (G4 baseline, G4.3) at relative +Z 4.0m and L1 tolerance 0.55m. Different absolute spawn/World clocks prevent causal speed comparisons. Keep DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.

**Next G4.4 only when source evidence warrants it:** same-issued-Action typed ACK motor gait changes, no secondary executor/ledger. Do not infer a physical speed mode from a requested gait.

## Paper 1.21.8 implementation and real native source results — 2026-10-29

**Physically tested exact CODE HEAD**: `4aee786793d14cf8a5265989ac52bc62b0824b5f`. No changes to main or protected Draft #545/#634. All tests were on isolated branch `self/dev-g43-passive-native-tail-control-20261029`.

Two independent disposable 2-World CI DEV runs passed: [#40845667744](https://github.com/rinsakamo/relay-self/actions/runs/40845667744) and [#40845705490](https://github.com/rinsakamo/relay-self/actions/runs/40845705490). The final-tested run's [retained original evidence artifact #12884886634](https://github.com/rinsakamo/relay-self/actions/runs/40845705490/artifacts/12884886634) contains original World logs/reports and derived hashes. Python 3.12 focused, Ruff, Node, Java build and both Paper Worlds pass.

### Final-tested run #40845705490

- G4 baseline physical World: native GOAL_REACHED / **5** original S49 OUTCOME Actions / **51** single-owner T2 P1/M0 WorldTicks / final native Goal error **0.5395743789342418m**.
- G4.1 + G4.2 + G4.3 physical World: native GOAL_REACHED / **6** original S49 OUTCOME Actions / **131** single-owner T2 P1/M0 WorldTicks / final native Goal error **0.4410493527032211m**. **Two** source-bound RUN early-brake events, original callback→CLEAR ACK host times **0.596084ms and 0.267498ms**; **6** G4.2 post-CLEAR windows. All 6 original Action receipts and all 6 G4.3 source-sorted passive intervals validated; T2 owner intact with no duplicate action issue/debit.
- G4.3 **early S16→nominal 120ms** native delta per Action (m): **0.341705347, 0.198317013, 0.166016545, 0.098674998, 0.059408881, 0.049804963**. Sample host intervals for first Action **226.481ms** (World/process scheduling), thereafter **123.05–123.46ms**, so do not interpret as exact 120ms.
- Nominal **120→300ms** continuation (m): **0.027905357, 0.076746532, 0.064246602, 0.013464998, 0.005243739, 0.014847656**.
- Late **nominal 550→800ms quiet-reference** native deltas: **[0, 0, 0, 0, 0, 0]m** (host interval ~252ms). These are same-World no-*new-S49*-motor *within-Action* references, **not independent controls and not per-tick input-OFF/physical-inertia causation proof**. They do show native XZ position becoming stable under the chosen observations.
- Full original native S16→800ms movement candidate per Action (m): **0.369610704, 0.278462194, 0.230263146, 0.112139996, 0.064652620, 0.064652620**.
- G4 baseline and G4.3 Worlds have matched **relative** +Z4.0m Goal/L1 tolerance 0.55m only, not identical absolute spawn or time. Their Action/T2 tick differences cannot be construed as gait efficiency results; G4.3 explicitly lengthens passive observation windows, naturally increasing WorldTicks.
- No within-Action mode transition, per-tick physical controls attestation, exact Paper native packet timing, QUAL or SCIENCE was run or claimed.

### Independent first run #40845667744

- G4 baseline: 5 Actions / 52 original T2 ticks / final Goal error 0.520945350m.
- G4.3: **6 Actions / 130 original T2 ticks / final Goal error 0.493255948m**, 3 source-bound early brake events; same 6/6 nonzero early post-S16 movement and 6/6 **zero late quiet-reference delta**.
- Early movement ranged **0.049805–0.268839m**. First run source-preserved despite different absolute spawns and runtime.

### Decision / next experiment

**G4.3 PASS as DEV observation**, not causal inertia qualification. G4.2's ~0.05–0.28m after-CLEAR candidates are confirmed by time-resolved native samples as early movement that settles to a stable later position, even though the *reason* and tick-level command application remain unknown. Future G4.4 should first implement typed, correlated **same-issued-Action** gait transition ACKs in the sole S15 reader and account physical gait per original T2 without a second issuer, and validate that each transition cannot advance L0 to REACHED without a later native settle observation. Ensure fail-closed stale/foreign ACK and preservation of CLEAR on any exception. No hidden approval of QUAL/SCIENCE.

**Final classification**: `DEV_ONLY / G43_REAL_WORLD_TWICE_PASS / NATIVE_TAIL_SETTLE_OBSERVED / CAUSAL_INERTIA_UNPROVEN / CONTINUOUS_PER_TICK_GAIT_NOT_IMPLEMENTED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
