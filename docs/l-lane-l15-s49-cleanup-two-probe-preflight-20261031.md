# RelaySelf L15 — S49 original dispatch/cleanup and two-probe Goal preflight (2026-10-31 JST)

## Scope and exact baseline

Child of L14 exact documentation HEAD `ce95c7db5dfc6ec50e53b32304951bee3f0084d9`, isolated branch `integration/l15-s49-original-goal-capture-preflight-20261031`.

L14's original-source validator had a physical integration incompatibility: S49's existing S15 `MOVE_BACKWARD` dispatch uses the issued Action ID for `set_control`, but its control-release `clear_controls` uses `<Action-ID>-s15-clear`. L14 rejected any other `effect_result.action_id`, including this **legitimate cleanup**, which made a genuine S49 sequence structurally unadmittable. The old L14 synthetic source fixture used `clear_controls` with the principal ID; this is not how S49 issues normal real motion.

L15 changes **only the read-only L14 validator** to permit an exact S15 cleanup suffix, and only when a single applied `set_control` for the principal Action is followed by one applied `clear_controls` with the suffix, followed by the S16 after-Action native probe. The original sent stream must include exactly these two effects in that order; other Action IDs/effects, duplicate cleanup, unknown requests, rejected effects and wrong order fail closed. The two final Goal probes must match the **last two sent native observe request IDs** and remain sequential after S16 closure. The sent stream cannot establish actual server-side send/effect timing, so no physical nonintervention claim is inferred.

New `tests/test_l15_s49_original_goal_preflight.py` exercises S49's **source-shaped** received sequence (adapter start -> original pre-Action Present -> dispatch ACK -> cleanup ACK -> S16 after-Action probe -> two Goal probes) and matching outbound commands, plus rejection cases for misplaced/failed/foreign/repeated cleanup, extra outbound motor, changed terminal probe request and missing/changed sent cleanup. This is offline synthetic testing, **not** a copied real S49 source or independently verified Goal.

## Next prospective S-owned physical collection; not run in this increment

1. Use a newly authorized disposable DEV World and the **sole existing S49 Mineflayer session**. An S-owned instrument must capture S7 `native_bridge_received_original.jsonl` *before decoding* and `native_bridge_sent_original.jsonl` *before write/drain*, with exact S7 SHA/line index and an unaltered start `seq=0`. Do not post-hoc stringify decoded protocol frames, replay a consumed grant or use a second native reader/writer.
2. Declare the Goal target/tolerance/criterion and distinct Goal owner **before** the admitted native pre-Action Present; preserve original criterion bytes, original S16 terminal, original pre-Action Present and separate Goal-owner original, with independent owner review. A self-reported `created_before_seq` is insufficient for independently proven preregistration.
3. In one bounded single-Action interval (not an entire multi-Action S49 run), keep S49 dispatch -> S15 clear ACK -> S16 after-observation and terminal OUTCOME. While the sole S49 issuer still owns control and before any next Action, request and receive two new correlated post-terminal probes through that **same session**. Keep the raw source line order. Mixed/unstable positions remain `UNDETERMINED`, not negative learning reward.
4. Feed the exact original streams and independent admissions into L14's existing `audit_l14_native_goal_window`. Audit an observed target distance, not the final multi-Action World Goal. S/R/V must separately verify original provenance, no unobserved intervention, and physical/Goal authority. Only after separate qualification can existing L10 compare a later real cognitive epoch against memory-OFF and cheap equal-information baselines.

This branch **does not implement a physical S49 opt-in recorder or run a new Minecraft World**. It closes the blocking S15 cleanup compatibility and native probe correlation needed before that future single-owner capture. S49/S16/S7 physical owners, main, other lanes, L0/L1 policy, P1/M0, S10/S11 and historical archives remain untouched.

## Verification and status

- GitHub DEV workflow: `.github/workflows/l15-s49-original-goal-preflight-focused-dev.yml`; Python 3.12 pytest (L15/L14/L13/L12/L11/L10/L9), Ruff/compileall/contracts, and existing saved G4.13 producer/artifact SHA audit.
- The archived G4.13 11 physically executed S16 Actions / 182 Paper ticks still have **0** L14 Goal source windows, **0** independently admitted per-Action Goal labels and **0** qualified real L10 training pairs.
- Classification: `DEV_ONLY / L15_S49_CLEANUP_AND_PROBE_SOURCE_PREFLIGHT / NEW_WORLD_0 / QUALIFIED_REAL_GOAL_0 / L10_ADOPTIONS_0 / S10_S11_UPDATES_0 / ACTION_AUTHORITY_0 / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.


## Exact-head successful focused GitHub DEV

- **Exact successful source/test/workflow HEAD:** `ebf316054928e9db5f45d236c7c4a896544e35c1`.
- **[GitHub Actions #41144568698 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/41144568698)**: Python 3.12 **176 focused tests PASS** (72 + 72 + 32 dots, 100%); Ruff, compileall and repository contracts PASS. Existing original G4.13 producer run SHA and artifact #12952335343 readback PASS; archived 11 Action endpoints / 182 Paper ticks remain 0 independent Goal training pairs. **No new World started**.
- Historical preliminary [#41144485969 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/41144485969) predated the final sent-observe request-ID guard. [#41144555923 FAILED](https://github.com/rinsakamo/relay-self/actions/runs/41144555923) because the L15 synthetic positive fixture still used old probe request IDs after the guard was added. The fixture was corrected in the successful source HEAD above; the stricter validator was not relaxed. Both historical runs remain visible.
- The documentation-only commit following the source HEAD is not substituted for an exact-HEAD code test.
