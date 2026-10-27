# T1k 複数STOP/Resume・故障耐性 実Minecraft DEV — 2026-10-27

**DEV_ONLY / DEV_WORLD_OBSERVED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**。
正常2世代は4試行中 **2 PASS / 2 FAIL**。故障選択は6試行、通常reportは全件FAILのまま。
最終の3ケース（run-005/007/010）で **NATIVE_FAULT_OBSERVED /
FAULT_INJECTED_FAIL_CLOSED_DEV_OBSERVED**。未注入・未確定試行は成功に数えていない。
全10試行の測定、原本report/hash indexのSHA256、World/session ID、再観測seq、
停止owner、各ledgerの値・tickは[測定JSON](t1k-native-dev-results-20261027.json)に保存した。

## 対象・実行環境

branch `self/dev-t1k-stop-resume-faults-20261027`。
開始local/remoteとも `5b0e54b54aa4089c1b5908886641ac25d37babce`。
T1j `8b02e27bf9ec11a10077b39e41bfa850c52a5f9d` の祖先関係を確認。
mainの既存clean checkoutを維持し、`/home/rinsa/work/relay-self-t1k-20261027` に隔離。
主修正 `564869429c8bf17d25afe8a5b31ed090c054cb16`、ACK照合修正 `0b95ac6a`。
run-004以降はcommit済み実装を使用。run-004〜008は主修正、run-009/010はACK照合修正を含む。
各 `subject.json` と `run-NNN-launch.json` に実際のHEAD・argv・source hashを保持。
run-003は主修正と同じ制御ロジックで、STOP2計測・cleanupの例外保全追加前の試行。
run-002の実行中にlineage検査を補強したため、この試行を最終実装の証明には使わない。

実機確認: Microsoft Windows 11 Home / WSL2 / Ubuntu 24.04.4、
Python 3.12.3、Node v22.22.2、Java/Javac 21.0.12.1、Maven 3.9.11。
Paper 1.21.8は既存T1h run-006/t1h_input_residual/server/paper.jar。
同serverのcache/libraries/versionsだけを各新Worldへコピーした。
既存World本体は起動・上書きしていない。Pluginは本隔離worktreeでビルド。
JDKは `/home/rinsa/work/s50-p1-flat-native-evidence-20261017/jdk21/runtime`、
Mineflayerは既存T1e node-runtimeを読み取り利用。
実CLI `--help` を確認し、R1/R2はユーザー指定の別々のCLI tokenを使用。
故障ケースにはR2 tokenを渡していない。

## Python / Node / Java

- 指定focused初回: 123 PASS。補強後focused: **158 PASS**（指定11ファイルに実行故障・原本照合を追加）。
- FAST: 初回564 PASS、最終 **587 PASS**。選択は既存T1j 33ファイル＋T1k 4ファイル。
- Node 22 `node --test adapters/mineflayer/*.test.mjs`: **68 PASS**。
- Java 21 Plugin Maven package: **BUILD SUCCESS**。
- Ruff、repository contracts、git diff --check通過。FULLは実施していない。

最終ログは外部rootの `focused-delivery.log`、`fast-delivery.log`、`node-all.log`、
`java-build.log`、`ruff-delivery.log`。テスト期待値をPASS目的で緩和していない。

## 実試行とFAIL原本

| run | ケース | 原本report | 結果・原因 |
|---|---|---|---|
| 001 | 正常2世代 | FAIL | 第2STOPの生存probe IDが第1STOPと重複。native拒否 |
| 002 | 正常2世代 | FAIL | 実系列は完了したが、reportが計算プロパティstateをJSON直下から取得して誤判定 |
| 003 | 正常2世代 | PASS | 2 STOP ACK、R1/R2、最終OUTCOME |
| 004 | 正常2世代 | PASS | commit済み実装、STOP2時点・全ledger計測を含む |
| 005 | 送信前断線 | FAIL | 実断線観測、permit消費・再開Motor0、期待拒否成立 |
| 006 | 送信後断線 | FAIL | 初期sourceのage上界191.281/199.452msでlatched。注入前、NATIVE_UNVERIFIED |
| 007 | 送信後断線 | FAIL | applied ACK後の実断線、UNKNOWN、期待拒否成立 |
| 008 | clear ACK欠落 | FAIL | native ACK保持・consumer欠落は存在したが、wire/parsed形状の照合誤りで原本分類は未確定 |
| 009 | clear ACK欠落 | FAIL | EAT中age上界488.351〜490.986ms。150ms上限で注入前拒否、NATIVE_UNVERIFIED |
| 010 | clear ACK欠落 | FAIL | 照合修正後の新World、ACK欠落検知・UNKNOWN、期待拒否成立 |

