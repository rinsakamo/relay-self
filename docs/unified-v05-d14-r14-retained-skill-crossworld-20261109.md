# D14 R14 — retained Skill candidate vs independent later real-World original S49

**State:** DEV implementation, **NOT_RUN** real R14 / Gemma / new World,
no Skill-driven Action, no Memory/Habit owner writer, no L1/L0 promotion.
Child of R13 Draft #820 → R12 #817 → R11 #816. Do not merge other work
or claim R11 is already qualified.

## Reason for this incremental step

R13 gave L2 a typed Action Catalog and a conditional Skill program, but
R12 retained a shadow candidate only in `shadow_candidate.json` AFTER the
original real World finished. There is no way for that candidate to have
caused an Action in its originating World.

R14 now supports **a different real World and native session** to ask a
more limited question: *does the saved, source-qualified candidate's
sequence occur in later independent ORIGINAL S49 behavior, and what did
the physical owner actually observe?*

This is **not yet Skill execution**. It measures compatibility and the
possibility of retained cross-World reuse without pretending that original
S49 decisions came from L2. No new issuer is created.

## Required existing originals

Prior World A must have five original R11 files, and an R12/R13 one-shot
Gemma raw folder with three retained files:

- `report.json`
- `paper_original.log`
- `d14_natural_events.jsonl`
- `original_s49_nonmotion_fence.json`
- `original_s49_motion_fence.json`
- in the **separate** L2 folder: `request.raw.json`,
  `response.raw.json`, `shadow_candidate.json`

Later World B must have **its own five R11 original files**.
Its Minecraft world UUID and native session ID must both differ from A.
A prior failure/partial source stays a failure; R14 never manufactures
a 24,000-tick World PASS or backfills missing original Action outcomes.

The R14 reader always re-runs R11's independent Paper/native/S49 fence
audits for both A and B through R12 `project_r11`, and replays the prior
L2 raw Gemma request and answer via R12 `replay_retained_shadow`. It checks
source hashes and current R13 catalog ABI; the raw model response must
agree with the retained candidate and inert compilation.

## One read-only cross-World test

```bash
export PYTHONPATH="src:tests:."
PRIOR=/absolute/path/to/qualified-r11-world-A
L2RAW=/absolute/path/to/separate-r12-l2-raw
LATER=/absolute/path/to/qualified-r11-world-B
OUT=/absolute/path/to/separate-r14-readouts

python -m tools.bug0_d14_r14_retained_skill_trial \
  --prior-world-evidence "$PRIOR" \
  --prior-l2-raw "$L2RAW" \
  --later-world-evidence "$LATER" \
  --out "$OUT/r14-retained-shadow.json"
```

R14 creates only an exclusive JSON readout, never modifies original files,
launches a World/Gemma, or creates a new Action grant. An output rooted
inside any original evidence directory is rejected.

### What the readout means

R14 matches **in order** at most the last 48 already native-audited R12
later-World experiences. A physical step can match only a real original
S49 S16 `outcome` with the same Action kind. REST/WAIT match only a
nonphysical owner decision. The matcher never equates a missing event
with a failed guard, silently skips a step on assumed risk, or reissues
an unknown Action. `repeat` here means a bounded observation count, not
an actual retry request.

EAT may report source-observed S51 food+inventory change, and ATTACK may
report a native target-hurt event. Those are not a proof of physical kill,
Paper damage caused by a particular strike, nutrition beyond measured
food delta, or causal superiority of a generated Skill. MOVE_AWAY's
effective physical STOP remains unqualified.

The output explicitly records:
- reference to the prior Skill program SHA, catalog SHA, both source
  World UUIDs, native session IDs and physical original digests;
- each matched event's original R12 Experience ID and, for physical
  Actions, the *actual original S49 Action ID*;
- the original outcome class and epistemic limitation;
- whether any part of the declared sequence matched;
- **skill_causal_action_selection_proven=false**, `l1_reuse_verified=false`,
  `skill_installs=0`, and zero new S49/LLM/Memory/Learning/Habit activity.

## Verification and next proper physical trial

1. Run exact-HEAD GitHub offline CI for R14/R13/R12/R11 focused pytest,
   repository contracts and Ruff. It does **not** create World or call LLM.
2. Get an R11 natural World A that passes independent original audits,
   run an explicit authorized R12/R13 Gemma proposal (abstention is allowed).
3. Later, run **another** independently authorized R11 natural World B,
   without importing A's candidate into its original S49 decisions.
4. Apply R14 and record both successful matches and nonmatches. A zero
   match is valid data, not a reason to fabricate training or retries.
5. **New R15 required for the first Skill-driven Action:** make a source-
   qualified, opted-in skill proposal feed S49's existing Action admission
   within the same live World, with the original physical PREPARE/S16,
   fresh native target/food/STOP checks, bounded resource accounting and
   independent readback. Never reinterpret an R14 observational match as
   this accomplishment.
6. Only after true Skill-controlled live trials: retain episodes into
   the existing Memory/Habit owner, test later epoch reuse, then consider
   an L1 policy. Do not automatically install an L0 reflex.

**Classification:** DEV_ONLY / SOURCE_GATED_CROSSWORLD_SHADOW_MATCH /
NO_SKILL_DRIVEN_ACTION / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
