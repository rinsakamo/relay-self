# T1h 高位STOP — 実Minecraft DEV統合結果（2026-10-26 JST）

**DEV_ONLY / DEV_WORLD_OBSERVED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**

同一S49所有者による高位STOP → 元MOVEの中断 → 元clear_controls適用ACK →
独立Paper callbackの後続静止観測 → **稼働中のS49所有者によるDEV STOP ACK** が成立した。
ActionはFAILED、SupervisorはUNKNOWNを維持する。shutdown ACKをSTOP ACKに代用しない。
今回は明示operatorが既存S49へSTOPを要求するopt-in DEV入口であり、
通常製品の全Action種別・全Self command boundaryへの接続完了を意味しない。

## コードと環境

- Branch: `self/dev-t1h-s49-stop-20261026`
- 開始HEAD: `9743c16136dbcecfff8bbfc2628fa52d24b45857`
- 基底T1g: `9f97473227bc839413f5ee31bc5469dcb425fa5b`、祖先関係確認済み。
- 最終実装HEAD: `1fea532623b9bf2c9a449c01dab73b4e44e9c59c`。
  最終正常STOPは `307caf2baff16b9c3acdb5c35f1dd440cd841f2d`、
  最終入力故障試験は前記最終実装HEAD。後者の差はDEV故障入力とラベルだけであり、正常経路は同一。
  最終報告commitは文書・測定JSONのみ。
- 専用worktree: `/home/rinsa/work/relay-self-t1h-20261026`。
  元checkoutのmain `32fe105fc12cbf54abd11bfba7c8a75d319939df` は変更しない。
- Windows 11のWSL2ホスト `RIN-DESKTOP`、Ubuntu側Python **3.12.3**、
  Node **22.22.2**、Java/javac **21.0.12.1**。
- Paper **1.21.8-60**、SHA256
  `8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e`。
- 今回buildした既存Plugin JAR SHA256
  `65ee217f95e8ac36dda30ebdfe930a2c5a28ec7ad8ac0662bce3a9f011be0642`。
  Javaソースは開始HEADと同一、追加Plugin・通信経路なし。
- fresh outputごとに新Worldを生成。bootstrapからコピーしたのは
  `cache/libraries/versions`だけであり、既存Worldデータの再実行はしていない。

## 修正とテスト

1. STOP要求時に元Actionのclear IDを固定し、呼出側が古いIDを期待IDにも指定する抜け道を拒否。
   不正requestは部分ラッチせず、未発行ActionのSTOPからMotor ACKを受理しない。
2. Paperのmarker直後のtickから連続性を検査し、全提示区間を走査する。
   早い静止窓があっても、その後の入力・移動・欠損を隠してACKしない。
3. 確定直前に既存単一readerで相関probeをdrainし、切断済sourceを過去の静止窓で成功にしない。
4. set_control送信が停止した場合も、元ExecutorがSTOPをポーリングして送信taskを取消・回収する。
   送信の回収後にのみ既存のonce-only clear経路へ入る。新reader・新物理issuerは作らない。
5. 既存DEV入口へ負対照とPython単調時計の測定を追加。
   最終stale試験は新規positive Worldの実native原本から旧session/Action ACKを読み出して再提示した。

**Python 3.12 FAST 482 PASS**（27ファイル、最終実装HEADで実施）。
指定focused4ファイル **52 PASS**、指定関連回帰3ファイル **52 PASS**。
FASTの選択リスト・全stdoutは外部証拠rootに保存。
Node 22関連 **73 PASS**（既存top-level 68件＋既存packet trace 5件）、
Java 21 **BUILD SUCCESS**、Ruff・構文・repository contracts PASS。
FULLとmain mergeは実施していない。GitHub上のCI成功へ読み替えず、以上はローカル検証結果である。

最初のsystem Pythonはpytest未導入で起動不能だったため、既存のPython3.12 venvを確認して使用。
Java buildの初回2回はJREのみの環境でrelease21コンパイラを選べずFAIL、
既存の完全なJDK21を明示して成功した。これらをWorld試行数やPASSに含めない。

## 実World全履歴

