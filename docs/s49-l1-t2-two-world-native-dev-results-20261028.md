# RelaySelf — L1 local-grid ↔ original S49 ↔ T2 M0/P1: two Paper Worlds

**2026-10-28 JST. DEV_ONLY / SAME_WORLD_NATIVE_DEV_VERIFIED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN / EXACT_NATIVE_GAIT_UNVERIFIED.**

## Frozen tested source and original run

- Exact successfully tested HEAD: `047b45bf6994b7991ee5118983824ad780d6107d` on isolated `self/dev-l1-t2-action-boundary-20261028`.
- [GitHub Actions physical run #40705499396](https://github.com/rinsakamo/relay-self/actions/runs/40705499396): **completed SUCCESS**, 2 independent disposable Paper 1.21.8 Worlds (not a qualified V science trial).
- [Archived artifact #12823608237](https://github.com/rinsakamo/relay-self/actions/runs/40705499396/artifacts/12823608237), retention 7 days: both `goal_report.json`, `minecraft_server.log`, derived `l1_t2_ledger_dev.json`, producer stdout. **The complete disposable Worlds and raw Mineflayer stdout bytes were not archived by this run.** The derived ledger is source-bound within the executing original session, not an independent physical packet recording.
- Server JAR SHA256: `8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e` (official Paper 1.21.8 build 60). Existing T1w plugin built from frozen `2672d0a1fe15584d16c2426540c528410bbb8c27` without modifying its source. No other Action issuer or native reader.
- Focused workflow `40705499584` SUCCESS on the same exact HEAD; Python 3.12, Ruff, syntax and negative controls. No FULL.

| Measured property | WORLD1 (unchanged) | WORLD2 (midroute stone) |
|---|---:|---:|
| Final parent L2 Goal error (tolerance 0.30m) | 0.060986272185244654m | 0.20876408371047944m |
| Original S49→T2 Action boundary receipts | 11 | 13 |
| Original T2 admitted consecutive ledger WorldTicks | 160 | 193 |
| Derived WAIT_DEV rows | 19 | 29 |
| Derived MOVE_OR_UNDETERMINED rows | 141 | 164 |
| L1 route refresh/replan records | 0 | 3 |
| T2 owner failed | false | false |
| Source-bound S16 refusal diagnostic | null | null |
| Node and Java exit code | 0 / 0 | 0 / 0 |

For WORLD2 the operator added a stone during the route and the **same Mineflayer native voxel cache** later observed it (`native_confirmed=true`). The L1 planner recomputed a detour and the original S49 supervisor completed the preserved L2 Goal. WORLD1 is the comparison without the extra stone. Both World derived ledgers were independently re-read by the workflow and checked for SHA256 digest, exact row count, strictly increasing source sequence, consecutive WorldTick index, and existing M0/P1 transition fields.

In both runs T1f `ADMITTED` Paper anchor preceded a **new source-current** L1 probe; the first original Action never relied on a pre-anchor L1 observation. Original S49 alone issues and closes every Action. Existing T2 alone posts symbolic M0 and virtual P1 with the original once-per-admitted-tick owner. No new full-tick gait mode or R-authenticated source was created, and the model's `MOVE_OR_UNDETERMINED` ticks are not guaranteed WALK, JOG, RUN or DASH. `WAIT_DEV` is S-owned, bounded post-clear inactivity, **not** R-qualified physical WAIT, not a science result.

M0 and P1 are engineering candidate quantities, not validated physiological performance. The current original default P1 profile is legacy (SHA `d23f1f595095adb1da0b3ce74a72803b85b68359dc94d2ee8b03fcd2078f68b0`), not the separately calibrated T1s or T1u/T1w exact gait proof. M0 still bills basal during WAIT.

## Failed-first source evidence retained

- [#40703852834](https://github.com/rinsakamo/relay-self/actions/runs/40703852834): the first real Paper run refused before Action because the first L1 probe seq2 preceded the admitted T2 Paper anchor seq3; corrected by new L1 observation after initial T2 source admission, not by relaxing the source-order guard.
- [#40704854862](https://github.com/rinsakamo/relay-self/actions/runs/40704854862): the paired first World refused an inconsistent original S16 terminal after 2 T2 ledger rows. It failed closed, with no second Action and no P1 credit invented. This result is not overwritten by the later successful run. A read-only original S16 refusal diagnostic was added and was null in both final World successes.
- Earlier Python negative test failures under pre-enabled workflow environment were corrected by explicit default-OFF test scopes. They did not run Minecraft before passing.

## Remaining work

1. Repeatability across varied seed and timing (first S16 boundary has a preserved negative run), and independent raw Node/Paper source preservation for later audit.
2. Explicit native-client physics step ↔ Paper accepted WorldTick correspondence for *actual* WALK/JOG/RUN/DASH mode changes and single-P1 accounting; do not infer gait from geometry or Action requests.
3. Formal adoption into Draft #545/#634 with user-controlled review, compatibility checks and normal fast-forward; no main or protected Draft updated by this DEV branch.
4. R qualification and V scientific evaluation require separate approval/evidence. This engineering run establishes an integrated **minimum DEV loop only**.

The exact tested HEAD is frozen as evidence; any later docs-only commit does not retroactively become World-tested.
