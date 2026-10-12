# RelaySelf S Lane S12 — physical behavioral discrimination preflight

Authority: Self product [#537](https://github.com/rinsakamo/relay-self/issues/537),
learning [#426](https://github.com/rinsakamo/relay-self/issues/426),
independent scientific evaluation [#544](https://github.com/rinsakamo/relay-self/issues/544).

Exact S parent: S11 [Draft #614](https://github.com/rinsakamo/relay-self/pull/614)
HEAD `69a150cc6f687e5b379713ba4c5e0ba2de60b38f` (CI 4/4 PASS).
Independent V [Draft #595](https://github.com/rinsakamo/relay-self/pull/595)
HEAD `53d50029da64a95c56bb56c6d48b5d14ce94e84a`.
Independent L5 [Draft #613](https://github.com/rinsakamo/relay-self/pull/613)
HEAD `17c5357fd5625274ee567ad979b780e77bf7b1e7`.

## Main result: physical discrimination is currently blocked before World start

Source read of frozen S49 `NormalSessionActionExecutor.require_authorizations`
shows that the only admitted physically issued candidate is
`MOVE_AWAY`, bound to `MOVE_BACKWARD`. `WAIT` is a valid
`WorldConditionedChoice` route but does **not** issue a normal-session
S49 Action. It therefore cannot be counted as a second externally
executed Action/OUTCOME or a separate controlled treatment. The
frozen S9 NoAI zombie intervention supplies a single controllable
physical Action; neither the historical S3 recall nor S11's source-shaped
L5 ShadowAdvice enters its authorization path.

Independent V [#544](https://github.com/rinsakamo/relay-self/issues/544#issuecomment-6123653506)
has also independently compared L5's 16 synthetic goal-labeled
episodes against the **same-information cheapest two-feature 4-cell rate
table**: the table exactly reproduces L5's candidate in all four
feature contexts. A positive shadow difference against weaker cheap
controls is therefore NOT an incremental behavioral or resource gain.

No independent original physical Goal receipt exists for S9, no
matched independently heldout RETAINED vs CHEAP original sessions,
and R6's completed 57-file S9 source-byte readback remains
**engineering REVIEW ONLY** (no R1/R2 typed native Action/OUTCOME
admission, and no science/Goal witness).

`adapters/mineflayer/self_s12_discrimination_preflight.py` consumes
S10's original frozen read-only Memory present/withheld A/B result,
S11's original nonauthorizing advice intake, and V's exact independent
source-shaped two-feature cheap-null result. It checks exact status,
SHA-pinned owner identity, invariant no-Action/no-Goal/no-learning flags,
and yields **NOT_READY** with explicit blockers for current S49.

**This gate cannot grant a physical permission, sign a source receipt,
create R1/R2 typed native originals, train a Habit, adjust L0, or
change any actual World action.** No caller-supplied new fictional
Action reference can make S49's frozen executor support an alternative.

## Existing preregistration tasks before any *future* physical discrimination

1. **S Product:** identify *two actually executable and independently
   source-admitted, safe, alternative Action policies* for the same
   task and initial World, or explicitly predeclare a sound contrast
   with `WAIT` as **nonissuance** and an independent stationary
   World/Goal measurement. Such a WAIT control is not an Action
   receipt and cannot be relabeled as one. This requires future
   separately reviewed S ownership; not part of S12.
2. **V Science:** predefine an externally measurable Goal success
   outcome separate from MOVE_AWAY execution and Memory recall,
   real task hazard/safety ceiling, paired randomization or
   matched-world equivalence, independent training/heldout sessions,
   cost/latency/energy accounting, and acceptance threshold.
3. **L Cognition:** compare any proposed experience-conditioned action
   with the strongest cheap same-information **two-feature table**,
   rather than only exact-cue/singleton/global majority. Establish
   actual original Goal/cost lift, or report CHEAP_EQUAL.
4. **R Evidence:** continue using frozen RSEE and genuine original
   raw-source evidence; do not reconstruct historical S9 R1/R2 typed
   Action/Goal provenance from derived logs or SHA alone.
5. **User authorization:** issue a new exact-head, bounded, explicit,
   one-shot permission only **after** the above are independently
   qualified; historical S8/S9 grants remain consumed. No implicit
   run rights from an offline PR.

## Regression

Source tests check exact S49 executor preconditions, S10/S11 no-authority
lineage, V source-shape/report controls and falsified positive original
Goal/cheap superiority. Dedicated exact S11-parent GitHub CI runs
Ruff/contracts, full Python regressions, Mineflayer protocol and
an independent **actual pinned V + L5** oracle producer consumed by
S12. This does not execute Minecraft, Java/Node bot, GGUF, GPU or an
LLM POST; V/L sibling branches are read-only.

Current ceiling:
`S12_CURRENT_S49_BEHAVIORAL_DISCRIMINATION_PREWORLD_NO_GO /
V_L5_STRONG_CHEAP_TWO_FEATURE_PARITY /
R6_ORIGINAL_BYTES_ENGINEERING_REVIEW_ONLY /
NO_NEW_WORLD_PERMISSION / G3_SCIENCE_NO_GO / NO_PRODUCTION_GO`.
