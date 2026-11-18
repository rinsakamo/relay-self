# Stage27g — original post-Action real bounded L1 evaluation DEV

Parent Issue #951; stacked on Stage27f Draft PR #971 and Stage27e real
Paper/native DEV #964. The source code deliberately reuses the existing
two-original-Self resident process, original `PhysicalIssueAdmission` and
one-slot `ResidentLlamaInferenceLane`. No independent inference or motion
issuer is introduced.

## Original physical Outcome to L1 evaluation

1. The original A real Gemma L1 selects MOVE from the immutable Stage26
   Preset/PLACE Invocation, only if it returns `1 / READY`. B does not issue
   an Action.
2. A's original L0 physical MOVE/STOP settles and its WAL is terminal;
   the Stage27e original PREPARED and Paper before/after independent positions
   remain captured exactly as before.
3. Stage27f's CPU `TargetAssessment` consumes original settled native probe.
   The read-only evaluation frame contains original Action/Intent/Skill,
   Invocation/Preset/TargetContract references and terminal original WAL digest.
   It is not Goal/Skill success.
4. **New Stage27g:** `submit_stage27g_original_evaluation` rechecks live
   original Self ownership, native epoch, terminal WAL, L0 Action Outcome,
   original Skill STARTED and Intent still current; submits that exact
   `BoundedChoiceRequest` through the same original one-slot resident
   `lane.submit`, without JEV and without another physical permit.
5. `finish_stage27g_original_evaluation` awaits actual terminal provider
   decision, verifies backend /slots idle, `finish_reason=stop`, usage tokens,
   and independently rehashes the persisted exact original model HTTP request
   and response bytes.
6. **Only after model response and idle**: request a distinct fresh native
   probe, revalidate same Self/native/World/Action/WAL/Intent/Skill and current
   TargetContract. If Gemma chose `REVIEW_COMPLETION` but the new native body
   position is no longer inside the envelope, demote it to
   `RECONSIDER_FRESH_WORLD_CHANGED`; never commit success.
7. Reread the original A native stdout JSONL on disk after the post-model
   probe; require exactly one same-session tuple (probe seq, request ID),
   reject foreign/duplicated/corrupted source, and retain stdout SHA256.
   In-process ordering is not independent cross-process timestamp proof.
8. Record the model number and recommendation, source HTTP digest, original
   and fresh assessment, native probe ID/seq, and B isolation. The original
   A Intent remains current and original Skill remains STARTED regardless
   of the model number. No further motor Action, same-World retry, skill
   replacement, or autonomous goal completion is authorized.

## Exact one-shot run mode

Existing `experiments/p0d_stage27_real_place_move_dev.py` accepts an
explicit `--stage27g-real-l1-evaluation` switch. It enables all Stage27e
and Stage27f original evidence, and adds exactly one post-Action bounded
Gemma L1 call **only if the initial A selected a physical MOVE and the
original Action completed without WAL/STOP uncertainty**.

Use the existing Stage27d runbook's EULA/grant/Paper jar/plugin SHA,
local one-slot real Gemma and isolated real-World arguments, adding the new
flag (instead of lower Stage27e/f flags). User's standing EULA and real-World
DEV consent applies. The real host must verify actual model weights/GPU
identity, model request count, native stdout, independent Paper sample,
PREPARED before LOOK, terminated WAL, exit audit, manifest SHA and single
attempt. Never force either model answer or repeat an uncertain physical
Action. Existing Stage27d/e/f CLI defaults remain unchanged.

## Unproven / next stage

A real model evaluation choice and observation still **cannot** complete or
fail the original Skill/Intent by itself. Separate original-owner lifecycle
transition, independent Action-ID ↔ Paper causal witness, complete native
stdin wire proof, atomic World+2 Self checkpoint, QUAL and SCIENCE remain
unproven. No real World trial was run by this GitHub code-only change.

Offline contract tests use a synthetic HTTP responder and scripted native
physical outcomes; successful source-simulated HTTP does NOT attest Gemma.
