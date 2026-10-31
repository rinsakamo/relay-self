# S49 × SelfBody × L8 × M 実World受動統合 DEV結果（2026-10-31）

**DEV_INTEGRATION_PASS / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**。
ユーザーの「fresh grant承認する。」を受領後、未使用rootで使い捨てWorldを
1回実行し、正常終了した。grant消費済み、retry 0、実装変更なし。

実行対象exact HEAD: `d53cd5a71e22b314da3f9353a51883c9a37a6d60`。
実行直前local/remote HEAD一致・worktree clean・NODE_OPTIONS空・25565空きを確認。
Java 21.0.12.1、Node 22.22.2、Mineflayer 4.39.0、Mojang Minecraft 1.21.8。
既存runner/host/Executorをそのまま使い、Paperや別のWorld ownerは追加していない。
前回起動FAILおよびオフライン再確認報告は履歴として保持する。

## 実動作と受動診断

session: `d94c7d92-752b-401e-93ac-5ab541cd2832`。

|元L0判断|event seq|同一native probe seq|Action|S16|
|---|---:|---:|---|---|
|WAIT|9|10|なし|対象なし|
|MOVE_AWAY|20|21|s49-native-move-20|OUTCOME / executed|
|MOVE_AWAY|48|49|s49-native-move-48|OUTCOME / executed|

実Action 2、元S16 OUTCOME 2。移動距離は0.7342911432m、0.6269065734m。
rawのset_control appliedはseq 23/51、対応するS15 clear_controls appliedは28/56。
Action IDは各1件、受信原本とreport内dispatch/clear receiptを照合した。
既存唯一のExecutor/reader経路と受信結果の範囲で重複Actionなし。
完全なoutbound/TCP監査や外部actor不在の独立証明はしていない。

S42完了epoch 3/3。同一session・probe seq・request ID・元choiceをrawと照合。
SelfBodyは元M tap経由のB0投影3/3、受動診断は全行RECORDED、observer_errors 0。
L8は全3行retention_off、候補なし、learning_updates 0、habit_grants 0。
M tensionは順にWAIT_MODEL_UNKNOWN / MOVE_MODEL_UNKNOWN / MOVE_MODEL_UNKNOWN。
UNKNOWNを物理Energy/Fatigueや成功へ読み替えない。B0 owner tickは0のまま。
診断由来Action発行・追加native read・追加cognition call・food creditは全て0。
real_model_calls 0、learning_in_world false。

## 終了・原本照合

Node exit 0、Java server exit 0。既存cleanupのnode/server reapとcollector終了を記録。
独立の事後確認でJava PID 3186・Node PID 3262は/procから消失、
一時World `/tmp/relay-self-s49-sskpwh6f` は削除済み、25565再bind成功。
shutdown_ackはseq 58の1件、connection_endはseq 59。これを高水準STOP ACKや
Paper idle/P1-qualified WAITとは扱わない。

W3はCOMPLETE_NODE_STDOUT、EOF true、capture_faultなし。
raw 30,661 bytes / 60 frames、単一session、seq 0..59連続。
SHA256: `18ad927a3670928e5b1d157c33c7852ebbd561c7b86f44e5227f249ebc62d953`。
これはNode bridge stdout原本で、Minecraft TCPや独立source認証ではない。
元hostのclassification文字列にはQUALIFIEDを含むが、本統合の判定はDEV限定。

異常: 実行/診断/cleanup失敗なし。Node punycode非推奨警告をhost.logに保存。
Goal success、実L8学習、Paper/P1会計、独立qualification、科学的利益は未検証。

## 保存と検証

原本root: `/home/rinsa/work/evidence-s49-slm-fresh-grant-20261031/`。
`grant.json`、`host.log`、`process-observations.jsonl`、`world-one/report.json`、
`world-one/server.log`、`world-one/native/`のraw/receipt、`audit-result.json`、
`SHA256SUMS`を保存。失敗原本rootは変更していない。
前turnの修正後オフライン結合回帰172 PASS、Ruffおよびtracked snapshot契約PASSを維持。
今回は実装変更がないため物理試験後の原本照合とcleanup検証を実施した。
main、保護原本、他レーン、元Action issuer権限は変更していない。

本報告のcommitはdocs-only。実行対象HEADと報告commitを区別し、Issue #537に
最終exact HEADと証拠rootを報告する。
