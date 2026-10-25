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

Each sample contains ordered `index`, `Bukkit.getCurrentTick()` (`server_tick`), `World.getFullTime()` (`world_full_time`), same JVM `System.nanoTime()` (`wall_nanos`), native World/Player UUIDs, and explicit `l0_checked=false action_bound=false`. These clocks are **not presumed equivalent**. Because this uses a Bukkit scheduler callback, it is only one sample *within* each observed tick; it cannot certify a whole-tick event census or native Mineflayer physics updates. Log contents are not independently authenticated; the reader cannot attest the log's origin.

`paper_tick_probe.read_passive_paper_ticks(log_text, expected_world=<uuid>, expected_player=<uuid>)` refuses missing/duplicate/changed server and World tick, inconsistent callback order, wall-clock regression, foreign World/Player, forged L0/action flags, or >256 rows. It derives the observed average rate from first-to-last callback difference as `(row_count - 1) / wall_duration_seconds`, never from requested TPS. It does **not** create `TickWindow` for T0, because none of the samples proves the Self-side L0 check actually ran.

The opt-in plugin retains its existing **physical M0.2 behavior** if `dev-enabled=true`; these changes add **logging only**, but enabling the plugin as a whole is not an observation-only operation. Do not enable in live or qualified Worlds. The plugin's normal M0.2 tick charge is unchanged. No native Paper run or JAR build was performed here.

Next source-admission seam: independently bind S49 session and Action with original owner evidence, collect actual per-tick L0 decision receipts through the single native receive path, and only then allow the T0 policy to inspect paired, complete tick windows. Missing evidence must not silently be replaced with Paper samples.

### Verification

- Local Python 3.13.5: 15 focused synthetic parser tests PASS and syntax compile PASS; this is **not** the product-standard Python 3.12 run.
- Paper API 1.21.8 Java 21/JAR build: **NOT RUN**; no Maven or Paper dependency in this tool environment.
- Native Paper/Mineflayer gameplay, CI, actual rate modification, M0/P1 experiment, R/V qualification: **NOT RUN**.
