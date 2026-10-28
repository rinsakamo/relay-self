# RelaySelf S49 DEV — in-flight L0 native hazard preemption during goal approach

**2026-10-28 / DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.

## What this test changes

Previous [goal interruption DEV](https://github.com/rinsakamo/relay-self/blob/self/dev-goal-l0-real-threat-interrupt-20261028/docs/s49-goal-real-threat-interruption-dev.md) only identified a zombie between separately completed Actions. This isolated branch tests original S49 goal-loop **during an already APPLIED forward input**.

The same S15 `execute_mineflayer_command` receive owner polls correlated native `probe` events during its bounded input window (DEV-only callback opt-in; regular path unchanged). A native probe must carry the current session, increasing sequence and genuine Mineflayer provenance; the same owner reads it, so no second reader or concurrent `receive()` is launched. L0 retains its goal and independently evaluates the real nearby entity list. An observed zombie inside the goal's danger threshold causes `INTERRUPT`, early `send_clear_controls`, actual `clear_controls APPLIED` receipt and subsequent native after-observation.

A prematurely ended physical movement **must not be relabeled S16 EXECUTED** just because some displacement occurred. For this DEV test, `WorldConsequence` is `FAILED` with the explicit reason `DEV_L0_INFLIGHT_NATIVE_THREAT_PREEMPTED` and the inherited S49 ActionSupervisor closes the issued Action as **UNKNOWN**, not OUTCOME. This expresses incomplete planned execution while retaining original S15 applied and clear receipts and after-position. It does NOT mean input never happened. No second Action, actual L1/L2 reconsideration or escape is claimed.

If the in-flight probe is delayed, its source wait is bounded by the remaining original input hold interval; timeout/fault follows error cleanup, not optimistic success. Missing clear ACK cannot qualify the test. The original default S15 path remains unchanged when `on_live_probe_dev=None` (or without `S49_L0_INFLIGHT_PREEMPT_DEV_ONLY=1`); the opt-in is only for original `MOVE_FORWARD` and a finite maximum 1.0s hold.

## Separate disposal Worlds

- BASELINE: original Dev operator `L2GoalProposal` (2.6m +Z XZ target), deterministic `L1GoalDirective` tolerance, L0 probe→MOVE→S16→probe until stable REACHED; no zombie stimulus.
- INFLIGHT: same typed goal, same original S49 ActionSupervisor and native S15/S16 process. Immediately after **first S15 set_control APPLIED ACK**, DEV World operator issues official Minecraft `summon minecraft:zombie` near the player's physical position. This is a World stimulus, **never a replacement for actual Mineflayer entity observation**. While original forward input is still held, a correlated native `probe` must observe that entity. L0 switches to INTERRUPT, the actual existing clear controls is sent and ACKed, and no second Action issues. The preempted first Action closes UNKNOWN. Any unobserved threat, stale/foreign probe, missing ACK or unexpected Action fail closed.

The S49 original Action ownership is preserved; `S49GoalExecutorDev` has the previously documented explicit *provisional goal-specific S14 DEV admission*, not the legacy zombie S12/S13 admissions. Neither a trained L1 nor a live L2 model is claimed. No Node/Paper exact physics tick sync.

## Evidence requirements

Raw reports include first S15 APPLIED effect ACK, real native threat probe sequence/request ID/entity ID/distance, L0 INTERRUPT choice, S15 CLEAR APPLIED ACK with later seq, after-native-S16 position and observed displacement, explicit S16 FAILED/preempt reason and inherited ActionSupervisor UNKNOWN; no 2nd Action or upper-level planning. Baseline normal REACHED. Two independent World sessions and all shutdown exits 0.

Negative tests: in-flight callback without explicit environment gate or with wrong Action ref rejected, stale/unreadable original reports rejected, original reader asserted, remaining input duration caps native probe wait, no outside owner. No real moving-target fighting, projectile reflex, guaranteed worst-case L0 timing or direction steering established.

Files:
- `adapters/mineflayer/execution.py`: opt-in bounded correlated probes and preempt clear.
- `adapters/mineflayer/s49_goal_executor_dev.py`: inherited S49 Action supervisor, physical callback opt-in and interrupted UNKNOWN.
- `adapters/mineflayer/s49_goal_loop_real_dev.py`: first S15 APPLIED event injects DEV physical hazard and records original L0 interrupt receipts.
- `adapters/mineflayer/s49_goal_inflight_review_dev.py`: independent dual-World source audit.
- `tests/test_s49_goal_inflight_native_dev.py` and `.github/workflows/self-goal-inflight-preempt-dev.yml`: Python3.12 focused/Ruff/Node22 first then separate Minecraft 1.21.8 Worlds.

## Initial real physical result — tested code HEAD a13e8e2777bcfc292b44229926c345fa22050f5e

[GitHub Actions #40669760200](https://github.com/rinsakamo/relay-self/actions/runs/40669760200) completed/SUCCESS. Two independent official Minecraft worlds, focused tests/Ruff/Node22 PASS, original native S49 and clean Node/server exits.

| Native source | Baseline | In-flight threat World |
|---|---:|---:|
| Session | `adb806a0-a631-4ddb-aafb-dce756209c77` | `b7579560-b2be-4c0c-ab89-d1c1c7d4f1f2` |
| Original Action count | 3 | 1 (interrupted) |
| Final goal error in baseline | 0.09847180263249555m | — |
| Native zombie ID / distance | — | `2` / **0.6502954405499092m** |
| S15 APPLIED ACK seq | — | **4** |
| Native hazard probe seq | — | **7** |
| S15 CLEAR ACK seq | — | **8** |
| S16 after-observation seq | — | **9** |
| Native measured displacement | — | **0.0196m** |
| Preempted S16 / Action terminal | — | **FAILED (PREEMPTED) / UNKNOWN** |
| Second Action after threat | n/a | **0** |

Physical sequence `APPLIED(4) → PROBE(7) → CLEAR(8) → AFTER(9)` has the same original S49 Action, session and native receiver. The original Goal ID, intent ID, fixed target XZ and L1 tolerance were retained for future upper-level reconsideration; no real higher-layer replan occurred.

Raw artifact ID **12808076696**, name `s49-goal-inflight-two-worlds-40669760200-1`, ZIP SHA256 **7e4dd6ffe2150b0c0096cb40e7ce952e01f4d537c125b7ddb662301a4597fdb8**.

**Important:** This initial run establishes one genuine in-flight interrupt, *not a guaranteed millisecond latency bound* or safety proof for arbitrary fast threats. Further testing and a physical native clock latency study are required. A subsequent source hardening commit bounds stalled in-flight native probe waits by the remaining input duration; its own rerun is distinct from initial run.

No changes to main, Draft PR #545/#634, qualification or science evidence.
