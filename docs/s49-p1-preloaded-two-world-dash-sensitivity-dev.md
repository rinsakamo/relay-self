# P1 next-epoch model F → physically applied DASH: two fresh World DEV sensitivity

Scope: **DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.

## Motivation and exact epistemic boundary

The original S49 native second Action in [run #40476376338](https://github.com/rinsakamo/relay-self/actions/runs/40476376338) was an **unboosted** original native MOVE (3.0301572096 m). It cannot identify whether the recovered-P1 SelfBody model would yield a stronger physical DASH.

The first step toward discriminating *motor output response*, NOT physical fatigue recovery, is to initialize two independently created disposable Paper 1.21.8 Worlds with the two **historical DEV model hypotheses** from that run:

| World arm | Counterfactual initial P1 F | Role |
| --- | ---: | --- |
| CARRY | 0.6177122410202606 | Prior first-DASH final F held over candidate |
| WAIT_ASSUMED | 0.21616083122103735 | Hypothetical WAIT for 175 candidate static ticks |

The candidate source SHA256 is `f126d16f42caa27230a02e4c818d7b7ae3c1d2e39e8ad75c55cd2ce9ddc16bd4`, case labels and exact values are hardcoded **only as DEV test cases**, never as P1 producer state. There is **no longitudinal observed recovery** in either new World. The Paper DEV plugin rejects arbitrary fatigue preloads and defaults to historical 0.6 otherwise.

In each new World, the **original S49 issuer** authorizes and executes the same scripted two native Actions; only the *first* gets the existing forward-DASH Paper speed modifier, governed by the single P1 gait model and its bounded P1 fade. Second native Action remains unboosted. M0 DASH extra is posted solely through the original DEV S49 owner against the existing native S16 OUTCOME; no new Action grant, issuer, native reader, P1 real state or R tick is created.

The new DEV pair review replays **every first-DASH Paper P1 World tick**, verifies both original S16 before/after source frames and movement distances, compares starting native y/health/food/zombie distance, and measures Paper applied DASH power, Paper sampled forward speed, and actual first Action native displacement.

The experiment **can** identify a physical output sensitivity to explicitly preloaded model F in independently created Worlds, subject to clock variation. It **cannot** establish that static WAIT ever changed the same Self's true P1 fatigue or caused a longitudinal speed gain. Different World clock phases and native client input timing are uncalibrated. Physical change is recorded only if both native distance and Paper speed gains exceed illustrative DEV thresholds, otherwise **NOT_ESTABLISHED**; absence of a positive difference is not silently turned into PASS-of-physical-gain.

## Implementation

- `adapters/mineflayer/s49_paper_forward_dash_dev.py`: independent opt-in `--p1-model-pair-case-dev CARRY|WAIT_ASSUMED`, requires `S49_P1_DASH_PAIR_DEV_ONLY=1` and existing P1-live DEV gates. Existing default 0.6 behavior unchanged. Source-replays both preloaded initial F values, explicitly allows low-F full-power plateau.
- `adapters/mineflayer/s49_paper_dash_dev/src/main/java/io/github/rinsakamo/relays49dash/S49DashDevPlugin.java`: one-shot Paper config validates pair-only preloads, otherwise retains the 0.6 initial fatigue guard.
- `adapters/mineflayer/s49_p1_dash_pair_review_dev.py`: independent file/source review of both fresh original sessions, Paper tick output, observed native displacement and ambiguity.
- `tests/test_s49_p1_dash_pair_review_dev.py`: synthetic positive, negative and plateau/fade model replays; rejects invalid source, preconditions, replay flags, unadmitted P1 initial state.
- `.github/workflows/self-p1-dash-preloaded-pair-dev.yml`: Python 3.12 focused and Ruff before any World, Java 21 plugin, Node 22 source, pinned stable Paper 1.21.8 build 60, two fresh original S49 sessions in independent Worlds, an honest comparison and both raw artifacts.

No main, protected Draft PR, QUAL or SCI changes. Exact tested commit/run/results will be appended *after* real DEV validation.
