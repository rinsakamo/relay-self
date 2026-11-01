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
