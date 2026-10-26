# RelaySelf — original S49 Paper passive motion AFTER native cleanup (DEV)

2026-10-26; isolated `self/dev-s49-forward-motor-admission-20261026`.
**DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.

## What changed

- Added optional one-shot DEV flag `--post-release-dev` requiring
  existing `--native-edges-dev --m0-move-dev --m0-live-dev --p1-live-dev`,
  new env `S49_POST_RELEASE_MOTION_DEV_ONLY=1`, and same disposable
  Paper 1.21.8 World safety envelope.
- Original S49 remains the only Action issuer/native message reader.
  S14/S15/S16 control authorization and original native ACKs do not change.
- Paper removes the temporary DASH speed modifier on owner release,
  then schedules precisely **five read-only World-tick position samples**.
  No new Action dispatch, speed change, P1 state update, M0 debit,
  ungrounded WAIT determination or SelfWorld admission. The passive
  observer cancels itself after five callbacks and on any actor/world
  drift, residual speed modifier, skipped/regressed World tick or plugin
  shutdown.
- The same-tick callback directly after task registration is ignored:
  it is not elapsed World time and cannot earn a sample. Exactly five
  subsequent contiguous World ticks are required.
- First post-release displacement is explicitly **MIXED**: its origin
  may precede removal. Remaining four consecutive deltas are labeled
  POST_RELEASE, but still do not prove that no new client inputs exist.
- The Python report re-checks action/session/world UUID/player UUID,
  exactly five contiguous ticks after Paper owner RELEASE, finite
  bounded XZ deltas, modifier absent, no motor/P1/M0 writes, and explicit
  `WAIT_ATTESTED=false`. Negative controls cover missing/replayed
  ticks, foreign actor/world, forged physical values, fake post-release
  motor activity, and invented WAIT/P1/M0 claims.

## Actual Minecraft DEV results

**Source validation HEAD `d1e20570f6856242164cd8cdf9ea6b136d6c9e64`**.
[New passive real Paper World run #40320218197 — SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/40320218197).
Python 3.12 focused tests and negative controls, Ruff, Node 22 bridge
tests, Java 21 plugin build, one disposable real Paper Minecraft World,
native original S49/Node/Java cleanup completed successfully.

| Item | Real observation |
|---|---|
| Original first S49 action | `s49-native-move-18` native S16 OUTCOME |
| Second original S49 Action | `s49-native-move-55` native S16 OUTCOME |
| Paper ARM tick | 249 |
| Native dispatch ACK and Paper delivery marker | seq 21; tick 251 |
| Native clear-controls ACK and Paper delivery marker | seq 35; tick 263 |
| Paper modifier release | tick 263 |
| Original DASH Paper callbacks | 13, continuous ticks 250–262 |
| DASH physical positive callbacks | 11 |
| Passive post-release callbacks | 5, continuous ticks **264–268** |
| First mixed-boundary XZ delta (tick 264) | 0.17948084897615058m |
| Purely after-release tick 265 delta | 0.034609387304899375m |
| Purely after-release tick 266 delta | 0.018896725468474873m |
| Purely after-release tick 267 delta | 0.0m |
| Purely after-release tick 268 delta | 0.01595102831554751m |
| Positive translation after release | 3/4 ticks (threshold 0.002m) |
| P1 fatigue, observed first Action | 0.600000 → 0.6177122410 |
| M0 original owner energy, 2 issued MOVE Actions | **12.0 → 10.413667611509306** |
| First real native Action distance | 4.396260226333246m |
| Unboosted second native Action distance | 3.030157205468642m |
| Extra DASH debit in original B0 owner | 0.08633238849069515 |
| Original B0 owner basal/MOVE logical steps | 2 × (0.50 + 0.25) |

The **observed 3/4 post-release movement samples** demonstrate that
the physical player does not necessarily become stationary in the
first tick after an ACK. The cause could be inertia, pending
packets/updates, another control edge, or collision changes; current
Paper movement observations do not separate them. A single zero delta
at tick 267 is NOT a source-attested WAIT and does not qualify physical
fatigue recovery.

The sampled Paper XZ speed peak in this trial (~15.50m/s) is a
single-sample outlier compared with previous ~7.78m/s readings;
do not treat it as sustainable DASH speed or a scientifically
controlled gain. The presence and bounded energy/motor state
transitions were audited; speed-cap/direction classification
is still unqualified.

## Failure and verification limits

First run [#40319835049](https://github.com/rinsakamo/relay-self/actions/runs/40319835049)
was **FAIL_CLOSED** for the *new passive observer*:
`S49_DASH_DEV_POST_ABORT tick_gap_or_replay`.
S49 original native Action 2/2 and B0 debit succeeded, but no
post-release proof was admitted. Its first scheduler callback could
occur in the registration tick; the change
`d1e20570f6856242164cd8cdf9ea6b136d6c9e64` skips that exact
unelapsed tick and continues to reject real gaps. A subsequent
real World and focused tests passed.

Legacy regression real-World workflows at the tested source HEAD also
succeeded: S49 P1 tick-gated DASH [#40320218296](https://github.com/rinsakamo/relay-self/actions/runs/40320218296),
forward sprint [#40320218142](https://github.com/rinsakamo/relay-self/actions/runs/40320218142),
Action-level M0 [#40320218105](https://github.com/rinsakamo/relay-self/actions/runs/40320218105),
and original native effect ACK [#40320218275](https://github.com/rinsakamo/relay-self/actions/runs/40320218275).
No FULL/main CI, new qualification trial, model inference or SCI.

## M0 time-scale calibration: deliberately not inferred

Current original M0 `MetabolismConfig.basal_cost=0.5` and
`move_cost=0.25` are charged per **M0 logical step**; the DEV
original S49 owner currently charges exactly one such step per
completed native MOVE Action. Paper native World ticks are independent
clock units and P1 extra charge is a per-observed-tick modeled
expenditure. One cannot recover a basal energy-per-second rate from
the original M0 model and the partial ACK/Paper observations alone.
No Action-duration-dependent basal debit, 13×0.5 scaling,
idle-World debit, or WAIT/P1 recovery is asserted or posted.

**Next DEV**: acquire a bounded independent tick-custody view of
client effect transmission/physics updates versus Paper timestamps,
then explicitly choose a real-time basal M0 rate before per-World-tick
charging. Keep M0 owner unique and deny speculative World gaps.
