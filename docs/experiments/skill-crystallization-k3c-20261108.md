# RelaySelf K3-C — semantic equality, bounded ESCALATE and fresh-Intent mock recovery

**DEV_ONLY / OFFLINE_ONLY / NO_NEW_GEMMA / NO_REAL_WORLD / NO_S49_ISSUE / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**

Parent: PR #791, exact parent HEAD a9a406fa84fbd9b221ac69070fef497b1b5ce9ae; implementation owner #431; S49 owner #537.

## Purpose and contracts

The real #791 Gemma output changed Skill ID, cited evidence and explanation, but did **not** change any execution field relative to the #790 normal-floor Skill: distance [2.314917, 2.457525), target 3.2, max 4 MOVE_AWAY, ESCALATE. The explanation claiming the old Skill allowed a single Action was factually wrong; semantic comparison of structured fields is not a natural-language explanation validator.

K3-C compares execution fields separately from metadata and classifies exact same execution fields as EXECUTION_EQUIVALENT. A changed distance/surface guard is EXECUTION_SPEC_CHANGED, but changing a field does not establish usefulness without independent paired behavior evidence.

New one-Intent mock semantics:

1. No-match before a Skill, with current valid observations: fixed two-move cheap fallback is allowed.
2. UNKNOWN, stale, wrong-session or incomplete observations: DEFER_INVALID_CUE, zero Actions; not ordinary no-match.
3. Selected Skill fails within its max four Actions: ESCALATE with terminal state, source sequence, World cursor, consumed Actions and zero automatic fallback. Remaining old Skill budget is not replenished.
4. Only a *new* synthetic Intent may recover, with a distinct Intent ID, fresh observation anchored to old terminal position, explicit mock admission and prior clear, new finite budget. Synthetic effects continue from the next unused cursor, not from a reset position.
5. Old receipt source/session, terminal position, trace and Action cursor are checked against the deterministic test fixture. Optional in-memory consumption ledger blocks duplicate handoff within the same process. Neither is an actual durable native S49 issuance/admission/replay fence.

## Fresh deterministic evaluation

New seed: **20261120** (different from #791 seed 20261112). This seed has now been inspected; do not reuse it for a later unopened Gemma holdout.

On 32 normal-shift synthetic cases, using reconstructed old/new Skill policy fields from #790/#791:

| Metric | Old #790 | New #791 |
| --- | ---: | ---: |
| Goal success before a new Intent | 6/32 | 6/32 |
| Selected | 11/32 | 11/32 |
| Synthetic Actions | 86 | 86 |
| Paired Action trace differences | — | 0/32 |
| Paired guard differences | — | 0/32 |

Fixed L0: 0/32, 64 synthetic Actions. Of the 11 selected new-Skill cases, 5 failed and returned ESCALATE; automatic postfailure fallback issued **zero** Actions. In a *separate controlled mock branch*, all five resumed from the terminal position with a **different** synthetic Intent and an explicit new one-Action budget; 5/5 then reached 3.2. This does not mean that the previous Skill succeeded, or that genuine S49 admission and World effects are established. All 128 stale/unknown/wrong-session/incomplete-cue negative controls deferred with zero Actions.

The above comparison was run on **reconstructed policy fixtures matching observed #790/#791 execution fields**, not by reading exact original JSON bytes in the current chat container. Run the CLI below inside the real checked-out repo against saved original files and audit existing SHA256 manifests before making a source-integrity claim.

## Reproduce on the current child worktree

~~~bash
python -m pytest -q tests/test_skill_crystallization_dev.py \
  tests/test_skill_crystallization_k3b_dev.py \
  tests/test_skill_crystallization_k3c_dev.py

python -m ruff check experiments/skill_crystallization_k3c_dev.py \
  tests/test_skill_crystallization_k3c_dev.py

python -m experiments.skill_crystallization_k3c_dev \
  --first evidence/l431-gemma-20261108/first-report.json \
  --k3b-report evidence/l431-k3b-gemma-20261108/report.json \
  --seed 20261120 \
  --out /tmp/l431-k3c-semantic-escalation.json
~~~

No HTTP or model call is performed. No new Minecraft World, S49, S15, S16, actual C1 experience, autonomous installer, official Habit/Memory change, or main merge is performed.

## Unproven and next gate

- #791 was valid formatted Skill output, not improved Skill behavior.
- The narrower guard tested by K3-C is a manually selected fixture, not an actual new Gemma modification.
- Synthetic recovery uses mock booleans for new Intent admission and clear, not real S49 receipts. No genuine recovery claim.
- Run a separate real L2 experiment to generate a behavior-changing scope/Plan revision or ABSTAIN, without leaking this new seed. Measure meaningfully changed selection/action traces with another new unopened holdout.
- Only then consider read-only S49 shadow integration preserving source, owner, Action budget, terminal clear and fresh next-Intent admission.
