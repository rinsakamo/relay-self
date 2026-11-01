# L1-MP3 host観測前固定（DEV）

#653 最新grant（[6551090255](https://github.com/rinsakamo/relay-self/issues/653#issuecomment-6551090255)）に基づく1 World限定。基点84adf1ae。過去grantは使用しない。

元S49 hostのroute B opt-in `--l1-prediction-journal`。元唯一Java stdout readerがflushするDEV専用ログsink内の同期callbackで、各WAIT_TICK読取り後に次tick予測を計算しexclusive journalへfsyncしてから次readlineへ進む。追加probe/Action/model/learningは0。係数trainingはWorld開始前固定、session/Action/markerはPRE_FORWARD送信前にarm、WorldはPRE_FORWARD受信時固定。subjectはtrainingと同一の予定値であり後続元INPUTで必ず照合する。後付けで凍結時刻を変更しない。

**HOST_BEFORE_NEXT_READ_ONLY / PAPER_PHYSICAL_PREQUENTIAL_NOT_ATTESTED**。OS/Paperのbufferに次callbackが既に存在する可能性を排除する同期機構は元sourceにない。したがってこのhost hookの試験成功をPaper物理観測前固定の成功へ昇格しない。source生成時刻との競合は未決定のまま保持する。batch採点とは分離し7つの先行保存値を照合する。対象不一致/欠測/順序異常は失敗で保存、再Worldなし。

0/last/training mean/same-information cheap linearを同じ7対で比較。cheapとの同値、Goal UNDETERMINED、L10/S10/S11/P1=0、QUALIFICATION_NO_GO、SCIENCE_NOT_RUN。実結果は終了後追記。

初回事前CI 41256883106は共通collectorの保護blob変更で19 FAIL / 409 PASS。原ログ保存。共通collectorを基点bytesへ戻し、保護manifest/testsを変更せずDEV hostのPathログsinkだけで同期通知する形へ修正。World未消費。

## 1回限りの実World結果

実行コード exact HEAD **`bd9115eeb3aa07a0554058124309c2f6b6cbbc14`**、tree `git`記録は証拠内executor-source.json。開始前[MP3 CI 168 PASS](https://github.com/rinsakamo/relay-self/actions/runs/41257427953)、[L1/W4回帰 428 PASS](https://github.com/rinsakamo/relay-self/actions/runs/41257432749)、経路A/BともSUCCESS。初回CIの19 FAIL / 409 PASSも保存。ローカルfocused 167 PASSは最後のcollector統合テスト追加前、追加後host単独7 PASS、保護監査込み58 PASS（追加前）。Ruff/compileall/contracts PASS。

2026-11-01 00:42 UTC、**新規使い捨てWorld 1回 / host PASS 1 / host FAIL 0 / retry 0 / grant CONSUMED**。以後の追加Worldは実施しない。

- session `9dc518a1-829a-4b81-b789-8e1a52e404be`、World `82356070-9e3e-431a-bf1d-7af589b6c958`、subject `dcae346d-e66f-331a-b459-a5a5370e9738`。
- 元L0 native seqは **WAIT 10→11 / MOVE_AWAY 20→21 / WAIT 55→56**。Action **1件** `s49-native-move-20`、元S16 **OUTCOME 1**、before23 / dispatch24 / S15 clear ACK29 / after30。移動0.626906573421061m。追加Action/probe/model callは0。
- training固定→session/Action/marker arm→PRE_FORWARD raw sourceによりWorld/予定subjectをticket固定→POST_CLEAR→WAIT_BEGIN→WAIT_TICK 254–261。subjectは予定値として固定し、後続元INPUTと一致確認。ticket SHA `081f4bb328b4a19e0958b4dd1afa12f16595e271c4e2ce7b6bf4ce201d62a03a`。係数 **0.20331885786720635**。8観測と7予測を原本journalへ保存、各予測fsync→次host readの順を元collector統合試験と別process監査で照合。
- 全Java raw stdoutと元collectorログが完全bytes一致。PRE_FORWARD/各WAIT行SHA一致、typed S50 windowと元S16/S7、全Node packet TRACE_END complete=true/lost=false、S7 57受信/14送信を再照合。監査はJSONにlive型真正性を再付与しない。
- Java exit0、Node exit0、launcher exit0。所有PID消滅、Worldルート削除、port再bind PASS。過去原本678ファイルSHA一致、main不変。共通collectorの最終差分0、保護manifest/tests変更0。
- 別process監査の初回はCRをsplitlinesで分割してSHA不一致、v2は末尾console promptにLFを要求して失敗。**両失敗と各script原本を保存**。v3はLFで実readline単位を復元し末尾partial bytesも保持してPASS。Worldや予測を再実行せず、原本byteは変更0。baseline copy PASS後、予測・時刻・target・source SHA・観測値・欠測・tick・armを変造したcopy **8/8拒否**。

| arm | MAE m | RMSE m |
|---|---:|---:|
| zero | 0.009178085930 | 0.019152432224 |
| last | 0.008375996444 | 0.015699639062 |
| training mean | 0.009479196403 | 0.018236439325 |
| L1 c*x[t] | 0.006060023056 | 0.014261249851 |
| same-information cheap linear | 0.006060023056 | 0.014261249851 |

**CHEAP_EQUIVALENT**。採点7対。新Worldの誤差は旧heldout replayより大きい。小標本の記述値であり独自L1優越・汎化・正式学習を主張しない。

**最終分類: `DEV_HOST_READ_ORDER_FORECAST_OBSERVED_PARTIAL_PHYSICAL_CHRONOLOGY_UNDETERMINED`**。
Paperの次callbackがOS bufferに既に生成されていた可能性は排除できない。hostの「次read前」から物理的な「次source観測前」へ昇格しない。予定subjectは元INPUTで事後照合した値であり、その事前観測を偽装しない。真正な物理prequential gateは未達・UNKNOWN。pure `score_live_dev`の原本検証falseフィールドを後から書換えず、別監査の元S16/cleanup確認と分離する。次World用refitは保留。

**Goal UNDETERMINED / P1 WAIT=L10=S10=S11=0 / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**。全tick入力idle、実効clear時刻、物理安定、時計同期、Goal資格はNOT_ATTESTED。

[判定](evidence/issue653-mp3-host-20261101/verdict.json) / [原本監査・数値](evidence/issue653-mp3-host-20261101/run1/independent-mp3-readback.json) / [全証拠SHA256SUMS](evidence/issue653-mp3-host-20261101/SHA256SUMS)。外部原本 `/home/rinsa/work/issue653-mp3-host-evidence-20261101/`。main mergeなし。
