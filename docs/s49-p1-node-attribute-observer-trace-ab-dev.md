# P1/DASH original S49 — Node attribute observer trace ON/OFF A/B DEV

**DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**

Prior exact ancestor: `92dbc7ec5bcd27f9f008f52b8d92cc983f5564ba`. Prior independently observed two-World results included Node active callback count and DASH attribute visibility mismatches, even when original S49 SET→CLEAR elapsed times were close.

## Controlled experiment (read before invoking workflow)

Question: does the producer-local **S49_SPEED_ATTR_BOUNDARY_DEV_ONLY** *observer* materially perturb the first original S49 DASH motor run? This experiment does **not** disable the Paper speed modifier or the Node *speed attribute projection*. The latter is `S49_SPEED_ATTR_SYNC_DEV_ONLY=1` in all four Worlds and is functional code required for projected movement speed, **not** file trace synchronization.

- Fresh independent Worlds (four): `ON_CARRY`, `OFF_CARRY`, `OFF_WAIT_ASSUMED`, `ON_WAIT_ASSUMED`. The order intentionally sandwiches the two OFF runs between ON runs, but is **not randomized** and does not provide statistical attribution.
- Each World uses exact original S49 S15/S16 two native Actions, the same 0.60-second first Action hold command, same pinned Paper 1.21.8 plugin, same Node 22 / Mineflayer 4.39.0, and exactly 7 positive Paper speed modifier callback ticks.
- CARRY (synthetic model F 0.6177122410202606) and WAIT_ASSUMED (synthetic model F 0.21616083122103735) are controlled separately. Neither represents actual physical recovery.
- Both groups pass `--speed-attr-boundary-dev` to retain established explicit S49 preflight gates and `S49_SPEED_ATTR_BOUNDARY_DEV_ONLY=1` from the outer workflow. Only the OFF group explicitly sets `S49_P1_TRACE_AB_OFF_DEV_ONLY=1`, causing the wrapper to mask the *Node observer* environment to `S49_SPEED_ATTR_BOUNDARY_DEV_ONLY=0` **only around original qualify()**. The speed mapper opt-in stays `1`. No bridge, Paper plugin, S15/S16 or execution engine code is changed.
- ON writes a single producer-local `node_speed_attr_boundary_dev.json` at original native CLEAR. OFF must not create that file and does not call the Node observer reviewer. Both continue original Paper server logs, original S49 typed Action evidence, and independent S16 displacement verification.

## Source-verified metrics and negative controls

Each trial must produce two original S49 native Action OUTCOMEs, full P1 Paper model replay, seven contiguous Paper positive speed modifier ticks, genuine `OWNER_RELEASE`, typed S15 ACK and S16 movement, original DEV M0 owner only, unchanged actor and session.

Primary per-model A/B metrics: first S16 measured XZ distance OFF minus ON; Paper positive-ordinal mean sampled velocity OFF minus ON; Paper positive modifier tick count and P1 gait callback count. The reporter records all four sessions and World identities separately. OFF **cannot** report native physics callback counts or DASH-visible Node callback counts; they are `null`, not zero or fabricated. ON Node trace is independently checked and includes per-first-Action active physics callbacks and positive-speed-attribute callbacks.

A valid negative, zero, or positive OFF-minus-ON movement difference is **DATA**, not a FAIL. Wrong P1 case/actor/session, missing original owner receipts, mismatched ON/OFF trace presence, unexpected source, or fabricated Node OFF tick evidence fail closed. A measured discrepancy by itself **cannot** establish trace observer causality because each run is a distinct World and Paper/Node phases are unsynchronized. In particular, this is NOT a direct A/B test of the independent T1n `node_timing.jsonl` synchronous `writeSync()` path. That path is not used by this specific original S49 bridge DEV configuration.

## DEV reproducibility

Run the isolated workflow `.github/workflows/self-p1-attr-trace-ab-dev.yml` on `self/dev-p1-attr-trace-ab-20261028`. Execute Python 3.12 focused tests and Ruff, Node 22 syntax/regression, Java 21 plugin build and pinned Paper SHA checks before launching any real World. Keep raw logs/reports on every failure via always-upload GitHub artifact. Owner grants and R/SCIENCE experiments are NOT being invoked; this is an expressly isolated DEV-only disposable World run.

