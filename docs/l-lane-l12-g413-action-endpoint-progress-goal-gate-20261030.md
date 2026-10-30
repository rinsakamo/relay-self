# RelaySelf L12 — real G4.13 S49 Action endpoint progress vs independent Goal reward (2026-10-30 JST)

## Mission and exact source

This is a child of the L11 final docs-only commit `8b191ec8d60b9be03ee09097cbe8ef89ed052223`, isolated at `integration/l12-g413-per-action-progress-no-reward-20261030`. It consumes the exact **historical real Paper1.21.8** [G4.13 workflow #40997098497](https://github.com/rinsakamo/relay-self/actions/runs/40997098497), artifact [#12952335343](https://github.com/rinsakamo/relay-self/actions/runs/40997098497/artifacts/12952335343) and its original saved report/T2 *file bytes*. See [L11 exact source SHA pins and producer identity](./l-lane-l11-g413-real-goal-original-audit-20261030.md). L12 reuses L11's existing bounded SHA/archive and S49/S16/T2 source validator as a mandatory prerequisite; no repackaging or source-shaped stand-ins become original evidence. This is a **read-only replay of historical files**, never a replay of a World or Action.

The L11 report established that the two separate real Paper Goal Worlds ended within tolerance at a **later** native probe, despite one last original Action endpoint still outside tolerance. L12 now inspects **all 11 original Action endpoint records** and compares three distinct quantities: per-Action reported native displacement; displacement **between adjacent Action-end observations**; and Goal error change **between those Action endpoints**. It does **not** equate these different observation intervals.

## Results from pinned original saved bytes

| Source | Original S16 executed Actions | S16 Action-end inside 0.49m tolerance | Outside | Adjacent endpoint step larger than per-Action reported displacement | Last S16 error | Later final probe error |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| WORLD-G4 | 5 | 1 | 4 | 4 | 0.452591871m | 0.402786908m |
| WORLD-G413 | 6 | 0 | 6 | 5 | 0.512405472m | 0.447752852m |
| **Combined** | **11** | **1** | **10** | **9** | — | — |

The later final probe reduced the reported Goal error by **0.049804963m** (G4) and **0.064652620m** (G413) relative to the last S16 endpoint. This is neither a per-Action success receipt nor a physical coasting measurement. Adjacent endpoints measure a different interval than one Action's reported movement; the source files do not isolate the cause of any discrepancy, including whether input-off momentum, frame-window offset or ordinary World control changes contributed.

Every one of the 11 original S16 records has `executed/outcome` for **execution**, not an independently admitted external per-Action **Goal** result. Even G4's fifth S16 endpoint (inside the tolerance) is only a spatial observation, not an independent Goal witness. Conversely G413's sixth original S16 endpoint (outside the tolerance) cannot be labeled an external Goal **failure** from this source alone; the later final native probe reached tolerance.

Therefore the only evidence-respecting Goal label for each Action is **UNKNOWN / unadmitted**, not `true` or `false`.

## Implementation and explicit boundaries

- `adapters/mineflayer/l12_archived_action_progress_no_reward_dev.py` adds `audit_l12_real_action_goal_gate(Path)` and frozen `L12ActionProgress` / `L12GoalTrainingGate`. The auditor requires an exact successful L11 SHA/source audit, reopens the **same validated** immutable report bytes, checks original Action serial order, session, native before/after seq, endpoint geometry against the same original L2 Goal, original vector length vs per-Action reported displacement and positive finite native observations. For each Action it outputs both endpoint-to-endpoint observed progress and per-Action reported displacement, preserving separate intervals. It preserves original source-report SHA and every original Action ID/sequence in the result.
- It checks the final Action endpoint is different from the subsequent Goal probe and does not attribute the later improvement to a specific Action. `external_action_goal_reached=None`, `per_action_goal_attested=false`, `causal_motor_contribution_attested=false`, `native_source_packet_authenticated=false` for **all** rows. A missing probe is not a negative label.
- The helper `require_l10_qualified_goal_training` intentionally **fails closed for all L11/G413 artifact-derived rows**. The existing L10 learning/retention code is untouched; any future positive admission requires a **new independent S/R/V owner contract** checking real native pre-Action World/Body observations, original S16 action receipts, independent per-Action external Goal bytes, distinct sessions and later cognitive epoch. The old World-level report is insufficient. No L0, S49, T2, P1, M0, S10, S11 or motor owner is modified.
- `tests/test_l12_archived_action_progress_no_reward_dev.py` checks the **actual original archived ZIP**, per-Action readings and values, late post-Action probe separations, no Goal/Action authority, refusal for missing or symlinked ZIP, changes to any of four original report/T2 bytes, and 11 synthetic *negative mutation controls against the genuine decoded real report* (invalid Action source order/movement/probe geometry, UNKNOWN etc). It does **not** manufacture new real sessions or goal labels.
- `.github/workflows/l12-g413-action-progress-goal-gate-dev.yml`: downloads **the same existing producer artifact** using read-only GitHub Actions permission, validates original producer SHA/run id, SHA-audits through L11, runs L12 source and focused L11/L10/L9 tests. No Java, Node, GPU, LLM, real server or new physical action.

### CI provenance

Source+workflow SHA: `4c8d50b2fe5251c5f6395af2536bcab727901a38`, [L12 focused real-artifact run #41054611579](https://github.com/rinsakamo/relay-self/actions/runs/41054611579). Prior [#41054423445](https://github.com/rinsakamo/relay-self/actions/runs/41054423445) and [#41054515698](https://github.com/rinsakamo/relay-self/actions/runs/41054515698) failed due to **workflow-only embedded Python assertions containing escaped newlines**, not a permission to relabel data. They remain visible. Original source/auditor never relaxed.

## Distinct missing evidence for L13

1. One independently authenticated **pre-decision** same-session native Present that includes a positively observed target + original SelfBody food and health for the **same prior Action**; G4.13 source report and T2 sidecars are insufficient for L10 cues.
2. A **separately owned per-Action external Goal receipt**, linked to the exact Action and its native before/after boundary, not the eventual final World Goal status and not an S16 execution disposition. Include explicit UNKNOWN support, no guessed failed label.
3. Distinct prior sessions, separately admitted original Action and Goal receipt SHA values, and a **later** current S epoch in which L1 proposes a shadow candidate compared against the same-information exact-cue cheap baseline.

G4.13 was a successful DEV goal-control demonstration, **not a learning trial**. We should not rerun a controlled server merely to manufacture labels or tamper with G4.13's protected source.

**Classification**: `DEV_ONLY / L12_REAL_S49_ENDPOINT_PROGRESS_SHA_BOUND / PER_ACTION_EXTERNAL_GOAL_0 / QUALIFIED_L10_TRAINING_0 / ORIGINAL_S49_UNCHANGED / NEW_WORLDS_0 / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
