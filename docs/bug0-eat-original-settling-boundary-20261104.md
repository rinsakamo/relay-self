# Bug-0 EAT — original S49/S15/S16 versus L22/L23/S50 physical settling (2026-11-04)

> **DEV READ-ONLY SOURCE AUDIT / NOT A STOP CERTIFICATE / NOT AN EAT GRANT.** Child [Draft PR #719](https://github.com/rinsakamo/relay-self/pull/719), parent S49 [#674](https://github.com/rinsakamo/relay-self/pull/674), unified design [#717](https://github.com/rinsakamo/relay-self/issues/717) / [#718](https://github.com/rinsakamo/relay-self/pull/718). No new World or physical command is authorized by this document.

## Source owners found — reuse, do not parallel-implement

| Owner / original | Concrete result | Maximum defensible claim | Explicitly NOT |
|---|---|---|---|
| S15 + S16 as used by S49 [`execution.py`](../adapters/mineflayer/execution.py) and [`normal_action.py`](../adapters/mineflayer/normal_action.py) | One supervised MOVE, native dispatch + `clear_controls` applied receipts, bounded after-probe, S16 consequence and original terminal | *The bridge observed an applied clear response and a source-bound outcome* | Server-effective clear tick, no residual velocity, continuous physical idle |
| L22 [original reviewer, head 451270faa](https://github.com/rinsakamo/relay-self/blob/451270faa1281889494f933a5eda33a71e88834f/adapters/mineflayer/l22_post_s16_settling.py), [runtime observer](https://github.com/rinsakamo/relay-self/blob/451270faa1281889494f933a5eda33a71e88834f/adapters/mineflayer/l22_runtime_settling.py), [report](https://github.com/rinsakamo/relay-self/blob/451270faa1281889494f933a5eda33a71e88834f/docs/l-lane-l22-post-s16-settling-20261031.md) | Genuine post-S16 move events, up to six plus probes, residual displacement ≈0.24046m in one archived DEV World, sampled quiet streak | `SETTLING_OBSERVED` or `STABILITY_UNPROVEN`; `stable_world_ticks_attested=false`, `physically_stopped_proven=false` | STOP certainty from two stationary probes or a quiet streak |
| L23 [PR #641](https://github.com/rinsakamo/relay-self/pull/641) | S7/S16/Paper callback source-shape and order `PRE_FORWARD → POST_CLEAR → WAIT_BEGIN → eight tick rows` | callback source-shape constraints / bounded readback | Tick-aligned effective clear, full input state census or autonomous Goal |
| S50 [PR #642](https://github.com/rinsakamo/relay-self/pull/642) | Paper build60 8 WAIT ticks 252..259 with 7 reported inputs OFF; motion still occurs in ticks 252..254 | original World tick and last-reported input samples | Last-reported input is NOT full tick coverage, effective clear or zero physical velocity |
| S50/L23 [PR #643](https://github.com/rinsakamo/relay-self/pull/643) | Client packet-side diagnostic `player_input write-return=0`, Paper `INPUT_EVENT=0`; position packets observed, residual movement | observed client write and separate Paper data | Delivery/acceptance of clear packet, exact cross-clock ordering, physical stop |

**Key source fact:** these are separate Drafts and evidence branches. Their reports cannot simply be imported into `#719` as live attestation, and L22/L23 have never promoted `physically_stopped_proven` to true.

## What was added to Bug-0 #719

`NormalSessionActionExecutor.read_only_post_move_eat_boundary(receipt)` projects the **existing owner-held** `NormalActionReceipt` after original S15/S16 closure:

1. Current terminal `OUTCOME` must belong to the exact `ActionSupervisor` instance; its original S15 `WorldConsequence` is `EXECUTED` for `MOVE_BACKWARD` in the same session.
2. The originally observed Mineflayer `clear_controls` receipt is applied, source-matched and temporally before the original after-probe. **S15 after-probes have no request ID; one is not invented.**
3. Owner has already fenced EAT as `_post_move_settling_unqualified=True`.
4. Result explicitly states `s15_clear_ack_applied=True`, `s16_terminal=outcome`, `settling_status=WORLD_TICK_IDLE_NOT_ATTESTED`, `physically_stopped_proven=False`, `eat_issuance_authorized=False`. It never clears the EAT fence.
5. When the existing S49 `--bug0-eat-shadow` (default **off**) is operator-enabled, the same original closure produces these additional **read-only** report fields. The legacy fixed `WAIT→MOVE_AWAY→MOVE_AWAY` trial is unchanged, with no extra probe, Action, reader, or model.

Synthetic offline tests use frozen S15/S16 typed fixture semantics and negative controls: wrong session, wrong clear kind/result, foreign after, non-owner or unissued Action, source reversal and fake clearance. The tests are **not** a live native or independently authenticated STOP attestation.

## Required first authentic EAT after MOVE — future owner handoff

EAT must remain blocked after an issued MOVE until **S-owner attestation** genuinely proves each of the following, in one continuous original World/session/source generation:

1. **Effective release**: one original issued MOVE + S15 control clear, and an independently observed **server-effective input-cleared tick** attributable to that specific Action. Mineflayer `clear_controls applied` is *not* the server tick.
2. **Continuous coverage**: all relevant input controls and physical movement/velocity sampled without gaps for a predeclared contiguous tick window after that effective release, in a source whose clock and tick authority are authenticated. A sampled quiet streak is insufficient.
3. **Body status / threat freshness**: current health, hunger, inventory, nearby hazard, position and physical control occupancy from the same session at the actual EAT proposal and issue boundary. A bounded empty entity registry is not global safety.
4. **Identity and permission**: unique external EAT PROPOSE and ISSUE authorities, each genuinely authenticated by the S owner and bound to the current exact Intent/Skill/Action, original session, probe, item/slot and deadlines. **Typed strings are not an authenticated grant**.
5. **Custody and evidence**: single original physical issuer; no second controller, no retry after uncertain native effect, original equip + consume receipts and independent inventory/food outcome, with raw source SHA, cleanup and separate DEV/QUAL/SCIENCE classification.

**No new generic S49 or L-owned physical STOP authorizer is introduced.** Existing S50/Paper code should be extended by its S owner only if the first two proofs remain absent. Once qualified, the owner can propose an opt-in, narrowly scoped **authenticated** resume signal; #719 does not create a publicly constructible dataclass or property that clears `_post_move_settling_unqualified` from synthetic L22 quiet samples.

## Next focused offline acceptance cases

- Original S15/S16 source with a valid applied clear produces **a diagnostic only**, never `EAT_AUTHORIZED`.
- Wrong ActionSupervisor/current Action, foreign session, wrong/rejected clear or source order rejects.
- L22 `STABILITY_UNPROVEN`, `SETTLING_OBSERVED`, or `QUIET_SAMPLES_ONLY`, even with 8 Paper WAIT tick labels, cannot unlock EAT without authenticated effective release and continuous tick source.
- With no prior MOVE in a fresh owner, the existing Bug-0 pre-EAT checks (two native probes, threats, physical single-issuer, typed grants) remain **necessary but not sufficient** for a live EAT launch.
- Parent S49 CI/runner remains frozen; no synthetic improvement or qualification gain is claimed.

**Classification:** `DEV_OFFLINE_ONLY / SOURCE_UNATTESTED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`. This note is a boundary contract, not a performed real-World test. Keep Bug-0 D/E high-level simulation/training postponed.
