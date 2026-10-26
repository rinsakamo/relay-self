# RelaySelf S49 → Paper P1 → original B0 M0 extra debit (DEV)

2026-10-26. This is an isolated **DEV-only** real Paper 1.21.8 trial.

- Validation exact HEAD:
  `4e897edc156fc50183fbae3113b794b50b129944`
- [GitHub Actions #40312393561 — SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40312393561)
- Only `self/dev-s49-forward-motor-admission-20261026` changed. main and Draft
  PR #634/#545 not adopted.

## Mechanism and ownership

The ordinary B0 `B0EnergyLedger` remains the **only energy mutation
owner**. No alternate energy gauge or M0 mirror is introduced. In this
isolated S49 run, the **original S49 owner** instantiates one `B0EnergyLedger`
after receiving its authentic Mineflayer `session_id`, and ONLY with explicit
`dev_m0_dash_invoice` and `S49_M0_DASH_DEBIT_DEV_ONLY=1`.
Ordinary default B0/S49 paths cannot access the debit API.

1. The original S14 admission/normal S49 Action issuer dispatches the
   unchanged one-shot `MOVE_FORWARD_SPRINT_DEV`.
2. Temporary Paper records the actual 13 callback World ticks, power
   changes, speed modifier and disarm completion; the wrapper verifies
   one session and action and independently replays the single P1
   fatigue state.
3. When and only when original S49 receives a terminal **S16 OUTCOME**
   with matching native before/after observations, dispatch ACK, cleanup
   ACK and movement, its callback constructs one immutable
   `DashM0InvoiceDev`. Paper itself can NEVER post energy.
4. Original S49 passes that invoice and the original S16 evidence to
   **its already-held B0EnergyLedger**. The owner validates native
   action/session/source, contiguous Paper callback tick window,
   positive bounded extra charge (<=0.20 × 0.05 × observed ticks), no
   duplicate Action or overlap, and sufficient spendable energy;
   only then atomically debits existing `BodyState.energy` and
   increments **one local M0 transaction tick**.
5. The subsequent second S49 Action is unboosted and incurs **zero
   extra DASH charges**. Standard B0 food credit, basal and MOVE cost
   paths were not altered. Since basal/MOVE clock integration has not
   been independently established, no 13 fake basal cost ticks are
   posted.

The source is **S49 producer-local with a Paper session/action join**;
Paper callback ticks are not an externally attested World clock
nor is this a persistent production-wide M0 transaction.

## Actual one-World measurements

| Field | Result |
|---|---:|
| Original S49 S16 | 2/2 native OUTCOME |
| Original S49 issued Action | `s49-native-move-19` |
| Paper World tick span | 251–263 inclusive (13) |
| Paper modifier boost ticks | 11/13 |
| Paper sampled 20TPS XZ speed peak | 7.775184687901019 m/s |
| Native boosted first Action displacement | 4.001023978927417 m |
| Native unboosted second Action displacement | 3.030157205468642 m |
| First–second DEV difference | +0.9708667734587757 m |
| P1 F initial → final | 0.6000000000 → 0.6177122410202606 |
| Applied DASH power first → last | 0.802197252290235 → 0.7678689695742946 |
| Same-source P1 replay | 13 consecutive callbacks PASS |
| M0 extra proposal | 0.08633238849069515 |
| **M0 extra actually posted** | **0.08633238849069515** |
| **Actual existing B0 owner energy** | **12.0 → 11.913667611509306** |
| M0 owner transaction count | 1 |
| Unboosted second Action extra debit | 0 |
| Food mint / additional Action issuers | 0 |
| Java / Node exit | 0 / 0 |

## Failure and regression boundaries

- Python 3.12 focused: tests for action replay, foreign
  session, wrong source scope, invalid/missing World tick window, 0/too many
  boost ticks, NaN/negative/excessive amount, M0 permission default
  disabled, and native S16 tampering.
- Ruff / Node 22 tests / Java 21 compile / original S49
  regression: PASS. No FULL CI and no main merge.
- A failed audit does **not** modify `BodyState` or credit food.
  A charged S49 Action ID is **not** allowed to debit again.
  Terminal or insufficient energy is fail-closed; no free DASH credit.
- Native source frames are S49-constrained, but Paper movement still
  uses explicitly-labelled `MOTION_PROJECTION` rather than
  independently attested forward input packet bits.
- Missing cross-host Tick/TPS custody, hard lateral/back direction caps,
  native authoritative P1 full-life persistence and production M0
  consolidation: **NOT QUALIFIED**. Science run 0, qualification run 0.

**DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.**

Next DEV: independently join the Paper elapsed World tick source to
original Action control lifetime and prove M0 basal/MOVE charge cadence
without conflating one M0 transaction tick with 13 World ticks.
