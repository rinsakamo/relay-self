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

## 2026-10-25: same-run Paper opt-in implementation

Two modules now stage the minimal **single-run** owner path:
`s49_paper_postwait_dev.py` joins S49 original S16 clear and original
Paper 8-tick post-action input/position observer; `s49_paper_world_first_dev.py`
is an explicit S-owned disposable wrapper for the unchanged S49 `qualify()`.
Only its Paper server asset/config are substituted, and an inherited original
S49 Executor sends the read-only Paper console observation **after the second
original S49 MOVE** has closed. The original S49 cleanup still owns Java,
Node, collector, and World. No separate issuer, direct native control, W4
external custody, or new SourceBoundTick is installed.

The pre-action BACK-on/off observer is **not** a DEV prerequisite: this first
run uses the existing post-action observer and omits the uncertain boundary
tick. Model fatigue begins at a clearly labeled synthetic configured initial
value (0.5), not inferred biological exertion. The Paper and original S49
receipts must be from the **same** newly created session/run.

Operator command (NOT EXECUTED IN THIS SESSION):

```bash
PYTHONPATH=src:tests:. python3.12 -m adapters.mineflayer.s49_paper_world_first_dev \
  --output-dir /ABSOLUTE/FRESH/OWNED/s49-paper-p1-001 \
  --paper-jar /ABSOLUTE/VERIFIED/paper-1.21.8.jar \
  --paper-sha256 FULL_64_HEX_SHA256 \
  --observer-jar /ABSOLUTE/VERIFIED/relay-s49-wait-observer-dev-0.1.0-dev.jar \
  --observer-sha256 FULL_64_HEX_SHA256 \
  --confirm S49-P1-DEV-DISPOSABLE-PAPER-WORLD
```

JAR SHA identities are mandatory. The observer is normally disabled and is
enabled only in the new disposable World. An actual successful run would be
labeled `DEV_WORLD_OBSERVED_WITH_SEEDED_P1_MODEL`; R-qualified
`p1_fatigue_recovered` remains 0 and V science remains unrun. Failure
on a new Paper server is a DEV debugging input, not a recovered Golden run.
