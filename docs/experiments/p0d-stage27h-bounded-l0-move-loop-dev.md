# Stage27h — original one-Skill bounded CPU L0 MOVE loop (DEV)

Parent Issue #951; stacks on Stage27g Draft PR #975 (real-world evidence).
The Stage27g real test observed a single A MOVE 0.2m, target residual 0.8m,
and a separate real Gemma CONTINUE_INTENT. Stage27h changes **the skill
execution granularity**, not the initial L1 chooser.

## Original owner architecture

Stage27h opts into one newly bound, operator-authorized **DEV** initial
MOVE Preset `SkillBudget(4, 15000, 2.0, 256)`; the original Stage26/27d-g
`SkillBudget(1, 1500, 2.0, 4)` default remains identical.

**Observation-limit correction after the 2026-11-18 pre-World HOLD:**
The original Stage27h `max_observations=16` counted only pre-MOVE and
terminal TargetAssessment probes while the issuer's 50ms STOP/settling
loop could request many additional native observations. This is now an
explicit whole-Invocation cap **256**, not an per-Action allowance. The
CPU L0 parent pessimistically reserves **60 requested STOP probes**
BEFORE each physical MOVE (up to four total Actions), and the issuer's
`_settled(max_probe_requests=60)` refuses a 61st native request.
A canonical terminal Action/settled receipt with complete distinct
`all_stop_probes` is required to refund unused reserved observations.
The original native stdout is read back independently for *every*
settling request ID and sequence, not only first/stable/final samples.
Each distinct pre-MOVE probe also counts as one. A terminal settled
probe counts **once** even though it is used for TargetAssessment.

If the physical STOP is applied but its observation quota expires
without confirming 8+8 tick settlement, the original issuer leaves
the WAL unresolved and the run HOLDs: never extend the Invocation
budget, fake STOP settled, or reissue that Action. Reserving is
pessimistic until terminal verification. At most four Actions reserve
`4 * 60` STOP slots and up to four distinct preflight probes, so
`max_observations=256` can encompass the full finite loop with 12
unused probe slots available. Real settling often uses fewer than 60;
the unused slots are returned **only** after final WAL verification.
The 60-probe finite cap may cause a legitimate slow/blocked world to
HOLD, rather than overshoot the cognitive observation contract.

Only one initial original A/B bounded L1 model selection is made. If A chooses
1/READY, the original A Intent/Skill is started ONCE. A finite CPU L0 parent
(`Stage27hBoundedMoveLoop`) iterates the following sequence:

1. Fresh same-session native WorldBody probe; validate life, oxygen,
   immutable target, owner, Session/World epoch, total budget and canonical
   multi-row WAL. Evaluate original frozen PLACE TargetContract.
2. If `OUTSIDE`, and action/time/distance/observation budgets remain:
   compile an original Stage27c **single-Action child interpreter** from the
   SAME Invocation and Preset. It is a child of this bounded L0 parent, NOT
   a new L1 Skill or a retuned parameter. No L1 calls in the loop.
3. Source-qualified PLACE motion is resolved from current body position.
   The **original PhysicalIssueAdmission** reserves a unique Action ID
   and WAL PREPARED. Before *any* native LOOK/ON, a distinct fsynced
   immutable PREPARED snapshot of the whole current WAL is captured.
4. Issue LOOK, short bounded forward ON, STOP, 8+8 tick settlement using
   the preexisting issuer. Require one canonical terminal WAL row per
   Action. Independently reread owned native stdout and Paper A before/
   after position windows; Paper position is CORRELATIONAL only.
5. The L0 parent authenticates original Action/Skill/Target/WAL linkage,
   checks cumulative displacement and deadline, evaluates the terminal
   native body position. If still `OUTSIDE`, the next loop iteration
   obtains a NEW native probe and repeats, without another GPU request.

Loop end statuses:
- `L0_TARGET_REACHED_YIELD_EVALUATION`: the Target *condition* was
  observed. This is NOT automatic Skill or Goal success.
- `L0_BUDGET_EXHAUSTED_YIELD_EVALUATION`: no extra budget or time grant;
  no repeated motion.
- `L0_NO_PROGRESS_YIELD_EVALUATION`: a settled but obstructed/ineffective
  motion ends the attempt; do not repeat zero-progress forever.
- `L0_CUMULATIVE_OVERSHOOT_YIELD_EVALUATION` / `L0_OVERSHOOT_...`:
  observed excess distance, not a safe success.
- `L0_WORLD_CONDITION_YIELD_EVALUATION`: UNKNOWN, blocked, vertical
  mismatch, etc. stop the loop and return to higher cognition.

Current finite parent is **process-local** and is not a restart permission
or durable Skill lifecycle. A new L0 child Interpreter is compiled *per
original Action* because existing Stage27c child IR is finite
`CHECK_TARGET -> ACTION -> YIELD_EVALUATION`; a single invocation and
Skill execution are preserved and independently fenced by the parent.
Every WAL row must belong to the SAME Self/Intent/Skill/Invocation/Preset/
TargetContract; the parent enforces cumulative real displacement plus
Action, time and observation limits.

## Real host isolated one-shot entry point

Runner `experiments/p0d_stage27_real_place_move_dev.py` adds a strictly
opt-in `--stage27h-l0-move-loop` flag, in addition to existing required
Paper/plugin jar SHA256, freshly verified model/PID/weights/GPU one-slot
and signed-off `--eula-accepted --real-world-dev-grant` args.
**Do not combine it with Stage27e/f/g execution flags**. Only this flag
selects the Stage27h multi-pulse original hook and immutable expanded
DEV Preset. Existing older runner modes remain unchanged.

One newly isolated World DEV attempt only; no retries after an uncertain
PREPARED, STOP, WAl, owner session, or external source. Do not force
the real Gemma A choice. Capture native/raw HTTP, original PREPARED for
each pulse, per-pulse Paper position and native stdout/ACKs, cumulative
L0 feedback, original WAL final rows, native/World scope, B isolation,
2-Self checkpoint and independently computed SHA256SUMS and manifest hash.
Existing captured checkpoint is before physical MOVE: **do not classify
it as post-Action atomic World+2 Self restoration**.

Offline tests use a synthetic HTTP provider and scripted native movement.
Actual Paper/Gemma execution of Stage27h is **not claimed** until a real
host run reports original raw evidence. QUAl/SCIENCE not authorized.

Remaining: original-owner terminal Goal/Skill transition (not automatic
L0), multi-row WAL recovery from a world-aligned checkpoint, persistent
learned Skill versioning, independent Paper Action-ID causality,
complete native stdin wire transcript and cross-process clocks.
