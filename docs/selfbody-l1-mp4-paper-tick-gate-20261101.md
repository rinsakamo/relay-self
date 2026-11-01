# RelaySelf — L1-MP4 Paper World-tick 前向き予測受付境界（DEV-only）

2026-11-01。親 [Draft #655](https://github.com/rinsakamo/relay-self/pull/655) exact HEAD `774c06965f83058ff0c55589f4369b5b82615ba3` から隔離branch `dev/l1-mp4-paper-tick-gate-20261101` を作成。前回#653 MP3実Worldは **1回実施済み・grant消費済み**。このbranchで実World、Java server/Node、Action、学習更新の実行は **0**。

## 解く境界

前回#655のhost loggerは `x[t]` callbackを読む→ `c*x[t]` 予測をfsync→次host readlineの順序を7件確認した。しかし**次Paper callbackが既に生成済みでOS bufferにあった可能性**を排除できず、物理前向きは `UNKNOWN`。

MP4は *Paperプラグインmain thread* の `getFullTime()` を、次 `S50_DEV_WAIT_TICK` 観測の受付を比較する単一World時系列境界として使う。Node/hostとPaperの異なるmonotonic clockを比較しない。

## 実装（既存S50 source ownerへのdefault-OFF拡張）

- `S50ForecastGate.java`：Bukkit依存なしの小さな単一WAIT-window状態機械。World/subject/marker/前回観測tickに結合された**7件以下**の受付・失効と、対象tick callbackでの1回限り照合。Action issuer・記憶・物理会計・元S49/S16 ownerには触れない。
- Paper `RelayMetabolismPlugin`：config `s50-forecast-gate-dev: false`（default）かつ既存 `s50-tick-meter-dev` がenabledのときだけ、console-only `relaydevforecast <marker> <prior_tick> <target_tick> <predicted_m> <ticket_sha256>` を受け付ける。
- `relaydevwait` で既存WAIT窓と一緒に受付を初期化。第1 `S50_DEV_WAIT_TICK` は `x[t]` として観測し、後続を予測可能にする。
- **Paperが受付する条件**：同一marker/World/subject、前回実際に観測したtick `t` と `prior_tick=t` が一致、`target_tick=t+1`、`current Paper getFullTime()<target_tick`、有限の非負予測、64 hexモデルチケット、重複受付なし。遅延・重複・別World・別subject・別window・欠測は拒否。hostが追いつかないtickは欠測のまま、後付け採点で穴埋めしない。
- Paper console受付 `S50_DEV_FORECAST_ACCEPT` / `REJECT` に受付時のWorld fulltimeと対象tick/チケットを原sourceとして記録。対象の `S50_DEV_WAIT_TICK` callback内で `S50_DEV_FORECAST_TICK` を記録し、受付と**同じmain thread内の対象tick順序**を後から照合可能にする。
- `S50_DEV_FORECAST_TICK`が `NO_ACCEPTED_FORECAST`の場合は物理gateの予測成功に数えない。モデルが安価なlinearと同じ情報・アルゴリズムなら、matchedでも `CHEAP_EQUIVALENT` のまま。

### 立証範囲（重要）

Paper main threadの受付時 `fulltime<t+1` により、**対象tickの元S50物理サンプリングcallbackより前にPaperが予測値を受理した事実**を示せる設計。この区間は同一World内のserver tick順序であり、OS stdout buffer問題を回避する。

ただし、単独ではMinecraft内のサブtick物理積分、Packet順序、S15 effective clear、将来の状態がそもそも計算・可視化されていないこと、物理運動の因果的影響、World間汎化、真正なL1性能優位、Goal成功、資格やSCIENCEを**証明しない**。Paper pluginの「受付」はその値が本当にL1から生成されたことの証明でもない。host側が元MP3 source-bind/immutable training/ticketと照合する必要がある。

### 今回の検証と次の試験

- オフラインではJava21 pure classのnegative tests（7連続受付、late/replay/foreign/missing/nonfinite/skip/source spoof）、Mavenで元Paper pluginの実コンパイル、repository contractsをCIで実行する。
- **今回の新規実Minecraft試験は0回**。前のgrantを再使用しない。新World/Java/Nodeは起動しない。過去の#655 physical resultを改変・再判定しない。
- 将来の別grantのもと、元host loggerが `S50_DEV_WAIT_TICK(t)` の変位 `x[t]` を読むと `relaydevforecast` を既存console経路で送信し、Paperが *t+1より前* に `ACCEPT` した場合のみ予測を採点。すでにtick t+1が通過していれば `LATE_TARGET_TICK` として拒否し、欠測を維持。新コマンドはゲーム内Actionではないが、サーバに対する予測データ送信なので実Worldでは別途事前許可と元owner監査が必要。
- 原Paper stdout・S50原本・S16・S7・cleanupの厳密readback、追加issuer/probe/Actionなし、同情報cheapベースラインを厳守。

**Classification:** `MP4_PAPER_TICK_GATE_OFFLINE_IMPLEMENTED / PHYSICAL_ACCEPTANCE_NOT_RUN / PREVIOUS_MP3_HOST_READ_ORDER_ONLY / CHEAP_EQUIVALENT / GOAL_UNDETERMINED / L10_S10_S11_0 / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`。


---

## MP4b / 既存host→Paper console readonly配線（DEV OFFLINE）

親MP3 `HostPrediction` の元stdout collector hookにオプトイン `enable_paper_gate()` を追加。**既存collectorのソースファイル・読み取り回数・S49 Action issuerは変更しない。**

1. `PRE_FORWARD` originalを見て元の過去World係数・対象session/Action/World・計画subjectをimmutable ticketに固定し、bounded `PaperForecastDispatch` を初期化。
2. `S50_DEV_WAIT_TICK(t)` を元collectorで観測→MP3の既存 `PREDICTION_FIXED(t+1)` fsync→7件上限の `ForecastCommand` をqueueへ入れる。コンソールを直接触る別readerは追加しない。
3. S49 hostのopt-in `--l1-paper-forecast-gate-dev` がある場合だけ、**元のPaper Java stdin / `_command`** で `relaydevforecast marker t t+1 prediction ticket_sha256` を一回だけ送信し、`PAPER_CONSOLE_WRITE` をjournalに追記。二度送らない。Queueは7上限、sessionとWorld違い・非finite値・無効digestはreject。送信/OS pipe flushはPaper上の受付ではない。
4. 元Paper console `S50_DEV_FORECAST_ACCEPT/REJECT` と `S50_DEV_FORECAST_TICK` の元原本だけが受付とsampling順を判断できる。**Python側のQUEUED / CONSOLE_WRITEを物理的なACCEPTへ昇格させない**。遅延は `LATE_TARGET_TICK` / `NO_ACCEPTED_FORECAST`、失敗は欠測保持、retry禁止。
5. original Node/Java shutdownの前に診断送信タスクをboundedに終了。元S49→S16の成功にPaper受付の捏造をしない。

### preflight と保護

今回の`--l1-paper-forecast-gate-dev` には前提 `--l1-prediction-journal` と元route B、既存S50 Paper asset bundleが必要。**Java起動前**に元SHA256 pin済みconfigが `dev-enabled:true`、`s50-tick-meter-dev:true`、`s50-forecast-gate-dev:true` をそれぞれ一度だけ含むことを拒否可能に照合する。false/defaultなら実行禁止。これは実Worldのgrant取得を意味せず、適用grantは別に必要。

Python3.12 synthetic fake console/JDK21 pure tick gate/Maven Paper compile/related S50 host regressionで検証。既存#655 MP3物理原本への遡及採点・手直し禁止。新World/Node/Java実行 **0**。

重要: 予測のtarget tick=t+1は20TPS前後のMinecraftでは短時間。実際の通信が間に合わなければ安全な**拒否**が正しい結果。成功率を上げるためWorldを停止・巻戻し・tick順序変更しない。受付が0/7でもDEVの遅延特性として報告する。S49元operatorは別grantなしに実Worldで再試行しない。

**状態上限:** `DEV_OFFLINE_HOST_PAPER_CONSOLE_CONTRACT_ONLY / PAPER_PHYSICAL_ACCEPTANCE_NOT_RUN / GRANT_CONSUMED / CHEAP_EQUIVALENT / GOAL_UNDETERMINED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`。


---

## 2026-11-01 02:55 UTC / MP4 physical World1 — DEV FAIL preserved, next two not started

- Run: https://github.com/rinsakamo/relay-self/actions/runs/41267002026
- Executing commit: `12f1d2237ef7327470c3ffe7084e01df2430c1ba`; pinned Paper 1.21.8 SHA and built plugin SHA recorded in run1 preflight/original.
- Paper callback `S50_DEV_WAIT_TICK` 8件 (tick257–264) / MP3 host prediction `PREDICTION_FIXED`7件 / `PAPER_CONSOLE_WRITE`7件。Paper `ACCEPT`0 / `REJECT`6 / `MATCH`0。拒否内訳：`LATE_TARGET_TICK`2、`NOT_NEXT_OBSERVED_TICK`4。console writeはPaper acceptanceでない。拒否のない残り1件も `ACCEPT` には数えない。
- FAILの**直接の原因**: 新built Paper pluginに#653既存S50 original `S50_DEV_INPUT_TICK` callbackが欠落。Paper WAIT 8件は存在したがS50入力8件は0。元 `wait_live_paper_window` が `missing complete live Paper WAIT/INPUT 8x2 window` でfail-closed。元S49 S16 OUTCOMEは別途成立、Node/Java exit0、World delete/25565 port rebind PASS。
- 原因特定の根拠：旧実機で用いた S owner plugin source exact `e6d901d7dc3effb5c7516350233383fbb982bbb1` に `s50-input-witness-dev`、`PlayerInputEvent`、`p.getCurrentInput()` `S50_DEV_INPUT_TICK` があるが、#657基点のmain Paper sourceにはそれらがなかった。見落としをオフラインCIで検出できず失敗として残す。
- 原本：[GitHub Actions artifact](https://github.com/rinsakamo/relay-self/actions/runs/41267002026) `l1-mp4-three-world-dev-41267002026-1`。元Paper stdout、S7/S16、host journal、Node witness、launcher.log、dev-readback、summary含む。**World2/3は未起動**、前回の失敗は再実行していない。

### 修正境界

過去 `e6d901...` のS50 input witnessのfield/Java sourceを、#657のdefault-OFF Paper pluginへ限定復元。元ownerに合わせ、`s50-input-witness-dev: false` default→実行config TRUE + SHA256前提にする。これは`LAST_REPORTED_INPUT_CALLBACK_SAMPLE_ONLY`の観測でありeffective clear/full-tick idle証明ではない。

残る新規2 Worldは `--first-world-index 2 --worlds 2` の**新しい一回限りのworkflowタグ**で実施可能とし、最初の破損Source/invalid cleanupで残りを停止。**World1の予測0/7受付を後付け成功へ変更しない**。

Goal UNDETERMINED / CHEAP_EQUIVALENT / L10/S10/S11=0 / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN。
