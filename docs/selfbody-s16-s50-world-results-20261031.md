# SelfBody × S49/S16 × S50 実World統合結果

2026-10-31、WSLで **DEV_WORLD_SELFBODY_S16_S50_JOIN_PASS**。
本物のS49 Action closure、正式S16、native Presentから既存SelfBodyViewを生成し、
同一WorldのS50 producer照合後、同じPythonプロセスでleaseを1回consumeした。
**実際の次認知epochによる参照は未実施**。補助readout取得と認知実行は区別する。

## ブランチ・変更

- 隔離branch: `dev/selfbody-s16-s50-world-join-20261031`。
- SelfBody開始: `ecb9ec8a8012ed6110393bc2085d0aa1a60cad77`。GitHub #647と一致。
- 成功World実行code: **`002117f6a8534b18a025a21d8da0f158c734593e`**。
- owner: SelfBody #632/#634/#646/#647、S50 #627/#642/#645、L23 #640/#641/#643。
- L23単一Action手順をDEV hostに接続。別履歴のreadback依存を
  [固定owner SHA・原本hash](selfbody-world-imported-owner-sources.json)付きで取り込んだ。
- S49通常runner、SelfBody core、native Present validatorは変更なし。
  sessionには既存L23の任意S7記録、bridgeには既存S50のdefault-off observerを接続。
- 既存executor/S15の`correlate_native_probes_dev=False`をこのhostだけTrueにし、
  **既存2 probe要求**をsession/Action/before-after IDで相関。応答一致を要求する。
  Action/control/clear/S16の権限・件数は変更なし。新しい生成ownerは作っていない。
- producerのtuple-valued `asdict`は既存CLIと同じJSON表現へ正規化する。
  対象はS50診断のみ。**typed S16/WorldConsequence/Presentは元objectのまま**。

## 全試行

| 試行 | code | 結果 |
|---|---|---|
| PREWORLD001 | 617088b4 | launcherの外部node_modules参照漏れ。Java/Node/World0 |
| 新規World1 | 617088b4 | Action1/S15/S16成立。before/after request_idなしでnative Present拒否、FAIL |
| 新規World2 | 7124045c | typed closure/native Present/SelfBody成立。S50 tuple/list表現差でconsume拒否、FAIL |
| 新規World3 | 002117f6 | S49/S16/native/SelfBody/S50/companion/cleanup、DEV PASS |

Worldは**3回**、実S49 Actionは合計3件、各World1件。
当初2回枠を保持し、schema故障修正後の最終1回を
[別の事前上限記録](evidence/selfbody-s16-s50-world-20261031/bounded-extension-before-run3.json)で宣言。
消費済みlease再使用、同じWorldのAction再実行、無制限retryはない。
World1 reportの空Action配列は補助接続拒否が追記より先だったため。
元S16/bridge原本は実Action1件を示し、failure auditに記録。FAIL reportは変更していない。

## 成功Worldの正式source

| 項目 | 実測 |
|---|---|
| session | `28241aa9-194e-4d9a-b384-a40e06f4a208` |
| Paper World UUID | `5a2a4aca-1fff-47e7-bbcf-9e16ebd04adc` |
| Action | `s49-native-move-20`、MOVE_BACKWARD、1件 |
| 決定native probe | seq21 |
| S15 before / dispatch / clear / after | **22 / 24 / 29 / 30** |
| dispatch / clear ACK | 各applied |
| 正式S16 | OUTCOME / observed_execution / executed |
| Action内変位 | 0.6269065734210617 m |
| typed closure | 元NormalActionClosedReadbackを1件取得 |
| S15 / S16 object | 元WorldConsequence / ActionOutcomeInterpretation |
| native Present | 実before/after probe、request ID一致、順序・provenance検査PASS |
| SelfBodyView | 元project_body_action_readback → compose_self_body_view、PASS |
| BodyObservation | session一致、native seq30、元after request/source一致 |
| consequence provenance | `normal-action-runtime` / `28241aa9-194e-4d9a-b384-a40e06f4a208:100` |
| 最終lease | ONE_S50_DIAGNOSTIC_JOIN_CONSUMED、保持pointerなし |

実行中にSelfBodyView/S16のobject identityとnative session/seq/request/source/
consequence provenanceをassertした。保存JSONはその検査診断であり、
typed原本の代替・事後再生成には使用していない。

## S50観測・結合

