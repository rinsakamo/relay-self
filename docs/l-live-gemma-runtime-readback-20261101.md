# Lレーン 実GemmaライブOPEN — 部分成立、World runはFAIL

2026-11-01 JST。Draft #677（base #675 → #673 → #671 → #668 → #666）、#431 / #653 / #537。

## 判定

**新規World 1回、再試行0。実Gemma OPEN 2回と元S49/S16 3組を観測したが、run全体および必須G3/live-prefix監査はFAIL。最初のライブ認知ゲート全体のPASSは成立していない。**

実行HEAD: `f51e7e6b2ffb6908b433ce9920ad0492411fe170`。
この文書・原本公開は実行後の別commitであり、実行HEADへ遡及しない。
main / #675 / 他レーン / 過去G3成功原本は変更しない。

#537の2026-10-14 DEV運用、2026-11-01認知発達方針、#653 G1、および今回の依頼の最大3 Action / 最大2 OPEN / 1 World / 再試行なしを適用した。資格・科学用grantや過去の消費済one-shotは使用していない。

## 実装・オフライン

ライブ入力に、同じ元Paper原本の7事前固定予測・実測絶対誤差・CHEAP zero-next MAEを追加。予測/採点/位置差の不整合は拒否する。以前は変位だけがL2に渡り、予測誤差数値は欠けていた。

既存`LlamaCppRelayProvider → RelayEngine.open`を使用するL専用journal subclassを追加。HTTP request/response（response ID・model・tokens含む）、単調時計、要求・応答原文・例外を保存。L経路だけ最大512生成tokens、JSON object形式、既存45秒gate/40秒HTTP timeout、1要求1試行、最大2回を維持。出力検証前に次の実験者刺激を解放しない。G2/G3のdefault zero-call経路は不変。

Python 3.12.3: **205 PASS**。timeout後の再呼出し拒否、不正JSON原文保持、未来trial拒否、元予測数値照合、HTTP journal/budget、S49単一issuer/cleanup、G2/G3回帰を含む。Ruff・compile・repository contracts PASS。依存node_modulesを配置後のrepository contractsは依存パッケージのREADMEリンクを誤走査してFAILしたため、依存物を外部へ移動し、tracked sourceを含む依存物なしのworktreeで再確認してPASS。初回Mavenは環境JDK不足でFAIL、既存JDK21の絶対パスを指定してBUILD SUCCESS。いずれもWorld前。

実行HEADのGitHub source-only CIは4件すべてSUCCESS（モデルはfixtureであり、実WorldのPASSではない）。