修正: STOP markerに結び付く一意な生存probe ID、終端stateの明示保存、
失敗経路にもpermit消費/未送信/UNKNOWN/ledgerを保存、同じreceiptのsession/seq/
Action/effect/result/error照合。lineageは旧marker・旧Action/clear・古いseq・異World/
Player・failed ownerの第2STOP ACKを拒否。fixture例外でも資源回収処理へ進む。

追加テスト作成中のFAILも保持した。`repair-focused-001.log` の1件は、最初のSTOPに
未来の第2marker・欠測を含むfixtureを渡した誤りで、実際の増分原本に合わせて修正。
`fault-audit-real-shape-fail.log` は実際のparsed receipt（typeなし）で照合不具合を再現し、
コード修正後に通過。旧ACK/異seqの負対照も追加した。
191〜491msの鮮度拒否は上限を変えず保持した。遅延のホスト内根本原因は未特定であり、
片道Paper→Node遅延へ読み替えていない。最終clear試行では並行pytestを終了させた。

## 同一World/sessionの正常2世代

両PASS Worldで MOVE×2 → cooked_beef EAT → 第3MOVE中STOP → 元S49 clear ACK →
独立Paper 8静止遷移 → STOP1 ACK → R1 → Paper/native/Paper → MOVE中STOP2 →
元S49 clear ACK → **別marker**・8静止遷移 → STOP2 ACK → R2 → Paper/native/Paper →
新MOVE OUTCOME → clear ACK・後続8静止観測、追加Actionなし。
reader・Motor writer・Supervisor・Executorは既存のS49経路を維持。

各Worldでset_control **5**、clear_controls **5**、consume_held **1**。
第1marker `T1I_MULTI_AFTER_CLEAR`、第2marker `T1K_R1_AFTER_CLEAR`。
STOP IDは `t1i-multi-epoch-stop` / `t1k-second-stop`、
resume IDは `T1J-R1` / `T1J-R2`。旧owner0/owner1はlatchedのまま、owner2で最終MOVE。
全Action/effect ID重複0、permit再利用0、旧ACK流用0、追加再開0。
lineageは2世代完了・open generationなし・failed=false。

| MOVE | Action ID | Supervisor終端 | run-004確定距離 |
|---|---|---|---:|
| 初期1 | t1f-epoch-0 | OUTCOME | 0.626907m |
| 初期2 | t1f-epoch-1 | OUTCOME | 0.626907m |
| 初期3 | t1f-epoch-2 | UNKNOWN | 終端距離未確定 |
| R1 | t1j-T1J-R1-move | UNKNOWN | 終端距離未確定 |
| R2 | t1j-T1J-R2-move | OUTCOME | 0.626907m |

R1はPaper基準→STOP2静止窓の変位0.426891mを別測定したが、UNKNOWNをOUTCOMEへ変更しない。
EATはOUTCOME、food18→20、cooked_beef3→2、credit `t2-native-meal` 1件。
R1/R2による旧食事の追加入金0。

| run | R1 Paper→native→Paper seq | R1基準/欠測tick | STOP2凍結tick | R2 seq | R2基準/欠測tick | R2会計tick |
|---|---|---|---:|---|---|---|
| run-003 | 463→464→465 | 1393 / 19 | 1394 | 496→497→498 | 1413 / 18 | 1414–1431 (18) |
| run-004 | 458→459→460 | 1389 / 18 | 1390 | 491→492→493 | 1409 / 18 | 1410–1427 (18) |

run-004のSTOP1/STOP2 clear ACKはseq433/466、各ACKは対応clear、
独立marker、Paper静止窓、生存probeで成立。STOP要求/再認可/permit消費/Motor送信は
Python単一時計の記録、clear receiptはnative seq、Paper静止窓はserver tickで追跡。
Actionイベントのat_nsは既存fixtureの論理順序で、物理遅延計測に使わない。
両PASSでsession seqは厳密単調かつ欠番なし、raw Paper WorldTick連続。
150ms鮮度上限を維持し、run-004全417 raw snapshotはADMITTED、最大上界118.300402ms。
これは同じNode時計のcausal-age上界であり、異時計の直接減算をしていない。

