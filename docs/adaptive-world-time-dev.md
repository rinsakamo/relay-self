# #150 — adaptive WorldTick rate: isolated DEV T0

Scope: **OFFLINE_ONLY / DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.

`adapters/mineflayer/m02_paper_dev/adaptive_world_rate.py` is a deterministic **proposal-only** function. It has no Paper API calls, Mineflayer calls, I/O, persistent owner, STOP issuer, or World control. Existing S49/S16 authority remains untouched.

- Paper's server tick is the proposed World-time axis; `simulated_seconds(delta)=delta/20` independently of requested or achieved wall TPS.
- `TickWindow` carries every actual server tick and matching L0 tick, checked exactly (not counts). Upstream must independently attest provenance; a handcrafted `TickWindow` is **not** a native receipt.
- Requested TPS is adjusted gradually after 3 good consecutive windows and reduced on throughput failure. The `experimental_cap_tps` is an explicit configurable safety bound, **not** an asserted hardware limit. Actual measured TPS, not nominal rate, is the feedback.
- If L0 coverage/ticks/session ordering is broken or danger/deadline occurs, only a `FALLBACK` proposal is returned with `stop_required=True`; the existing authorized controller must enact a genuine STOP and confirm its ACK. No paper marker may be treated as physical control authority.
- Native physical MOVE/RUN/fight remains **20 TPS only** until a separately tested WorldTick motor and existing owner authorization are available. Claiming one boolean cannot itself qualify the motor; the API is an offline thought experiment.
- For cognition pressure, a proposal can drop the rate to 2 TPS but never to zero. World freeze is intentionally absent: future 2+ Self bounded barrier is a **different**, host-only coordination mechanism with independently controlled authorization and fairness.
- M0/P1 physical updates must use only admitted WorldTicks with actual activity, never request TPS as an extra multiplier. Blocked MOVE != P1 WAIT. T0 does not mutate their ledgers.

Next: Paper native tick L0 sensor (T1) -> S49 physical trace & M0/P1 per-tick accounting (T2) -> measured high-rate player motor (T3) -> 2+ Self epoch barrier (T4). Do not run a fresh World, merge Draft PRs or claim R qualification from this offline prototype.

Run offline focused tests from the repository root: `python3.12 -m pytest -q tests/test_adaptive_world_rate.py`.

## T1 — native Paper passive tick callback, added 2026-10-26

**DEV observation only, not L0/world-control integration**. The existing M0.2 Paper plugin adds an optional `adaptive-tick-observer-dev` (default **false**) under the pre-existing `dev-enabled` guard. Only an explicitly enabled disposable Paper 1.21.8 DEV world produces up to **256** `PAPER_DEV_TIME_SAMPLE` lines for the exact owned online bot. No TPS adjustment, extra motor authority, Paper-side L0, session inference, or control release is added.

Each sample contains ordered `index`, `Bukkit.getCurrentTick()` (`server_tick`), `World.getFullTime()` (`world_full_time`), same JVM monotonic elapsed duration from plugin initialization (`wall_nanos = System.nanoTime() - originNanos`; **not** an absolute wall timestamp), native World/Player UUIDs, and explicit `l0_checked=false action_bound=false`. These clocks are **not presumed equivalent**. Because this uses a Bukkit scheduler callback, it is only one sample *within* each observed tick; it cannot certify a whole-tick event census or native Mineflayer physics updates. Log contents are not independently authenticated; the reader cannot attest the log's origin.

`paper_tick_probe.read_passive_paper_ticks(log_text, expected_world=<uuid>, expected_player=<uuid>)` refuses missing/duplicate/changed server and World tick, inconsistent callback order, wall-clock regression, foreign World/Player, forged L0/action flags, or >256 rows. It derives the observed average rate from first-to-last callback difference as `(row_count - 1) / wall_duration_seconds`, never from requested TPS. It does **not** create `TickWindow` for T0, because none of the samples proves the Self-side L0 check actually ran.

The opt-in plugin retains its existing **physical M0.2 behavior** if `dev-enabled=true`; these changes add **logging only**, but enabling the plugin as a whole is not an observation-only operation. Do not enable in live or qualified Worlds. The plugin's normal M0.2 tick charge is unchanged. No native Paper run or JAR build was performed here.