- [L OPEN 205 tests](https://github.com/rinsakamo/relay-self/actions/runs/41311892391)
- [L prior-source](https://github.com/rinsakamo/relay-self/actions/runs/41311892464)
- [G2 regression](https://github.com/rinsakamo/relay-self/actions/runs/41311892387)
- [G3 regression](https://github.com/rinsakamo/relay-self/actions/runs/41311892452)

## 実モデル・World同一性

開始前に実プロセスとlisten portを確認し、llama-server/Paperの既存稼働なし。モデルのダウンロードなし。所有Gemmaサーバーをlocalhostのみへ起動し、ファイルSHA、実exe/argv、`/proc/98374/maps`の当該GGUF mapping、`/v1/models`/`props`、response model/fingerprintを照合した。aliasだけによる重み同一性の断定ではない。

- GGUF: `/home/rinsa/models/gguf/gemma-4-12B-it-Q4_K_M.gguf`
- SHA256: `c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`
- llama.cpp: build10874 / `e2d2c0d6a`、実binary SHA `ad5d4787bc739ad88a55b614c18d29580b3ec071cad632edb0ebb42b89f78536`
- endpoint: `http://127.0.0.1:8080/v1/chat/completions`、alias `relay-self-gemma4-12b-q4km`
- Paper 1.21.8 build60 SHA: `8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e`
- source-built plugin SHA: `3be4d5827f24f163617c0848f665ff1f4d01daa96ae10eb41c9450ec9a19ef00`
- Java21 / Node22.22.2 / Mineflayer4.39.0。既存正規S49 Executorのみ使用。
- World UUID: `c692a108-1aeb-46f8-85d1-339bcbb21464`
- native session: `9aea8e8f-b224-412f-8301-fb2d0054f364`

## 身体経験・モデル応答

元L0判断はWAIT → MOVE_AWAY ×3、実行primitiveはGRASS/MOVE_BACKWARDのまま。L2による選択・条件変更・追加Actionは0。

| trial | 元Action | Action移動 m | native dispatch/clear/S16 seq | Paper WAIT ticks | WAIT総変位 m |
| --- | --- | ---: | --- | --- | ---: |
| 1 | s49-native-move-33 | 0.6269065734 | 36 / 41 / 42 | 293–300 | 0.0642466015 |
| 2 | s49-native-move-60 | 0.7342911432 | 63 / 68 / 70 | 493–500 | 0.0322335431 |
| 3 | s49-native-move-89 | 0.6269065734 | 92 / 97 / 98 | 722–729 | 0.0642466015 |

OPEN1はtrial1終了後、OPEN2はtrial2終了後。各入力はそれぞれ1件/2件の完了済経験であり、future Outcomeなし。request_idは`l-mp11-live:<World UUID>:after-1` / `after-2`。実際のHTTP要求と再構成した元Paper入力は完全一致。

| OPEN | wall elapsed s | prompt/output tokens | 仮説 | 前試行との対応・限界 |
| --- | ---: | --- | --- | --- |
| 1 | 6.835496 | 1568 / 184 | QUESTION_APPLICABILITY、PHASE_DEPENDENT、CHECK_PAPER_CALLBACK_PHASE、予測総変位0.0642466015m | trial1の0.032m予測と0.022m第一pair誤差に言及。ただし説明では両者をprediction errorと混同。反証案はphaseとの相関確認。 |
| 2 | 8.309113 | 2250 / 196 | KEEP_UNRESOLVED、SURFACE_DEPENDENT、CHECK_PAPER_CALLBACK_PHASE、予測総変位0.048m | trial1/2の第一pair誤差0.022/0.012mとCHEAP MAE約0.002/0.0007mに言及。CHEAP誤差をthresholdと呼ぶ誤りあり。同一grassのみなのでsurface依存は未支持の候補。反証案はsurface比較。 |

HTTP response IDs:
`chatcmpl-Wa2ybFKZOuYKsRhE8ISpdOO1VR1ZMxGY` と `chatcmpl-irf4Tl1QAVPHqK47SUCvhx9q2cUYY4ye`（[OPEN2原文](evidence/l-live-gemma-20261101/llama-http-2.json)）。両応答はstop終了、JSON schema検証成功、UNKNOWN/CONDITIONAL_HYPOTHESISの制限内。

trial1元予測MAE=0.0038579825m、CHEAP=0.0021077733m。trial2元予測MAE=0.0022487135m、CHEAP=0.0007444012m。**元の固定予測はCHEAPより劣位**。OPEN1の総変位予測は直前の総変位をそのまま反復しており、構造学習を示さない。次trialでの総変位予測誤差は約0.0320130584m / 0.0162466015mだが、異なる対象のper-tick MAEと比較しない。単発改善を学習採用条件や科学的利得にしない。

A: **実Gemmaがライブ経験を受けて2仮説を生成した事実を部分DEVとして確認**。一般論だけでなく入力の具体的な誤差・比較数値に対応する。ただし正しい因果解釈や法則発見は未確認。

B: family・reconsideration・反証案・数値予測の変化は観測。**経験による有効な仮説改訂の成立はUNDETERMINED**。前の仮説自体は次要求へ渡しておらず、厳密には履歴1件/2件に対する独立生成。経験差の因果効果を識別する対照もない。

C: 実装対象外。L2選択実験0、学習admission0、Memory/S10/S11/L1/Habit採用0、L0昇格0。Goal UNDETERMINED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN。

## 原本監査とFAIL保持

Paper完全原本は672136 bytes、SHA `faf648c3654fc6cafdbd9542dc2f5b30cde408973dcd9c9cf30713148d9b7777`。終了時のJLine console promptが改行なしの2 bytes `> `（hex `3e20`）として残ったため、既存`audit_multi_trial_paper`のcomplete-line条件が拒否した。runner原報告はstatus FAIL、paper_windows_attested=0。これはWorld内容やL2 schemaの失敗とは区別するが、全体FAILをPASSへ読み替えない。

指定のG3監査は正当な2応答を確認後に`--expected-live-l2-calls 2`で1回実行、live-prefix監査も実行した。**両方exit1**（元runが成功していないとして拒否）。各失敗ログと原reportを保持。原本への改行追加、原報告のstatus変更、既存監査条件の緩和、再Worldは行っていない。

別の[補足readback](evidence/l-live-gemma-20261101/supplementary-readback.json)では、完全原本のSHAと末尾2 bytesを明示し、診断用complete-line prefixにのみ既存Paper readerを適用。24 WAIT/input callbacks、21予測pair、3草地lockを照合した。これは必須G3監査の代替PASSではない。補足scriptも公開し、結果を`PARTIAL_DEV_SOURCE_RECONCILED_ORIGINAL_RUN_REMAINS_FAIL`に固定。

3ライブprefixの終了後原本照合は3/3一致:

1. 178460 bytes: `a4c3e88c9a107622f91e621b5e8f397a8481934b9ec196c4aef81f0b1dc7e04e`
2. 441948 bytes: `39fe117e07ab3f793423b163c43a9fd245df14080970eb83bd7784276502a98a`
3. 667269 bytes: `5583ba7c64ed847f8867a95413b7e5e219bd361c0fb507dae6fee8567c34ccaf`

W3 stdout SHA `4d626a9e765240981950564d35575098fedf71bbf0707fd9dfd913eb0b945066`、107 frames、seq0–106、shutdown ACK1、EOF確認。3組のdispatch/clear/before/after原frameとS16対応を照合。W3 stdoutはMinecraft TCP独立認証ではない。

ホスト実装順序・native seq・元Paperマーカー・要求内容とmonotonic journalは整合。モデル完了前の次刺激解放なし。独立共通時計によるlive時刻認証や実効S15 clearのPaper tickはNOT_ATTESTED。Paper input OFFだけを物理安定やGoal成功にしない。

cleanup: Node98997 exit0 / Java98865 exit0、PID消失、使い捨て`/tmp/relay-self-s49-91d9d6bs`消失。今回所有したGemma98374もSIGINTで正常終了しPID消失。25565/8080解放。原本は外部証拠rootにも保持。

## 証拠と次の課題

[原report](evidence/l-live-gemma-20261101/report.json)、[Paper原本](evidence/l-live-gemma-20261101/paper-stdout-original.log)、[W3原本](evidence/l-live-gemma-20261101/native-stdout/w3-node-stdout.raw.jsonl)、[OPEN1原文](evidence/l-live-gemma-20261101/llama-http-1.json)、[SHA一覧](evidence/l-live-gemma-20261101/SHA256SUMS.json)。外部証拠root: `/home/rinsa/work/l-live-gemma-evidence-20261101`。GGUF・認証情報は公開しない。

次は**将来の新規run向け**に、JLine末尾promptと欠損した観測行を厳密に区別する原本保持方式を事前固定する。過去FAILは維持。その後、前仮説と予測/実測/誤差の型付きfeedbackを次OPENへ渡し、数値の役割（予測・単pair誤差・MAE）混同を拒否する。さらに別途正規ownerによる条件変更・事前freeze・反証・holdoutへ進む。今回の試験に再試行は追加しない。