## M0/P1の世代別凍結

run-004: ledger0はtick1370で凍結、341行、仮想energy15.621275321043846、
fatigue0.0052093432652756365、credit1件。R1基準1389から新ledger1を開始し、
tick1390の1行でSTOP2凍結、energy15.61992965892872、fatigue0.01012258556778389。
R2基準1409からledger2の連続18行のみ会計した。会計行計360、欠測18+18=36 tick。
run-003は343+1+18=362行、欠測19+18=37 tick。

ledger0/ledger1の過去行・energy/fatigue/credit集合は不変を比較確認。
凍結前の値は各 `t1k_old_ledgers`、新区間は `resume_attempts_dev[].ledger` に全行保存。
欠測基礎代謝・距離・疲労回復を架空補完せず、stop_gap_debit_and_credit=0。
Minecraftの物理代謝は継続しており、仮想carryは停止中の物理全コスト復元ではない。
新区間の基準tickは非課金、その後の連続観測だけを会計。P1-qualified WAITは未成立。

## 実故障原本

| run / ケース | 実成立位置 | 再開Motor / clear送信試行 | Action | 通常shutdown |
|---|---|---|---|---|
| 005 / 送信前 | consumed R1・再観測後、Motor前のsocketClosed seq464 | 0 / 0 | 未発行 | Node3、ACKなし |
| 007 / 送信後 | set applied ACK seq464→socketClosed seq469 | 1 / 1、clear receiptなし | UNKNOWN | Node3、ACKなし |
| 010 / clear ACK欠落 | native applied clear seq472をPython consumerのみ欠落 | 1 / 1、clear再送0 | UNKNOWN | Node0、shutdown ACKあり |

3ケースとも **NATIVE_FAULT_OBSERVED / FAULT_INJECTED_FAIL_CLOSED_DEV_OBSERVED**。
通常reportのFAILをPASSへ変更していない。全てR1のみでR2 tokenなし、R1消費済み、
送信前/送信済みを区別。permit無効化済み、旧owner latched、旧ledger不変。
Action/effect ID重複・permit再利用・追加Action・架空OUTCOME・clear再送はいずれも0。
run-007はPython受信時刻でもset ACKがkick要求前に到着しており、
「送信済みだがACK未確認の切断」とは区別する。今回この別境界は未検証。

run-005の新区間会計0行、run-007はsource loss観測時と最終が同じ2行。
run-010は連続観測14行だけをMOVE_OR_UNDETERMINEDで会計し、ACK不明のclearをWAITにせず、
疲労回復0。停止欠測はrun-005が19 tick、run-007/010が18 tick。追加EAT credit0、最終credit1件を維持。
Node shutdown ACKをS49 clear ACKや第2STOP ACKの代用にしていない。

## cleanup・原本・保護

全10試行でJava exit0、Java/Node PID消滅、25565再bind、process_reap_complete=true。
通常transport shutdownは8/10。**run-005/007はNode exit3、shutdown ACKなし、
UNEXPECTED_DISCONNECT_NO_SHUTDOWN_ACK、cleanup_complete=false**。
これは資源回収完了とは別の事実。故障期待拒否を通常shutdown成功に読み替えない。

証拠root `/home/rinsa/work/t1k-evidence-20261027` のrun-001〜010を保持。
各server World、paper.log、native.jsonl、commands.jsonl、node/Python timing、
report.json、source_hashes.json、subject・launch原本とFAILログは変更していない。
全記録済みSHA256を終了後に読み戻して一致確認。元Worldは全件別UUIDで新規生成。
生成build/cacheは外部rootへ退避し、専用branchをcleanにしてpush。
main、Draft #545/#634、S18 freeze、R/V資格World・証拠、過去DEV Worldは変更していない。

## 未成立と次段階

R資格STOP、全subtick無活動、native source独立認証、P1-qualified WAIT、高TPS期限、
長時間自律性、停止中の実身体全コスト復元、モデル認知、科学的有効性は未成立。
FULL/main mergeは行っていない。P1仕様・M0/P1式も変更していない。

次段階は150ms超過のホスト/transport/処理待ちを同時計の証拠で切り分け、
sourceのlatchを解除せず、新規DEV Worldでstartup安定性と長時間のsource/ledger継続を評価する。
ACK未確認での送信直後断線は今回のACK適用後断線と別に、必要なら独立ケースで検証する。
