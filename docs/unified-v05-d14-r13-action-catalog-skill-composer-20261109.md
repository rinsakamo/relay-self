# D14 R13 — S49 owner-checked Action Catalog and L2 conditional Skill programs

**DEV_ONLY / NO_REAL_WORLD_ACTION / NO_GEMMA_POST / NO_SKILL_INSTALL / QUAL_NO_GO**

Parent: [R12 Draft #817](https://github.com/rinsakamo/relay-self/pull/817).
R13 is a child branch and does not change R11/R12 history, main, Paper,
S49 Action authority, S51, STOP, L1 or L0.

## Why

R12 L2 Skill composition originally exposed only the action strings
`MOVE_AWAY, ATTACK, EAT, REST, WAIT`. Names are not enough to plan a
reusable conditional Skill: ATTACK needs a current native zombie entity ID,
EAT needs an observed S51 food choice and slot, and MOVE_AWAY requires
the original native event/S49/S14 motion admission. REST is an intent, not
a physical command. WAIT selects non-action, not a guaranteed rest.

R13 adds a read-only `action_catalog()` in
`tools/bug0_d14_r13_action_catalog.py`. It reflects existing method
signatures and typed authorization dataclass fields at runtime. If a
required method or field drifts, Catalog creation fails closed. Source
file/method paths, bounded descriptions, arguments, preconditions, limits
and possible observations are included. The semantic descriptions are
**human-authored**, verified against existing code in DEV, not generated
automatically and not runtime authority. Introspection proves the Python
method shape only, never a physical World entitlement or semantic truth.

Action           | Type                   | Referenced binding
---------------- | ---------------------- | ------------------
MOVE_AWAY        | physical S49 Action    | NATIVE_S49_MOVE_SOURCE
ATTACK           | physical S49 Action    | NATIVE_STABLE_ZOMBIE_ID
EAT              | physical S49 Action    | S51_OBSERVED_EAT_CHOICE
REST             | passive intent         | NONE
WAIT             | non-issuing choice     | NONE

## New bounded Skill program

An L2 proposal is a conditional program, NOT an Action list that S49 can
execute. A program is max 10 declared attempts. Each step has:
- original `action`;
- matching Catalog `guard` and source `binding` (no literal made-up target
  ID, item name or slot);
- `repeat` in [1, 3], a **static upper bound** not an unbounded loop;
- `if_unavailable` = SKIP or STOP, a conditional branch;
- program-wide `max_actions` (static total repeats must not exceed it),
  `stop_condition=GOAL_OR_SOURCE_CHANGE`, `on_failure=ESCALATE`.

Example **not yet run on a live World**:

```json
{
  "name": "guarded survival",
  "cue": "observed near zombie then safe food opportunity",
  "steps": [
    {
      "action": "ATTACK", "guard": "STABLE_CLOSE_ZOMBIE",
      "binding": "NATIVE_STABLE_ZOMBIE_ID", "repeat": 2,
      "if_unavailable": "SKIP"
    },
    {
      "action": "EAT", "guard": "S51_SAFE_EAT_CANDIDATE",
      "binding": "S51_OBSERVED_EAT_CHOICE", "repeat": 1,
      "if_unavailable": "STOP"
    }
  ],
  "max_actions": 3,
  "stop_condition": "GOAL_OR_SOURCE_CHANGE",
  "on_failure": "ESCALATE"
}
```

This can be **statically validated and compiled as an inert shadow**; the
compiler does not evaluate guards, resolve live target IDs, authorize
repeats or issue anything. A future live executor MUST re-evaluate all
guards using current own-session native observations and obtain the
original S49/S51 grants for each single physical Action. The current S49
MOVE→STOP fence remains in force; it is entirely possible the example
EAT step cannot run. It must simply STOP/DEFER, not bypass S49 or infer
successful physical STOP.

## R12 handoff

R12 independently audits R11 sources as before. It now exposes the
owner-reflected Catalog in the native-only L2 context, changes its
strict JSON Schema Skill type from bare strings to typed steps, and
validates generated programs against a fresh owner-checked Catalog.
The L2 system prompt explicitly describes catalog use and the right
to refrain from Skill creation.

A proposed candidate sidecar now includes `owner_catalog_sha256` and
`shadow_compilation`. Read-only replay recomputes the original model
response, source-bound context and current Catalog, rejecting tampered
Skills or mismatching owner contracts. It still writes NO L1, Learning,
Habit or Memory owner record.

## Verification

- Run the exact HEAD Python/ruff/tests workflow on this child branch.
- Confirm a legitimate conditional program, abstention, stale ABI,
  unknown Action, inconsistent binding, invented target ID, bad budget,
  unbounded repeat, grant claim or owner mismatch are rejected appropriately.
- R11 physical World must have a real original-source audited result before
  invoking R12/R13 on its evidence. Do not claim R12/R13 live Gemma or
  new autonomous Skill acquisition from code or CI alone.
- Later: capability projections for all implemented Body actions, one
  source-qualified live epoch, and optional L2 skill execution through
  the original S49 issuer; learn from physical feedback then retain in
  the appropriate owner only after real outcomes. Do not bootstrap
  a new Action authority by calling the candidate an installed Skill.

Classification: DEV_ONLY / ACTION_CATALOG_API_SHAPE_CHECKED /
CONDITIONAL_SKILL_SHADOW_ONLY / LIVE_EPOCH_NOT_CONNECTED /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
