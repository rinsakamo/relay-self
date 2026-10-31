# L23 Paper × S49 × S16 実World DEV結果（2026-10-31）

新規Paper World **2回：初回FAIL、修正後PASS**。初回7 tick原本を保存し、
8件目を待たずに切断する実装不備だけを修正した。追加Actionや判定緩和はない。
同一の修正後WorldでS49 Action、S16後の追加移動、Paper連続tick、L23原本照合が成立した。
main・S側ownerブランチ・既存原本は変更していない。merge/force pushなし。

## HEADとFAST

- Branch: `dev/l23-paper-settling-boundary-20261031`。
- 初回実測HEAD: `c845f9fc6390dfdcc32f4acb10fd94db00b4bbac`。
- 修正後実測HEAD: `049cb0df29dfc627af85cf0500f610d71b97dd05`。
- 初回FAST: 97 PASS / 1 SKIP（Node PATH未指定）。Node22指定後98/98 PASS。
- 修正後FAST: **99/99 PASS**。Ruff・Python構文・repository contracts PASS。
- 最終の証拠・文書commit後も同じfocusedテストとchecksを実行し、GitHubコメントにexact HEADと結果を記録する。
- FULLは今回未実行。

## 原本からの結果

| 観測 | Run1（FAIL、原本不変） | Run2（DEV PASS） |
|---|---|---|
| S49運動Action | 1 | 1 (`s49-native-move-18`) |
| Action内移動 | 1.291498796m | 0.626906573m |
| native dispatch / S15 clear | seq25 / seq32、applied | seq22 / seq27、applied |
| S16正式OUTCOME | before24 / after40 | before21 / after28 |
| S16後native move | 0件 | 6件：29,30,31,32,33,35 |
| S16後追加移動 | 0m | **0.230263146m** |
| L22サンプル | 3、quiet 1/2/3 | 5、quiet 0/0/1/2/3 |
| PRE_FORWARD / POST_CLEAR | fullTime247 / 269 | fullTime242 / 248 |
| WAIT_BEGIN | fullTime270 | fullTime249 |
| Paper WAIT_TICK | 271–277、7件で切断 | **250–257、8件連続** |
| Paper活動 | 取得7件は静穏（不完全） | **250,251,252に活動** |
| L23 | PAPER_SOURCE_REJECTED | PAPER_SOURCE_SHAPE_REVIEWED_ONLY |
| Paper最終poseとS7最終probeの距離 | 未受理 | 0m（幾何のみ） |
| Node / Java exit | 0 / 0 | 0 / 0 |
| 所有PID消滅・World削除・25565再bind | 全確認 | 全確認 |

Run2はPaper World UUID `6dc19601-85ef-4a4c-b900-a9dcb1162438`、
native session `6b29d6fe-ea4d-41cb-8645-dd00f9c8f062`。
Paperは位置とtick_meter_blocksで活動を記録し、motion_packets/blocksは0のまま。
後者の0を入力無活動の証拠にしない。nativeの最終2 Goal probesはseq40/41。
Goal幾何candidateはNOT_REACHEDだが、正式受理はUNDETERMINED。

原本は実行reportと別に読み直し、S7 receipt SHA・S16・Paper各行の順序と
fullTimeを検査した。独立readbackは実行report内L22/L23結果と一致する。
ログ順 `PRE_FORWARD → POST_CLEAR → WAIT_BEGIN → 8 callbacks` と各tick値を
区別する。POST_CLEAR fullTime248をS15のserver実効clear tickとは主張しない。

## 固定資産・介入

