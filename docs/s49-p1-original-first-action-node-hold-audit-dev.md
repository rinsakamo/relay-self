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
