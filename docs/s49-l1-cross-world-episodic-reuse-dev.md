# RelaySelf S49 DEV — L1 episodic route reuse across genuine Minecraft Worlds

**Date:** 2026-10-28 JST  
**Classification:** DEV_WORLD_OBSERVED / DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN

## Question

Can a successful detour around a physical Minecraft obstruction be retained as a small episode, then *selected from the earlier source* for a **different independent World**, rather than having a DEV operator specify the same waypoint coordinates again? Can this preserve the original target, original S49 single physical Action owner, fresh XZ observation and safe fail-closed semantics?

## Design

This branch adds a typed bounded `L1RouteEpisodeDev` with source session, original goal ID, genuine first-World blocked Action and terminal S16 sequence, original goal offset, the three previously successful *relative* waypoint offsets, source successful native Action count and final native original-goal error/tolerance.

The first successful route is not trusted merely because a JSON file says PASS: `s49_l1_experience_export_dev` first calls the independent **two real-World reviewer** on WALL_STOP and DETOUR, verifies physical S16 source actions and real stage arrivals, and only then extracts a normalized episode. The memory artifact records the raw source report SHA256. The recall path requires that raw source file and rejects a modified source report/mismatching digest.

Before recall the next independent World must independently demonstrate a fresh original S49 physical blocked S16: `UNDETERMINED` consequence and original ActionSupervisor `UNKNOWN` after actual control-clear. The original target/offset and source-supported reason must match the stored episode; the prior World session ID must differ. Only then are the earlier **relative** waypoint XZ targets translated to the new World origin, with a new versioned L1-style plan and new Action IDs. The old UNKNOWN Action ID is never retried. All three stage L0 controllers rely on genuine current native probes, repeated original S15 LOOK+MOVE and S16 OUTCOME feedback, with settling WAIT_VERIFY→REACHED.

**Bounded domain:** initial original L2 target must be +4m in the +Z direction, obstruction is the same fixed disposable three-block-wide stone wall at +2m; a single known successful three-stage template is eligible. Novel wall shapes, changed target distances, session/provenance failures and forged episode schema fail closed. This is **successful experience replay / episodic pattern reuse**, *not* automatic path discovery, generalized L1 training, obstacle sensing, a live L2 model, or an autonomous L2 replan. The supplied first-world route was explicit. The memory is a DEV JSON artifact persisted in the run's archive; not yet integrated into long-lived SelfWorld storage or an online L1 retrieval index.

## Tested implementation

- `src/relay_self/goal_experience_dev.py`: typed episode, source geometry constraints, exact new-goal matching and positional translation into independently bound `L1DetourPlanDev`.
- `adapters/mineflayer/s49_l1_experience_export_dev.py`: first-World source audit, per-episode original native SHA256 retention, safe schema-bound memory export and reload.
- `adapters/mineflayer/s49_goal_loop_real_dev.py`: opt-in L1 episode selection only *after* the new original native wall UNKNOWN terminal, with original parent L2 goal restoration and event source summary.
- `adapters/mineflayer/s49_l1_experience_transfer_review_dev.py`: independent three-World source reviewer, checks all recall offsets, new session provenance, new Action IDs, S15 LOOK receipts, genuine S16 stage outcomes and final XZ error.
- `tests/test_s49_l1_episodic_reuse_dev.py`: bounded episode and reused waypoint match, negative controls for foreign sessions, changed goals, fake motor terminal or reason, changed memory and missing raw sources.
- `.github/workflows/self-l1-episodic-reuse-dev.yml`: isolated Python3.12 focused/Ruff/Node22, three official Minecraft1.21.8 vanilla/Java21 independent Worlds and original Mineflayer, source preservation even on failure.

All are **DEV-only**: env `S49_L1_EPISODIC_REUSE_DEV_ONLY=1` in addition to prior S49 real-server/goal/turn/wall/waypoint gates. No changes to production default, main, or Draft PR #545/#634, protected historical evidence, QUAL or SCIENCE.

## Exact verified real-world result — 2026-10-28

[GitHub Actions #40675752757](https://github.com/rinsakamo/relay-self/actions/runs/40675752757) **completed / SUCCESS**, tested exact code HEAD `9e36f38cb3d4ac7157492c1e2ac95e5be1837412`.

- Python3.12 focused **39 PASS**, Ruff and Node22 syntax PASS.
- Real official Minecraft 1.21.8, Java21, original Mineflayer, exactly three independent disposable World sessions. Node/server exits 0, original S49 supervisor and native S15/S16 retained.
- WALL_STOP: `8c2103aa-ccc7-4789-8f5c-88f5c57e5df1`, real blocked S16 UNKNOWN with no added movement.
- DETOUR source: `e2970da2-1284-4c42-ba0f-201ad64eb70e`, original explicit L1 three-stage route, *8* original physical native Action OUTCOMEs.
- TRANSFER: `99f2748c-b74b-45cd-b567-2ad0e7e06cd0`, fresh real blocked S16 UNKNOWN, previous source-episode selected, *8* new original physical Action OUTCOMEs, all three stage arrivals confirmed.

Original source report SHA256 preserved as `ee2fcd4644f4c173f2c173ec0ad5a4b0a08aa8f4bf83d71567838487d580d367`; source report retained alongside memory artifact in one workflow.

| Transferred World stage | Stored relative XZ waypoint | Real measured arrival error |
|---|---|---:|
| Lateral-before-wall | (+2.5,+1.1)m | 0.14435981193749062m |
| Past-wall | (+2.5,+3.8)m | 0.2868037560204165m |
| Original destination | (0,+4.0)m | **0.31676729966068146m** |

The final original parent Goal tolerance in the transfer World was **0.3454593147961198m**; the actual Euclidean observed XZ error was **0.31676729966068146m**, within tolerance. The L0 final stop was validated with native WAIT_VERIFY and REACHED, not a scalar summed movement distance. Source and transfer use independent physical sessions, original owner and new Action IDs. No extra action issuers or native packet readers.

Audit verdict: `S49_L1_CROSS_WORLD_EPISODIC_REUSE_DEV_PASS`, `S49_L1_CROSS_WORLD_EPISODIC_WAYPOINT_REUSE_DEV`.

Raw [three-World evidence / memory / server logs artifact](https://github.com/rinsakamo/relay-self/actions/runs/40675752757/artifacts/12810276654), artifact ID **12810276654**, original ZIP SHA256 **bf60ed2ec2fb321360672ac32b09605843e961910930ab0f6f9c1b24b446ff1c**. Earlier failed preflight run #40675646617 was Ruff import ordering only, before starting any Minecraft World; an isolated source-order correction and exact HEAD rerun passed.

### Limits and priority

This is evidence of **episodic reusable route selection given a matching native failure**. It is not yet multiple-pattern L1 policy learning, body-aware obstacle sensing, route generation from SelfWorld, robust novel environments, online long-term memory or an integrated motor in-flight hazard interrupt during every waypoint step.

Next priority: integrate the current episode into SelfWorld v0 with type-tagged storage and retrieval on real failure events, compare multiple successful/failed routes, and test mismatching wall geometries as explicit negative physical controls. Thereafter add a live in-flight L0 interrupt during a selected waypoint, preserving the original S15 CLEAR ACK and Action UNKNOWN semantics. Keep DEV-first and no forced QUAL/SCIENCE.
