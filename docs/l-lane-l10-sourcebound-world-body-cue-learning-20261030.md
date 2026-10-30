# RelaySelf L10 — source-bound SelfWorld/SelfBody cues → L6 next-epoch L1 shadow (2026-10-30)

## Scope and owners

Branch: `integration/l10-sourcebound-worldbody-cue-learning-20261030`, created from the **L9 final docs commit** `095b384eb1ead275a8cbd277b8f3ec94066fc864`.

L9 joined an **already-returned** S decision epoch and the same typed Mineflayer probe projected into SelfWorld/SelfBody v0. L10 closes the narrower next seam: before retaining experience, derive two **preregistered and explicitly bounded source features** from the same source-qualified current Present and each older separate-session Present; attach those exact features to the corresponding separately admitted original S16 OUTCOME + external Goal source; call the existing L6 next-epoch shadow, and observe the already-returned original S choice via L8/L9.

L10 does **not** make arbitrary SelfWorld inferences into measurements, qualify a physical World, prove goal success, infer physical M0 energy or P1 fatigue, commit S10 learning, grant S11 Habits, call a live model or issue an S49 Action. S/R/V remains responsible for authenticating independent original Present, Action and Goal receipts. Membership in a set of digest-shaped strings is not a physical attestation.

### Implementation and source lineage

1. Existing `src/relay_self/l9_world_body_epoch_shadow.py` now exposes pure `verify_original_world_body_present(native,world,body,owner_self_id)`, factoring the **same** original L9 World/Body source check before the L8 comparison. The original L9 path invokes it unchanged; L10 can call the exact source check before building learning cues. It rejects cross-Self/session/epoch/native seq/request mismatches, forged complete bounded entity registries, altered positive target geometry, changed observed x/y/z, health/food/saturation and hypothetical or action-readback fields substituted as current source.
2. `src/relay_self/l10_world_body_cue_learning.py` defines `project_admitted_world_body_cues`, `PriorWorldBodyEpisode`, and `evaluate_l10_next_epoch_shadow`. After exact L9 source validation, it also uses the **existing S34 native target geometry validator**, with S-owned exact Present digest admission.
3. The **fixed feature contract**, applied identically to all earlier sessions and the current session:
   - `body_food_low` iff native Minecraft `food < 10` (a **Minecraft food gauge**, not M0 energy or P1 fatigue);
   - `world_zombie_near` iff the **positively present original zombie** distance is less than **4.0m** (same numeric boundary as the existing S42 fixed World choice);
   - constant `world_body_present_observed` so a known far target and a missing observation are never conflated. Missing target is REFUSE/UNKNOWN, **not inferred safe**.
   All tags remain sorted and immutable. No source labels/goal outcomes contribute to generating current features.
4. Each prior `PriorWorldBodyEpisode` includes the independent typed native Present, SelfWorld, SelfBody, stored `WorldBodyCueWitness`, **qualified terminal S16 OUTCOME** and separate `ExternalGoalLabel`. L10 **recomputes every prior witness** from its exact Original Present and independently admitted prior source digest. It refuses foreign or replayed session, re-labelled cue, non-previous revision, mismatched S16 session/revision/tag, missing Action/Goal digest, original-probe/Action SHA collision, missing external goal binding and nonterminal UNKNOWN. Current and prior SHA admissions are separate; the original Action and Goal admission stays the existing L6/L3 owner.
5. Only after these checks does L10 call `advance_learning_epoch`, comparing retention ON/OFF with the **same S-owned no-memory choice** and the existing L5 strongest same-data cheap baselines (exact cue, singleton feature and global). It invokes only the L9/L8 observer **after** the original S coordinator has completed, **never** the S scheduler, action issuer or T2/P1/M0 accounting owner. The original S decision survives any L1 contrast.

### Proven tests: synthetic fixtures, genuine existing S coordinator API

