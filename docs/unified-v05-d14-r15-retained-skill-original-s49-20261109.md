# D14 R15 — opted-in retained L2 Skill action choice through ORIGINAL S49

**Scope:** DEV implementation, no local World/real Gemma executed in this
GitHub-only step; QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
Parent: [R14 #821](https://github.com/rinsakamo/relay-self/pull/821),
R13 #820, R12 #817, R11 #816. R15 does not modify main or those parents.

## New controlled step

R14 could compare a candidate against another World's original actions only
after the fact. R15 adds an **opt-in, bounded live Skill hint** to
`NaturalLifeLoop` while keeping the existing original S49 as the only
physical Action issuer. This is the first source-controlled candidate to
influence physical action *selection*, not an installed autonomous Habit.

The normal R11 path remains unchanged: the new
`_skill_trial_choice(...)` hook returns `None` unless the R15 subclass is
explicitly selected. R15's cursor reads the previously generated R12/R13
Skill program and evaluates its conditional steps on current same-session
native observations. It can request WAIT, REST, ATTACK, MOVE_AWAY or EAT
only with the exact guard/source binding described by R13.

- **ATTACK:** a stable close native zombie and existing R9 fallback, same
  original S49 two-stage grants, PREPARE and S16.
- **MOVE_AWAY:** original unsolicited native entities event, current
  original S49/S14 motion selection, existing S14 binding, two scoped
  grants, original durable MOVE fence; may bypass R9's *baseline choice
  to wait/attack* but **never** bypass original S49 physical admission.
  Post-MOVE effective physical STOP is still unqualified, so later EAT
  may be unavailable. A Skill cannot fix this by declaring a condition.
- **EAT:** original S51 food candidate / native source and original S49
  grants/fence (post-MOVE STOP gate remains).
- **REST:** intent selection only, NOT physical rest or an energy credit.
- **WAIT:** not issuing a physical Action. It may suppress an original
  R11 selected ATTACK/MOVE/EAT choice in this bounded DEV trial; there
  is no claim WAIT improves survival.

Guards are evaluated against fresh current native source. A completely
known unavailability can SKIP/STOP according to the Skill; ambiguous
cases are UNKNOWN and **must not** be silently treated as negative. Every
issued physical Action must finish through original S49 and S16. Any
refusal, missing/uncertain terminal or interrupted trial stops the Skill
cursor with no retry, no changed S49 supervisor, no replay and no new issuer.

The existing R11 24k natural World, Java plugin, Paper physics, zombie
AI/respawn/drop, R9 stone sword, source journals and original S49 owner
remain unchanged unless explicitly opted in to this R15 child.

## Hard pre-World source and grant requirements

The current run must satisfy **all** original R11/R10/R9/R7/R6/S50 DEV
one-World opt-ins and pinned JAR, exact clean checkout, bounded watchdog
and free port, as in the R11 LocalCodex runbook.

Additional R15-only grant:

```bash
export D14_R15_SKILL_TRIAL_ONEWORLD_ONLY=1
export D14_R15_PRIOR_WORLD_EVIDENCE=/absolute/path/to/qualified-r11-world-A
export D14_R15_PRIOR_L2_RAW=/absolute/path/to/separate-prior-l2-raw
```

Before creating any new World, `validate_local_sources` independently
re-audits prior R11 World A's Paper/native/S49 durable source and verifies
R12/R13 raw Gemma one-shot input/response, candidate integrity and the
current owner Action Catalog SHA. No Skill? Model abstained? Unqualified
original? Absent scope grant? Reject **BLOCKED_PREWORLD** (no new
Minecraft World). The previous and new session IDs must differ. The new
R15 World is not automatically retried.

Previous prior evidence must be outside the new output directory. The
prior request/response and the newly generated R15 World remain separate
and immutable; this experiment is not a Memory/Habit installation.

## Execution and readouts

Use the current R15 branch's exact HEAD and the same
`tools/bug0_d14_local_oneworld.py` CLI documented in R11:

```bash
export PYTHONPATH="src:tests:."
python -m tools.bug0_d14_local_oneworld \
  --repo /absolute/path/to/relay-self \
  --expect-head "$(git rev-parse HEAD)" \
  --evidence-dir /absolute/path/to/fresh-r15-evidence \
  --paper-jar "$D14_R3_PAPER_JAR" \
  --plugin-jar "$D14_R3_RESPAWN_JAR" \
  --max-wall-seconds 3600
```

Set all **original R11 required** environment grants as described in the
R11 original runbook; these R15 lines do not replace them. Do not run
if the actual local Gemma/Paper/WSL source is unavailable or unapproved.

The R15 subclass appends each selected Skill hint and its verified original
S49 Action ID/S16 OUTCOME (or owner refusal/no effect) to a distinct
`r15_skill_s49_trial.jsonl`, fsynced. It also keeps the original source
`LIFE_DECISION` and `LIFE_ACTION` records unchanged in kind and authority.

The local wrapper first runs original R11 independent Paper/S49/loot
audits; then R15 independently correlates the sidecar and original owner
report, recomputes previous candidate source and prevents swapped
original World/Session/Action ID or forged Skill metadata. It records
`r15_skill_original_s49_readout.json` or an explicit fail-closed error
without revising any original Action outcome. The same original evidence
manifest covers the extra R15 file.

R15 readout can distinguish a Skill suggestion that changed choice
(e.g. MOVE when the original R9 would wait) from an already-selected
ATTACK that R11 would have done without the Skill. **Only a live
source-qualified R15 run can establish any real causal Skill choice.**

## Independent limits

This implementation does not prove survival, skill utility, generalized
body understanding, autonomous grant origin, learning, long-run Skill
retention in owner MySelf/Memory/Habit, or future L1 use. World-source
damage and effective physical STOP remain subject to their own owners.
The current Skill is still an experimental **external retained candidate**
verified from previous local model output. No new learning update, C1
Intent experience commit, Memory/Habit owner writer or L0 reflex install
occurs. R15 does not call the LLM in the new World.

Acceptance sequence:
1. Exact HEAD CI Python focused tests, Ruff and repository contracts.
2. Source-qualified prior R11 World and raw R12/R13 Gemma candidate.
3. Separate explicit one-time R15 real World grant. If original source
   fails preflight, stop without World or auto-retry.
4. Original S49 S16 readback and independent R15 sidecar correlation.
5. Only then, a later child can retain **actual source-qualified Intent
   experiences** in the existing Memory owner and test L1 retrieval/reuse,
   with no automatic L0 promotion.

DEV_ONLY / ORIGINAL_S49_ONLY / SKILL_SELECTED_S49_ACTION_NOT_YET_RUN /
LEARNING_AND_HABIT_UNCHANGED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
