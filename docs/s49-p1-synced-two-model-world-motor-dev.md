# P1 hypothetical F → native DASH motor response with Mineflayer speed mapping ON

Scope **DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**.

## Motivating evidence

The [earlier two-model F experiment](https://github.com/rinsakamo/relay-self/actions/runs/40479045528) saw Paper-side model motor outputs 0.766861… and 1.0 but **identical first-action native displacement** because the client speed attribute projection was OFF.

The [attribute propagation control experiment](https://github.com/rinsakamo/relay-self/actions/runs/40487527583) held *the exact same* P1 model F (0.617712…) and compared projection OFF/ON. The existing bounded Mineflayer 1.21.8 projector made the real `minecraft:movement_speed` bonus visible to physics in 9 ACTIVE ticks and changed actual native displacement by +0.825008 m; Paper peak speed increased +2.076 m/s. This motivates holding client projection ON in both model-F scenarios.

## New paired design

Start **two independent fresh genuine disposable Paper 1.21.8 Worlds**. The original S49 Action owner runs the same 3 L0 decisions, 2 native S16 OUTCOMEs and original DEV M0 accounting in each. The only intentionally changed motor condition is an opt-in, **synthetically preloaded single-gauge P1 model fatigue**. All other motor/speed projection flags are identical:

| Arm | Model F preloaded | Paper speed→client physics |
| --- | ---: | --- |
| CARRY | 0.6177122410202606 | ON |
| WAIT_ASSUMED | 0.21616083122103735 | ON |

Both values and their source SHA `f126d16f42caa27230a02e4c818d7b7ae3c1d2e39e8ad75c55cd2ce9ddc16bd4` are earlier DEV hypothetical SelfBody model estimates, **not physical native fatigue readings**. In each World the Paper plugin adds its original P1-dependent temporary forward DASH modifier for the original S49 first Action only; second original Action is unboosted. The existing speed mapper excludes duplicate sprint.

Original S49 S15/S16 native action evidence, Paper's complete P1 gait tick replay, original session/World ids, first L0 threat/motor conditions, and per-World first Action `S49_SPEED_ATTR_NATIVE_BOUNDARY_DEV_V1` Node packet→attribute→physicsTick samples are independently checked. A separate DEV reviewer composes those checks, records absolute and between-World native displacement and server sampled speed, and rejects foreign sessions, spoofed source identities, unsynced attribute projection, missing packet or physics samples, extra issuers/readers, fake physical P1/recovery and false L0 admission.

**Physical motor separation is a measured outcome, not a requirement for a successful source-valid test.** If power differs but native displacement/speed do not, the negative result remains evidence. Native→Paper World clock synchronization is not asserted.

### Epistemic/authority limits

This experiment can establish how the real Minecraft motor responds to an *explicitly preloaded* P1 model fatigue value with the client speed attribute pathway working. It **cannot** establish longitudinal recovery of the *same Self* during physical WAIT, which is still only a conservative Paper static-candidate / hypothetical P1 replay. The reported model F is not a P1 native sensor measurement, and no physical L0 DASH power is admitted. Original S49 sole issuer, Mineflayer reader, S16 receipts and M0 postings are retained. No source-bound R WAIT, S10 learning, production P1 update, PR/main update, QUAL or SCI.

## Implementation/verification

- Existing `adapters/mineflayer/s49_paper_forward_dash_dev.py`: admit the Node attribute boundary capture with either of the two hardcoded DEV P1 preload arms, with the existing `S49_SPEED_ATTR_BOUNDARY_DEV_ONLY=1` and `S49_SPEED_ATTR_SYNC_DEV_ONLY=1` gates.
- New pure reviewer: `adapters/mineflayer/s49_p1_synced_motor_pair_dev.py`, reusing source reviewers for both original S49 physical S16 proof + Paper P1 replay and for both bounded Node native client attribute physics traces.
- New synthetic negative controls: `tests/test_s49_p1_synced_motor_pair_dev.py`. Focused Python 3.12/Ruff, Node 22 syntax and speed mapping tests, Java 21 plugin build **before** World.
- New independent opt-in paired-World workflow: `.github/workflows/self-p1-synced-motor-pair-dev.yml`; source evidence uploaded on success or failure, with run-id-scoped independent directories.

The exact tested commit and positive or negative measured physical results will be appended after inspecting the actual run. Previous evidence or failed runs will not be retroactively changed.

## Two genuine World results — 2026-10-27

**Exact World-tested code HEAD:** `9390143b778336bd2d1be99f465db530d014408a`.
[GitHub Actions run #40491478791](https://github.com/rinsakamo/relay-self/actions/runs/40491478791): **SUCCESS**. Python 3.12 focused **189 PASS** (72+72+45 dots, skip/fail not observed), Ruff **All checks passed**, Node 22 speed projection **3 PASS / 0 FAIL**, Java 21 `BUILD SUCCESS`, two original-S49-owned disposable Paper 1.21.8 Worlds, each with two original native S16 OUTCOMEs.

Both independent Worlds enabled `S49_SPEED_ATTR_SYNC_DEV_ONLY=1`; the same pinned Paper binary/plugin, original L0 decisions, action types, first target conditions and source reviewer gates were used. The **only intentionally varied motor model input** was the earlier hypothetical SelfBody P1 F.

| Native/Paper/Node observation | CARRY | WAIT_ASSUMED |
| --- | ---: | ---: |
| Hypothetically preloaded first F | **0.6177122410202606** | **0.21616083122103735** |
| Paper first applied normalized DASH power | **0.7668612208455023** | **1.0** |
| Paper mean applied normalized DASH power | 0.7530451601244172 | 1.0 |
| Paper boosted callbacks in first original S49 Action | **10** | **11** |
| Node packet samples with Paper DASH bonus | **5** | **6** |
| Node actual physicsTick samples with projected speed bonus | **8** | **10** |
| Node-local first Action physics displacement m | 3.632398900843789 | 4.137497782349481 |
| Paper server mean boosted-tick speed m/s | **6.508853203334039** | **7.522723240635418** |
| Paper sampled peak during boosted ticks m/s | 7.453515602079346 | 8.407958462125507 |
| Native original first S49 S16 displacement m | **3.7597989509361467** | **4.264897832441838** |
| Native original second unboosted S16 displacement m | 3.030157205468642 | 3.030157205468642 |
| Single P1 gait model final F | 0.6319075203598625 | 0.24684025162550322 |
| Original S49 DEV M0 remaining | 10.424695483987557 | 10.39 |

Reported **physical differences (WAIT_ASSUMED minus CARRY):**
- First applied Paper model DASH power **+0.23313877915449766** (23.31 percentage points).
- First original S49 S16 native XZ displacement **+0.5050988815056909 m**.
- Paper mean sampled speed on boosted ticks **+1.0138700373013796 m/s**.

Independent source join: both Paper gait histories replayed; both existing original S49 S15/S16 receipts validated; actual native packet and projected speed present during Node `physicsTick` **8/10** samples; second unboosted native S16 distance was identical. Each World retained the original sole issuer and original DEV S49 M0 ledger. The new read-only stage created **no** M0/P1 posting or extra native packet reader.

**Causal limitation critical:** the two fresh Worlds were **not time-phase matched** (10 versus 11 boosted Paper tick samples; 8 versus 10 Node projected-attribute physics ticks). Consequently, the +0.505 m and +1.014 m/s differences are real measured effects *associated with the distinct explicitly preloaded fatigue model conditions*, but neither magnitude is uniquely attributable to fatigue power alone. Some difference can arise from the unequal active boost duration or client/server tick phase. Source-backed **model-input→motor-output sensitivity observed** in DEV; precise causal effect size and real same-Self recovery remain **unestablished**.

- Both P1 values are hypothetical model preload states, not measured physiology or a witnessed longitudinal WAIT recovery.
- No real P1 fatigue sensor, no R-qualified global WAIT, no cross-process synchronous World tick, no promotion to physical L0 DASH power admission or SCI result.
- Artifact `p1-synced-model-motor-pair-40491478791-1`, ID **12728843278**, digest `sha256:6ca1ee6083007d174c836ad641a0f78c6f6ec82ebc66ae092b372f33798b0469`.
- Branch's production and protected main / Draft PRs remain unchanged. Only `DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN` is claimed.

**Next minimal DEV engineering work:** control the first Action's active boost duration (e.g. identical Paper tick count with original S49 owner-held fence) in both Worlds and quantify peak/mean speed on exactly aligned within-Action tick indices. That is distinct from attributing true same-Self physical recovery.
