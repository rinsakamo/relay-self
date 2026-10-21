# S49 cancellation-safe cleanup: 独立 owner 審査資料

2026-10-21。これは隔離実装の工学的レビュー資料であり、保護例外の承認ではない。
**PROTECTED_SOURCE_CHANGE_NO_GO / DEV_ONLY / QUALIFICATION NO_GO / SCIENCE NOT_RUN**。
実 World、Java server、Node bridge、physical Action/OUTCOME、実環境 S10 更新はすべて0。
既存 W4 正常 DEV（World1、判断3、Action2、raw61）は本修正の資格証拠に流用しない。

## Subject と境界

- owner: [#392](https://github.com/rinsakamo/relay-self/issues/392)、SelfWorld [#633](https://github.com/rinsakamo/relay-self/issues/633)、W4 [#634](https://github.com/rinsakamo/relay-self/pull/634)、S [#545](https://github.com/rinsakamo/relay-self/pull/545)、S18 [#354](https://github.com/rinsakamo/relay-self/pull/354)。
- 専用 worktree: `/home/rinsa/work/relay-self-s49-cancellation-20261021`。
- 既存隔離 branch `self/product-self-one-command-s49cleanup-20261021` を fast-forward で継続。
- 開始 candidate HEAD `52fda1926991ca41695327746d7b918337ef6118`。開始時 GitHub とローカルから再取得。
- W4 HEAD `1473c74e4448bb9a527747de0619c8e55ffbd827`、S HEAD `3240691a29e1f02bcb89cc20cf650ac9a0e83662`、primary main `32fe105fc12cbf54abd11bfba7c8a75d319939df` は不変更。
- candidate の旧 CI [39518468522](https://github.com/rinsakamo/relay-self/actions/runs/39518468522) は4 FAIL/3 SUCCESS。新実装の成績として数えない。
- exact commit はこの資料を含む Git commit。最終 CI/full/投稿 readback の結果は #392/#633/#634 の今回の完了コメントに追記し、下記の commit 時点の結果と区別する。

## 例外伝播と依存関係の監査

原 `qualify()` は try 内で temp → Java/server stdout collector → Node session → original L0/executor → staging task → `wait_for(host.run_session(...), 95)` を作る。
`host.run_session` の観測、reprobe、grant、S14、唯一の executor、S16 OUTCOME は順に await される。finally に入る時点で host は return/unwind 済みであり、本修正は新規 Action/観測を再開しない。

旧 finally は Stage R summary → staging.cancel/await → Node shutdown（通常 Exception のみ捕捉、次に terminate）→ W3 receipt 読取 → Java `_shutdown_server` → temp → report の直列処理。
保護原本では staging の二次例外と temp 例外も後段を飛ばす。旧 candidate は通常の二次例外の一部だけを捕捉する。
`CancelledError` は `Exception` の派生ではなく、Node shutdown/terminate、Java/collector の await から抜けると後段を飛ばす。
[Python 3.11 task cancellation](https://docs.python.org/3.11/library/asyncio-task.html#task-cancellation) と [3.12 shield](https://docs.python.org/3.12/library/asyncio-task.html#shielding-from-cancellation) に沿って監督する。

`process_session.shutdown` は default では shutdown送信→wait、W3時は唯一の decoderでEOFまでdrain→wait→seal。
内部 `terminate` の process.wait は無期限。`_shutdown_server` は stop/write/drain→35秒wait→必要ならkill/wait、次にcollectorを5秒waitしtimeout時cancelのみ。
そのため、S49側で helper 全体を期限付きで監督し、例外後も同じ所有processのkill/reapと同じcollectorのsettlementを別stepで実施する。
W3 seal は既存ファイルを閉じる責務も持つため、terminate取消でseal未到達なら同じcaptureをINCOMPLETEとしてsealする。第二のreaderは作らない。

## 修正前の独立再現

Git blobを別namespaceへ読み、実Java/Node/process/native/Action portsをfakeへ置換。原コード・旧candidateファイルは変更しない。
`before-protected-reproduction.json` と `before-reproduction.json` に呼出し列、Node/Java exit、temp呼出し、report有無/内容、rc、例外、stdout/stderrを保存。
以下は原保護blobの実測。cancelは `CancelledError` として伝播するが、cleanupを完了しないことが欠陥。

| 注入 | Java shutdown | temp cleanup | final report | 伝播 |
| --- | --- | --- | --- | --- |
| Node shutdown cancellation | 未呼出し | 未呼出し | 無 | CancelledError |
| Node shutdown例外 + terminate cancellation | 未呼出し | 未呼出し | 無 | CancelledError |
| staging await中の二次例外 | 未呼出し | 未呼出し | 無 | RuntimeError |
| Java shutdown cancellation | 呼出し | 未呼出し | 無 | CancelledError |
| collector cancellation | 呼出し | 未呼出し | 無 | CancelledError |
| W3 receipt取得例外 | 未呼出し | 未呼出し | 無 | RuntimeError |
| temp cleanup例外 | 呼出し | 呼出し/失敗 | 無 | RuntimeError |
| report write例外 | 呼出し | 呼出し | 無 | OSError |

旧candidateでもNode shutdown取消→Java未呼出し/report無しを再現。旧candidateはstaging/tempの通常例外をFAIL/rc1/report有へ降格できるが、取消とreceipt例外は後段を飛ばす。
最初の開発用pytest実行にはfixtureのraw引数設定不備があった。そのログは保持するが欠陥証拠には使用しない。上表は修正した独立probeのJSON実測である。

## 最小実装の責務

変更は `adapters/mineflayer/s49_normal_session_real_ci.py` 内のteardown/final verdict/reportに限定。
original `qualify()` の try本体は保護原本・旧candidateとAST一致。CLI/env gates、stagingのWorld script、L0/S14/S16、既存grant/issuer、`_new_session()`、Stage R active pathは変更しない。

1. host終了後、stagingをcancelしてsettle。既に別主体からcancelされていた場合は成功扱いしない。
2. cleanup専用taskを1つ保持し、callerはshield越しに同じtaskを終了まで再await。caller再取消は蓄積し、`uncancel()`で消さない。
3. 各awaitは `asyncio.wait` で上限を設ける。staging5秒、Node shutdown25秒（内部10秒×2を包含）、terminate10秒、kill後reap5秒、Java helper45秒、Java reap5秒、collector5秒。timeout後のcancel settlement猶予は各0.5秒。retry/relaunchしない。
4. Node shutdown例外/取消/不明exitではterminate、失敗なら元の所有processをkill→reap。Java helper失敗/取消後にserverが生きていればkill→reap。kill失敗でもreapを試みる。
5. collectorとtempは先行faultと独立して処理。W3 receipt/Stage R summaryの例外も記録して続行。W3 fallback sealはACK/EOFを作らず既存captureを閉じる。
6. 全fault、unconfirmed、取消、非0/不明exit、W3不完全/ACK欠落/別sessionを成功取消条件にする。Node/Java exitは確定intだけを記録。未確認を0にしない。
7. 最初の取消は保持して最終report後に再送出。通常faultはFAIL/rc1、事前BLOCKEDは昇格しない。report失敗はstderrの `S49_REPORT_WRITE_FAILED` と例外で明示し、PASS返却/出力を行わない。元cancelがある場合は保存例外をcauseにして元cancelを再送出する。
8. reportは同一directoryの一時ファイルへ完全JSONを書きflush/fsyncしてreplace。最終verdictから保存完了までawaitせず、非同期の再取消による途中PASS確定を避ける。replace失敗時は旧snapshotのbytesを維持し、新run成功と解釈しない。

変更行の案内: `_write_final_report`（124行付近）、`_cleanup_session`（139行付近）、`qualify`取消捕捉（529行付近）、監督/final verdict/report（545行以降）。正確な差分は `git diff 52fda192..HEAD -- adapters/mineflayer/s49_normal_session_real_ci.py`。

`session._process` と `_seal_raw_capture` は既存S49所有sessionの緊急cleanupだけから使う。process_sessionという別保護原本のAPIを拡張せずに修正を隔離するための限定的なprivate seamであり、ownerレビュー対象。
OS強制終了、電源喪失、event-loopの停止/非協調コード、不可逆なstorage障害を越える保証はない。同期temp/report I/OをOSレベルで強制打切りできるとは主張しない。
非協調taskは期限後にunconfirmedとしてFAILにし、終われば例外を回収する。PID停止を確認できない場合やreaderを撤収できない場合の統合資格はNO_GO。

審査の対象境界は **qualifyが受領したhandleの終了処理**。保護helper `_ready_server` 内でspawn後・handle返却前にcancelされる場合、または `_new_session`/`MineflayerProcessSession.launch` のstartup待機内でcancelされる場合の未返却process custodyは別の未解決境界である。S49 finallyから未受領handleを捏造して回収したとは主張しない。今回これらの保護helperを変更せず、実Worldを起動していない。live採用前にhelper ownerによる取得時cancelの引渡し/停止契約と故障注入が必要。downloadのto_threadも取消でworker自体を強制終了できるものではない。したがってこの修正のteardown回帰から全startup段階の取消安全性や物理資格を推論しない。

## 回帰と最小の負対照集合

新規 `tests/test_s49_cleanup.py` は原 `qualify()` を直接呼び、外部process/effect portsだけをfake化する。
18ケースの表は clean、Node/Java非0、shutdown例外/取消、terminate例外/取消、staging/collector二次例外、collector取消、receipt例外、temp例外、W3 incomplete/ACK欠落、Node timeout、複合故障を各責務につき選択する。
追加の独立責務はreport保存失敗、caller3回取消とcancelling state保持、terminate timeout、kill/reap失敗、unknown exit、receipt/temp取消、atomic replace失敗+元cancel、実Stage R HOLD producerのreadonly summary、取消非協調taskの期限切れ、事前staging取消、実W3 fileのincomplete seal、supervisor fault後のreportである。無意味な全組合せは作らない。

| commit前に完了した検査 | 結果 |
| --- | --- |
| original cleanup故障注入 Python3.12.3 / pytest9.1.1 | 32 PASS / 0 FAIL / 0 SKIP |
| original cleanup故障注入 Python3.11.17 / pytest9.1.1 | 32 PASS / 0 FAIL / 0 SKIP |
| exact source CI S49/W3/Stage R focused | [88156105 CI](https://github.com/rinsakamo/relay-self/actions/runs/39562971507)、Python3.11.17/3.12.15 とも68 PASS / 0 FAIL / 0 SKIP。JUnit readback済み |
| 最新W4 consumerとの外部cross-head検査 | 176 PASS / 2 FAIL。下記の旧欠陥証人の意味の変化。通常consumerの失敗ではない |
| Ruff0.16.7 | PASS |
| repository contracts | PASS |
| Node22.22.2 adapter | 37 PASS / 0 FAIL / 0 SKIP |
| 19原本照合 | S49のみ不一致、残り18一致。期待SHA不変更 |
| 正常try本体AST照合 | 保護原本/旧candidateと一致 |

新規32件のうち18ケースは `S49_FAULT_RECORD` に注入/calls/exits/report/rc/取消伝播を出力する。詳細故障は個別assertとcaptured reportで照合する。
既存W4 readback testが候補単独で10 FAILする入れ子asyncio.runは未修正baselineでも確認。最新W4 `1473c74e` の既存fixture修正1行（`await asyncio.to_thread(_offline_lines)`）をこの隔離候補の既存testへ適用した。W4 runtime/sourceの変更や新しいW4合成試験の追加はしていない。
全量pytestの開発途中2実行は追加W3 cleanup修正のため中断し、1501/1502 PASS時点のログを保持。完了した全量成績としては数えない。

最新W4 `1473c74e` の未変更test/consumerと今回S49 blob `b0b96c79...` を外部pytest pluginでメモリ上だけ接続した追加検査は176 PASS/2 FAIL（0 SKIP）。失敗2件は `test_original_s49_qualify_fake_node_cleanup_failure[exit_7/shutdown_exception]` が保護された旧欠陥の証人として `original_rc == 0` を期待するため、今回の正しいFAIL/rc1と一致しない。得られた両FAIL reportは最新 `audit_original_s49_cleanup_claim_offline` が拒否することも2/2確認。これを新S49の正常経路回帰失敗とは解釈しない一方、cross-head全件PASSとも呼ばない。正式採用時に旧欠陥証人の期待意味をownerが別審査し、W4本線のfixtureを今回は書換えない。

既存 `.github/workflows/self-demo.yml` にoriginal S49 focusedのPython3.11/3.12 jobを追加する。JUnitのcaptured故障記録をartifact保存する。新しいworkflow/Issue/PR/Action issuerは作らない。
既存path allowlistにはこの専用S49 test/docだけを明示する。19保護blobの期待SHA・S18試験・保護jobは一切緩和せず、その拒否を保持する。
CIの保護拒否を除外した全greenとは表示しない。exact HEADの各jobとfull/physical SKIPPEDはowner最終コメントで別記する。

## 保護原本照合

保護原S49 `fd2b06e9dbed17be0e35b3a1bbd0ed423b9af258`、開始candidate `9064982380d1dc7fbc936939c9901ffecd9d8714`、今回 `b0b96c798593f0621ac63076929cc4ab287812e7`。
固定19原本のbefore/afterは以下。beforeは保護基準、開始candidateのS49のみ上記906498…だったことを別記する。

| Path | before protected Git blob | after candidate Git blob |
| --- | --- | --- |
| `adapters/mineflayer/s49_normal_session_real_ci.py` | `fd2b06e9dbed17be0e35b3a1bbd0ed423b9af258` | `b0b96c798593f0621ac63076929cc4ab287812e7` |
| `adapters/mineflayer/s34_native_world_cognition_ci.py` | `eaecb117ad26059d6d2abb2c12bca61b2dce1f01` | `eaecb117ad26059d6d2abb2c12bca61b2dce1f01` |
| `adapters/mineflayer/s31a_real_server_ci.py` | `7ee3e95af66e1b981f72509a3dd661d79ef95744` | `7ee3e95af66e1b981f72509a3dd661d79ef95744` |
| `adapters/mineflayer/process_session.py` | `6eec8f80621c581d47154f7c76e72303e00c04f0` | `6eec8f80621c581d47154f7c76e72303e00c04f0` |
| `adapters/mineflayer/normal_action.py` | `0ded8fa296c92076a643de08cd6fc360061e1d08` | `0ded8fa296c92076a643de08cd6fc360061e1d08` |
| `adapters/mineflayer/execution.py` | `2af25bc6808f8a4199fe2ee500d1c1dfbea25de2` | `2af25bc6808f8a4199fe2ee500d1c1dfbea25de2` |
| `adapters/mineflayer/action_outcome.py` | `502a14304c8ab9f5e37bff4a054cf2a21730d294` | `502a14304c8ab9f5e37bff4a054cf2a21730d294` |
| `src/relay_self/intent.py` | `f4ef9500cd7941e5e9e07fd41ac2b6e4b4d5ac25` | `f4ef9500cd7941e5e9e07fd41ac2b6e4b4d5ac25` |
| `src/relay_self/skill.py` | `61885956810b4125721f685d449b361262b71120` | `61885956810b4125721f685d449b361262b71120` |
| `src/relay_self/action.py` | `869e761cfa2646f48f12e5e8088375ae64f04607` | `869e761cfa2646f48f12e5e8088375ae64f04607` |
| `src/relay_self/action_supervision.py` | `3320caab19d05afa74f046e3e0f143bc1aad5821` | `3320caab19d05afa74f046e3e0f143bc1aad5821` |
| `src/relay_self/learning.py` | `9fd949e94e91ded1c070d359378833f354fba577` | `9fd949e94e91ded1c070d359378833f354fba577` |
| `src/relay_self/habit.py` | `edc8904753421ef836843ae736f194f5a3a39168` | `edc8904753421ef836843ae736f194f5a3a39168` |
| `src/relay_self/action_feedback.py` | `8ae84e2e555550128a59a23c342f67a032a0c859` | `8ae84e2e555550128a59a23c342f67a032a0c859` |
| `src/relay_self/action_outcome.py` | `d28bbc1745104bcd7872061bef2fe6222ceccb2a` | `d28bbc1745104bcd7872061bef2fe6222ceccb2a` |
| `docs/postmain-architecture.json` | `e8419c55b5535d451346fd2a9a3c42326a80aa29` | `e8419c55b5535d451346fd2a9a3c42326a80aa29` |
| `docs/postmain-architecture.md` | `62b8e807d1b35a7f06d15b61e411434f57fe111d` | `62b8e807d1b35a7f06d15b61e411434f57fe111d` |
| `tests/test_postmain_architecture_freeze.py` | `d343aa052541b4ee9d2ce3e00653cc1a56d681ce` | `d343aa052541b4ee9d2ce3e00653cc1a56d681ce` |
| `src/relay_self/persistent_cognition.py` | `5d4fff3fa10bad78f98118758c8a22d53e8390fb` | `5d4fff3fa10bad78f98118758c8a22d53e8390fb` |

S18 architecture manifest/document/frozen testは同一。S49以外の18原本は同一。固定19原本testのS49不一致は設計された保護拒否である。
この機械的照合は独立ownerの採用審査を代替しない。#392 ownerの明示承認と必要な保護例外/rebaseline決定まで **PROTECTED_SOURCE_CHANGE_NO_GO**。
W4 #634、S #545、mainへmerge/cherry-pickせず、期待SHAを書換えてgreenにしない。

Rollbackは専用branch上で本修正commitをrevertし、開始HEAD `52fda1926991ca41695327746d7b918337ef6118` と比較する。reset/force-pushは不要。
保護原本そのものへ戻す必要がある場合は、別owner commitで `git show fd2b06e9dbed17be0e35b3a1bbd0ed423b9af258 > adapters/mineflayer/s49_normal_session_real_ci.py` とし、hash-objectでfd2…への一致を確認する。これは手順書であり今回は実行しない。
古いreport、凍結証拠、one-time grant、W4/S/primary checkoutを修復/再生成しない。

## W4 live leaseへの具体的な引渡し条件

cleanup修正の工学的PASSからlive有効化を導かない。原ownerとW4の接続は別レビュー。

| 責務 | 次工程の必須条件 |
| --- | --- |
| original session単一receiver | `_new_session`で唯一のsessionが作られた後、host起動前にownerがlease adapterを1回だけ設置。W4はprocess stdoutを直接読まない |
| lease発行/消費/取消 | 同じsession/run/operationに束縛した明示capability。PREWORLD read完了→取消/消費→ACTION_READへの単方向遷移。task ID/ContextVar/Lockだけを権限としない |
| opt-in | default原S49経路は不変。明示bool/CLI設定・新規run ID・取得前契約pinが揃った時だけW4接続を検討。旧grant再使用禁止 |
| L0/S14/S16順序 | ownerのpreprobe→既存server writer配置→既存collector marker→同じreaderのpostprobe→L0→S14 admission→元executor→S16 OUTCOME。cancelをまたいで再開しない |
| issuer単一性 | `NormalSessionActionExecutor`以外が新規Action/許可を発行しない。W4観測/receiptがAction/S10 grantを作らない |
| 競合防止 | original staging/host/W4 placementが同時にreceiverやWorld配置を所有しない。元3刺激scriptをW4配置に再ラベルせず、置換/排他をowner審査する |
| shutdown中の失効 | host終了/取消時に全leaseをQUIESCEしてからNode shutdown drainへ唯一readerを移す。pending readはsettleし、未確認ならBLOCKED |
| 取消後の再発行禁止 | 同じsession/runのgrant ledgerをterminalにし、cleanup callback/後着frameからleaseやActionを再発行しない |
| stale grant拒否 | session/run/request/probe seq/principalを厳密照合し、sessionを跨ぐgrantや再利用tokenをfail closed。local ledgerをglobal single-useと呼ばない |
| external custody不在 | 独立custodian/signer、取得前pin、native source/配置tick、fresh grantが揃わなければ `W4_EXTERNAL_TRUST_NO_GO / PREWORLD_BLOCKED` |

最小interface案は、原ownerがsession作成後/host開始前に明示opt-inのlease設定を行い、finally入口で同じownerのquiesce/revokeを同期に要求し、その完了をcleanupが検証するseam。別案として公開 `force_stop_and_reap(timeout)` / `seal_incomplete_capture()` を既存sessionへ設けるなら、process_session保護変更として別審査する。
今回はこれらのAPIや新しいlive経路を導入しない。外部信頼と正式な実行権限のないQUALIFICATION/SCIENCEは実施しない。

## 証拠の保存先

local evidence root: `/home/rinsa/work/s49-cancellation-evidence-20261021`。
独立baseline source/probe/JSON、修正後JUnit/captured故障記録、全量pytest、Node/Ruff/contracts、source-audit.json、CI job/log、GitHub投稿/readbackを保存する。最終SHA256 indexは全結果確定後に生成する。
コミット後のexact HEAD結果とCI詳細は#392/#633/#634の完了報告を正とする。ローカル結果をCIと混同せず、SKIPPEDを成功へ算入しない。