| 項目 | 実測 |
|---|---|
| WAIT_TICK / INPUT_TICK | **249–256、各8件連続** |
| Paper7入力 | 全8件全OFF（server-last-reported sample） |
| INPUT_EVENT | 0件 |
| tick249 / 250 / 251変位 | 0.049492188301323736 / 0.009543604920851934 / 0.00521080828678544 m |
| tick252–256変位 | 各0、完全静止の証明ではない |
| Node入力 | back ON → clear全OFF → shutdown clear全OFF |
| Node physics | 241 sample、番号連続 |
| write-return | player_input0 / position22 / position_look1 / flying0 / look0 / entity_action0 |
| sidecar | 267記録＋TRACE_END、complete=true / lost=false |
| S16後native追加変位 | 0.23026314641538548 m、別観測窓 |
| S50 source独立再読 | PASS |
| SelfBodyS50MotionCompanion | 元SelfBodyView identity保持、生成PASS |
| sampled_at / cognitive_summary | 8 tick identity照合、summary取得PASS |

PaperとNodeの時計は直接同期していない。write-returnはwire到達・Paper受信/適用の保証ではない。
入力OFFと残留移動の併存を再現したが、実効clear tickや全tick静止を主張しない。
M0.2は16 Actionの完全profileを保った**exhaustion能動介入**である。

## 次epoch・最小の残課題

readonly companionとcognitive_summaryは同一host内で利用可能になった。
既存passive SelfBody ownerは既存native認知probeを受けるIFであり、
このcompanionを次の実認知epochへ渡す正規slotは今回のhostにない。
**次epoch参照は未実施**。新しい認知判断、L0 Action、Goal確定、WAIT回復、
S10更新、S11 grant、M/P1回復、L8学習は発生させていない。
残る最小課題はownerの正規IFでのDEV opt-in readonly受渡しと、その参照実測。

## FAST・独立監査・cleanup

Python3.12: 指定SelfBody **87 PASS**を含む最終focused **238 PASS**、
session/cleanup回帰91 PASS、normal callback回帰35 PASS、合計**364件**。
Node22: S50 observer6 PASS、既存bridge/protocol37 PASS、合計**43件**。
Ruff、Python AST構文、Node構文、repository contracts PASS。FULLは未実施。
S16 UNKNOWN、clear ACKのみ、native欠落/順序不正、別session/Action/provenance、
重複closure、期限切れ、S50原本/tick/sidecar欠損、誤Worldを拒否。
成功原本のbyteコピーを使う5負対照も拒否。原本は変更していない。

終了後の別Pythonプロセスが元S7/S16/事前plan/PaperからL22/L23を再計算し、
report一致、Node連続記録/TRACE_END、S50 producer、Body診断のsource対応を照合。
独立CLI2本もPASS。typed真正性の検査は実行中に限定している。
全3WorldでNode0/Java0、所有PID消滅、World削除、port25565再bindを確認。
最終runner0。他レーンprocess終了、main merge、force push、既存branch/worktree変更なし。

## 原本・SHA256

外部全文原本: `/home/rinsa/work/selfbody-s16-s50-evidence-20261031/`。
JAR、build source、Node依存、runtime hashを含む。
成功Worldの稼働中にJAR **125個**と生成configのSHAを外側から採取した。
Java21.0.12.1、Node22.22.2、Python3.12.3、Mineflayer4.39.0、Paper1.21.8 build60。
pluginはS owner `e6d901d7dc3effb5c7516350233383fbb982bbb1`から新規build。
最初のJREのみのbuild失敗ログも保持し、JDK21明示で成功した。

[Git保存原本・FAIL履歴](evidence/selfbody-s16-s50-world-20261031/) /
[成功report](evidence/selfbody-s16-s50-world-20261031/run3/s49-report.json) /
[独立監査](evidence/selfbody-s16-s50-world-20261031/run3/independent-original-readback.json) /
[SHA256SUMS](evidence/selfbody-s16-s50-world-20261031/SHA256SUMS)。JAR/WorldはGit対象外。

| 原本 | SHA256 |
|---|---|
| Paper server | `8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e` |
| 新規plugin | `405657013fa315d76aab3730c6324b3583f9b30facf9233ef0b88fda9026585a` |
| active config | `2fd8f5bac2fea7fe857b1e7712a6979a2b76b78f626c374af7fbc7fee44e72d0` |
| Paper stdout | `7bc19f00d7d95c50048a7e0220a8549986b84d717673da03e1b09e6207c9fe35` |
| Node sidecar | `adf264f5fa1a3c4f91149eeef5de5be722ad9105d4bc0e2eb991e9bac9ae5ad3` |
| 元S16原本 | `0abed468aa99f7927433e3717a80067a969e2bf7ed733326776f712af5133eaa` |
| Git証拠manifest | `df541da173276cc788e5ac64fae80c8f2e01ba864fb74b907769676eee95ccb2` |

`EFFECTIVE_CLIENT_CLEAR_TICK=NOT_ATTESTED / FULL_TICK_INPUT_COVERAGE_NOT_ATTESTED /
PHYSICAL_STABILITY_UNPROVEN / GOAL_UNDETERMINED / P1_WAIT_0 / L10_PAIRS_0 /
S10_UPDATES_0 / S11_GRANTS_0 / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`。
