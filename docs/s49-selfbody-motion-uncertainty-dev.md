# RelaySelf — SelfBody Motion Feedback: uncertainty-aware next motor proposal (DEV)

**Date:** 2026-10-25  
**Result:** `DEV_SELFBODY_MOTION_UNCERTAINTY_REAL_WORLD_PASS`  
**Authority:** `DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`  
**Isolation:** `self/dev-selfbody-motion-uncertainty-20261025`

## Objective

When past MOVE outcomes appear consistent, SelfBody must **not** assume
it knows the exact relationship between host requested duration,
Mineflayer client physicsTick, and Minecraft Paper world-tick movement.
For the *next already issued and authorized* S49 Action, reduce the
size of the duration correction when historical closed S16 prediction
errors or unresolved discretization make the movement prediction
uncertain.

The new code is DEV-only, opt-in, session-local and deliberately simple.
It does not estimate calibrated confidence or server-effective input
ticks, does not command new Actions and does not alter the protected
original S49 executor or the production P1 fatigue algorithm.

## Scope / implementation

- `adapters/mineflayer/s49_selfbody_motion_uncertainty_dev.py`:
  `guard_next_motion_correction_dev(state, proposal)` only consumes
  original S16-closed, source/sequence-matched SelfBody Motion samples
  that *precede* the next issued Action. Historical online prediction
  errors produce an observed RMS. `max(0.10m, observed_RMS)`
  is the DEV uncertainty heuristic. The **0.10m floor is arbitrary,
  not experimentally calibrated** and does not certify any particular
  number of world ticks.
- Nonprobabilistic damping: `gain = clamp(1 -
  uncertainty/explicit_DEV_goal, 0, 1)`, then
  `guarded = original_model_duration + gain *
  (ungarded_proposed_duration - original_model_duration)`.
  Thus the proposal stays **inside the original S49/P1 baseline and
  the existing at-most-25% correction**; in the high-uncertainty limit,
  it simply declines to change the issued control duration.
- The existing `SelfBodyMotionState.observe_closed`,
  `propose_motion_correction`, original S14/S15/S16 Action authority,
  and `apply_to_next_issued()` are not changed. The DEV-only external
  runner opts in with `--motion-uncertainty-dev` and records the
  historical errors, floor, gain, guarded duration and the subsequent
  closed native S16 prediction error separately.
- `tests/test_s49_selfbody_motion_uncertainty_dev.py`:
  exact original S16-shaped sample input; identical-three-moves
  produces *nonzero* floor; higher authentic historical residual
  shrinks the one-Action command correction more; sixth future outcome
  is not fed back into its own past proposal; foreign session/action,
  invalid sequence, missing/nonfinite error, unbounded duration,
  insufficient sample history and false goal are rejected.
- Dedicated `self-selfbody-motion-uncertainty-world-dev.yml`:
  Python 3.12 focused tests and Ruff, Java21 Paper observer, Node22
  Mineflayer, pinned Paper1.21.8 build60 SHA verification, one
  disposable World. No FULL/qualification/science job.

## Exact-head actual World trial