[Exact physically *untested* Python3.12 focused code/workflow SHA `4bc75273baa61941795146ea25ade9a041d9bee8`](https://github.com/rinsakamo/relay-self/commit/4bc75273baa61941795146ea25ade9a041d9bee8). [GitHub Actions run #41044421992 **SUCCESS**](https://github.com/rinsakamo/relay-self/actions/runs/41044421992), **187 focused pytest PASS**, Ruff/compileall and repository contracts PASS. The 187 include L10, full L9, L8/S, L6, L5, L3/L1, S42, epoch plan and runtime coordination regressions; neither a full repository regression nor real Java/Paper/Minecraft exercise was run.

The L10 fixture creates **16 distinct simulated prior sessions**: four combinations of near/far positive zombie distance and low/high Minecraft food, two candidate Actions `WAIT`/`MOVE_AWAY` and two observations per Action per context. For each distinct prior session the test creates a typed source-shaped Mineflayer probe, projects to the existing typed SelfWorld/SelfBody classes, binds a separately typed S16 `OUTCOME`, and constructs a separate source-shaped `ExternalGoalLabel` and independent admission digests. These are **synthetic fixtures**, not externally authenticated World/Goal originals and not an observed learning outcome.

#### Controlled synthetic contrast (one current near-zombie, low-food source)

| Case | Result |
| --- | --- |
| Existing S42 no-memory current decision | `MOVE_AWAY` retained |
| L6 previous experience retention **OFF** | `MOVE_AWAY` (L8 `WITHHELD`), no new Memory |
| Same current S decision, retention **ON** with 16 prior synthetic completed outcomes and independent synthetic Goal labels | L1 **candidate** `WAIT` (L8 `CHEAP_DIFFERS`), original S `MOVE_AWAY` **unchanged** |
| Strongest same-information cheap exact-cue rule | **`WAIT` also**; L5 classifies `CHEAP_EQUIVALENT`, **not** unique contextual learning benefit |
| Remove a training quadrant or contradict one quadrant | `INSUFFICIENT` and original `MOVE_AWAY` |
| Unadmitted/future/foreign/stale/rewritten source, UNKNOWN Action, missing Goal digest or changed current S result | Reject or keep original baseline; cannot manufacture training |

No claim of causality for retention or value for L2/L1 beyond this deterministic offline comparator; cheap exact-cue baseline already explains the 2-feature pattern. No real-world Goal-performance improvement is claimed. In particular, `L10WorldBodyLearningResult.action_issues/native_reads/learning_commits/habit_grants = 0`, `action_authority=false`, `physical_learning_attested=false`.

### Retained fail-to-pass history

- [#41043782128](https://github.com/rinsakamo/relay-self/actions/runs/41043782128) first CI: Ruff import ordering and unused import.
- [#41043901392](https://github.com/rinsakamo/relay-self/actions/runs/41043901392) intermediate pushed-head Ruff failure before subsequent clean test commit.
- [#41043909345](https://github.com/rinsakamo/relay-self/actions/runs/41043909345): test fixture incorrectly tried `dataclasses.replace(..., provenance=...)` on `MineflayerObservation` although `provenance` is a **computed property** from original session/seq, not a dataclass field. Fixed the fixture; source/authority validator unchanged.
- [#41044421992 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/41044421992): complete focused source and regression test pass, unmodified S49 / G4.x / original SelfWorld / SelfBody, preserved original S choice.

### Next: L11 / owner adoption boundary

Do **not** use an artificial extra feature or a less powerful cheap comparator merely to obtain a favorable L1 result. Next meaningful step is **S/R/V source admission with independent original World Present, original Action terminal and Goal receipts**, then evaluate a *prospective* next-epoch candidate against the same-data exact-cue control under natural variation. Only separately authorized S owner may consider a shadow candidate for real S49 execution. Keep L0 automatic distillation, physical qualification and SCIENCE explicitly off.

**Final classification**: `DEV_ONLY / L10_SOURCEBOUND_TYPED_CUES / PY312_187_FOCUSED_PASS / L1_CHEAP_EQUIVALENT / ORIGINAL_S_CHOICE_UNCHANGED / NO_REAL_WORLD / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
