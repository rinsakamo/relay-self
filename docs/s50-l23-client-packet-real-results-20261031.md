# S50 × L23 クライアント送信関数 実World診断結果

2026-10-31、Local WSL。新規World **2回（初回FAIL、最小修正後DEV PASS）**。
診断分類は **NO_PLAYER_INPUT_WRITE_ON_OBSERVED_CLIENT_PATH**。
既存の唯一のbridgeは位置パケット送信関数を呼んだが、観測経路に
`player_input` のwrite-returnは現れなかった。新しいパケット送信機能は追加していない。

## ソースと修正

- 統合branch: `dev/s50-l23-client-packet-integrated-20261031`、Draft #643。
- 開始/初回World HEAD: `b67371e2097c4d5cf2d4b3aec398064cbc6ea183`。開始時GitHub/local/remote一致。
- 成功World実行HEAD: **`69cf00a25501b1181e4269e8340436601b7dc33b`**。
- Paper source: S owner `3bb79ed57c4a0940bdc586c72976c7ece079319f` のgit archiveから外部copyで新規build。
  最新S owner `33275fc5221fd18bbdc47b167fc0a83fe7cf8ad4` とのplugin src差分0。
- L23 owner `d51b34b859cb18c4965681422163f9a1cfad3a8d` のS49/S34/process_session/normal_action blob契約維持。
  main/S owner/L23既存branch/過去原本は変更していない。

初回はcreateBot直後の診断初期検査でNode1終了。
Mineflayerは`inject_allowed`で非同期にphysics pluginを注入するため、
この時点では`getControlState`未定義。Action0、S16未生成、sidecar未生成。
Java0、World削除、所有PID消滅、port再bindを確認。原本はrun1として保存しFAILを維持。

最小修正は、write wrapperを即時に1回だけ取り付けたまま、control API検査を
physics/effectの実サンプル取得時へ移動したこと。遅延注入のNode回帰テストを追加。
元writeのreceiver/引数/戻り値/例外と、S49発行/clear処理は維持。

実World後、独立readerが旧名`action`を参照していた不整合も発見。
実reportの`actual_native_actions`へ修正し、誤ったfieldを拒否するnegativeを追加。
実World原本・Actionコードは変更せず、同じ保存原本を再読して監査PASS。

## 成功World原本

| 項目 | 実測 |
|---|---|
| session | `3148d4a1-1a2a-4475-9f70-f3363a356be4` |
| World UUID | `6cfb0817-fbe2-49f2-9b5e-bbf59f3a2e62` |
| Action | 1件、`s49-native-move-23` / MOVE_BACKWARD |
| dispatch / S15 clear | seq27 / seq32、各applied |
| S16 | before26 / after34、executed / outcome |
| Action内変位 | 0.7342911432182309m |
| S16後native move | seq35–39、5件 |
| S16後追加変位 | **0.12287857661821566m** |
| PRE_FORWARD / POST_CLEAR / WAIT_BEGIN | Paper242 / 248 / 250 |
| WAIT_TICK / INPUT_TICK | **251–258、各8件連続** |
| INPUT_EVENT | **0件** |
| input_events / last_input_event_tick | 全8件で0 / -1、overflow false |
| Paper7入力 | 全8件で全OFF |
| Node physics samples | 243件、番号1–243連続 |
| sidecar | 269行＋TRACE_END、complete true / lost false |
| L23 | PAPER_SOURCE_SHAPE_REVIEWED_ONLY、Paper最終pose/S7差0m |

| write-return packet | 件数 |
|---|---:|
| player_input | **0** |
| position | **22** |
| position_look | **1** |
| flying | 0 |
| look | 0 |
| entity_action | 0 |
| 位置移動4種合計 | **23** |

| Node effect | record index | 直前physics番号 | control状態 |
|---|---:|---:|---|
| set_control(true) | 236 | 222 | backのみON |
| clear_controls | 245 | 226 | 7入力全OFF |
| shutdown_clear_controls | 269 | 243 | 7入力全OFF |

Nodeの記録順序はON→clear→shutdown clear。Node番号はPaper tickと同期していない。
write-return indexも連続し、記録欠損/lostなし。元関数の例外は伝播する実装であり、
このrunにadapter_error・失敗effect・Node異常終了はなかった。
ただし記録するのは正常returnのみで、別の呼出元内部で捕捉されたwrite例外の総数は直接計測していない。