**21 World試行、report PASS 18 / FAIL 3**。DEV STOP ACK発行 **7**。
期待どおりSTOP ACKを拒否した負対照は延べ **13**（通信断FAIL2件を含む）。
残るFAIL1件はmarker到着前に検査した初期fixture不整合で、原本を保持し新Worldで修正再試験済み。

負対照の`PASS`は期待した拒否を意味し、STOP成功ではない。
通信断2件は故障としてSTOP ACKを拒否したが、Node正常shutdownがないため
report FAIL / cleanup_complete=falseを維持した。プロセス回収と正常transport終端を混同しない。

| Trial | report | DEV STOP ACK | 内容 |
| --- | --- | --- | --- |
| `run-001/t1h_stop_move` | PASS | あり | 正常STOP（又はACK二重確定拒否） |
| `run-002/t1h_delayed_ack` | PASS | なし | STOP cannot ACK without original clear |
| `run-002/t1h_disconnect` | FAIL | なし | source lost before STOP ACK |
| `run-002/t1h_double_ack` | PASS | あり | 正常STOP（又はACK二重確定拒否） |
| `run-002/t1h_input_residual` | PASS | なし | no 8 consecutive motion-free Paper tick transitions |
| `run-002/t1h_lost_ack` | PASS | なし | STOP cannot ACK without original clear |
| `run-002/t1h_motion_residual` | PASS | なし | no 8 consecutive motion-free Paper tick transitions |
| `run-002/t1h_paper_short` | FAIL | なし | unique post-clear Paper marker required |
| `run-002/t1h_pre_stop` | PASS | なし | STOP cannot ACK without original clear |
| `run-002/t1h_stale_ack` | PASS | なし | no matching acknowledged original S49 clear |
| `run-002/t1h_stop_move` | PASS | あり | 正常STOP（又はACK二重確定拒否） |
| `run-003/t1h_disconnect_after_idle` | FAIL | なし | source lost before STOP ACK |
| `run-003/t1h_double_ack` | PASS | あり | 正常STOP（又はACK二重確定拒否） |
| `run-003/t1h_paper_short` | PASS | なし | insufficient Paper post-clear callback samples |
| `run-003/t1h_stop_move` | PASS | あり | 正常STOP（又はACK二重確定拒否） |
| `run-004/t1h_lost_ack` | PASS | なし | STOP cannot ACK without original clear |
| `run-004/t1h_pre_stop` | PASS | なし | STOP cannot ACK without original clear |
| `run-004/t1h_stop_move` | PASS | あり | 正常STOP（又はACK二重確定拒否） |
| `run-005/t1h_stale_ack` | PASS | なし | no matching acknowledged original S49 clear |
| `run-005/t1h_stop_move` | PASS | あり | 正常STOP（又はACK二重確定拒否） |
| `run-006/t1h_input_residual` | PASS | なし | no 8 consecutive motion-free Paper tick transitions |

発行前STOPでset_control/clear_controls各0、STOP前の正常Action発行は可能。
MOVE中STOP、ACK欠落、ACK遅延、早期/静止後の切断、Paper観測不足、
入力残存、移動残存、旧session/Action ACK、二重STOP/ACK拒否を確認した。

- ACK欠落・0.7秒遅延は**Python consumerでの故障注入**。実bridge原ACKは原本に残る。
  ネットワークパケット損失・遅延の実測とは主張しない。
- 入力残存は明示DEV tokenと既存DEV flagsが揃う場合だけ、元bridgeが意図的にclearを省略し
  偽のapplied ACKを返す負対照。初回run-002ではPaper入力はfalseで、移動残存によって拒否した。
  原本照合でこの観測限界を発見し、run-006では同じbridge/API内でstuck sneakを注入。
  Paperのsneak=trueと移動残存を原ログで確認し、STOP ACKを拒否した。
  shutdownは常に実clearを行う。別Motor issuerや2回目のset_controlは追加しない。
- 移動残存は既存Paper consoleから環境側levitationを適用。入力が解除済みでも静止認定を拒否する。
- 初期run-002のstaleケースはconsumerでIDを書き換えた形状負対照。
  最終run-005は**実際の古いnative receipt**を読み戻した再提示であり、両方の履歴を保持した。
- run-002/paper_shortのFAILはmarker未着で安全側拒否。
  run-003では実markerがflushされた直後に検査し、観測不足として期待どおり拒否した。

## 最終正常STOPの測定

