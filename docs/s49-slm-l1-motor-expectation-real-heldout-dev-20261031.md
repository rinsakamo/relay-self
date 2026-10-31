# RelaySelf — self-supervised L1 motor expectation from actual S49 Minecraft movement

Date: 2026-10-31. **DEV_SELF_SUPERVISED_MOTOR_FORECAST_REAL_WORLD_PASS /
CHEAP_LAST_EQUIVALENT_ON_TWO_HELDOUT_ACTIONS /
GOAL_L8_TRAINING_ZERO / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.

This is a DEV non-authorizing motor-consequence forecast. The existing
strict S49/S16, B0, S42, L8 Goal learning and S10/Habit authority are
unchanged. It is **not** the external-Goal L8 learning sought by L Lane,
and **not** a demonstrated policy improvement.

## Physical source ownership and exact HEADs

- Original **prior real** Minecraft World:
  [GitHub Actions #41174086368](https://github.com/rinsakamo/relay-self/actions/runs/41174086368),
  [artifact #13031807923](https://github.com/rinsakamo/relay-self/actions/runs/41174086368/artifacts/13031807923),
  session `eb66128b-a3d2-4bc2-889f-429f0a7c93de`;
  W3 stdout SHA256
  `7f5d69f72a2cbfde7751960eaef4a06c9434b2ec94fa57e50b6ce63604bd5e8c`.
- Original **new heldout real** Minecraft World, physical tested exact HEAD:
  `5e31b6add1298d2d07d363005c043941f5de772b`.
  [Actions #41178788300 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/41178788300),
  [physical evidence artifact #13034076938](https://github.com/rinsakamo/relay-self/actions/runs/41178788300/artifacts/13034076938).
  New session `41a1637b-7bc6-4332-a4d7-da034374f549`;
  W3 stdout SHA256
  `39afa08ad7de927a6eec845759d8051441c49b507a9c5d5089294886e475aec1`.
- Corrected numerical comparison implementation and readback replay exact
  HEAD `f1514f02ce2fa098bc8dcae5b03c09a74a948748`.
  [Offline replay #41179072552 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/41179072552),
  [corrected verdict artifact #13033539378](https://github.com/rinsakamo/relay-self/actions/runs/41179072552/artifacts/13033539378).
  **No new World was started to correct the comparator.**
- GitHub-hosted Linux disposable Mojang Minecraft 1.21.8, Python3.12,
  Node22, Java21, Mineflayer4.39.0. User granted continued real DEV
  World tests for this integration lane. One new physical World trial,
  zero auto-retry. No change to user's local WSL2 World.

## Real observation → forecast → heldout physical outcome

New `slm_motor_expectation_dev.py` uses the original
`read_previous_s49_world` and `audit_w3_sealed_stdout` to re-validate
prior original W3 and S49 report, then runs the original native decoder
to re-extract before/after physical x/z positions and checks both reported
S49 movement distances to within 1e-8m. Source scope:
`S49_W3_NODE_STDOUT_OBSERVED_MOTOR_DEV_NOT_INDEPENDENT_TCP`.
It rejects any wrong SHA, action count, source session, Action type,
S16 terminal, missing native probe, dispatch/clear, out-of-range
displacement or inconsistent report. This is S49 self-observation,
**not independent TCP or an external Goal attestation**.

The prior real World yielded two executed MOVE_BACKWARD native
displacements:

| Physical sample | Observed movement |
|---|---:|
| Prior Action 1 | 0.8322911817508141 m |
| Prior Action 2 | 0.6269065734210613 m |

Before the new World started, the sole read-only L1 motor shadow fixed:

- **experience-model** = arithmetic mean of those two real displacements:
  **0.7295988775859377 m**.
- **same-data cheap baseline** = last observed movement:
  **0.6269065734210613 m**.

No current-World outcome was part of the training forecast. The original
L0 choice remained `WAIT → MOVE_AWAY → MOVE_AWAY`, and two original
S16 OUTCOME actions were executed:

| New heldout Action | Observed movement |
|---|---:|
| `s49-native-move-20` | 0.7342911432182317 m |
| `s49-native-move-48` | 0.6269065734210626 m |

Post-cleanup original S49 owner ran the motor evaluator **only after**
the real two Action outcomes. It changed no physical execution,
L0 choice, no Memory S10, no B0 owner state or actual Minecraft Energy.

## Actual predictive comparison: cheap-equivalent, NOT positive gain

Mean absolute error of the two fixed prior-model predictions:

- Model mean MAE: **0.053692284898584575 m**.
- Cheap last-value MAE: **0.05369228489858591 m**.

These differ by only about **1.3e-15 m** due to floating-point rounding.
The original exact physical run stored
`beats_cheap_control=true` because an unqualified strict `<`
comparison treated that roundoff as a win. **That original boolean is
not evidence of an improvement.** The original physical run/bytes/receipt
were **not edited or reclassified retroactively**.

The corrected comparator uses an explicit **0.0001 m (0.1 mm) minimum
margin** for a stronger model claim and returns:

`comparison_status=CHEAP_EQUIVALENT_WITHIN_MARGIN`,
`beats_cheap_control=false`.

The corrected independent offline readback re-decoded **both** actual
past/current W3 native originals and recomputed the same physical
displacements, source identities, earlier frozen forecast and corrected
comparisons; [CI #41179072552 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/41179072552).
Its corrected JSON is saved separately in artifact #13033539378.
The historical raw result remains preserved in #13034076938.

This produces a **real experience-conditioned, non-authorizing
prediction and a real heldout error measurement**, but demonstrates
**no statistically meaningful benefit over a cheap one-sample rule**.

## L8/S49/M and cleanup

- Original S49 L0 WAIT(event/probe 8?/actual report), then two original
  MOVE_AWAY choices. The actual report and W3 native original are
  authoritative for exact event/probe sequences; no independent
  chronological tick evidence is asserted.
- Physical real original Action2 / S16 OUTCOME2. S42/SelfBody/L8/M
  source-matched `RECORDED` 3/3, observer_errors 0.
- `one_l8_memory_owner=true`, L8 Goal retention enabled but qualified
  external Goal labels **0**, `no_admissible_l1_proposal` 3/3.
  Real S10 commits/L8 Goal learning/Habit grants/model calls/new
  Action issuers/extra native reads/M food credits all **0**.
- New W3 `COMPLETE_NODE_STDOUT` **35,590 bytes / 60 frames**
  seq0–59, EOF true, capture fault null, one shutdown ACK.
  Original Node/Java exit 0, existing five-stage cleanup complete.
  Original W3 is Node stdout, not authenticated Minecraft TCP.
- The physical workflow completed its Python focused regression,
  Ruff, repository contracts, original Mineflayer preflight and
  physical verification. The corrected offline replay then passed
  focused regression/Ruff/contracts plus both actual W3 re-reads.

## Next developmental objective

The cheap rule's tie means this two-sample mean needs no promotion.
Collect different real Minecraft motor contexts (gait, distance,
obstacle, material, fatigue and goal tolerance) in future isolated
DEV Worlds and evaluate source-shaped action-consequence predictions
against the strongest cheap control on heldout sessions, **without**
overriding the sole S49 Action owner. For actual goal-conditioned
L8 learned action selection, independent Goal receipts and L/S/V
admission still need to be provided. No science/qualification claim.

Main, pinned L8, M, S49/SelfBody and L22 original owner branches
are not modified. The only modified branch is
`integration/s49-slm-passive-dev-20261031`.
