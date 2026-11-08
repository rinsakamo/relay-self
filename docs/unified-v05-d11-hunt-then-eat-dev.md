# Unified v0.5 D11 — 自然腐肉が落ちるまで同じSelfで狩り、元S51で食べる（DEV）

**親**：D10 [Draft PR #798](https://github.com/rinsakamo/relay-self/pull/798)、元S49実World R1 [#42448101239](https://github.com/rinsakamo/relay-self/actions/runs/42448101239)。既存D7-FのSTOP/S51実食事、D8真の2周期、D10 0個からの狩り直しを再利用する。

## D11の動作・実装
- 同一Minecraft World / native session / 元S49 ActionSupervisor。0個ドロップは本物のPaper結果として残し、600 server ticks後の新ゾンビ出現・新Intent・再ATTACKを続ける。試験用外部上限12世代。
- 最初に腐肉が落ちた際、元S49の実MOVE、Paperの真のItem UUIDとPICKUP、native在庫増を要求。食事を許可するには、**既存D7-FのS50直接入力とPaperの入力OFF・静止に対する元S49 live STOP読取**を用いる。これによって一度だけ元S51 EATを発行する。
- 第1世代の陽性は既存D7-Fそのものを使い、以前の0個後の陽性は元D10のMOVE receipt→既存D7-F/S51を新規の世代出典で接続。新しい物理Action issuerは作らない。
- WorldのFoodを直接変更しない。既存D7-Fと同じDEV用Hunger effectをWorld環境側に付与するが、実際にFoodが閾値に達したかをnative観測し、元S49 L0のEAT判断が成立した場合だけ発行する。これも自律的なFood Goal発見とは呼ばない。
- オフライン監査は真のPaper殺害者・ドロップ0/1/2・600tick spawn・元ATTACK/MOVEの全S16・同じ元supervisorと、追加された元S51の実`EAT`台帳、Food上昇・腐肉在庫減少・S50/Paper STOPを独立検証。Source cloneや過去のAction再利用は拒否する。
- 12世代すべて自然ドロップ0ならEAT0の`NOT_EXERCISED`。Worldの実ドロップ確率・プレイヤー在庫・Food本体・物理則に操作なし。EAT後の長期連続生存、正確なserver-effective clear tick、物理exactly-once、学習成功の証明ではない。

## 実証境界
`DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`。main、親D10 #798、D9 #795、D8 #788と原本には変更しない。別の1回限りの実Worldトリガー前に正確なソースHEADのoffline CI SUCCESSが必要。
