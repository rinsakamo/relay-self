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
