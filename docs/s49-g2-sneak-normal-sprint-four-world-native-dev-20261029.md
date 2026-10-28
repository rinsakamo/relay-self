# RelaySelf G2 — S49-owned crouch / ordinary / sprint applied gait in four real Paper Worlds

**Date:** 2026-10-29 JST. **DEV_ONLY / G2_THREE_PHYSICAL_MODE_CANDIDATES_OBSERVED / SOURCE_BOUND_NOT_PACKET_ATTESTED / NATIVE_FULL_TICK_GAIT_UNVERIFIED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**

## Exact physical source, run, artifacts

- Branch `self/dev-l1-t2-action-boundary-20261028`.
- **Frozen successful four-World physical code HEAD:** `e33085d112cecbb2f8ae04034d4a1ab00259980a`.
- [GitHub Actions physical run #40718522235](https://github.com/rinsakamo/relay-self/actions/runs/40718522235): **SUCCESS**, 4 independent disposable Paper 1.21.8 Worlds, same original session reader and S49 Action issuer per World.
- [Artifact #12828124024](https://github.com/rinsakamo/relay-self/actions/runs/40718522235/artifacts/12828124024): 4 derived `goal_report.json`, `g1_applied_gait_observation_dev.json`, `l1_t2_ledger_dev.json`, Paper server logs, producer stdout. Downloaded artifact ZIP SHA256 `318486b4e3a05efc0cad7ac7eb83bf57067f2f4cd12091a0b2a5adf43b2e6e59`; the complete raw Mineflayer stdout or complete World bytes are **not** archived.
- Same code HEAD [focused CI #40718521845](https://github.com/rinsakamo/relay-self/actions/runs/40718521845): **SUCCESS** Python 3.12 focused **62 PASS**, Node 22 strict protocol tests **24 PASS**, Ruff / Python & Node syntax PASS. No FULL.
- Server official Paper 1.21.8 build60 SHA256 `8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e`; existing pinned T1w Paper plugin source `2672d0a1fe15584d16c2426540c528410bbb8c27` (no plugin Java changes).
- Default OFF. **New S49 G2 sneak:** exact `MOVE_FORWARD_SNEAK_DEV` Action binding, encoded `set_forward_sneak_dev(forward=true,sneak=true)`. Python wire protocol, existing process session, strict Node parser, original Node bot effect handler all check explicit `S49_GOAL_G2_SNEAK_DEV_ONLY=1` at their respective boundaries; no generic arbitrary controls. S49 before/after native Action and T2 only-once accounting are preserved. First **three** original Actions crouch, subsequent Action(s) ordinary. No extra reader, issuer, P1 gauge, M0 posting.

## Physical result: four Worlds

| Property | WORLD1 wall+detour | WORLD2 midroute stone+refresh | WORLD3 initial sprint | WORLD4 three crouches then normal |
|---|---:|---:|---:|---:|
| Stage | L1_DETOUR_ORIGINAL_GOAL_REACHED | L1_DETOUR_ORIGINAL_GOAL_REACHED | GOAL_REACHED | GOAL_REACHED |
| Original Action→T2 receipts | 11 | 13 | 4 | 6 |
| Consecutive T2 WorldTick ledger rows | 164 | 195 | 46 | 66 |
| Stable ordinary forward candidate intervals | 29 | 35 | 11 | 10 |
| Stable sprint forward candidate intervals | 0 | 0 | **1** | 0 |
| Stable crouch/sneak forward candidate intervals | 0 | 0 | 0 | **6** |
| Stable physical idle candidate intervals | 68 | 81 | 4 | 4 |
| Blocked/stalled control undecided | 9 | 7 | 5 | 6 |
| Original T2 owner.failed | false | false | false | false |

WORLD3's first action `set_forward_sprint_dev` APPLIED and S16 OUTCOME, final Goal error **0.2500456183042612 m**, 4 receipts. Its one stable physical sprint candidate saw Paper speed base ~0.10, value ~0.13, sprint true and a native forward+sprint control state. It is an **attribute observation and compatible one-tick motion candidate**, not an exact RUN/DASH rate.

WORLD4's **first three** `set_forward_sneak_dev` Action dispatches were all APPLIED, all S16 OUTCOME, without independent issuer. It then reverted to ordinary forward and reached original L2 Goal, **final error 0.19207331756680057 m**. G1 observed **6 stable crouch-forward** intervals with actual Paper `sneaking=true` and original Node `forward=true,sneak=true`; also **10 stable ordinary-forward** intervals with `sneaking=false,sprinting=false`. The body state transitioned, not just an action request. Same original T2 admitted 66 consecutive WorldTicks, no double P1 and no additional M0 DASH charges.

## Source-derived measured displacement (candidate subset only)

From the archived `g1_applied_gait_observation_dev.json`; `dxz_m` is horizontal endpoint chord for one consecutive Paper WorldTick (not integrated actual travel, not an independently attested client physics step, not calibrated physiological gait):

| World / observed category | Candidate count | Mean chord (block / Paper WorldTick) | Median |
|---|---:|---:|---:|
| WORLD4 stable crouch-forward | 6 | 0.074449 | 0.063117 |
| WORLD4 stable ordinary-forward | 10 | 0.160598 | 0.169397 |
| WORLD3 stable ordinary-forward | 11 | 0.165555 | 0.183805 |
| WORLD3 stable sprint-forward | 1 | 0.220354 | 0.220354 |
| WORLD1 stable ordinary-forward | 29 | 0.171003 | 0.180723 |
| WORLD2 stable ordinary-forward | 35 | 0.161377 | 0.180723 |

For WORLD4 filtered samples, crouch-forward mean chord is ~**46%** of ordinary-forward mean within that World; this is **not** a proven physical gait speed ratio. Each group has different acceleration/trajectory and time-in-mode sampling. Stable crouch Paper speed base/value remained ~0.10 with **zero speed modifiers**: the observed slower locomotion comes from crouch physics rather than a different server movement-speed attribute. A naive attribute-only WALK classifier would miss it. All movement/no-movement undecided spans remain undecided and do not become unearned WAIT recovery.

## Failed-first run, retained and not rewritten

[Physical attempt #40717725065](https://github.com/rinsakamo/relay-self/actions/runs/40717725065), tested HEAD `6c819054a46c157a82a0a79cd1d1805643b077cc`: WORLD1/2/3 PASS, WORLD4 **FAIL before first sneaking movement**. Native S49→T2 S16 refusal recorded `NATIVE_TERMINAL_NOT_SAFE_FOR_T2` with consequence FAILED, terminal UNKNOWN, no CLEAR ACK, 0 qualified receipts, no P1 credit; no second Action issued. The new Python effect encoding and Node handler were present, but the strict Node protocol `parseCommand` EFFECTS whitelist/shape had not been updated, so it could not accept the new wire command. The fix adds **only** the exact gated Node parser branch and explicit node negatives; it does not relax S16 or T2 source admissibility. The later successful run confirms the full physical path.

An earlier focused error was a Ruff import block formatting issue in the new test, fixed before final tested HEAD. Failures are retained, not erased by later success.

## Interpretation and next G2/G3 boundary

- Crouch/ordinary/sprint are **three physical-mode candidates**, not the four intended RelaySelf `WALK/JOG/RUN/DASH` gait modes. In particular, ordinary forward cannot be labeled JOG or RUN solely from `dxz_m`, and sprint is not evidence of the separate +50% **DASH** modifier.
- `gait_dev` and `applied_controls_dev` come from original Paper/Mineflayer callbacks, but a complete client physics step → transmitted packet → Paper accepted movement → precise WorldTick causal identity remains **unverified**. G1 recorder is a bounded read-only complement to the existing T2 single P1/M0 owner.
- WORLD4 measured six crouch samples. Next G2 should first repeat stable sprint, observe controlled mode-switch timing and applied speed attribute, separately observe actual configured DASH force/attribute if available, and preserve bad/edge timestamps. Only after authentic applied modes and atomic DASH extra M0 accounting may G3 integrate `advance_gait_dev`.
- Retain default-OFF, disposable DEV, source-derived hashes, no main/protected Draft history changes. No qualification or scientific run claimed.

This report is **additional** G2 hardware-body characterization; it does not automatically merge code into Draft PR #545 / #634 or replace the original L1 obstacle/interrupt evidence.