Next source-admission seam: independently bind S49 session and Action with original owner evidence, collect actual per-tick L0 decision receipts through the single native receive path, and only then allow the T0 policy to inspect paired, complete tick windows. Missing evidence must not silently be replaced with Paper samples.

### Verification

- Local Python 3.13.5: 15 focused synthetic parser tests PASS and syntax compile PASS; this is **not** the product-standard Python 3.12 run.
- Paper API 1.21.8 Java 21/JAR build: **NOT RUN**; no Maven or Paper dependency in this tool environment.
- Native Paper/Mineflayer gameplay, CI, actual rate modification, M0/P1 experiment, R/V qualification: **NOT RUN**.

## T1b — Paper → Mineflayer single-stream delivery (2026-10-26)

**Opt-in only / runtime disabled by default.** With both `dev-enabled=true`, `adaptive-tick-observer-dev=true` in the disposable Paper M0.2 world **and** `RELAYSELF_PAPER_TICK_DEV=1` on the existing Mineflayer bridge (explicit Minecraft `1.21.8`), Paper registers the outgoing plugin-message channel `relayself:world_tick_dev`. The bridge registers its subscription after login. **Only subscribed online target-player ticks** start the bounded paired log+wire sequence (`index=1..256`). No second TCP connection, native reader, Action issuer, or control command is introduced.

Paper logs `PAPER_DEV_TIME_SAMPLE` and sends **the identical ASCII field string** in the same scheduled callback. The existing Node bridge receives the channel and emits `paper_tick_sample` through its original session/sequence-numbered stdout. The existing Python stream decoder accepts a new, strictly typed passive sample. An independent read-only matcher `join_paper_tick_transport()` rejects missing or mixed Paper-log/native-bridge rows, World/Player/session inconsistencies, non-monotonic client receipts and timestamp changes. The Node listener permanently fences the channel after its **first** invalid/gapped message; it must not rejoin subsequent rows and hide earlier loss. Missing subscription produces no accepted tick window.

**Boundaries still unimplemented:** A received tick is **not** the Self L0 check for that tick. L0 must receive and process a bounded, genuinely fresh input on the same existing native receiver, record per-tick `L0 checked` receipts with deadlines and stop/unknown if missed. No T0 `TickWindow` or adaptive TPS command is created from the passive wire or log match. `action_bound=false` and `paper_native_source_authenticated=false` remain mandatory. No claim that transport latency or the separate Python L0 execution is completed in the originating Paper server tick. The JDK21/Paper API compile and actual 1.21.8 client protocol delivery remain **not verified** until isolated native DEV execution.

**Local check performed**: Node 22 `node --check` and 5 focused `node --test` cases passed on a locally reconstructed channel+test copy. They check strict schema, channel registration, invalid/missing tick, permanent failure and absence of L0/Action authority. They are **not** a byte-for-byte exact-HEAD test, full Node suite, Java build, Python3.12 pytest or physical Paper run. The Python wire matcher/decoder negative-control tests have been committed but are **not yet executed** against the repository checkout in this environment. Avoid reporting those as PASS.

Continue with source-bound true L0 completion and per-tick freshness checks *before* enabling live TPS controls. Existing #537 DEV-first test policy and #627 native physical/action owner take precedence.

## T1c — per-delivered-tick client-cache L0 shadow (2026-10-26)

**Source limitation remains explicit:** This is **not yet** the final "L0 monitors every fresh WorldTick" guarantee. It is one *synchronous* low-cost, bounded **cache-only shadow L0 evaluation per received Paper tick event**, on the existing Mineflayer bridge and original `session_id/seq` stdout. The additional `paper_l0_shadow.mjs` checks local cached health, hunger, and bounded nearby hostile entity registry; `UNKNOWN` is returned if client input is absent, malformed, or coverage exceeds the bound. It does not issue movement/attack/STOP, does not grant a fresh native world observation, does not infer Paper current-tick physics from Mineflayer cache, and does not authorize adaptive TPS.

