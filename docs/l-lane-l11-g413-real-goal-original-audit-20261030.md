# RelaySelf L11 — archived **real Paper** G4.13 source-file readback and Goal/Action boundary (2026-10-30)

## Source actually inspected

This L11 child was created from L10 final doc SHA `747014b0550a0e18ba75fad82504a69796c33199` into the **independent DEV branch** `integration/l11-g413-real-original-goal-boundary-20261030`. It does not change G4.13 source, S49, L10 original memory logic, SelfWorld/SelfBody, main, protected Draft PRs, or any physical runtime.

Unlike prior L10 synthetic-only source-shaped experience, the **actual archived bytes** from an existing **successful real Paper 1.21.8 G4.13** run were obtained using GitHub Actions saved-artifact download:
- Producer: [run #40997098497 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40997098497), producer exact code/workflow HEAD `55f5f7c6f2e483ceb6bcb9d692c02b1dcf751e24`, run attempt 1.
- Archive: [artifact #12952335343](https://github.com/rinsakamo/relay-self/actions/runs/40997098497/artifacts/12952335343), 18 entries (WORLD-G4 + WORLD-G413 Goal report, T2/G1/Paper sidecars, logs and producer output). Received archive SHA256 in this investigation: `f167c7b16c8aee0df0b163a4b057d7aea69530d91d41b22e2ca968c417cdc525`. The ZIP envelope is not independently authenticated original Minecraft network bytes and might change if repackaged.
- **Four pinned, real saved *file-byte*** SHA256 (not recreated JSON serialization):
  - `WORLD-G4/goal_report.json`: `5cc9d5c2bf262dcf241ba3ce715c2347fd075db96de5fda16352c1b84ab17757`.
  - `WORLD-G4/l1_t2_ledger_dev.json`: `017eabbc2fdfc963160eabf72e549b6550c133a00a3958cc3104e04f7f66163e`.
  - `WORLD-G413/goal_report.json`: `a2139d5edb7fae955470306ddc8f83535c3995666236562f3727d9d308a4cec6`.
  - `WORLD-G413/l1_t2_ledger_dev.json`: `0f21851ab06377532b46514534d49df6db5b39fa7ede65a1c2919553be20f75d`.

The persisted Goal and T2 files are **original saved bytes of derived report and ledger output**, NOT native Mineflayer bridge stdout bytes, raw Minecraft TCP packets, independently signed Goal receipts, or evidence of an L3 Goal label. Source SHA identity proves content integrity relative to pinned archive, not native truth beyond the already-successful producer's scope.

## Verified engineering facts and important boundary

| Source World | S49 Action `executed/outcome` rows | Original Paper T2 WorldTicks | L1 tolerance | Last S16 Action-end Goal error | Later *final probe* Goal error | Last S16 within tolerance? |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| WORLD-G4 | 5 | 49 | 0.490m | **0.453m** | **0.403m** | Yes |
| WORLD-G413 | 6 | 133 | 0.490m | **0.512m** | **0.448m** | **No** |

Both producer reports returned `PASS / GOAL_REACHED` at a separate final probe **after** the last Action's `after_seq`. Both have distinct real Minecraft sessions. Every original Action row records `s16_terminal=outcome` and `s16_status=executed`, source-native before/after sequence order and explicit Action endpoint x/z. The saved T2 ledger has 49 and 133 contiguous positive original Paper WorldTicks and one original action-boundary receipt per Action. The source report/T2 SHA and session are explicitly joined.

**Critical negative example**: G413's 6th executed Action ended at 0.512405472m, which is **outside the 0.490m L1 tolerance**. The **later** final native Goal observation was 0.447752852m, inside tolerance. Treating `GOAL_REACHED` from this World report as success of every preceding `S16 OUTCOME` Action would introduce hindsight leakage and an invalid learning reward. Even the G4 final Action whose observed endpoint happens to be inside tolerance lacks an **independently admitted per-Action external Goal result**, so L11 does not construct a separate L3 `ExternalGoalLabel` for it.

For both original reports `real_world=true`, `learned_L1_attested=false`, `qualification_go=false`, `science_go=false`, `experience_requested_dev=false`. T2 also reports `independent_native_source_authenticated=false`, `exact_gait_attested=false`. Those limitations are preserved. **Neither 11 S49 OUTCOMEs nor 182 T2 rows are 11 verified Goal rewards or training events.**

## Implementation

`adapters/mineflayer/l11_saved_real_goal_originals_dev.py`: a pure read-only bounded ZIP auditor. It verifies four saved original file SHAs exactly, duplicate/path-traversing/oversized/symlink ZIP entries, real successful producer identity (workflow preflight), two different sessions, original complete `Action` terminal sequences, final x/z Euclidean error, Action-end x/z error per Action and source sequence ordering, original report/T2 cross-file SHA reference, T2 row count and contiguous WorldTick/session owner, 1:1 original Action-boundary receipts, and absent source/learning/science authority. It never contacts a World, starts Java/Node/GPU/LLM, or issues Action. With no real original ZIP, the CLI explicitly returns `L11_ORIGINAL_BYTES_NOT_SUPPLIED`; altered/missing ZIP bytes refuse.

The returned `L11OriginalBoundaryAudit` always sets:
- `action_goal_labels_admitted=0`, `l10_qualified_episode_pairs=0`, `l10_current_world_body_cues_admitted=false` because neither independent per-Action Goal originals nor an L10 native-current SelfWorld/SelfBody source exist in this G4.13 archive.
- `s10_learning_updates=0`, `s11_habit_grants=0`, `action_issues=0`, `replayed_worlds=0`, `physical_learning_attested=false`, `science_go=false`.

`tests/test_l11_saved_real_goal_originals_dev.py`: tests against the **same actual downloaded artifact bytes**, not fabricated real-looking JSON. Negative controls alter each of four original files, omit a required file, inject duplicate ZIP member and substitute a symlink source. Existing L10/L9 regressions run unchanged. Audit exits nonzero on tampering. No historical proof file is modified.

Workflow `.github/workflows/l11-g413-real-original-goal-audit-dev.yml`: uses ephemeral Github Actions `actions:read` token to verify original producer run and artifact metadata, then downloads its **existing** signed blob without forwarding GitHub bearer credentials to signed storage, SHA-audits in Python3.12 and runs focused tests. The source ZIP is kept under `/tmp`, not committed to repo or served as an L1 training fixture. This is an artifact **readback** and does not start a fresh Minecraft run. Its availability depends on the archived producer artifact remaining unexpired; failure to access it is not a license to generate replacement evidence.

## L11-to-L12 handoff

The next independent owner gate is **a genuinely per-Action, independently verified external Goal result**, with the original World Present/Body food/target native source required by L10, separately S/R/V-qualified and bound to a **later** cognitive epoch. The existing WORLD-G413 final Goal state is an observation of one eventual World result, **not** an independently admitted individual Action-success label. L10's first real prospective next-epoch memory contrast stays **NO-GO** on this archive. Do not inflate 11 S16 executed terminal records into training examples. Never weaken the exact-cue cheap comparator or infer L0 auto-distillation.

**Classification (source boundary): `DEV_ONLY / L11_ARCHIVED_G413_REAL_SOURCE_SHA_BOUND / 11_S16_OUTCOME_182_T2 / PER_ACTION_GOAL_LABELS_0 / L10_REAL_LEARNING_NOT_ADMITTED / NEW_WORLD_0 / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.**
