# S49 → S50 → P1: World-first DEV boundary (2026-10-25)

Status: **DEV_ONLY / OFFLINE MODEL REPLAY IMPLEMENTED / WORLD NOT RUN /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.

This deliberately reduces the development target. The goal is to run an
existing S49 physical MOVE, observe a settled idle interval with an existing
Paper observer in the **same disposable World/session**, and demonstrate
P1 WAIT recovery by the unchanged `experiments.fatigue_p1.advance`.

## What is implemented here

`adapters/mineflayer/s49_s50_p1_wait_replay_dev.py` reuses the existing
`review_s49_preaction_paper_dev` for typed S16 MOVE_BACKWARD closure,
Paper-reported BACK true→false, idle input and no observed Self movement,
same Paper run/subject/World, eight consecutive callbacks and COMPLETE.
It excludes the ambiguous BACK-off boundary tick, and only replays the eight
subsequent World ticks into P1 `FatigueFrame(WAIT)`.

The caller must provide an **existing** P1 enabled profile and FatigueState
at the preceding World tick. The replay will not create or infer a fatigue
state from a missing source, skip a tick, treat blocked MOVE as WAIT,
alter the M0 basal calculation, issue any Action, or commit an evaluator state.

For a synthetic log its result is **OFFLINE_WAIT_MODEL_REPLAY**,
`world_run_verified=false`. The independent R fields stay unchanged:
`source_bound_tick=null`, `wait_interval_ref=null`,
`wait_ticks_admitted=0`, `p1_fatigue_recovered=0`.
A separate `dev_fatigue_recovered` is the result of model replay, **not**
an externally qualified physical recovery or a World observation.

Focused local test:

```bash
PYTHONPATH=src:tests:. python3.12 -m pytest -q \
  tests/test_s49_s50_p1_wait_replay_dev.py
```

## Real World next: minimum owner integration, no R-grade attestation

**Important architectural gap:** The original S49 `qualify()` currently
downloads/boots a Mojang vanilla server. Vanilla cannot load the separately
built Paper 1.21.8 observer. The repository already has the S-owned disposable
Paper DEV launch path `m02_paper_dev.s51_paper_physics_dev`, but it runs an
S50/S51 governed flow, not the original S49 `execute()`. Therefore two
existing independent runs CANNOT be spliced into a successful SAME-WORLD
S49→P1 DEV demonstration.

The smallest practical next implementation is an **opt-in S-owned DEV
harness** which:
1. Reuses the existing Paper DEV server lifecycle and SHA-pinned observer JAR,
   in a fresh private World, port and run output root. No main/Golden reuse.
2. Invokes the existing original S49 single Action issuer/Executor in that
   Paper World; does not invent a second motor controller.
3. Enables the observer before MOVE (when using the preaction stream),
   captures original S16 closure/clear and the subsequent Paper server
   input-idle/movement callbacks in that SAME run.
4. Acquires/maintains legitimate P1 state up to the last pre-WAIT tick
   (including MOVE state evolution); does not fabricate a starting fatigue
   level. If no such state exists, record WAIT observed but fatigue result
   UNDETERMINED instead of an invented recovery.
5. Runs the pure replay/advance, records the observed World and P1 before/
   after/recovered in DEV-only fields, preserves both raw original logs,
   closes/reaps Java and Node and keeps failed attempts. If input resumes,
   the player moves, an Action remains open, or the source is missing,
   reject the interval. Boundary tick unknown? Drop it.
6. Reports `DEV_WORLD_OBSERVED` only if the actual **single session**
   World receipts and P1 transition were collected; this report alone never
   makes `QUALIFICATION_GO` or `SCIENCE_GO`.

**Not a DEV prerequisite:** external custody, independent OS signing,
W4 epoch attestation, raw TCP-witness certification, or proving ACK caused
each Paper packet. Retain these as distinct R/V qualification work.

## Present limitation

This branch is not a Paper plugin installation, World launcher change or a
real Minecraft run. It supplies the P1 calculation seam plus regressions, and
records the concrete server mismatch to fix next. Do not label a synthetic
fixture WORLD PASS; do not reuse historic paper/v7 evidence as this run.