| Paper tick | 前sampleからの位置差m | 7入力 |
|---|---:|---|
| 251 | 0.05903579322217567 | 全OFF |
| 252 | 0.005210808286785218 | 全OFF |
| 253–258 | 各0 | 全OFF |

これはlast-reported入力全OFFと位置変化の併存を再現した実測。
S16後全変位とPaper8sample窓内変位は観測区間が異なるため一致を要求しない。

## 差異の解釈

実際にロードしたMineflayer4.39.0のphysics.jsでは、controlのback変更はclient-local状態を更新し、
位置/角度送信はphysics側の別経路で行う。`player_input` writeはsneak変更分岐にある。
今回のback ON/OFFのみ、sneakは常時OFFという原本と、player_input0/位置23という実測は整合する。
ロード依存ソースのcopyとSHAも保存した。これが今回の切り分け結果であり、
Paperが全入力パケットを未受信だったという証明ではない。

Nodeはセッション内のラップしたwrite経路、Paper入力イベントはmarker開始以後の観測。
区間も時計も異なる。write-returnは送信関数の正常復帰のみであり、wire到達・受信・適用を保証しない。
同一session/marker/WorldのDEV原本関連付けであり、同一packetの因果対応や独立認証ではない。

## 独立監査・環境・保存

既存`tools/s50_l23_packet_world_readback.py`を終了後に実行。
さらに別PythonプロセスでS7送受信/receipt、S16、事前Goal plan、Paperを読み直し、
L22/L23を再計算してreportと完全一致を確認。Node session、marker、World、
INPUT/WAIT tick並び、TRACE_ENDと連続index、原本SHA、cleanupを照合してDEV PASS。
外部readerの初回payloadキー誤りもstdoutを保持し、原本の正しいflat schemaで再読した。

Java runtime21.0.12.1、Node22.22.2、Python3.12.3、Mineflayer4.39.0、Paper1.21.8 build60。
build JDK21 / Maven3.9.11。公式build60 metadataのsize/SHAと実JARを起動前に照合。
元config全文/16 Actionを保持しdev/tick-meter/input-witnessを有効化。
**M0.2はexhaustionへの能動介入であり純粋な受動観測ではない。**

- server SHA256: `8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e`
- 新規build plugin SHA256: `5044295969381d515ed03414d3fe0be7f3e4370a593efb28fffd82380584726f`
- config SHA256: `2fd8f5bac2fea7fe857b1e7712a6979a2b76b78f626c374af7fbc7fee44e72d0`

成功runはNode0/Java0/runner0、所有PID消滅、World削除、25565再bind成功。
初回もWorld/PID/port cleanup完了。既存プロセスkill、NODE_OPTIONS、別client、GPU/RSEE操作なし。

FAST: 開始HEAD Node5/Python72 PASS。修正後Node6/Python72 PASS。
最終reader修正後 **Node6/Python73 PASS**、Ruff/構文/repository contracts PASS。FULL未実施。

外部原本: `/home/rinsa/work/s50-client-packet-evidence-20261031/`。
root直下は初回FAIL、`run2/`が成功run。JAR/build sourceは`assets/`。
[Git保存原本](evidence/s50-client-packet-20261031/)にはrun1/run2、独立監査、SHA256SUMSを保存。
JAR/WorldはGit対象外。実測後のcommitはreader/test修正と証拠・文書のみ。

## 判定上限と次の最小実装

`EFFECTIVE_CLIENT_CLEAR_TICK=NOT_ATTESTED / FULL_TICK_INPUT_COVERAGE_NOT_ATTESTED /
STABILITY_UNPROVEN / GOAL_UNDETERMINED / L10_PAIRS_0 / S10_UPDATES_0 /
S11_GRANTS_0 / P1_WAIT_0 / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`。
L8学習経験への正式受理なし。

今回の送信診断は完了。前後入力もPaperの入力更新として反映させる必要があるなら、
S50 ownerで1.21.8入力状態の送信仕様と既存Mineflayerの差分を別タスクとして定義し、
その変更で新規World検証するのが次の最小候補。今回には送信機能を追加していない。
実効clear tick/全tick coverageを求める場合は、S source側のnative受信・適用anchorが別途必要。