[GitHub Actions #40191658486](https://github.com/rinsakamo/relay-self/actions/runs/40191658486)
— **completed/SUCCESS** at exact test commit
`d4b4d9fd0b4e38de523fdbbd9305ce51361e59c4`.

[Original source artifact #12597703765](https://github.com/rinsakamo/relay-self/actions/runs/40191658486/artifacts/12597703765)
was independently downloaded and read: original S49 JSON, DEV report
JSON, original Paper console + observer wait logs, single-process
Node motion clock JSONL. Five files, all saved. Original Java and
Node exited **0/0**; original S49's six actual L0 decisions
`WAIT/MOVE/MOVE/MOVE/WAIT/MOVE`, **four S16 terminal actual
MOVE OUTCOMEs**, single original session
`467fd38f-982f-4a03-b258-63ebef8ee287`.
Python3.12 focused tests, Ruff, Java21 compile and World readback all PASS.

**SelfBody pre-fourth original MOVE history:** each of three real
original S16 distances ~`0.6269065734` blocks for a requested
`0.2s`; online pre-action prediction error RMS
`1.7554167343e-16 m` (machine-level numerical zero).
This is *not* evidence of zero future uncertainty; DEV minimum
`0.1m` is applied, yielding nonprobabilistic stability gain
`0.77777778`.

| Original S49 fourth actual MOVE property | Without DEV uncertainty guard | With DEV uncertainty guard |
|---|---:|---:|
| P1 base duration | 0.1964893232 s | 0.1964893232 s |
| SelfBody desired, before damping | 0.1473669924 s | 0.1473669924 s |
| Actual original command duration | 0.1473669924 s (separate prior trial) | **0.1582830659 s** |
| Predicted movement | 0.4619266812 blocks | **0.4961434724 blocks** |
| Observed actual original S16 movement | 0.4302315372 blocks | **0.4302315372 blocks** |
| Native SelfBody predicted minus observed | 0.0316951440 blocks | **0.0659119352 blocks** |

The *without guard* comparator was an **independent earlier
disposable World**, not a counterfactual in the same world:
[run #40185745453](https://github.com/rinsakamo/relay-self/actions/runs/40185745453),
[artifact #12595403705](https://github.com/rinsakamo/relay-self/actions/runs/40185745453/artifacts/12595403705).
Thus one must **not** infer that duration damping improved
accuracy. In these two examples it **did not**: physical displacement
happened to remain the same and modeled prediction error grew.
That is consistent with, but does not independently prove,
tick/discrete-step control nonlinearities. A larger sample or
two-condition trial with separate clock-phase histories is needed
to determine predictive benefit.

**Read-only clocks in this successful guarded run:**

- Original second S49 Action `s49-native-move-46`: Node local
  BACK state ON→OFF `201.579898 ms`, four Mineflayer physicsTick
  callbacks, S16 displacement `0.6269065734` blocks.
- Paper client MOVE position-change samples from world tick 441–445
  (five distinct Paper position-change ticks), same original
  claimed Action ID. Paper event net displacement
  `0.7665246863` blocks within a *different* sampling boundary;
  it is not an estimate of Node→server latency.
- The Paper PlayerInputEvent BACK ON/OFF remains unobserved.
  No server-effective BACK command tick count or synchronized clock
  alignment can be claimed.

### Confidence / limits

`stability_gain` is **not a probability or validated confidence score**.
The `0.1m` uncertainty floor is provisional. Motion outcomes
are World-observed proxies, not physical-proprioception sensors.
This existence test demonstrates the uncertainty reduction policy
can modify the next original authorized motor command and close S16;
it does **not** demonstrate improved accuracy, optimal control, R
qualification, science results, real physiological fatigue or S10
policy updates.

The earlier workflow runs
[#40191172816](https://github.com/rinsakamo/relay-self/actions/runs/40191172816),
[#40191414739](https://github.com/rinsakamo/relay-self/actions/runs/40191414739)
and [#40191546672](https://github.com/rinsakamo/relay-self/actions/runs/40191546672)
were **PREWORLD Ruff I001** format checks. No World was run for
those failures; all historical workflow records remain unmodified.
The exact-head successful run is a separate new trial.

Protected original source blobs remained identical:
`bridge.mjs` `42b5a8f1ff49a1728727844fbb4533a95bb34bcf`;
`normal_action.py` `0ded8fa296c92076a643de08cd6fc360061e1d08`;
`fatigue_p1.py` `bd4f35a4079da0770ef11cdec921dbba31de9b81`.

**main and Draft PR #545/#634 are unchanged.** This branch is
DEV isolation, not an adoption or official R/S qualification.

## Small next DEV milestone

Use a small, fixed set of independent S49 Worlds with at least
two distinct host-control durations or a minor experimental
clock-phase variation, compare **prediction errors and actual
S16 source measurements** instead of increasing SourceBoundTick
proof requirements. Keep the original single-reader, Action closure
and epistemic boundaries unchanged.
