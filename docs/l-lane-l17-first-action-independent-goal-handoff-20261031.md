# RelaySelf L17 — L16 original first-Action prefix → L14/L13 independent Goal source handoff

2026-10-31 JST. Parent: isolated L16 docs exact HEAD `eef2c8bd55e9ccd553cb09c80514ae32b8e96c63`. Scope: **read-only offline** and existing S/L source owners only. No new World, grant, S49 Action, L10 retention, S10 Memory/Habit or V SCIENCE.

## Implementation

`src/relay_self/l17_first_action_goal_handoff.py` exports `review_l17_first_action_goal(..., external=None)`.

The **first mandatory step** is rerunning the actual `inspect_l16_first_action_prefix` against the complete original S7 received/sent JSONL, sealed S7 SHA/count index, S49 Action ID, original S15 control-clear, two consecutive terminal probe IDs and the operator's immutable pre-World plan. An asserted L16 result is not trusted without original bytes.

**Missing external originals** → `WAITING_FOR_EXTERNAL_ORIGINALS`. The L16 operator's observed `REACHED` / `NOT_REACHED` / `UNDETERMINED` remains a bounded DEV diagnostic, **not a reward**. No fabricated negative example, and zero training candidates or writes.

Only `L17IndependentInputs` containing *separately supplied* external criterion original, independent criterion SHA admission, preexisting L13 `L13ReceiptTriplet` (typed native prior SelfWorld/Body + actual S16 terminal original + independent Goal original), distinct L13 S/R/V admissions and a later `WorldBodyCueWitness` can initiate the second review. No method in L17 can mint those owners or generate their source bytes.

On supplied originals, L17 verifies independent criterion identity and exact raw pre-Action Present, independent criterion coordinates/tolerance/stability against the original operator pre-World plan, then invokes unchanged L14 → L13 review on **the same exact S7 source bytes and SHA**. It independently compares session, Action ID, pre/after sequences, both post-Action probe sequences, both native original stream hashes, two geometric distance results and the three-way Goal status. Any mismatch is **rejected**, not normalized as unknown and not converted to a reward.

**Stable, consistent, externally sourced source-shaped result** → `SOURCE_SHAPED_L10_CANDIDATE` with existing L13 `PriorWorldBodyEpisode` *available only as a source-shaped review object*; **NOT qualified real training**. **Unstable/ambiguous native observation + external `UNDETERMINED`** → `UNDETERMINED_NO_GOAL_LABEL`, no `PriorWorldBodyEpisode`.

All statuses explicitly maintain `qualified_real_training_pairs=0`, `real_l10_adoptions=0`, `s10_updates=0`, `s11_habit_grants=0`, `new_actions=0`, `new_worlds=0`. Neither the L13 typed claims nor independent SHA membership prove producer authenticity, no-unobserved-intervention or causal Goal improvement.

## Synthetic DEV coverage

`tests/test_l17_first_action_goal_handoff.py` uses existing L15/L16 source-shaped original fixture bytes to exercise:

- No independent Goal/S16 originals (blocked even when L16 operator diagnostic is `REACHED`).
- Consistent positive `REACHED`, negative `NOT_REACHED`, and physically ambiguous `UNDETERMINED` without falsely claiming real-world provenance.
- Wrong/missing criterion admission and prior timing, mismatched x/z plan, cross-session/Action/pre-Action Present, mixed S16 original, changed Goal result/owner/seq, duplicated raw JSON key, replayed current epoch, extra Action, altered source hash, bad L16 plan; all fail closed.

The synthetic fixtures deliberately create internally consistent owner strings and SHA bytes. They are **not** real physical Goal receipts. The old G4.13 original archive is not silently promoted; all 11 physical S16 Action results still have **0** independently sourced per-Action Goal labels and **0** qualified real L10 training pairs.

## Physical-source owner work still required (prospective)

L16's S49 bridge captures S7 native raw bytes + original terminal probes in an explicitly opted-in disposable DEV World, but has **not** run a World in this turn and **does not write an independent external Goal owner's original receipt or L13 S16 owner original**. To feed L17 from a real run, physical S49/S16 owner must explicitly preserve its actual typed S16 terminal original, S/R/V must independently predeclare a Goal criterion *before the physical Action*, observe and attest the actual per-Action window without additional unobserved interventions, and independently admit original bytes/source identity. The L13 source revision and later distinct SelfWorld/SelfBody epoch must exist; otherwise the result remains blocked.

If independent originals become available and pass source-level checks, L10 next-epoch **comparative** evaluation (memory OFF/ON and cheap exact-cue/singleton/global controls) is a separate task. Source-shaped comparison never by itself grants S10/S11 or L0 promotion.

Classification: `DEV_ONLY / L17_L16_L14_READONLY_HANDOFF / PHYSICAL_NEW_WORLD_0 / L10_REAL_PAIRS_0 / S10_S11_UPDATES_0 / NO_ACTION_AUTHORITY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.

## Local read-only S49/S7 capture re-audit (new L17 CLI)

The additional `adapters.mineflayer.l17_saved_original_goal_readback` consumes **an existing** L16 physical capture root with the four original S7/L16 files and an independently specified S49 report path. It makes **no new World calls or Action/Memory writes**. It reconstructs the operator Goal plan from its exact original bytes, recomputes the L16 window against both raw bridge streams and their S7 hash/index, and compares the entire reconstructed dataclass to the existing S49 `l16_capture.window` report. A stale/modified/missing original, foreign Action/session or report contradiction fails closed.

No flags → `L17_DRY_RUN_NO_HOST_READ`; supplying exactly one path → argument error. For a separately obtained prospective physical capture:

```bash
PYTHONPATH=src:tests:. python -m adapters.mineflayer.l17_saved_original_goal_readback \
  --root /absolute/new/l16-physical-root \
  --s49-report /absolute/existing/s49-report.json
```

This CLI returns `waiting_for_independent_s16_goal_originals` even if the operator-local original Goal diagnostic says `REACHED`, because it **does not create or ingest an independent Goal owner's original**. A success means only raw/source-level consistency, not physical original authentication, real learning, or lack of unobserved interventions. The saved source and report are never modified. Its negative tests include content, hash, missing files, symlink roots, foreign session/Action, forged report statuses and altered plan.

## Exact-head GitHub DEV verification

**Exact successful code/test/workflow SHA `6c315647962dcc2a6e6ba4daa45793baee00e308`**, [GitHub Actions #41151568508 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/41151568508), Python 3.12 **146 focused PASS / 2 SKIP**, Ruff PASS, compileall PASS, repository contract PASS. Two SKIPs are historical/optional real archive cases unavailable in this isolated workflow; **no new Minecraft World**. Existing independent saved G4.13 archive negative audit was run in L15 [#41144568698 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/41144568698) and is not a per-Action Goal qualification.

The previous successful code-only increment [#41151360787 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/41151360787) verified **129 PASS / 2 SKIP** before the saved-file readback CLI was added. Earlier failed source revisions [#41151322463](https://github.com/rinsakamo/relay-self/actions/runs/41151322463) (unused test import) and [#41151514936](https://github.com/rinsakamo/relay-self/actions/runs/41151514936) (Ruff import ordering in the new CLI/tests) are retained. The stricter source/Goal checks were not relaxed; the final source-head CI includes both new suites.

A documentation-only HEAD after the exact tested code SHA has no new code changes and is not claimed as a separately tested source. No future automatic checks or physical trial has been scheduled.
