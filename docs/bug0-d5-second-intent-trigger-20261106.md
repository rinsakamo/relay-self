# Bug-0 D5 real-World single-use trigger (NOT ACTIVE)

This file is a one-use, docs-only trigger sentinel. Its initial creation
does **not** authorize or launch any real World. Only a later separate
commit changing this file alone, with commit subject
`run-bug0-d5-second-intent-oneworld-once-20261106`, may launch the guarded
workflow after the source branch's offline tests succeed.

## Bound experiment

The existing D4 real World operator fixture establishes the first actual
zombie death, natural item UUID pickup, S49/S51 consumption, and the real
Paper 600-tick next-generation spawn. The D5 post-respawn continuation keeps
the **same World, Mineflayer session, original S49 supervisor and action
history**, closes first Intent, commits second Intent, rearms from a fresh
native next-zombie observation, and issues **one new S49 ATTACK** using a
distinct PROPOSE/ISSUE/Action ID. The second zombie is operator-placed into
melee range; it keeps normal health so this test does not claim second death.

Stop on any missing proof, UNKNOWN, ambiguous native coverage, failed
pickup/food, Paper clock mismatch, or unsafe physical receipt. Do not
retry this World automatically. Independent post-audit reads the original
Paper log/report and preserves SHA256/cleanup. No LLМ, learning, or WorldBody
fatigue rule changes.

Expected classification on independent post-audit PASS:
`DEV_ONLY / D5_REAL_S49_SECOND_INTENT_ATTACK_PASS /
SECOND_EXPERIENCE_CYCLE_NOT_COMPLETE / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.

D6's Self-owned MOVE to loot and a *complete second kill/pickup/EAT experience*
remain separate unproven milestones.

Related: #717, #742, Draft PR #759 and #762.

## One-use dispatch record

TRIGGERED_ONCE_HEAD = 063dd598903df3a9ae7d9c85395b6a28d82caae5
This commit is the only approved physical World launch for D5 #764. Do not rerun the workflow on failure.
