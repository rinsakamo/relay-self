# RelaySelf S49 original native effect ACK → Paper World tick delivery markers

**Date:** 2026-10-26. **DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.

### Scope and exact tested source

Isolated branch `self/dev-s49-forward-motor-admission-20261026`.
Source HEAD for positive Paper-callback overlap `b9a3a696b88a9d8d556efba2d3929047359a6845`,
[real disposable Paper Minecraft run #40317670460 — SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40317670460).
Separate no-poll first verified HEAD `70262236d73f02373d9faf24cc61243270245faf`,
[real World run #40317185530 — SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40317185530).
The next HEAD `7dc8a0171e0c5c48097678f3cb4afd60649a1c39`
adds the marker-only negative control. No R/SCI run, no FULL CI, no
new native reader or Action issuer. main and Draft PR #545/#634 unchanged.

### What is measured

The existing original S49 S14/S15/S16 owner issues a single
`MOVE_FORWARD_SPRINT_DEV`; the **existing S15 native receive loop**
produces a typed `MineflayerEffectResult` for
`set_forward_sprint_dev` APPLIED and `clear_controls` APPLIED.
A DEV-only async hook sends one Paper server-console `relays49dashmark`
after receiving each typed ACK. Its console input is flushed once with
**no 100ms Paper log polling during physical control**.
Paper logs its **receipt/delivery tick** after checking same World UUID,
player UUID, Action ID, session and marker order; subsequent
`relays49dashoff` uses the same ordered server stdin.

Only after original native S16 OUTCOME and Paper owner release does a
separate Python DEV auditor check two marker rows against the original
S16 dispatch/cleanup native sequence numbers. Marker duplicates,
wrong or replayed IDs, foreign actor/session/world, noncontiguous
Paper ticks, reversed ACKs and missing Paper physical DASH output
**inside** the ACK marker time window are rejected before the
original S49-owned `B0EnergyLedger` settles the charge. Test-only
`tests/test_s49_native_ack_paper_edges_dev.py` covers these negative
cases and native original receive callback failure.

**Critical epistemic distinction:** a Paper delivery timestamp is
later than the native ACK receipt and cannot determine the exact
physical client effect's World tick. The marker arrival delay and
Node↔Paper time alignment are not independently measured.
No cross-host clock synchronization or input packet attestation.

### One real-World measured trace (run #40317670460)

| Source evidence | Actual measured value |
|---|---|
| Paper ARM | World tick 248 |
| Native original dispatch ACK | sequence 22 |
| Paper dispatch ACK marker delivery | World tick 250 |
| Native original clear-controls ACK | sequence 35 |
| Paper cleanup ACK marker delivery | World tick 262 |
| Paper owner RELEASE | World tick 262 |
| Continuous Paper motion callbacks | World ticks 249–261, 13 total |
| Positive DASH callbacks in ACK marker bracket | 11 |
| Original S49 native S16 | 2/2 OUTCOME |
| P1 single fatigue F initial/final | 0.600000 → 0.6177122410202606 |
| DASH motor power first/last | 0.802197252290235 → 0.7678689695742946 |
| Original first/second native distances | 4.0010239789274165 m / 3.0301572054686408 m |
| Native local B0 basal charges | 0.5 + 0.5 |
| Native local B0 MOVE charges | 0.25 + 0.25 |
| DASH extra M0 charge | 0.08633238849069515 |
| Original local B0 M0 balance | **12.0 → 10.413667611509306** |
| Owner M0 transaction ticks | 0→1→2 |

This is **one legacy M0 MOVE transition per completed native Action**.
The existing `metabolism_step("MOVE")` defines basal and movement
expenditure per **M0 step**, not per Paper World tick. The 13 Paper
callback ticks are used only to replay the P1/DASH extra candidate:
**no fabricated basal charge for 13 ticks or unknown WAIT interval**.
Paper itself has no M0 ledger writing rights.

### Observer effect and limits

An earlier proof-of-concept implementation blocked inside each native
ACK hook until a Paper log line appeared (100ms polling).
[Confounded real World run #40316764744 — SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40316764744)
had 17 Paper callbacks and first Action moved 5.1108m.
Removing these blocking waits retained both native ACK markers and
reduced the observed first-Action interval to approximately 13
Paper callbacks and 4.001m in the subsequent run above.
This **supports an observer-effect explanation**, but changes
between separate runs prevent a controlled A/B causal estimate.

Separate run #40317185530 produced an anomalously high *single sampled*
Paper speed peak (~14.89m/s); it is not evidence of sustainable DASH
speed or a qualified physical speed cap. No forward input packet
admission, lateral/back ceiling, actual native effect time,
World tick time synchronization, permanent P1 owner persistence, or
global production M0 calibration is claimed.

**Next DEV:** align independent Node/Paper cadence and native ACK
transport jitter with bounded clock evidence, and calibrate basal
M0 energy rates for World time before any per-Paper-tick debit.
Do not advance R/SCI or change original qualification evidence.