対象: `run-005/t1h_stop_move`、正常経路確認HEAD `307caf2b`。

- session: `9b4c7d6f-af6d-4860-bafd-bd72f6e7827c`
- World: `122315df-50d7-4cc2-b53f-9fd45f35220e`
- 元Action: `t1h-owned-move`、元clear: `t1h-owned-move-clear`。
- 正常Paper身体観測 **ADMITTED** → Supervisor **ISSUED** → set_control適用 → owner STOP。
- STOP要求Python時刻: `1044220900282154` ns。
- 初回STOP認識: `1044220916307657` ns、要求から **16.025503 ms**。
- clear送出: `1044220916318965` ns、clear ACK受信: `1044220918015300` ns。
  要求→対応clear ACK **17.733146 ms**（同一Python単調時計）。
- set_control **1** / clear_controls **1**。適用ACK seq **34**。
- Paper marker server tick **36**。
  最初の後続Paper callback server tick **37** /
  World full_time **1035**。
- marker後の残留移動経路 **0.094659164989 block**。
  これはmarker以後のPaper位置差の累積であり、STOPの厳密な物理実効tickを示さない。
- 7入力すべてfalse。8連続静止遷移の終点server tick **42–49** /
  World full_time **1040–1047**。
  9位置sampleから8静止遷移を確認。marker→窓終端 **13 WorldTick進行**。
- DEV STOP ACK確定Python時刻: `1044221771595094` ns、要求から **871.312940 ms**。
  この値には保守的な0.85秒観測待機が含まれ、最短身体停止時間ではない。
- 最終Action **FAILED** / Supervisor **UNKNOWN**。STOP後の新規Action発行 **0**、Motor effect送出 **0**。
- Java **exit0** / Node **exit0**、bridge shutdown_ackとconnection_endを別途確認。
  PID消失、25565再bind成功。

Python・Node・Paperの異なる単調時計の片道遅延は **UNKNOWN**。
Paper `Bukkit server_tick` とWorld `getFullTime`を別々に保存し、同一時計として減算しない。
初回run-001にはSTOP要求時刻が未計測のため、その要求→ACK遅延はUNKNOWNのまま保存した。

## 全体の安全・cleanup・保護

全21件で所有Java/NodeのPID消失とport再bindを確認。
正常cleanup **19/21**（Java0/Node0＋native正常終端）。
注入通信断 **2/21**はJava0/Node3、connection_endあり・shutdown_ackなしで正常cleanup未成立。
全session内のAction/effect ID重複 **0**、effect receipt重複 **0**、STOP後の次Action effect **0**。
別session間では固定fixture ID文字列を再利用するため、重複判定のキーは(session_id, action_id)である。

元main、Draft #545/#634、M0/P1ソース、Javaソース、workflow、過去World/原本、R/V資格原本は変更なし。
STOP fixtureではT2 ownerを作らず、架空会計tick **0**、P1 WAIT資格への変換 **0**。
TPS actuator・高TPS Motorは引き続き無効。

## 原本と再計算

外部証拠root: `/home/rinsa/work/t1h-integration-evidence-20261026`。
各trialに`server/`、`paper.log`、`native.jsonl`、`commands.jsonl`、
`python_timing.jsonl`、`node_timing.jsonl`、`report.json`、`source_hashes.json`を保存。
各batchの`subject.json`はその時点のHEAD・dirty diff・runner hashを記録し、
最終run-004/005/006はclean実装commitに対応する。初期dirty実装での試行を最終HEAD試行と表示しない。

全trialのsource_hashesを読み戻して検証済み。
`reduce_results.py`は原本をread-onlyで再計算し、外部`final-measurements.json`へ出力する。
[この報告の測定JSON](t1h-native-dev-results-20261026.json)には全試行・原本hash・時刻・拒否理由を収録。

## 未成立と次段階

DEV STOP ACKは観測された限定的な静止窓に対するACKのみ。
**R資格STOP ACK、独立認証済み全WorldTick不活動、サブtick完全無活動、P1-qualified WAIT、
高TPS STOP期限、科学的一般化は未成立**。
次は既存Selfの通常multi-epoch command境界とEAT中断へ同じownerを結線するDEV検証。
Rによる独立資格と高TPS Motorは別段階として扱う。
