# L MP11 — live source prefixes verified in one real Paper World (DEV)

Date: 2026-11-01. Draft PR #673, stacked on #671 → #668 → #666. Real execution HEAD bf662571f454d5c9c69bf3de51eba2f4dd600163. Existing S49 is still the ONLY Action issuer; no WB/M/G4/main changes.

## Physical DEV — PASS

Real physical GitHub Actions run: https://github.com/rinsakamo/relay-self/actions/runs/41303509890

One Paper Minecraft 1.21.8 World, one subject UUID dcae346d-e66f-331a-b459-a5a5370e9738, World UUID db9070d5-210e-4a76-9e4e-d7807e3d21de, native session 5180bbe7-ec7b-4eb8-9151-2ce43234efaa. Successful first run (run_attempt=1); no automatic retry. Original Java/Paper exit=0 and Node/Mineflayer exit=0, normal cleanup.

Original S49 Action MOVEs:
- s49-native-move-32: 0.7342911432182311m, typed S16 seq42, Paper WAIT ticks 299–306
- s49-native-move-59: 0.6269065734210615m, typed S16 seq68, Paper WAIT ticks 498–505
- s49-native-move-89: 0.6269065734210613m, typed S16 seq98, Paper WAIT ticks 698–705

Each original S49 Action had original S15 clear, S16 OUTCOME, one complete S50 eight-WAIT and input window. Three original windows: 24 WAIT records, 21 fixed-before-next-callback prediction/score pairs. The original untrained slope0.65 has NO verified gain over cheap zero-next-displacement rule.

## Live source witness reconciled against full postrun original

Original Paper final log SHA256: 535831c4c2202e1991daf25f82e4ec9f2adc3675fada2e622fbe1ab84285650d
Original W3 Node stdout SHA256: 7ab2e35451f191f2afc795e5d41e93769a5ddf8a35e26107af31fc1c5638be2b; original W3 receipt status COMPLETE_NODE_STDOUT.

At each closed original Action while BOTH Paper + Node processes were still running, the original S49 callback sampled full-line Paper bytes and emitted read-only L context from ONLY already completed prior Actions. Independent postrun comparison of each captured prefix length/SHA against the exact bytes of the final original Paper log returned 3/3 MATCH.

| Action | First/last WAIT tick | Paper prefix bytes | SHA256 |
| --- | --- | ---: | --- |
| s49-native-move-32 | 299–306 | 164656 | feb0d21b462372a76f6cc4b2b0a3b36a84817b8d22d168805fe18896553b5bea |
| s49-native-move-59 | 498–505 | 412267 | f83396c5145ff418d2fd6e49173b5e1a485c13865a8c086b497fad00709a014f |
| s49-native-move-89 | 698–705 | 607296 | aae20c92d03c6096b8172ab520300535c5a3e76977a40afeb5938b42da163e64 |

Postrun independent readback classification: L_MP11_LIVE_PREFIX_POSTRUN_SOURCE_RECONCILED_DEV_ONLY. The new L live source records retain an explicit PROVISIONAL/unsealed status: prefix SHA comparison authenticates the bytes relative to the final original, not an independent wallclock trace of the earlier read or the exact effective S15-clear Paper tick.

GitHub source-only exact-executable-HEAD preflight: Python 3.12 139 PASS, Ruff, compileall, repository contracts PASS, Maven Paper plugin BUILD SUCCESS. Separate focused offline CI: 156 PASS. Original G2/G3 regression CI PASS.

Stored original artifact ID 13082395550, name l-mp11-live-prior-source-one-world-three-action-41303509890-1; includes Java/Paper stdout, original W3 Node stdout, W3 receipt, active config, report and independent G3/L original readbacks. Source-original artifact is NOT altered by this document.

## Scope and next gate

Confirmed: a **real running World** yielded closed Action/S16/WAIT8 experience that the original host could snapshot BEFORE the next native S49 Action. This is an observation/interface milestone. This World still executed three human-staged same-GRASS, same-MOVE_BACKWARD stimuli under pre-existing L0. Real L2/Gemma calls=0; L2-selected trials=0; controlled physical variation=0; retained learning/Habit/L0 promotion=0. Goal UNDETERMINED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.

Next: bounded actual Gemma OPEN after one live completed prefix, prospective frozen model hypothesis/test, safe distinct physical condition through the existing owner and a future heldout comparison. Never count a hypothetical experiment or expensive single-shot model superiority as automatically learned intelligence. A cheap fixed L0 remains the preferred control on simple familiar tasks.
