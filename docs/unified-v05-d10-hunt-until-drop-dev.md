# D10 — 同じSelfが真の腐肉を拾うまでゾンビを狩り続ける（DEV）

親 [D9-A Draft PR #795](https://github.com/rinsakamo/relay-self/pull/795)／既存D6実World複数世代とD8実食事2周期を再利用。

## 動作
- 同一Paper World・Mineflayer native session・元S49 ActionSupervisor。
- 管理ゾンビ死亡は **元S49が許可・発行した本当のATTACK**。Paper原本 `EntityDeathEvent` とSelf killer、vanilla腐肉 `rotten_count` を照合。
- `rotten_count=0` のとき、**新しいFoodや在庫を作らず**、600 server tick後のWorld-owned別UUIDゾンビをnativeで見て、旧Intentを完了し新Intentへ再arm。同じS49 owner/ActionSupervisor・過去Action IDs/OUTCOME・両永続ledgerを保持して再度ATTACK。
- `rotten_count=1/2` のとき、初めてそのItem UUIDを対象として、元S49による方向検証付きMOVE→Paper pickup→native腐肉在庫増を観測し、**狩猟ループを停止**。未回収なら成功ではない。
- `doMobLoot` を0用に変更しない／ドロップ率・Item/Inventory/Foodを操作しない。既存D6の受動EAT封鎖を維持。**D10はEAT成功の試験ではない**。食事は後段で既存D7-F/S51に正しく接続する。
- 疲労・Health・食料によって元のS49が拒否したらDEFER/STOP。既存L0選択を上書きしない。Worldの600tickは30秒の実時計保証ではない。

## 安全上限と判定
D6では4回で終了していたDEV試験上限を **D10の明示的grantの場合のみ12世代**に延長。これは使い捨てCI Worldの時間・リソース安全上限であり、Selfが腐肉なしで狩りを諦めるGoalではない。12世代すべて真の0なら `NOT_EXERCISED`（成功ではない）。この試験上限を撤廃して無期限実行を証明したとは言わない。

元D6の4世代・D8・D9経路のデフォルト上限や物理権限は変更しない。DEV-onlyではWorldへ新しいAction grantが必要。新World1回ごとにexact source CI SUCCESS→別1コミットのsingle-use trigger。独立Paper/native/S49二台帳監査、SHA256、cleanup、GitHub報告。分類 `DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`。
