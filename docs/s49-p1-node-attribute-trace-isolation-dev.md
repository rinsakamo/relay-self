# P1 DASH Node 属性観測 OFF / MEM / FILE — DEV実Minecraft

**DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**。
Ancestor: `00ba35e694fbc2ea425f108cb4a874b60da9fb8f` from prior four-World OFF/ON test.

## 目的と境界

先行4 WorldではOFF時の第一S16距離がCARRY +0.195m、WAIT_ASSUMED +0.257m伸びた。しかし別World・非同期位相であり、同期trace停止が原因と断定していない。

このDEVでは通常時の`S49_SPEED_ATTR_SYNC_DEV_ONLY=1`（速度属性projection）をすべて維持し、**S49_SPEED_ATTR_BOUNDARY observer のみ**を三分割する。

- **OFF**: Node属性probeのイベントリスナー・physicsTickサンプリングなし。Node属性traceなし。
- **MEM**: FILEと同じ元Mineflayerの既存botイベント・物理tick内メモリ記録を行うが、第一CLEARでJSONシリアライズもfile openも同期I/Oも行わない。Node属性traceなし。メモリ内のtick数は外部へ出していないため検証上はUNKNOWNであり、Paper tickをNode tickの代用にしない。
- **FILE**: MEMと同じサンプラで、第一CLEARで既存のJSONシリアライズと`writeFileSync`を一回実施。ファイルを原本照合し、Node physics/正ブースト可視数をレビューする。

元S49 sole Action issuer/2 OUTCOME、0.60sの壁時計S15保持、Paper 1.21.8 build60、Mineflayer4.39.0、7連続Paperブーストtick、P1 gaitのカウント、元のS16移動量、未ブースト第二Action、M0 owner、Java21を維持する。単にDEV gateを分け、native packet readerを増設しない。Python 3.12 focused、Ruff、Node22、Java21、既存のPaper SHA検証を実World起動前に行う。

実行順序はFILE_CARRY → MEM_CARRY → OFF_CARRY → OFF_WAIT_ASSUMED → MEM_WAIT_ASSUMED → FILE_WAIT_ASSUMED。6独立World・6 sessionとし、同一疲労仮説内の負の測定値も棄却しない。Python reporterはS49 S15/S16 typed evidence、Paper元server logの7 tick、元release、Node FILE原本のモード一致、OFF/MEM Nodeファイル不在、モデルpreloadをsource-verifyする。OFF/MEM Node tick証拠を捏造せず、NULLに保持する。計測値比較はMEM−OFF、FILE−MEM、FILE−OFFの第一S16距離およびPaperの7ブーストtick平均sampled speedで行う。

**制約**: この試験はPaper/Node同一tickの位相一致や同一World内の因果比較ではなく、有限の独立World試行である。MEMに外部可視の原本がないのも明示的な制約。FILE−MEMが差を示しても同期書き込みの因果的寄与を単独で証明しない。もともとのT1n `node_timing.jsonl` の同期`writeSync()`約59ms停止とは別の実装・別ファイル経路。

新しいファイル:
- `adapters/mineflayer/s49_p1_attr_trace_isolation_review_dev.py`
- `tests/test_s49_p1_attr_trace_isolation_review_dev.py`
- `.github/workflows/self-p1-attr-trace-isolation-dev.yml`

実機結果はGitHub Actionsのexact SHA job logs、Paper/Node source artifactからのみ追記する。main、Draft PR #545/#634、R/SCIENCE、本番M0/P1は変更しない。

## Pilot first six-World native execution (reviewer FAIL, values from original stdout only)

