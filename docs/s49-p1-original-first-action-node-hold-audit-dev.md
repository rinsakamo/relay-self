# P1/DASH: first original S49 Action Node hold window vs seven Paper boost ticks — DEV

Status: **DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.

## Frozen baseline

- Previous exact source HEAD: `d2ecdb5c2609615c84ef55a75b1ca2bfb8b382b1`.
- Previous [two-World real DEV run #40495397519](https://github.com/rinsakamo/relay-self/actions/runs/40495397519) was SUCCESS.
- Both Worlds had 7 real positive Paper modifier ticks, 13 Paper P1 gait callbacks and 6 Node attribute-positive physicsTicks; native S16 distance difference was +0.4783798571805118 m.
- That test **did not** establish equal original S49 Action holding intervals, nor matched Node active physicsTick counts, nor synchronized Paper and Node phase.

## New isolated source readback

New `s49_p1_native_hold_pair_dev.py` reuses the original **two S49-issued first Actions** and the unmodified `0.60 s` nominal movement duration specified in `execution.py`. It reads only producer-local `node_speed_attr_boundary_dev.json` captured by the existing original Mineflayer bridge, and replays the prior entire Paper/S16/source reviewer.

For each independent World it requires:

1. The existing reviewer has already validated real Paper seven-positive-tick and S16 source lineage.
2. An exactly-one `FIRST_ORIGINAL_SET` and `FIRST_ORIGINAL_CLEAR`, same session/action as the Paper source, ordered Node monotonic timestamps and contiguous local `ACTIVE_PHYSICS` ordinals.
3. Native physics tick counts agree with the existing speed-attribute boundary reviewer.
4. No unexpected second issuer, native reader, P1/M0 posting or synthesized joint clock.

It then **observationally**, rather than by overriding Action timing, compares the two Node SET→CLEAR local hold windows (difference <= 50 ms), exact Node active physicsTick counts, exact positive-attribute tick counts, and exact total Paper gait callback counts.

The main classification is either `P1_FIRST_ACTION_OBSERVED_NODE_HOLD_AND_TICKS_MATCH_DEV_ONLY` or `P1_FIRST_ACTION_NODE_HOLD_MATCH_NOT_ESTABLISHED_DEV_ONLY`; mismatch is useful **negative DEV data**, not a reason to invent physical tick matching or a fatigue response. Malformed/foreign-source input remains fail-closed.

## Nonclaims and limitations

- The unchanged original S49 duration is **time-controlled**, not physically tick-count-controlled. The new reviewer does not add a clock-to-Action feedback loop.
- The 50 ms criterion is a **DEV tolerancing choice**, not a calibrated physiological threshold.
- Node `monotonic_ms` is sampled locally and is not aligned to Paper World tick boundaries. Equal counts are not cross-process phase alignment.
- Raw speed sample 1 can include pre-modifier integration; ordinal 2–7 remains a descriptive comparison.
- Distinct synthetic F preloads (`CARRY`, `WAIT_ASSUMED`) are not an observed recovery in the same Self. Never infer same-Self recovery, R qualified WAIT, scientific causality, or physical production L0 power admission.

## Run/review procedure

Workflow: `.github/workflows/self-p1-native-hold-pair-dev.yml` on branch `self/dev-p1-node-hold-audit-20261028`.

Pinned Python 3.12 / Node 22 / Java 21, original Mineflayer 4.39.0, Paper 1.21.8 build 60 with exact hash, and two disposable Worlds. Prior 7-Paper-boost reviewer and new native hold reviewer run sequentially. Both outcome reports and raw traces are stored as a GitHub Actions artifact even on failure.

This is a new measurement of an unresolved confound. Do not modify main or Draft #545/#634. Preserve unsuccessful attempts and their raw evidence. Do not report real-World PASS before verifying the exact workflow execution and sources.

## Exact two-real-World result (2026-10-28 JST)

World-tested code HEAD: `0d90873db025372d8ee249411256fe067554db27`.
[GitHub Actions #40529005012](https://github.com/rinsakamo/relay-self/actions/runs/40529005012): **SUCCESS** on the full original two-World DEV job, including new independent read-only original Node hold review.

- Python 3.12 focused **239 PASS** (72 + 72 + 72 + 23 reported, no failures); Ruff **All checks passed**; Node 22 **3 PASS**; Java 21 **BUILD SUCCESS**.
- Both independent Worlds completed the original S49 **two S15/S16 native Actions**, original cleanup, source-replayed Paper P1 and source-bound DEV M0 ownership; no additional native readers or issuers.
- Exactly seven positive Paper modifier callbacks and 13 full Paper gait callbacks per first original Action.
- Both original first Action Node-local SET→CLEAR elapsed windows measured **601 ms**.
- Both Node first Action traces contained **12 active physicsTicks**. The physical speed attribute was visibly DASH-positive in **8 Node active physicsTick callbacks per World**. The latter is source-visible attribute state, not proof of a synchronized Paper physics effect.
- Original first S16 displacement delta, WAIT_ASSUMED minus CARRY: **+0.2601302369458587 m**.
- Cross-process Paper/Node effect phase, exact original native control duration in Paper World ticks, true same-Self recovery, and physiological P1 causality remain unverified.
- **Classification:** `P1_FIRST_ACTION_OBSERVED_NODE_HOLD_AND_TICKS_MATCH_DEV_ONLY`.

| Audited item | CARRY | WAIT_ASSUMED |
| --- | ---: | ---: |
| Original Node SET→CLEAR, ms | 601 | 601 |
| Original Node active physicsTick callbacks | 12 | 12 |
| Node active callbacks with visible DASH attribute | 8 | 8 |
| Original Paper P1 gait callbacks | 13 | 13 |
| Original Paper positive bonus callbacks | 7 | 7 |
| Original first S16 distance difference from CARRY, m | baseline | +0.2601302369458587 |

Evidence artifact: `p1-node-hold-audit-pair-40529005012-1`, artifact ID **12744884048**, uploaded SHA256 `11ff9a557bb5517f3b59d2b1c4a0db5dabcde88b12302931796de80d6532d440`.

Important comparative result from a separate, already-verified follow-on branch: [Paper producer index-15 owner-held run #40511721549](https://github.com/rinsakamo/relay-self/actions/runs/40511721549) matched the original S15 Paper hold target but recorded **16 versus 15 Node active physicsTicks** and a **negative −0.07868426623641867 m** whole-S16 distance delta. This is evidence against treating either individual positive motor delta as a robust isolated fatigue effect.

**Next DEV action:** explicitly control original S15 hold using producer-local Node physics tick observation, keep the original single SET/CLEAR owner and bounded cleanup, and independently check the actual resulting Node and Paper intervals. Observational matching cannot be presented as owner-enforced tick matching.

DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN. No original production P1 state update, R WAIT qualification, physical L0 DASH grant, SCIENCE, main or Draft PR merge.

## Independent second real-World repeat at the *same* exact test HEAD

A separate registered workflow trigger also ran the **same** exact SHA `0d90873db025372d8ee249411256fe067554db27`; this is an independent second two-World draw, not a replay of artifact bytes. [GitHub Actions #40529004783](https://github.com/rinsakamo/relay-self/actions/runs/40529004783): **SUCCESS**, including the genuine negative-readback classification below. Both original S49 World pairs completed all native and source review stages.

| Audited item | CARRY | WAIT_ASSUMED |
| --- | ---: | ---: |
| Original Node SET→CLEAR, ms | 602 | 601 |
| Original Node active physicsTick callbacks | **11** | **12** |
| Node active callbacks with visible DASH attribute | **8** | **6** |
| Original Paper P1 gait callbacks | 13 | 13 |
| Original Paper positive modifier callbacks | 7 | 7 |
| First S16 distance difference from CARRY, m | baseline | +0.2831018145320452 |

**Independent reviewer classification:** `P1_FIRST_ACTION_NODE_HOLD_MATCH_NOT_ESTABLISHED_DEV_ONLY`, not a false exact-match PASS. The measured elapsed durations differ by only 1 ms and both Paper clocks yielded 13 first Action gait callbacks, but Node active tick counts and visible DASH attribute tick counts differ. Near-equal 0.60-second durations are therefore insufficient to force equal native physics callback counts or aligned speed attribution.

Evidence artifact `p1-node-hold-audit-pair-40529004783-1`, ID **12743884989**, SHA256 `153f6c510b57f87c4245eae2d7eb90535992fd9280c00e44542772c1d474d746`.

Both runs are **DEV tool/job successes**, while their scientific/engineering *hypothesis outcomes differ*. The second is explicitly **not** a source failure and must be preserved. The registered prior seven-boost workflow branch filter has been restored to its old branch; only the new native-hold workflow watches this isolated development branch for future pushes.

**Combined takeaway:** one independent pair had 601/601 ms, 12/12 Node active ticks, 8/8 DASH attribute-visible ticks; the next had 602/601 ms, 11/12 Node active ticks, 8/6 DASH-visible ticks. Both had 7/7 Paper positive ticks. Neither provides synchronized Node/Paper phase or owner-enforced native tick-count matching. Next native-physicsTick-controlled S15 hold is a new engineering stage, not an already satisfied qualification.

DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
