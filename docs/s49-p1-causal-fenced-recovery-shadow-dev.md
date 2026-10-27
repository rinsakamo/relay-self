# S49 causal Paper stillness → P1 read-only WAIT counterfactual (DEV)

2026-10-27. **DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.

New branch `self/dev-p1-causal-wait-shadow-20261027` starts from parent
`459ad8cf993fb5b1ad40589c95b6e93fd5b0daf2`. The existing original
S49 Action owner, Paper plugin, single P1 fatigue model, and M0 ledger owners
are unchanged.

## Admission boundary

Only after the prior original S49/Node/Paper causal fence reviewer, the original
first-action P1 replay, original Paper action bracket, and M0 readback all
succeed, run the opt-in `--p1-fenced-recovery-shadow-dev` projection. It uses
`advance_gait_dev` on a *temporary FatigueState* once for each contiguous,
source-reviewed Paper low-motion tick. The profile is the same single-P1
model (`FatigueProfile(enabled=True, initial=0.6)`), not an additional
fatigue counter. No production or verified WAIT `SourceBoundTick` is created.

**Important uncertainty:** original P1 replay finishes on the first DASH
World tick, before the fenced static candidate begins. The intervening ticks
are not categorized as WAIT. The projection **assumes the last first-DASH
fatigue is held constant over that unclassified gap**. This is a
counterfactual, not actual fatigue measured at the beginning of stillness.
Low horizontal Paper motion + original S49 no-new-Action is not global
Body inactivity or exclusive World-issued Action attestation.

The report separately shows (a) the hypothetical recovered amount if *every*
candidate tick were WAIT, (b) zero admitted WAIT ticks and zero actual P1
recovery, and (c) the identical original M0 readback. On bad or forged fences,
source-bound authority flags, gaps, identity, nonfinite P1 or altered owner
state, the operation rejects rather than producing an applied recovery.

## Prior real-World input

The parent previously confirmed START 258 / END 442 and static 264–437,
174 contiguous Paper World ticks in run
https://github.com/rinsakamo/relay-self/actions/runs/40438046090.
This parent measurement is **not** a result of the new projection code.
The new isolated DEV test replays a newly executed disposable World, if the
workflow succeeds, and emits a separate report entry; tick IDs can differ.

At the canonical illustrative P1 end-of-first-DASH fatigue `0.6155207399`,
174 WAIT-assumed ticks imply 8.7 normalized World seconds and a calculated
fatigue reduction of approximately `0.3988305491`, leaving
`0.2166901908`. Neither is a measured actual WAIT effect. The profile's
`0.12/s` recovery rate is the already defined DEV gameplay model, not
human physiology or a proven 20-TPS wall-clock mapping.

## Scope

Python 3.12 focused tests and negative controls, Ruff, syntax, and a disposable
Paper World workflow on this new DEV branch. No FULL, main merge, PR #545/#634
update, R qualification, or SCI run is authorized by this shadow report.