For every `paper_tick_sample`, the bridge immediately emits a `paper_l0_shadow` message with reference to the same Paper `server_tick`, World/Player UUID, and sample index. A local monotonic duration measures only the *JS cache check*, **not** elapsed Paper-to-client network latency or assurance that L0 responded before the next Paper tick. `l0_shadow_evaluated=true` is intentionally separate from `l0_fresh_world_tick_attested=false`, `authorized_action_issued=false` and `tps_admission_granted=false`. The previous Paper-channel fail-closed sequence barrier remains unchanged.

`python_protocol.py` parses `MineflayerPaperL0Shadow` on the same native stream and rejects forged/missing fields, values or authority flags. `join_paper_l0_shadow()` requires one sequential immediate shadow after every transport tick and exposes `shadow_cache_evaluated_ticks`, `unknown_or_uncovered_ticks`, but **never** projects to T0 `TickWindow.l0_checked_ticks`. This guards against incorrectly treating event receipt or stale local cached state as per-WorldTick completed L0.

Local available tool runtime: Python3.13.5, Node22.16.0, Java21; Python3.12 and Maven unavailable, GitHub direct clone blocked by DNS, no Paper jar/native World. **4 Node 22 focused shadow tests PASS** on exact source and test Git blob SHA (2/2 matched): normal sample, bodily urgency/nearby threat, unknown/missing cached state, malformed Paper sample. Existing Python-side newly-added shadow protocol/join negative tests have been committed but **NOT RUN in an exact checkout**. This is an offline engineering implementation result; Java/Paper/Node *integrated* execution is unverified.

**Next prerequisite before any TPS actuator or action-side 200TPS motor:** a truly source-bound per-WorldTick sensor snapshot with a bounded completed local L0 reflex/STOP handoff and measured update-to-action deadline. The Minecraft native path's traffic, scheduling and remote entity state may remain stale even when every received Paper plugin message produces a cache-only scan. The rate policy must fail closed until that boundary is satisfied.

## T1d — native receiver local L0 deadline guard (2026-10-26)

The existing Mineflayer callback now runs `handleBudgetedPaperTick` from
`adapters/mineflayer/paper_tick_deadline.mjs`. It checks the cache-only L0
shadow, then a **Node monotonic-clock, receive-to-completion** local deadline
before emitting either of the paired `paper_tick_sample` /
`paper_l0_shadow` stream records.

The first tick is explicitly `INITIAL_CADENCE_UNKNOWN`; later ticks are
`HOST_LOCAL_BUDGET_MET_ONLY` iff the local processing duration is **strictly
less than half** the *previous-to-current measured Node receive interval*.
This 1/2 is a conservative **DEV policy parameter** subject to later
measurement, *not* a certified physiological L0 response bound. Both 20TPS
and 200TPS nominal cases use their actually measured arrival intervals,
not requested server TPS. Server/JVM monotonic timestamps and Node monotonic
timestamps are **never subtracted across clock domains**.

Bad/missing/out-of-order ticks, invalid input and locally slow processing
fail closed: `PaperTickDeadlineGuard` latches permanently and the existing
Paper channel converts the failure into `adapter_error`, invalidating
subsequent ticks. The triggering tick emits **no accepted tick/L0 pair**.
The mechanism does not issue STOP or other physical effects, and it cannot
recover when accelerated World gameplay outruns the cognitive controller.
During this phase **there is no live TPS actuator at all**.

This demonstrates only that the synchronous **cached** shadow scan was
completed within an **observed local receive cadence**. It does **not**
establish server-to-client network delay, queue lateness, fresh World
observations, near-threat coverage, native S49 Action causality, 20/200TPS
physical Motor support or a per-tick real-time reflex guarantee.
`l0_fresh_world_tick_attested=false` and
`tps_admission_granted=false` stay mandatory. A native Paper World
trial with original packet/logs is still required for further claims.

**Validation:** Node 22.16.0 `node --check` for source and test files and
`node --test adapters/mineflayer/paper_tick_deadline.test.mjs`:
**7/7 PASS**, including unknown first cadence, 20/200TPS relative
intervals, deadline exceedance, sticky failure, missing/reordered tick,
forged authority and no partial receipt on refusal. Exact tested source
and test Git blob SHA both match the remote branch blobs (2/2).
Python 3.12, Maven/Paper API compile, physical World/Mineflayer execution,
exact-HEAD full-suite CI, R qualification and V science: **NOT RUN**.
