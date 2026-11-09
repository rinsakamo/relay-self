# D14 R12 — natural R11 experience → optional L2 shadow Skill

**Status:** DEV implementation / exact-HEAD CI pending / NO real R12 World or Gemma
run / no owner Memory or Habit write / no Skill install. This is a child of
R11 Draft #816, not a merge of K3-H #802. It leaves existing R11 and original
S49, S51, D7, Paper rules and 24,000-tick horizon untouched.

## Actual boundary

R11 is a **post-World evidence source**, not a live cognitive stream. R12
re-runs R11's independent Paper / original-S49 journal + durable-fence audit
and R11's daylight/item readout **from physical source files** before it may
construct an L2 input. It does not trust pre-existing JSON PASS readouts,
model claims, or the operator's description of World history.

L2 sees only native Self-view decisions and S49 S16 outcomes (bounded newest
48 events), a sourced terminal reason, present uncertainty and the source
session. Paper-global managed-zombie item UUIDs, hidden item types, drop
proximity, unrelated kills and physical STOP inferences are **not** projected.
The full original evidence is not rewritten or reduced; the L2 context records
the count of older omitted events. Older events are not yet retrieved by
semantic Memory search.

R12 can optionally make one explicit local llama.cpp POST with
Reasoning OFF and strict JSON Schema. The L2 model chooses CONTINUE,
TRY_SOMETHING, PROPOSE_SKILL, OBSERVE or DEFER. A conditional Skill candidate
has a bounded inert DSL. A source/Action-envelope validator rejects forged
experience IDs, malformed/non-bounded steps and nonexistent Action authority.

A model-generated Skill candidate is retained **only** as a
`shadow_candidate.json` sidecar with evidence fingerprints. It is not a
registered Skill, a verified Habit, a C1 experience commit, a memory owner
mutation or an L0 reflex. This post-World result cannot be issued in the
terminated session. The next-development gate is live epoch delivery and
source-bound conditional reuse through existing owners.

## Source and model prerequisites

- First read repo, #431/#537/#742, R11 #816, R12 branch, and previous
  K3-H #802. Verify the actual checked-out **R12 exact HEAD** and CI status.
- Create a **fresh** R11-qualified World with R11's own LocalCodex runbook.
  The current R10 result and a CI-only R11 test cannot be substituted. The
  R11 World may end in natural death; record that result honestly.
- Require original R11 output files:
  `report.json`, `paper_original.log`, `d14_natural_events.jsonl`,
  `original_s49_nonmotion_fence.json`, and
  `original_s49_motion_fence.json`. If the R11 parent audit rejects the run,
  R12 must reject, not synthesize a learning episode.
- Keep R12 output and raw request/response OUTSIDE the original evidence
  directory so original R11 manifest remains byte-for-byte unchanged.
- For optional model access, run the known Gemma-4-12B-it Q4_K_M exact SHA on
  llama.cpp build10874, 8192 context / 1 slot, Reasoning OFF, strict schema,
  and local OpenAI-compatible `/v1/chat/completions` endpoint.
- Model execution must have a **separate explicit** local opt-in,
  `R12_L2_POSTWORLD_DEV_ONLY=1`. Merely creating a branch/CI grant does
  not authorize GPU/World execution.

## Read-only projection CLI

Example, from the checked-out R12 repository with PYTHONPATH set:

```bash
export PYTHONPATH="src:tests:."
SRC=/absolute/path/to/r11-original-evidence
OUT=/absolute/path/to/separate-r12-evidence

python -m tools.bug0_d14_r12_l2_shadow \
  --phase project \
  --report "$SRC/report.json" \
  --server-log "$SRC/paper_original.log" \
  --event-journal "$SRC/d14_natural_events.jsonl" \
  --nonmotion-fence "$SRC/original_s49_nonmotion_fence.json" \
  --motion-fence "$SRC/original_s49_motion_fence.json" \
  --out "$OUT/projection.json"
```

The independent parent audits are re-run. This does not access the model.
Output is created exclusively and preserves hash references to all five
originals. If the original source changes, stop and keep the failure.

## Optional one-shot L2 reflection (not real World action)

A second command independently re-audits the original R11 source. It does
NOT trust the generated projection file. This command may use a genuine local
model only after explicit independent authorization:

```bash
export R12_L2_POSTWORLD_DEV_ONLY=1
python -m tools.bug0_d14_r12_l2_shadow \
  --phase propose \
  --report "$SRC/report.json" \
  --server-log "$SRC/paper_original.log" \
  --event-journal "$SRC/d14_natural_events.jsonl" \
  --nonmotion-fence "$SRC/original_s49_nonmotion_fence.json" \
  --motion-fence "$SRC/original_s49_motion_fence.json" \
  --endpoint http://127.0.0.1:8080/v1/chat/completions \
  --model local-gemma \
  --record-dir "$OUT/r12-l2-raw" \
  --out "$OUT/r12-l2-summary.json"
```

Use the actual API model identifier; `local-gemma` is an example. Retain the
original request, response, selected decision, validator result, and any
negative case. The raw directory is exclusive to one attempt; never
overwrite/retry a failed first POST. The caller must independently verify
the model's exact SHA/build/process/GPU identity, server runtime controls,
request/response bytes and final cleanup. Source self-consistency is not
provider-independent attestation.

If the model returns a valid Skill, **do not execute it**. It has not been
tested on another live World. No implicit fallback, rearm or Action token
may be obtained from the candidate sidecar.

## Required acceptance and next stage

1. R12 source projection works only after the R11 native/Paper/fence audit
   and does not leak global loot/hidden physics to the Self-view context.
2. Bad session/Action ID, duplicate source, absent fence, bad terminal,
   wrong source, corrupted Paper, reused raw directory, forged model ID,
   non-local endpoint, over-budget Skill or unadmitted action all reject.
3. The model is free to decline a Skill. A SKILL choice alone is not a
   validated improvement; a S16 OUTCOME alone is not a kill, hunger recovery
   or Intent success.
4. Next PR: stream qualified experiences into current MySelf/SelfWorld/
   SelfBody projection while the SAME World is running; call L2 when needed,
   store source-qualified skill candidates in the existing retention owner,
   run bounded comparisons behind the original S49 owner only after explicit
   dev authorization, and compare future epoch reuse with baseline.
5. Keep R11's unrun physical experiment and R12's unrun model experiment
   distinct. No L1/Habit promotion or L0 install is qualified in R12.

**Taxonomy:** DEV_ONLY / SOURCE_AUDITED_L2_INPUT_DESIGNED /
POST_WORLD_L2_SHADOW_ONLY / LIVE_LEARNING_NOT_RUN /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
