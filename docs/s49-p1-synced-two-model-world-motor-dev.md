# P1 hypothetical F → native DASH motor response with Mineflayer speed mapping ON

Scope **DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.

## Motivating evidence

The [earlier two-model F experiment](https://github.com/rinsakamo/relay-self/actions/runs/40479045528) saw Paper-side model motor outputs 0.766861… and 1.0 but **identical first-action native displacement** because the client speed attribute projection was OFF.

The [attribute propagation control experiment](https://github.com/rinsakamo/relay-self/actions/runs/40487527583) held *the exact same* P1 model F (0.617712…) and compared projection OFF/ON. The existing bounded Mineflayer 1.21.8 projector made the real `minecraft:movement_speed` bonus visible to physics in 9 ACTIVE ticks and changed actual native displacement by +0.825008 m; Paper peak speed increased +2.076 m/s. This motivates holding client projection ON in both model-F scenarios.

## New paired design

Start **two independent fresh genuine disposable Paper 1.21.8 Worlds**. The original S49 Action owner runs the same 3 L0 decisions, 2 native S16 OUTCOMEs and original DEV M0 accounting in each. The only intentionally changed motor condition is an opt-in, **synthetically preloaded single-gauge P1 model fatigue**. All other motor/speed projection flags are identical:

| Arm | Model F preloaded | Paper speed→client physics |
| --- | ---: | --- |
| CARRY | 0.6177122410202606 | ON |
| WAIT_ASSUMED | 0.21616083122103735 | ON |

Both values and their source SHA `f126d16f42caa27230a02e4c818d7b7ae3c1d2e39e8ad75c55cd2ce9ddc16bd4` are earlier DEV hypothetical SelfBody model estimates, **not physical native fatigue readings**. In each World the Paper plugin adds its original P1-dependent temporary forward DASH modifier for the original S49 first Action only; second original Action is unboosted. The existing speed mapper excludes duplicate sprint.

Original S49 S15/S16 native action evidence, Paper's complete P1 gait tick replay, original session/World ids, first L0 threat/motor conditions, and per-World first Action `S49_SPEED_ATTR_NATIVE_BOUNDARY_DEV_V1` Node packet→attribute→physicsTick samples are independently checked. A separate DEV reviewer composes those checks, records absolute and between-World native displacement and server sampled speed, and rejects foreign sessions, spoofed source identities, unsynced attribute projection, missing packet or physics samples, extra issuers/readers, fake physical P1/recovery and false L0 admission.

**Physical motor separation is a measured outcome, not a requirement for a successful source-valid test.** If power differs but native displacement/speed do not, the negative result remains evidence. Native→Paper World clock synchronization is not asserted.

### Epistemic/authority limits

This experiment can establish how the real Minecraft motor responds to an *explicitly preloaded* P1 model fatigue value with the client speed attribute pathway working. It **cannot** establish longitudinal recovery of the *same Self* during physical WAIT, which is still only a conservative Paper static-candidate / hypothetical P1 replay. The reported model F is not a P1 native sensor measurement, and no physical L0 DASH power is admitted. Original S49 sole issuer, Mineflayer reader, S16 receipts and M0 postings are retained. No source-bound R WAIT, S10 learning, production P1 update, PR/main update, QUAL or SCI.

## Implementation/verification

- Existing `adapters/mineflayer/s49_paper_forward_dash_dev.py`: admit the Node attribute boundary capture with either of the two hardcoded DEV P1 preload arms, with the existing `S49_SPEED_ATTR_BOUNDARY_DEV_ONLY=1` and `S49_SPEED_ATTR_SYNC_DEV_ONLY=1` gates.
- New pure reviewer: `adapters/mineflayer/s49_p1_synced_motor_pair_dev.py`, reusing source reviewers for both original S49 physical S16 proof + Paper P1 replay and for both bounded Node native client attribute physics traces.
- New synthetic negative controls: `tests/test_s49_p1_synced_motor_pair_dev.py`. Focused Python 3.12/Ruff, Node 22 syntax and speed mapping tests, Java 21 plugin build **before** World.
- New independent opt-in paired-World workflow: `.github/workflows/self-p1-synced-motor-pair-dev.yml`; source evidence uploaded on success or failure, with run-id-scoped independent directories.

The exact tested commit and positive or negative measured physical results will be appended after inspecting the actual run. Previous evidence or failed runs will not be retroactively changed.
