# P1 matched Paper modifier plus original S49 S15 owner-held Paper tick boundary — DEV

Scope: **DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.

## Prior real source

Two original S49 sessions in independent Paper 1.21.8 Worlds already produced **exactly 7 positive speed modifier callbacks** each, with both native and Node source verification PASS ([#40495397519](https://github.com/rinsakamo/relay-self/actions/runs/40495397519)). A second DEV run independently compared Paper ordinals 2–7 and Node consecutive active speed-attribute physics samples, also PASS ([#40503444978](https://github.com/rinsakamo/relay-self/actions/runs/40503444978)). The original S15 first Action remained held by a fixed **0.60-second host timer**, which does not align with a guaranteed count of Paper World tick samples.

## New minimal owner-controlled DEV experiment

Only with `S49_ORIGINAL_OWNER_TICK_HOLD_DEV_ONLY=1` and `--original-owner-paper-tick-hold-dev`, and only with the existing exact P1 pair, native-edge, speed-attribute and matched-seven-positive-boost DEV flags:

- The original S49 Action Executor calls the unchanged S14 grant path, then S15 sends the original Mineflayer sprint+forward command and receives its original native ACK.
- In the **same original S15 execution function**, an optional callback replaces the usual 0.60-second hold with a wait for the producer-local Paper sample **index=15** for this exact Action/session; original S15 then issues the one and only CLEAR, consumes its original native ACK and closes S16.
- The Paper plugin still caps its temporary speed modifier at exactly **7 positive Paper callbacks**; no new native command or owner is added. Paper does not clear Mineflayer controls.
- The source-local wait checks contiguous Paper world tick rows and single original player/World, positive modifier count 7 and modifier absent on sample 15, without accepting fabricated session/tick changes. Await has a bounded timeout and native cleanup on failure.

Run independent real Worlds, CARRY F=0.6177122410202606 and WAIT_ASSUMED F=0.21616083122103735, both with speed projection ON. Source reviewer reuses existing S15/S16, Paper fatigue tick replay, seven-positive-boost source and Node stable-phase readback; independently validates the original S15 paper tick hold receipt, actual first/second native movement and matched source owner.

**Critical distinction:** this matches the *original S15's producer-local Paper observation hold target*, not actual synchronized native control start/stop World ticks. The first Paper ARM precedes native APPLIED and host log receipt times can differ. Two Worlds have separate Paper and Node clocks. The **exact original native Action duration in World ticks is not attested**; the measured displacement delta is descriptive, not a qualified isolated physiological fatigue effect. The initial fatigue values remain synthetic model hypotheses, **not** physical recovery of the same Self during genuine WAIT.

No R WAIT/SCI/FULL/main/PR merge, no extra P1 or M0 ledger posts, no new Action issuer or packet reader. Record actual run/results only after local Python 3.12 focused and Ruff, Node 22 and Java 21 all pass and two fresh disposable Paper Worlds complete.

## Real original S49 owner-held Paper tick DEV result — 2026-10-27

**Exact original World-tested code HEAD:** `a7b59fe936e8eecba57f923bec967e00a50d834e`.
[GitHub Actions run #40511721549](https://github.com/rinsakamo/relay-self/actions/runs/40511721549): **SUCCESS**.

- Python 3.12 focused **292 PASS**, 0 visible FAIL or SKIP; Ruff **All checks passed**.
- Node 22 speed mapper regression **3 PASS/0 FAIL**, Java 21 `BUILD SUCCESS`.
- Two fresh genuine Paper 1.21.8 Worlds, each with the **same original S49 issuer** and two original S15/S16 native Action OUTCOMEs, native cleanup ACKs and original S49 DEV M0 posted only by its owner.
- Paper producer-local sample index **15** reached in each World inside the *original* S15 Action hold callback **before** original S15 issues CLEAR. No new native reader, Action issuer or Paper motor-owner.
- Paper first Action **7 consecutive positive DASH modifier ticks** and **16 total Paper gait samples** in both Worlds. Node projected Paper DASH speed present for 6 active physicsTick callbacks in both. Distinct Node-local active first Action physics callbacks: **16 CARRY vs 15 WAIT_ASSUMED**; this timing mismatch remains and is not erased.

| Source-verified observation | CARRY model F=0.6177122410 | WAIT_ASSUMED model F=0.2161608312 |
| --- | ---: | ---: |
| Original S15 paper hold target index | **15** | **15** |
| Paper first gait tick | 247 | 249 |
| Original S15 hold target Paper World tick | **261** | **263** |
| Paper last first Action gait tick | 262 | 264 |
| Paper first Action gait samples | **16** | **16** |
| Positive Paper DASH modifier ticks | **7** | **7** |
| Node active physicsTick samples | **16** | **15** |
| Node active samples with visible DASH attribute | **6** | **6** |
| Paper sampled peak speed m/s | 7.644857962413143 | 8.319954119040972 |
| Original first S49 S16 native XZ movement m | **4.787992001375678** | **4.70930773513926** |
| Original second S16 native XZ movement m | 3.030157209647223 | 3.030157205468642 |
| Original S49 DEV M0 remaining | 10.447001274774198 | 10.43 |

**Measured native first S16 distance difference (WAIT_ASSUMED minus CARRY): −0.07868426623641867 m.** This reverses the previous positive native displacement differences, despite the same seven positive Paper bonus callbacks, the same first owner-held Paper observation index and visibly different P1 model motor power. It must be reported as a **negative result for a repeatable low-F native total-distance improvement**, not erased or reclassified as a positive gain.

The independent read-only post-run steady-phase sources still report:
- Paper speed differences across positive ordinals 2–7 (WAIT_ASSUMED minus CARRY): `[≈0, +0.3012052261, +0.4656632795, +0.5637367721, +0.6172848991, +0.6546789855]` m/s.
- Node consecutive positive-attribute physics speed-proxy differences on its common local ordinal windows: `[+0.4656632795, +0.5637367721, +0.6172848991, +0.6546789855, +0.6750961566]` m/s.

These positive short-interval speed contrasts **do not imply** a positive whole-Action S16 displacement gain. Client host event phase, Action onset/offset within Paper ticks and the Node active callback count remain unmatched, even though producer-local hold target and Paper positive tick counts were both fixed. Exact native control duration World ticks, cross-World clock synchronicity and fully isolated physiological fatigue motor effects remain **not established**.

**Evidence artifact:** `p1-original-owner-tick-hold-pair-40511721549-1`, ID **12736709651**, digest `sha256:1de35e4f3806eb690a3b69d411b81a073e940f004fd567b102df31a05cf21d67`.

Prior failed CI [#40511492106](https://github.com/rinsakamo/relay-self/actions/runs/40511492106) was Ruff import order and stopped **before World**. That FAIL stays in history; its correction was tested in the fresh successful World run above.

**Final classification:** `DEV_WORLD_OBSERVED / DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`. Both P1 input values were *deliberately model-preloaded* on different Worlds, not derived from one physical Self's observed WAIT recovery. No R-qualified global WAIT, P1 production state update, M0 extra by new reviewer, L0 physical DASH power grant or SCIENCE result. Source code in this isolated DEV branch; no protected main or Draft PR change.

**Recommended next DEV engineering step:** use the *same original S49 S15 ownership* to hold until a measured **Node-local physicsTick count** or add paired explicit source-local native control start/end markers, while preserving a bounded cleanup timeout. Only then test whether the native Action elapsed control phase and Node active callback counts become comparable. Paper index 15 alone does **not** match native active tick count.