Original main and Draft PR #545/#634 are not modified. Report any REAL status and measurements only from a completed exact SHA-run and uploaded source artifact.

## Exact four real-World outcome — 2026-10-28 (JST)

**Exact World-tested source HEAD:** `5a946a6a226d3dbddb81d2fc44413c598550737d`.
[GitHub Actions #40617669117](https://github.com/rinsakamo/relay-self/actions/runs/40617669117): **SUCCESS**. Focused Python 3.12 **261 PASS** with Ruff "All checks passed", Node 22 **3 PASS**, Java 21 `BUILD SUCCESS`. Pinned Paper 1.21.8 build 60 SHA and Mineflayer 4.39.0; each of four independent original S49 Worlds completed two genuine native Action OUTCOMEs and source verification.

All four had exact seven contiguous Paper positive bonus ticks, 13 total first Action Paper gait callbacks, the original OWNER_RELEASE and unboosted second S16 control. In all arms `S49_SPEED_ATTR_SYNC_DEV_ONLY=1`, and synthetic P1 model outputs were held at the same respective inputs.

| Same F arm | Node trace | First original S16 XZ distance (m) | Paper seven-positive mean sampled speed (m/s) | Node first active physics ticks | Node positive-attribute-visible ticks |
| --- | --- | ---: | ---: | ---: | ---: |
| CARRY | ON | 3.6473987246 | 6.2673692468 | 12 | 6 |
| CARRY | OFF | 3.8425873335 | 6.5674695122 | NOT OBSERVED | NOT OBSERVED |
| WAIT_ASSUMED | ON | 3.8452692791 | 6.6391648414 | 12 | 6 |
| WAIT_ASSUMED | OFF | 4.1027175663 | 7.0294249116 | NOT OBSERVED | NOT OBSERVED |

**Within-model OFF minus ON:**
- CARRY: first S16 +0.1951886088651542m; Paper mean +0.30010026540531864m/s.
- WAIT_ASSUMED: first S16 +0.2574482871531565m; Paper mean +0.390260070222209m/s.

ON produced one real bounded Node attribute trace per World. OFF produced **none** (verified by the original source reviewer and explicit producer source path checks). The OFF runs did not enable Node physics-clock instrumentation; their tick counts remain UNKNOWN. No extra native issuer/reader; original S49 S16 and Paper P1 replay both intact. Zero production P1 updates and zero extra owner ledger postings.

**Interpretation and limitations:** both OFF motor-distance comparisons were positive in this single four-World sequence, consistent with possible observer/timing perturbation. However they were not randomized, paired within a shared original World, or cross-process phase-matched. Earlier ON-only DEV runs with comparable 0.60s holds showed movement-distance variation even with the same observer setting. Accordingly, **trace-caused distance gain is NOT ESTABLISHED**, neither is precise P1 motor causal attribution. The observer's per-tick in-memory work, its synchronous `writeFileSync()` at CLEAR, the subsequent ACK/S16 receipt timing, and independent Node/Paper phase shifts have not been separated. Crucially the earlier T1n `node_timing.jsonl` per-tick `writeSync()` stall is a **different producer/path** and is not an active tested confound here.

The next targeted DEV hypothesis should split the Node observer into (1) no sample, (2) in-memory sample but no synchronous file write at CLEAR, and (3) sample plus write at CLEAR, while keeping the exact same speed projection. Add Node-local timing for CLEAR→ACK→S16 and use cross-balanced repeated real Worlds, keeping every OFF Node tick as UNKNOWN. Do not report causal confirmation from four independent Worlds.

**Raw evidence artifact:** `p1-attr-trace-ab-four-worlds-40617669117-1`, GitHub artifact ID **12786455133**, ZIP SHA256 `72284298a80983fcad384aec3e971836687a0e3b2dae467a48953b1fe6e2bc59`.

**Final classification:** `DEV_WORLD_OBSERVED / DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`. Original main and Draft PR #545/#634 were not modified.
