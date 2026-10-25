# RelaySelf — SelfBody Motion Feedback three-clock native DEV observation

**Date:** 2026-10-25
**Classification:** `DEV_S49_THREE_CLOCKS_OBSERVED / DEV_ONLY /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`

## Engineering purpose

Measure the **different time domains** that exist between original S49
Action authority, Node/Mineflayer local motor control, and the Paper World.
Retain the original S49 sole Action issuer/receiver/S16 terminal evidence.
Do **not** equate host-requested duration to server-effective input ticks.

Isolated branch:
`self/dev-selfbody-motor-clock-observe-20261025`

New modules:
- `s49_native_motor_clock_dev.py`: generates a *single temporary sibling
  copy* of the original Node `bridge.mjs`, with five small exact-match
  source alterations (file writer import, bounded telemetry state,
  physicsTick callback, BACK ON row, BACK OFF row). The original bridge
  and protocol remain byte-identical. A generated sibling maintains
  unchanged relative Mineflayer imports, process ownership and stdout
  JSONL messages. The temporary file is removed after original S49
  Java/Node cleanup. No second controller, native receive loop or action.
- `s49_motor_clock_review_dev.py`: checks Node log rows' locally
  monotonic nanoseconds, client physics callback counts, matching
  original S49 Action IDs, ON/physicsTick/OFF ordering, and the existing
  eight *separate* Paper WAIT tick records. Fails closed on forged
  Paper-effective tick claims, extra Action issuers, malformed log
  intervals or cross-session mismatches.
- `s49_paper_world_first_dev.py`: explicit gated
  `--motor-clock-dev` only alongside
  `--selfbody-motion-feedback --actual-sixth-motor` and pre-existing
  S49 five other DEV epoch gates. The original S49 qualifier performs
  exactly one session's authorization, execution, S16 and cleanup.
- `tests/test_s49_motor_clock_dev.py`: generated temporary bridge
  isolated from original bytes, pass/fail for three distinct local
  clock domains, absent/falsified samples and missing opt-in.
- `self-selfbody-motor-clock-observe-world-dev.yml`: Python 3.12
  focused, Ruff, Java21 observer compilation, Node22 original package,
  pinned Paper 1.21.8, **one** actual disposable World and persisted
  records. No FULL regression, R or science runs.

### Actual original S49 single-World outcome

[Successful Actions run #40187092136](https://github.com/rinsakamo/relay-self/actions/runs/40187092136),
exact World test HEAD `0690a088de151f87bf30a031fc8e297c4ef47d50`.
[Original artifact #12596244524](https://github.com/rinsakamo/relay-self/actions/runs/40187092136/artifacts/12596244524)
was downloaded and independently inspected: `original_s49_report.json`,
`world_first_dev_report.json`, `native_motor_clock_dev.jsonl`
(23 Node rows), `paper_server.log`, and `paper_observer_window.log`.
Original and outer reports **PASS**, original S49 six L0 choices
`WAIT→MOVE→MOVE→MOVE→WAIT→MOVE`, four native S14/S16 authorized
`OUTCOME`s, Java and Node exit `0/0`. Original session
`3553ab27-b44c-4652-a5ad-75be167e5413`.

| Original Action ID | Node BACK ON→OFF (monotonic ms) | Node physicsTick callbacks while BACK | Original S16 displacement (blocks) |
| --- | ---: | ---: | ---: |
| `s49-native-move-19` | 201.451023 | **4** | 0.6269065734 |
| `s49-native-move-47` | 200.961045 | **4** | 0.6269065734 |
| `s49-native-move-69` | 201.115799 | **4** | 0.6269065734 |
| `s49-native-move-97` | 147.992576 | **3** | 0.4302315372 |

Node-local `physicsTick` counter intervals for these four Actions
were respectively 220→224, 419→423, 470→474 and 540→543.
**The decrease from four client callbacks to three coincided with**
the last, shorter SelfBody-proposed control hold and with shorter
native Minecraft movement. There were no extra original S49
issuers or consumers.

The **existing independent Paper observer** captured exactly eight
consecutive World-full-time WAIT callbacks at **459–466** following
the *second* Action `s49-native-move-47`; this is a separate
server-time observation, **not** the Paper ticks during which any
BACK input was effective. Unlike a pre-action server input watcher,
the existing post-action observer did not attest Paper BACK ON/OFF
edges. Its console claims are not independent S16 source signatures.

### Interpretation and limitations

- Node `process.hrtime.bigint()` gives the local elapsed interval
  between `bot.setControlState('back', true)` and
  `bot.clearControlStates()` in a **single Node process**. It
  measures local control state duration; it is not original Python
  `asyncio.sleep()` duration and does not measure server-applied
  control time.
- Mineflayer's `physicsTick` is a client-library callback, **not a
  source-qualified server tick**. 4 vs 3 callbacks and distinct
  displacement is informative, but is not a proof of the exact
  server-internal tick where movement happened. There may be inertia
  and post-release movement before the S16 after-snapshot.
- Paper `World.getFullTime()` is a **server World logical time**
  observation from a later eight-tick WAIT period. No cross-process
  clock offset or Paper control hold interval was invented.
- The telemetry is DEV-only instrumentation executed inside a copied
  Node bridge, with synchronous bounded file writes. Instrumentation
  can perturb scheduling and needs a negative-control comparison
  before it is called representative of non-instrumented timing.
- Native real fatigue remains unknown; a SelfBody inference is a
  predictor, not a measured biological actuator. No S10 update,
  qualified WorldTick, causal identification, R/SCIENCE work.

### Immutable earlier failed checks

[#40186913691](https://github.com/rinsakamo/relay-self/actions/runs/40186913691)
and [#40186999842](https://github.com/rinsakamo/relay-self/actions/runs/40186999842)
were both **PREWORLD** Ruff import-order failures. Neither started a
Minecraft World. The exact sorted import fix in
`5c8e595150783c6d4c10e5344bda267d645d6b3e` was followed by
successful #40187092136, preserving the previous failed statuses.

Preserved source blobs:
- original `bridge.mjs`
  `42b5a8f1ff49a1728727844fbb4533a95bb34bcf`;
- original `normal_action.py`
  `0ded8fa296c92076a643de08cd6fc360061e1d08`;
- original `experiments/fatigue_p1.py`
  `bd4f35a4079da0770ef11cdec921dbba31de9b81`.

**Draft PR #545/#634 and main unchanged.** Adoption of prior
DEV-only original S49 qualifier opt-ins still needs separate owner
source review.

## Next bounded DEV investigation

For *server-effective* motion ticks, use the existing Paper
`relays49preobserve` read-only callback **before** the original
authorized MOVE, confirm server `BACK_TRUE/BACK_FALSE` edge ticks
and capture player position/tick in that server World. Never equate
these server events to Node local clocks without an explicit
cross-domain timing model. No new native Action issuer, retries or
formal R proof should be introduced just to demonstrate DEV function.