Java runtime 21.0.12.1、Node 22.22.2、Python 3.12.3、Mineflayer 4.39.0、
Maven 3.9.11、Paper **1.21.8 build60 / 29c8822**。
既存Paper JARの実測値を[公式build60 metadata](https://fill.papermc.io/v3/projects/paper/versions/1.21.8/builds/60)のsize/SHAと実行前に照合。

| 資産 | SHA256 |
|---|---|
| Paper server | `8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e` |
| S plugin JAR | `495a2735c61ae8d017f45b9af5e078dcca0d7113a554eadf5664982ff58f12df` |
| 有効config.yml | `e5961d918d8d59ce29ac22723dff0936d2b59732cd7188317a5a3ead894b19bc` |

S HEAD `3240691a29e1f02bcb89cc20cf650ac9a0e83662` の未改変4ソースを
外部ディレクトリにgit archiveで取得し、各byteを当該commitと照合してビルド。
JRE-only環境でのビルド失敗2件と、既存JDK21指定による成功ログも保存した（World試行ではない）。
標準configをコピーし、dev-enabledとs50-tick-meter-devだけを有効化。
元のM0.2・16 Action・その他設定を維持した。**代謝/exhaustionへの能動介入であり純粋な受動観測ではない。**
各新規Worldは既存S49が一時ディレクトリで所有し、同じ唯一のS7 readerを使用した。
Goal (0,0)、許容0.49m、安定差0.05mはWorld開始前固定。
独立L20/L21原本は今回に再登録できる適切な原本がなく、偽造せずオプション未使用。

## 判定と次の最小要件

`DEV_ONLY / CLOCK_ALIGNMENT_NOT_ATTESTED / STABILITY_UNPROVEN /
GOAL_UNDETERMINED / L10_PAIRS_0 / S10_UPDATES_0 / S11_GRANTS_0 /
P1_WAIT_0 / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`。

今回のDEV物理観測ループは成立。次に強い判定が必要な場合の最小追加要件は、
S50 owner [#627](https://github.com/rinsakamo/relay-self/issues/627) が生成する
S15実効入力解除とWorld tickのsource anchor、および対象区間の入力活動coverage。
L23はそれを読み取る。独立Goal正式受理は別ownerの事前登録・受理gateが必要。
8静穏callbackや数値一致だけで完全物理静止、P1 WAIT回復、L10学習を受理しない。

## 証拠

外部原本: `/home/rinsa/work/l23-evidence-20261031/`（資産/build/実行監視scriptを含む）。
Git保存コピー: [docs/evidence/l23-real-20261031](evidence/l23-real-20261031)。

- [Run1 原本照合](evidence/l23-real-20261031/run1/original-readback.json) / [stdout](evidence/l23-real-20261031/run1/server.log)
- [Run2 S7受信原本](evidence/l23-real-20261031/run2/capture/native_bridge_received_original.jsonl) / [送信原本](evidence/l23-real-20261031/run2/capture/native_bridge_sent_original.jsonl) / [receipt](evidence/l23-real-20261031/run2/capture/native_bridge_source_receipt.json)
- [S16 owner原本](evidence/l23-real-20261031/run2/capture/l18_s16_terminal_original.jsonl) / [事前Goal](evidence/l23-real-20261031/run2/capture/l16_pre_world_goal_plan.json)
- [Paper stdout原本](evidence/l23-real-20261031/run2/server.log) / [L22](evidence/l23-real-20261031/run2/l22-diagnostic.json) / [L23](evidence/l23-real-20261031/run2/l23-readback.json)
- [原本再読検査](evidence/l23-real-20261031/run2/original-readback.json) / [S49 report](evidence/l23-real-20261031/run2/s49-report.json) / [cleanup](evidence/l23-real-20261031/run2/cleanup.json)
- [環境・exact argv・HEAD](evidence/l23-real-20261031/run2/environment.json) / [資産pins](evidence/l23-real-20261031/assets/pins.json) / [SHA256SUMS](evidence/l23-real-20261031/SHA256SUMS)

GitHub: [Issue #640](https://github.com/rinsakamo/relay-self/issues/640) / [Draft PR #641](https://github.com/rinsakamo/relay-self/pull/641)。