[Actions #40619481077](https://github.com/rinsakamo/relay-self/actions/runs/40619481077), exact tested HEAD `3f515da543247fc2789990447793975f7ac2adc5`: **FAIL** only in post-World `review_worlds`, because Python checked `type(root) is Path` instead of `isinstance(root, Path)` and rejected an actual `PosixPath`. The six original S49 report outputs were emitted in their order and the always-artifact upload succeeded. This is **not** a source-complete six-World review, and cannot be relabeled workflow SUCCESS.

Pilot native first S16 movement from each original `S49_REPORT` printed during the completed physical stage:

| Arm | first S16 horizontal movement (m) | original unboosted second S16 (m) | Paper positive modifier ticks / total gait |
|---|---:|---:|---:|
| FILE_CARRY | 3.6473987246227164 | 3.030157205468642 | 7 / 13 |
| MEM_CARRY | 3.842587333487872 | 3.030157205468642 | 7 / 13 |
| OFF_CARRY | 3.647398724622719 | 3.0301572096472205 | 7 / 13 |
| OFF_WAIT_ASSUMED | 3.8452692791044356 | 3.030157205468642 | 7 / 13 |
| MEM_WAIT_ASSUMED | 3.845269279104439 | 3.030157205468642 | 7 / 13 |
| FILE_WAIT_ASSUMED | 3.8452692791044374 | 3.0301572054686403 | 7 / 13 |

CARRY: MEM−OFF +0.195188608865153m; FILE−MEM −0.195188608865156m; FILE−OFF within floating-point noise. WAIT_ASSUMED: all movement deltas effectively zero. These real-source values already **fail to repeat** the previous four-World finding that turning Node trace OFF always increased movement; thus none of the three modes has proven causal effect.

A legacy `p1_trace_ab_dev.native_trace_write_during_first_action=false` field appears in the pilot's all six reports even for FILE. **This field is not reliable for CLEAR-time I/O**; the source `bridge.mjs` unambiguously writes synchronously in FILE on CLEAR and returns before persistence in MEM. Trust mode-specific actual FILE presence and the Node source, not that legacy field. The corrected reviewer explicitly examines source-typed mode and actual files.

Reviewer error correction: `fa17075816bb49988d75ba0582c63489f749bd0d`; new six-World run [#40619793744](https://github.com/rinsakamo/relay-self/actions/runs/40619793744) is independent and must earn PASS on its own. No main/PR merge; QUAL/SCIENCE not run.

## Source-reviewed independent six-World rerun — PASS

[Actions #40619793744](https://github.com/rinsakamo/relay-self/actions/runs/40619793744), exact tested HEAD `fa17075816bb49988d75ba0582c63489f749bd0d`, **completed/SUCCESS**. The source reviewer `P1_NODE_TRACE_SIX_WORLD_REVIEW_PASS` and all six native World runs succeeded, with distinct session and World UUIDs, typed S15/S16 original Action receipts, Paper first Action seven-positive-tick/13-gait-tick series, FILE-only Node source and both OFF/MEM files absent. This does not promote QUAL/SCIENCE.

| Mode | CARRY first S16 (m) | WAIT_ASSUMED first S16 (m) | CARRY Paper mean positive speed (m/s) | WAIT Paper mean positive speed (m/s) |
|---|---:|---:|---:|---:|
| OFF | 3.647398720447 | 3.845269279104 | 6.267369234999 | 6.639164841390 |
| MEM | 3.656538103083 | 3.845269279104 | 5.835939618133 | 6.639164841390 |
| FILE | 4.140090360652 | 4.102717566258 | 6.567469500404 | 7.029424911612 |

From the exact reviewer `per_model_differences`:
- CARRY: MEM−OFF **+0.009139382637m**, FILE−MEM **+0.483552257569m**, FILE−OFF **+0.492691640206m**; speed MEM−OFF −0.431429616866m/s, FILE−MEM +0.731529882271m/s.
- WAIT_ASSUMED: MEM−OFF effectively 0m, FILE−MEM **+0.257448287153m**, FILE−OFF **+0.257448287153m**; speed FILE−MEM +0.390260070222m/s.

FILE source Node physical callback counts: CARRY **13**, positive attribute visible **8**; WAIT_ASSUMED **12**, positive attribute visible **8**. OFF/MEM counts are **UNKNOWN**, not zero. All six Paper source positive boosts = **7** and Paper total gait callbacks = **13**.

This run's FILE condition is **longer** than MEM for both P1 model assumptions. Earlier pilot's FILE condition was **shorter** than MEM for CARRY and effectively equal for WAIT_ASSUMED. Hence a consistent positive or negative movement effect for synchronous CLEAR-write is **not demonstrated**. The previous four-World OFF advantage also fails as a repeatable direction in these datasets. Different independent Worlds, unmeasured relative Node/Paper physics phase and varying original first SET→CLEAR callback counts remain major confounds.

Artifact `p1-attr-isolation-six-worlds-40619793744-1`, ID **12786594585**, ZIP SHA256 **d4b4b731cd55b56bc92edc267a443d4d61d323f12bbb60a3ad803b1df851a82e**. Pre-World Python 3.12 focused tests all PASS, Ruff PASS, Node22 three tests PASS, Java21 Paper plugin build and pinned Paper SHA PASS; complete SUCCESS step and source artifacts verified from Actions API.

### Interpretation and next step

The active `S49_SPEED_ATTR_SYNC_DEV_ONLY=1` is client attribute projection, not the source of T1n `node_timing.jsonl` `writeSync()`. The targeted synchronous FILE write occurs at original S49 CLEAR. The state of evidence after **12 new real Worlds** (6 pilot World outputs but reviewer FAIL; 6 full source-reviewed PASS) is that *probe effect is possible but not isolated*, and Paper/Node phase and original Action duration remain unresolved. There is no source-bound measured number for MEM/OFF Node physicsTicks, by design.

The minimally informative next DEV step is therefore **Node producer-physicsTick-controlled first original S15 hold** with bounded timeout, original single reader/issuer and Paper source still independently audited. Repeating more unconstrained wall-clock 0.60s trials alone would not remove the primary phase confound. No production authority, QUAL grant or SCIENCE eligibility is implied.

**Final:** `DEV_WORLD_OBSERVED / DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`. Main and Draft #545/#634 unchanged. Evidence report appended on this isolated DEV branch only.
