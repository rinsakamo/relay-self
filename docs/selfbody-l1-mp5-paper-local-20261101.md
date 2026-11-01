# RelaySelf — L1-MP5 Paper-local 次tick運動予測（DEV / shadow）

2026-11-01。親 [Draft PR #657](https://github.com/rinsakamo/relay-self/pull/657) の **MP4 World 1–3失敗・部分成功の実World原本を保存**した上で、独立branch `dev/l1-mp5-paper-local-forecast-20261101` へstack。MP4原試験：3/3新World、Paper 1tickコンソール受付0件。host経由1tick往復方式はその条件では成立しなかった。

## 仮説と因果境界

過去Worldから得た係数 `0.20331885786720635` を、元S49が唯一のnative Actionを発行する**前**にPaperへ一度だけfreezeする。Paperの元 `S50_DEV_WAIT_TICK` callbackで実測変位 `x[t]` を取得した後、同じmain-thread callbackの中で `pred[t+1]=c*x[t]` を保存。次のPaper callback `t+1` で以前の予測を実測 `x[t+1]` と照合してから、後続の予測を作る。原Paper tick/host異時計を比較しない。**元S49 Action ownerとS16、Paperの物理代謝会計を一切書き換えない。**

```
previous-World original -> frozen MP3 model/ticket
                                  |
S49 original PRE_FORWARD source --+--> console-only relaydevlocalmodel (1回) --> Paper MODEL_ARM
                                  |                                      |
                   S49 native MOVE (sole owner)                   POST_CLEAR / WAIT_BEGIN
                                                                          |
Paper WAIT callback tick t: original x[t] sampled --> model c*x[t] frozen for tick t+1
Paper WAIT callback tick t+1: previous prediction scored against x[t+1], then next frozen
```

### 追加実装

- `S50PaperLocalForecast.java`: Bukkit依存なし、1モデル/marker/World/subject/ticket SHAを1度だけ `arm`; `begin`は事前登録した同一Worldでのみ。元WAIT実測8件を連続tickで消費、 **7個の事前予測・7個の事後採点**、新規学習と係数更新なし。不連続tick、重複、過大値、非有限、再arm、別World/subjectをfail-closed。
- `RelayMetabolismPlugin`: `s50-paper-local-forecast-dev: false` default OFF。explicit opt-inは元 `s50-tick-meter-dev:true`、`s50-input-witness-dev:true` を必須とし、旧 `s50-forecast-gate-dev`（MP4 console RTT）と排他。console-only `relaydevlocalmodel marker slope ticketSHA` はPRE_FORWARD後、元Action前のみ登録可能。Paper `S50_DEV_LOCAL_MODEL_ARM`、`S50_DEV_LOCAL_WAIT_ARMED`、`S50_DEV_LOCAL_FORECAST_FIXED` / `S50_DEV_LOCAL_FORECAST_SCORE` original stdoutを追加するが、元 `S50_DEV_WAIT_TICK` / `S50_DEV_INPUT_TICK` / 元Action・代謝写像には介入しない。
- `self_body_s50_l1_paper_local.py`: pinned config SHA、flag重複・FALSE・旧gate併用・モデル数値・console injection拒否。元 `PRE_FORWARD` originalから作られたMP3 `FrozenPredictionTicket` のモデル係数とSHAを1回送付。Paper `MODEL_ARM` original readbackがmarker/World/subject/チケット/係数に厳密一致したとき**のみ**既存 `executor.execute` に進む。
- `self_body_s50_world_dev.py`: 新しい `--l1-paper-local-forecast-dev`（default OFF）。既存MP3 journal、route Bと元L23 Paper asset 6 SHAが必須。旧MP4 per-tick dispatchの有無と排他。モデル係数は元MP3 train archiveのみ。原本確認不可なら**Action 0でBLOCK**。World中モデルの更新・refit・S10/S11/L10 admissionなし。

### 何を証明し、何を証明しないか

実際のPaperログで `MODEL_ARM` がPRE_FORWARD後・元S49 MOVE前にあり、callback tで `FIXED prior=t target=t+1`、次callback t+1で `SCORE` を出した場合、**同一Paper main-thread observer上で次のサンプリングcallbackより前に予測を保存していた**ことは言える。これはMP4のhost RTT欠落を回避する。

一方、Physics substep、Packet受理、S15 effective clear、tick t+1の内部物理積分より必ず前の順序、全tick入力idle、Goal達成、学習による真の汎化、**cheap linear超過**は示さない。今回のpredictorはcheap linearと完全同型で、同値を明示する。MP5のローカル計算はPaper内で行われる診断shadowであり、**L1が実際にアクションを決定したことや身体が自ら学習したことを示すものではない**。

### 検証・再試験条件

- CI：Java21純状態機械（model immutable/8 callback/7 forecast/7 score/late/foreign/replay）、既存MP4ゲート、Python3.12 config/receipt偽装拒否、S49/S50関連regression、Ruff、compileall、実Paper API Maven。
- 既存3実World原本、#653/537/657報告の内容は変更しない。今回のbranchから**実World起動0回（offline stage）**。
- 新たな実World検証では、Paper plugin/typed Node runtime/S49実行資材のSHAを検査し、古いMP4 console gateをOFF、MP5 localをON、全原本を保存。新World 1件DEV→単一WorldのVALID/FAIL分類。元owner `S50 INPUT+WAIT 8x2`、元S49 S16 OUTCOME、Node/Java exit0、cleanupを監査する。
- このプロジェクトの継続grantはDEV対象に限定され、前回3-Worldロットは3/3消費済み。以降は**新しい独立試験としてWorld回数を数える**。再試行0、main / 他レーン / 過去原本保護。

Status ceiling: `MP5_PAPER_LOCAL_OFFLINE_ONLY / PRIOR_MODEL_CHEAP_EQUIVALENT / PAPER_LOCAL_PHYSICAL_PREQUENTIAL_UNTESTED / GOAL_UNDETERMINED / L10_S10_S11_0 / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`。


---

## MP5 実World DEV結果（2026-11-01 03:27 UTC）

**実行済み**。新規使い捨てMinecraft World 1回、元S49 native Action 1件、再試行0。[実行workflow #41269170943](https://github.com/rinsakamo/relay-self/actions/runs/41269170943) **SUCCESS**、実行HEAD `ded5076a752751cf38e8e42d94ef4c484919d9fe`。保護される過去MP3/MP4 3 Worldsとmainは未変更。

- JDK21 pure状態機械113チェックPASS、元S50関連Python3.12 regression 69 PASS（実Worldワークフロー事前検証）、Maven実Paper plugin `BUILD SUCCESS`、Pinned Paper 1.21.8 build60 / Mineflayer 4.39.0 / config SHA照合。独立preflight通過後に限りWorld 1回起動。
- 元Paper stdoutに `S50_DEV_LOCAL_MODEL_ARM` **1件**（World tick244、S49元Action開始前、係数 `0.20331885786720635`、ticket `c72cecfcd80cd8e7a3b69a9d39ca2fa1d60f5f5d7e23ae0486761826ff2d1775`）、`S50_DEV_LOCAL_WAIT_ARMED` **1件**（World tick251）を確認。対象World `8344f804-672f-4115-acf3-202852b5b098`、subject `dcae346d-e66f-331a-b459-a5a5370e9738`。
- 元 `S50_DEV_WAIT_TICK` と `S50_DEV_INPUT_TICK` **各8件**、tick252–259。各tickで元WAIT観測 `x[t]` → `S50_DEV_LOCAL_FORECAST_FIXED` (次tick対象) と後続callbackで `S50_DEV_LOCAL_FORECAST_SCORE` の照合 **7/7**。原stdoutで `WAIT[t] < FIXED[t→t+1] < WAIT[t+1] < SCORE[t+1]` を独立readback。stdout-original==server.log byte-level SHA256 `efb0c0e42a7db8a42f17117043ad5a64c6dc68101a4477c1ebe4bf79db154966`。
- 7件の平均絶対誤差 **MAE 0.0006927084716710721m**、RMSE 0.0013140724536525347m。同じx[t]から同じ係数を適用するcheap linearとは数学的に**完全同値**。zero baseline MAE 0.0021077733153767675m、last baseline MAE 0.0070703126144747875m。
- **重要**：今回の変位の時間系列は既存学習Worldとほぼ同一（`0.0494921883m → 0.0095436049m → 0.0052108083m → 以後ゼロ`）。別Worldであるが、未知条件への汎化・適応やL1固有の学習優越を示さない。**Paper内の次callback前予測固定のみが新たに実証された**。
- 元S49/S16/S50 owner DEV PASS、Node exit0 / Java exit0、ポート再bind/cleanup PASS。Original Packet/S16/S7/host journal/原Paper stdoutをGitHub artifact `mp5-paper-local-one-world-41269170943-1` に保存。各ファイルのSHAと再解析出力は[独立readback JSON](../evidence/issue653-mp5-paper-local-20261101/run1/independent-mp5-readback.json)。
- 科学・学習資格：元Goal `UNDETERMINED`、L10/S10/S11/学習更新0。tick内部物理積分順序 / effective clear / full-tick input idle / 異条件の汎化は NOT_ATTESTED。

**判定：`DEV_WORLD_PASS_PAPER_LOCAL_CALLBACK_PREQUENTIAL_7_OF_7 / SAME_INFORMATION_CHEAP_EQUIVALENT / GOAL_UNDETERMINED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`。** 今回のMP5新規Worldは1/1消費済み、再実行していない。
