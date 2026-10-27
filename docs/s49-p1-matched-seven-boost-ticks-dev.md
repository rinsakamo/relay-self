# P1 hypothetical motor response at seven matched Paper bonus ticks — DEV

Scope: **DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.

## Question

Earlier [DEV real World #40491478791](https://github.com/rinsakamo/relay-self/actions/runs/40491478791) confirmed **motor output sensitivity** to two synthetic P1 model initial F states, with the existing Mineflayer speed-attribute bridge enabled in both Worlds:

- CARRY F=0.6177122410202606, first S16=3.759799 m; 10 positive Paper bonus callbacks
- WAIT_ASSUMED F=0.21616083122103735, first S16=4.264898 m; 11 positive Paper bonus callbacks

A +0.5051m native S16 difference was observed, **but** 10-versus-11 boosted World ticks and different Node active attribute physics tick counts confound precise motor difference attribution. No actual same-Self recovery was measured.

## Controlled change, without a second Action owner

The existing **one-shot original Paper DEV speed modifier** gains an optional `p1-matched-boost-cap-dev: 7` when and only when the existing exact two hardcoded synthetic model-F preload scenarios are enabled. The plugin counts **positive modifier-applied World callback ticks**, leaves the original S49 first native Action duration/issuer unchanged, and clears its temporary modifier after the 7th positive tick. This is a motor-only DEV test cap, not an extra timeout, WAIT command, new native reader, new action issuer, or change to P1/M0 authority.

In separate disposable Worlds, the original S49 issues exactly the same first boosted and second unboosted native S15/S16 MOVE actions. Both Worlds use the exact pinned Paper 1.21.8 build, Java 21 plugin, Mineflayer 4.39.0, `S49_SPEED_ATTR_SYNC_DEV_ONLY=1`, `S49_SPEED_ATTR_BOUNDARY_DEV_ONLY=1`, and `S49_P1_MATCHED_BOOST_DEV_ONLY=1`. The single intentionally changed motor-model input is the prior frozen hypothetical F:

| Arm | Preloaded DEV P1 model F |
|---|---:|
| CARRY | 0.6177122410202606 |
| WAIT_ASSUMED | 0.21616083122103735 |

Each completed original Action must produce *exactly 7 consecutive Paper World tick rows* with `modifier_applied=true`, `p1_matched_boost_cap_reached=true`, the same player/world/action/session throughout, **at least one subsequent no-boost gait tick**, and a genuine `OWNER_RELEASE` completion. Unexpected extra, missing or replayed ticks, wrong actor, forged P1/M0 authority or wrong cap fail closed.

Source review reuses the original S49 S15/S16 receipt verification, complete Paper P1 model replay and Node speed attribute source trace review. The new pure reviewer then compares **same positive-boost ordinal 1..7** speed and power values and actual S16 displacement for both Worlds. The result may be positive or negative; physical displacement gain is not a condition for valid source evidence.

## Important epistemic boundary

- **7 positive Paper ticks are duration-matched for the *server modifier*, not for the native S49 Action**. The original Action can still run for a slightly different number of Paper/Node ticks.
- Matching by 1..7 ordinal is **not** synchronization of World ticks between two independent Worlds, nor synchronization of Node physics callbacks and Paper modifier timing.
- Server tick speed uses prior-position deltas; the first positive row need not measure the already-applied modifier's physical effect.
- Model F is a deliberately loaded *hypothesis*, **not** a physiological reading or a witnessed same-Self WAIT recovery. No actual P1 state posting, qualified R WAIT, or production L0 DASH power admission.
- Existing M0 posting remains the original DEV S49 S16 owner; new reviewer posts no P1 or M0 entries.
- No R/SCIENCE/FULL runs; main, Draft PR #545 and #634 remain untouched.

### Reproducibility

Run `.github/workflows/self-p1-matched-boost-7ticks-dev.yml` on the isolated opt-in DEV branch. Python 3.12 focused tests/Ruff + Node 22 tests + Java 21 plugin compilation precede both real disposable Paper Worlds. Save raw source traces even on failed validation. Record the *exact* tested HEAD, real run id, artifacts, and measured both-arm comparison only after readback.

Model-hypothesis source SHA256 from the original earlier static candidate: `f126d16f42caa27230a02e4c818d7b7ae3c1d2e39e8ad75c55cd2ce9ddc16bd4`.

## Exact real-World DEV result — 2026-10-27

**World-tested code HEAD:** `e0fdb1df198eefc55dc727ceac51f2f2bf3f72a5`.
[GitHub Actions run #40495397519](https://github.com/rinsakamo/relay-self/actions/runs/40495397519): **SUCCESS**.

- Python 3.12 focused **219 PASS**, Ruff **All checks passed**;
  Node 22 **3 PASS / 0 FAIL**; Java 21 `BUILD SUCCESS`.
- Two genuinely independent disposable Paper 1.21.8 World trials,
  both with original S49 **two native S15/S16 Action OUTCOMEs**.
  Original exclusive Action issuer, Mineflayer receiver and DEV M0
  S16 posting owner retained.
- Both completed original first Actions report `OWNER_RELEASE`,
  **exactly 7 positive modifier-applied Paper World callback ticks**,
  consecutive, positive indices **2..8** (CARRY World ticks 240..246,
  WAIT_ASSUMED World ticks 242..248), and subsequent ordinary no-bonus
  gait ticks. Both had **13 total Paper P1 gait callback ticks**.
- Both Node-local source traces have **6 active physicsTick samples
  with projected Paper DASH speed attribute**; no new native reader or
  Action issuer. Two independent Node/Paper timebases are NOT synchronized.

| Source-verified measure | CARRY | WAIT_ASSUMED |
| --- | ---: | ---: |
| Preloaded *model* F | 0.6177122410202606 | 0.21616083122103735 |
| First applied Paper DASH model power | 0.7668612208455023 | 1.0 |
| Seven matched positive Paper power mean | 0.7571246460828889 | 1.0 |
| Positive Paper bonus callbacks | **7** | **7** |
| Paper total P1 gait callbacks | **13** | **13** |
| Node active attribute-positive physics ticks | **6** | **6** |
| Paper positive-ordinal mean speed m/s | **6.267369246773084** | **7.437469645316114** |
| Original first S49 S16 native XZ distance m | **3.647398724622718** | **4.12577858180323** |
| Original second unboosted S16 native distance m | 3.030157209647224 | 3.0301572054686403 |

**Computed deltas:** native first S16 movement (WAIT_ASSUMED minus CARRY)
**+0.4783798571805118 m**; seven positive-ordinal Paper sample mean speed
**+1.170100398543031 m/s**; positive Paper applied normalized power mean
**+0.2428753539171111**. The power difference varies from
0.23313877915449766 at ordinal 1 to 0.25249164664880985 at ordinal 7.

**First-sample timing sensitivity:** at positive ordinal 1, sampled Paper
speed in CARRY = **3.939209586823882 m/s** versus WAIT_ASSUMED =
**8.638019061045021 m/s** (delta **4.6988094742211395 m/s**). That
single value can straddle the just-applied modifier effect and dominates
the naive seven-sample mean. Excluding ordinal 1, ordinals 2–7 have
positive pairwise deltas in the range **0.414741538518939 to
0.6748042106348873 m/s**; their unweighted mean is
**0.581982219263 m/s** (descriptive DEV comparison, not effect-size
qualification). Independent full Paper log digests are:
CARRY `0d97d4b81feb9723163c6d1cabfe761ce59638a4569a804c61e29e844f0e5b93`,
WAIT_ASSUMED `a489c5462d66c93b9ac1ae5f7a118bb8e744369a77b363c395f74773d77f39a7`.

**Interpretation:** Unlike the prior 10-vs-11 bonus sample run, this run
confirms physical movement separation *with a matched number of real
Paper speed-modifier callbacks*. The model input difference is associated
with higher measured native displacement and matched-ordinal Paper speeds.
It does **not** isolate P1 fatigue as the unique cause of the exact
movement delta: two independently started Worlds still have unsynchronized
Paper and Node timing and the **original first native Action duration
itself was not tick-matched**. The seven Paper positive samples are not
simultaneous or fully corresponding Node integration intervals.

Both hypothetical P1 preloads were injected into separate new Worlds, not
observed longitudinally in the same Self. No real-world P1 F reading,
formal global WAIT, R source-bound tick, actual production P1 recovery,
L0 physical DASH power grant, science run, or protected main/PR merge.

**Evidence artifact:** `p1-7matched-model-motor-pair-40495397519-1`,
ID **12729449166**,
SHA256 `0e98bdff2f40ae129d3d5d4b0fa37724dc256b546d4e2063efc0b2bccf3e376f`.

### Preserved negative/repair history

- `40493992067`: synthetic fixture passed unjoined prior stage.
  Python focused FAIL before any real World.
- `40494165188`: synthetic fixture referred to pre-join arm keys.
  Python focused FAIL before any real World.
- `40494307913`: real original S49 correctly rejected new capped motor
  as invalid under its old "forward detected implies modifier applied"
  classification. Original issuer failed closed; no second Action;
  this remains FAIL.
- `40494907930`: both original S49 sessions and seven-positive-tick
  modifier caps completed, but an independent source reviewer rejected
  early *actual zero-speed* Paper samples as invalid. FAIL retained.
- `40495397519`: complete fresh run with both original S49 Actions,
  independent Paper/Node source join and matched boost cap. SUCCESS.

The DEV-only classifier now explicitly distinguishes genuine forward
input/motion from the legitimate seven-tick modifier-cap exhaustion, and
its inferred-boost count reflects *actual positive modifier* callbacks.
The ordinary no-cap source validation remains active and tested.

**Next engineering step:** if necessary, match original first native
Action holding duration at an original-S49-controlled boundary and
collect phase-aligned Node physicsTick indices. This still would be a
DEV response comparison, not proof that physical WAIT actually recovered
the same Self's P1 fatigue.
