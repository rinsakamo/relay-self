# RelaySelf DEV: P1-conditioned motor duration on sixth original S49 epoch

Date: 2026-10-25. Branch `self/dev-p1-original-motor-sixth-20261025`.
**DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.**

## Implementation and protected boundaries

- The historical original `adapters/mineflayer/normal_action.py` blob
  `0ded8fa296c92076a643de08cd6fc360061e1d08` and
  `experiments/fatigue_p1.py` blob
  `bd4f35a4079da0770ef11cdec921dbba31de9b81` are unchanged.
- On isolated DEV source, `qualify()` accepts a sixth original-host epoch
  only with `dev_sixth_epoch="MOVE_AWAY"`, prior fourth native MOVE,
  fifth native WAIT and `S49_SIXTH_EPOCH_DEV_ONLY=1`. Defaults remain
  three original decisions and two original Actions.
- The exact same original `NormalWorldL0`, `NormalSessionActionExecutor`,
  `ActionSupervisor`, original S14 admission, PROPOSE/ISSUE
  `NormalActionAuthorization` and S16 OUTCOME remain in charge.
  A scoped DEV-only transport hook affects **only the already-issued
  sixth native MOVE_BACKWARD command**. It rejects changed Action IDs,
  unrelated sessions/probes, missing P1 model, a second command, and
  non-reduced timings. No second Action issuer/recipient/receiver is created.
- The new near-zombie stimulus is disposable external DEV World staging.
  All previous zombie targets are natively cleared by the same single
  original receiver before the next target is spawned.
- The fifth SelfBody/SelfWorld carries an **explicit hypothesis** of P1
  fatigue based on the observed third MOVE displacement and preceding
  eight Paper WAIT callback ticks. The model's fatigue is held across
  subsequent unobserved World ticks **without invented WAIT recovery**.
  It is not a physical fatigue measurement, nor a source-qualified R tick.

## Exact reproducible outcome

The first live attempt
[World #40179867606](https://github.com/rinsakamo/relay-self/actions/runs/40179867606)
produced a real successful **original S49 six-decision/four-Action**
session, but its outer review returned `BLOCKED_OR_FAILED` because the
retrospective fourth/fifth source reviews expected only three final
Action requests. The immutable failed run/artifact remains classified
as failed. The DEV-only review was corrected for a 6-epoch four-Action
terminal; no original protected executor change or reinterpretation
of earlier evidence.

New fresh disposable Paper 1.21.8 / Java 21 / Node 22 World:
[run #40180134123](https://github.com/rinsakamo/relay-self/actions/runs/40180134123)
at code HEAD `010804b78cd60dd381fa63dfa32886ef9f124f54`,
[artifact #12594047360](https://github.com/rinsakamo/relay-self/actions/runs/40180134123/artifacts/12594047360).
Both inner original S49 and outer DEV report **PASS**, Java/Node exit0.

Original decisions:
`WAIT → MOVE_AWAY → MOVE_AWAY → MOVE_AWAY → WAIT → MOVE_AWAY`.
Event seq `10,23,53,75,95,102`; correlated probe seq
`11,24,54,76,96,103`. Original Action OUTCOME count **4**;
the sixth issued Action `s49-native-move-102` completed its S16
clear and measured horizontal displacement `0.6269065734210614`
blocks. Original earlier three MOVE OUTCOMEs were also measured.

Third original MOVE `s49-native-move-75` moved
`0.6269065734210613` blocks; unchanged P1 model
`advance(MOVE)` formed model fatigue
`0.025076262936842453` (body sensor hypothesis 3%, model
capacity about 98.2446616%). Same original native fifth probe seq96:
**model-free nominal input** `0.2000000000000000 s` versus
**P1 model-conditioned duration** `0.19648932318884205 s`,
a reduction of `0.0035106768111579645 s`. This candidate on the
fifth WAIT was not itself executed; it was carried with exact source
identity into the sixth original Action issued for native event102 /
probe103. The single S49 executor's DEV-scoped transport accepted the
shortened duration, completed the native command, and sealed the S16
OUTCOME. The Action identity and duration are matched in both original
and outer saved reports.

Python3.12 focused, syntax/Ruff, fail-closed explicit opt-ins:
[run #40180115274](https://github.com/rinsakamo/relay-self/actions/runs/40180115274)
**SUCCESS**. Fresh live workflow's focused stage passed as well.

## Interpretation / NO_GO gates

**Demonstrated**: A fallible P1 model created after original third
MOVE can affect the **actual timing of the sixth, independently
authorized, native command** without minting an issuer, changing S42
`MOVE_AWAY` selection or modifying original executor source.

**Not demonstrated**: Different physical displacement caused by
fatigue. The sixth displacement was essentially the same ~0.627 blocks
as the earlier original MOVEs. The 3.5 ms timing delta is much smaller
than a 50 ms World tick and must not be re-labelled as a verified
physical movement effect. No randomized matched-world comparison, no
calibrated fatigue sensor, no continuous P1 World-tick ledger, and no
evidence that the modeled state persisted physically across the gap.

`SourceBoundTick(WAIT)` remains absent. R-admitted WAIT=0;
R-qualified P1 recovery=0; S10 updates=0; no V science. Original
`s49_normal_session_real_ci.py` has an isolated protected-source DEV
candidate change and still requires explicit owner/source adoption
review before #545/#634/main; original archives and other Draft PRs
were not merged or modified.

**Next**: Quantize/actuate a meaningful fatigue-conditioned difference
only after a documented operator-approved DEV scenario that respects
the original single S49 authorization and Paper World observability,
then compare original native measured displacement in matched World
pairs. Avoid claiming R-qualified fatigue or physical causal effects
from the present timing-only experiment.
