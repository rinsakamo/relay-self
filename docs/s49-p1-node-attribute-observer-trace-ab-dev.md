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
