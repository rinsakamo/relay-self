# L-BCG — 身体経験から条件付きL1注意候補を学習する DEV shadow

2026-11-01。Owner: L #426/#431。Integration: S #537、SelfBody #632、
SelfWorld #633、既存 #653/#654/#655。科学的判定は #619。

## 既存資産と重複回避

- #654: 前Action S50 Paper sampleあり/なしのL1 attention shadow。
  実World PASSだが、1-bit cheap controlと同値。Goal UNDETERMINED。
- #655: S50 8 sampled callback の一歩先変位を推定するcheap線形回帰。
  numeric forecast≠policy learning。Action単位の予測は #537 側に既存。
- `learning_epoch.py`、`l10_world_body_cue_learning.py`、
  `experience_bridge.py`、`habit_shadow.py` が Memory/qualified Goal/
  S10/Habit 関門を既に持つ。新DBやL1 semantic ownerは作らない。

## 今回実装

`src/relay_self/l1_bcg_motion_shadow.py` は独立した **pure read-only
conditional attention discriminator**。入力は外部S/R ownerから与えられる
`MotionContext`、複数独立Worldの `MotorOutcome`、
`MotorSourceAdmission`。World / SelfBody / SelfWorld の既存由来情報を
ownerがprojectした後に渡す前提であり、**この型はS16やPaper原本を認証しない**。

- 訓練ラベルは「post-clear物理残留変位 > 当該時点の残距離−許容誤差」
  という**残留変位リスクの代理指標**。Goal達成、RECHECKの真の
  行動利益、Action許可、S10学習資格を示すラベルではない。
- 適用条件の候補軸：残距離と許容誤差からのclearance band、
  高速/低速歩容、P1高疲労、M低エネルギー、観測済み障害物。
  band 0.15m は探索用の特徴量境界であり**学習済み正解規則ではない**。
- 1軸または2軸の組合せを比較し、各条件cellに少なくとも**独立2 World**、
  ラベル矛盾なし、双方のラベル支持がある場合だけ候補を生成。
  最大48件、有界CPU、LLM/GPU実行0。
- 今回の `RECHECK` / `CONTINUE` は非実行の **L1注意仮説**。
  どちらもS49 ActionやGoal outcomeを発行しない。
- Memory OFF、固定clearanceしきい値、1-bit「過去に危険あり」、
  最終経験の単純参照に加え、全cue完全一致の単純経験検索を同じ入力上のcheap controlとして併記。
  完全一致検索がDEFERし条件抽象化だけが候補を出せても、正解は未証明。
  複雑な学習がcheapと同等なら `CHEAP_EQUIVALENT` を受理。
- currentが古い・推論由来、外国Self、違う物理regime、
  未知障害物条件、未知特徴値、矛盾・支持不足はDEFER/REJECT。
  学習した仮説は物理的真実ではない。
- 定型監査：過去と今のsession/World分離、S16とsettling別digest、
  owner-admitted digest membership、post-clear物理検証grade、
  **訓練World revision < 現在revision**を必須。
  **digestの形とmembershipは原本の独立認証ではない**。

## 実装・テストの証明範囲

`tests/test_l1_bcg_motion_shadow.py` では人工的に構成した複数の独立
World IDとラベルで、条件学習・未登場cue組合せ・単純安価規則との
相違・二軸相互作用・旧記憶無効・矛盾・失効・provisional拒否を検証。
**人工World IDを実Minecraft Worldの試行数として数えない。**
学習後にholdoutラベルを渡さないが、実機で有効な汎化の証明ではない。

`PHYSICAL_POST_CLEAR_VERIFIED` を満たす **実World S50資料は現在未提示**。
#653のPaper8サンプルは `PROVISIONAL_PAPER_ONLY` なのでtraining不可。
#537のAction単位変位もS16単体でsettling physicsを認証できない。
そのため本PRで学習済み実World判断や目標改善は**0件**。

## 次の最小実Minecraft DEV handoff（LocalCodex / S owner）

1. 本PRのHEADをpinして、既存S49/S16/Body/Worldの **唯一のowner** へ
   default-OFF read-only consumerを接続。既存native probeとActionを増やさない。
2. 学習Worldを複数、変化させる軸を事前に指定して収集。元Action/S16原本と
   **報告入力OFFでなく実効clear後の連続観測**によるpost-clear残留変位を
   別々に認証する。証拠がなければUNKNOWN、学習しない。
3. 学習用Worldを終了し凍結してから未経験World（距離、速度、P1/M、
   障害物、複合変更）を固定。**World内の8tickを8 World扱いしない**。
4. 初回は同一元L0判断の終了後にshadowを記録。OFF／1-bit／固定条件規則／
   直近経験／L-BCGの差、支持World数・不確実性をreport。
5. ownerが認める次段階でのみ、L1候補→既存Action選択に最小接続し、
   学習OFF／ON／cheapの**実Outcome改善**をpaired DEVで比べる。
   Goalを議論する試験では独立Goal証拠が必要。L0安全・S49唯一issuer・
   S16 qualificationを保持。
6. 新regimeでの不適用・誤りをログにし、既存Memory/Belief/Predictionの
   別権限で仮説更新。今回L0自動昇格、S10/S11 production promotionなし。

**DEV_OFFLINE_SYNTHETIC_CONDITIONAL_SHADOW_ONLY / REAL_WORLD_LEARNED_POLICY_NOT_TESTED /
GOAL_UNDETERMINED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**。

No new World or provider call is authorized by this PR. #655 MP3の単発grantを
L-BCGに流用しない。main・保護原本・元S49/S16/L0/S50 owner・過去科学結論は不変。

## BCG-H1 — 既存S49 hostへの最小readonly接続（2026-11-01）

`adapters/mineflayer/self_body_s50_l_bcg_handoff.py` と
`tests/test_l_bcg_live_handoff.py` を追加。
`self_body_s50_world_dev.py` に **default-OFF**
`--l-bcg-shadow-dev` オプションを追加。既存route Bの原第3 L0選択が
**完了してから** `LiveNextEpochReadout` と元`WorldConditionedChoice`を
受ける。既存 `compare_l1_motion_attention_shadow` の厳格なsession・S50
Paper暫定window・S42 choice/元Present型の照合を再利用し、L0 choice、
Action、native probeを変更せず `report["l_bcg_shadow"]` のみに記録する。

**現実の初回runでは保留が正しい。** 元readoutには現時点で認証済み
Goal clearance、歩容、P1/M疲労・エネルギー、障害物の全cueや、
物理実効clearを認証した複数training Worldがない。
そこでhostは `current=None`、`training=()`、`admission=None` とし、
`DEFER_UNKNOWN / CURRENT_GOAL_GAIT_P1_M_OBSTACLE_SOURCE_NOT_ADMITTED`
を明示する。初回この結果が出ても学習・汎化成功ではない。

将来S/R ownerが別途 `MotionContext`、既存Memory/S16と有資格
post-clear S50に対応する `MotorOutcome` 群、`MotorSourceAdmission`
を渡す場合だけ、同一self/session/World/body/world-sourceを束ねて
`compare_conditional_motion_shadow` を利用可能にする。現状その
runtime owner-side producerは存在しない。testのsource/digestの組立ては
物理真正性を証明せず、本番データを静かに`admitted`へ昇格させてはならない。

親PR #655のhost追加HEAD
`bd9115eeb3aa07a0554058124309c2f6b6cbbc14` を隔離PR #656へ
non-force two-parent mergeで取り込み、既存親ファイルの変更を尊重。
既存原本とmain変更なし。

**BCG-H1 evidence ceiling:** `OFFLINE_TYPED_HANDOFF_ONLY`。
追加されたhost entrypointは実Worldで未実行。
`QUALIFICATION_NO_GO / SCIENCE_NOT_RUN / REAL_WORLD_BCG_0`。

## BCG-H2 — 現在の認知入力のsource-preserving可用性監査（2026-11-01）

既存 `LiveNextEpochReadout`、元`WorldConditionedChoice` を
#653 のsource束縛で再検査した後、`inventory_original_bcg_cues` が
今ある事実の所在を `BCGCueInventory` に残す。**新たなWorld Truth、
Learning owner、観測、Actionは作らない**。

- **現在のnative観測**: SelfBodyの position(x/y/z)、health、
  Minecraft food、food_saturation；S42 ownerが既に読んだ
  `s42_threat_distance_m`。数値はそれぞれ元native参照付き。
- **現在のSelfWorld観測**: 同一world sourceのEntityが実際に可視の
  場合のみ `world_observed_target_distance_m` を記録。
  coverage scopeとtruncationを保存。Entity不在やcoverage不足から
  `verified_obstacle=False` を生成しない。
- **L-BCGに不足**: 原目標の `goal_remaining_m` / tolerance、
  選択歩容、P1疲労、M実エネルギー、障害物の独立観測、World revision、
  実効clear後の複数World物理残留量のowner-admitted training。
  **Minecraft food≠M energy、敵距離≠Goal残距離、
  Paperのlast_reported_input_off≠実効clear**。
- 現hostの `report["l_bcg_shadow"]["cue_inventory"]` では
  `missing_required` と `observed` を分離し、
  学習器向け完全cueはまだ**不成立**。
- source完全性を偽る `current` の文字列束縛は別件で外部物理originalを
  認証しない。外部入力経路の返却上限も
  `EXTERNAL_TYPED_CUES_NOT_ORIGINAL_BYTE_ATTESTED` として明示。
  本接続の DEV判定は read-only `DEFER` まで。

#655の[独立実World DEV原本](https://github.com/rinsakamo/relay-self/blob/774c06965f83058ff0c55589f4369b5b82615ba3/docs/evidence/issue653-mp3-host-20261101/verdict.json)
はhost順序PASS / 物理prequential chronology **未認証** / 新World
更新保留、Goal UNDETERMINED。親レーンのこのWorldをL-BCG用の
`PHYSICAL_POST_CLEAR_VERIFIED` 訓練原本へ無断転用しない。

## BCG-H3 — 初回実World後のhost-only整合性ゲート

既存S49 hostで専用grantを使ったDEV Worldを実行した**後**、
`python tools/l_bcg_world_report_preflight.py <s49-report.json>` で
`DEV_BCG_HOST_REPORT_SELF_CONSISTENT_ONLY` を得るread-only検査を追加。
元L0の `WAIT→MOVE_AWAY→WAIT`、元native/SelfBody/SelfWorld
source相互参照、元の数値観測とreportの `cue_inventory` の完全性、
L-BCG `DEFER`、Action/learning/S10/S11非増加、coverageと原Entity
参照をreport内部で照合する。改ざんした報告・予測値への観測昇格はFAIL。

**重大な上限**: この検査はhostが自身で書いた一つのJSONの自己整合性のみ。
元S7のraw受信・S16原本・Paper binary・Java/Node process cleanup・
操作grantの独立監査は別途行う。この検査結果を物理の実効clear、
Goal/Policy改善、`PHYSICAL_POST_CLEAR_VERIFIED`、QUAL/SCIENCE
根拠として使わない。既存のWorld owner外ではnative Actionを発行しない。

**専用L-BCG World grantは未取得**。#655の消費済み1 World grantは流用不可。

## BCG-H4 — LocalCodex source監査と実World前準備（2026-11-01）

**WORLD_GRANT_REQUIRED / 新規実World 0回**。
最新remote子HEAD `618bd307b65ac81cc2b217fc7ef77c58f361080b` を隔離worktreeへ取得。
Issue #431/#537/#653とDraft #654/#655/#656の本文・既存コメントを再確認したが、
L-BCG専用の未消費grantは確認できない。#653 MP3専用grant
[6551090255](https://github.com/rinsakamo/relay-self/issues/653#issuecomment-6551090255)
は[消費済み](https://github.com/rinsakamo/relay-self/issues/653#issuecomment-6551338030)。
#537のSLM grantも別対象なので適用しない。World起動・再試行は行わない。

先行[H1 CI](https://github.com/rinsakamo/relay-self/actions/runs/41258096294)はSUCCESS。
[H2/H3 CI](https://github.com/rinsakamo/relay-self/actions/runs/41261320168)は
exact `618bd307…` にて **Python 3.12 129 PASS / Ruff / compileall / contracts PASS**
と確定し、同HEADの関連4 workflowもSUCCESS。
親#655のremote `774c06965f83058ff0c55589f4369b5b82615ba3` は
既取り込み親 `bd9115ee…` から **docs内80ファイルのみ**の追加・更新。
実装依存は増えていないため、この実測原本群を子へmergeしない。
親の実WorldはL-BCG実行数・訓練数へ加算しない。

### H4で修正したhost JSONゲート

追加否定テストは修正前 **8 FAIL / 17 PASS**。初回FAILログを保存。
`false == 0` による回数型の混同、Action原本表現のGoal/学習資格の過大申告、
不正なAction/decision/entity型、非有限観測値を拒否する。
既存ownerが入れ子に出す `goal_admitted` / `accepted_goal_status` /
`learning_feedback_qualified` / S10/S11更新・grantも過大申告を拒否する。
正常な合成host JSONのPASSは維持する。元S49 runner、L0、S16、
source reader、Action issuer、cue projectionや条件学習器自体の変更はない。
**この強化も一つのhost JSONの自己整合性だけで、原本の真正性認証ではない。**

### runtimeの実測preflight

WSL2 / Ubuntu 24.04.4、Python 3.12.3、OpenJDK 21.0.12.1、
Node 22.22.2、Mineflayer 4.39.0を確認。Windows build `10.0.26300.9711`。
Minecraft 1.21.8 Paper資材とplugin/configの3 SHA256は既存pinに一致。
port 25565 bind可能、`/tmp/relay-self-s49-*` 残存なし。
RTX 3060は検査時707 MiB使用 / GPU利用率0%。モデル起動・呼出し0。
既存pluginは **ACTIVE_METABOLISM_NOT_PASSIVE** profileであり、
foodをM energyの認証済み入力へ読み替える根拠にはならない。
Java/Nodeのversionコマンドのみ実行し、Minecraft server/bridgeは未起動。
今回所有するWorld/PIDはなく、World削除・server停止の物理試験は対象外。

許可後も既存 `adapters.mineflayer.self_body_s50_world_dev` のみを使う。
route Bと `--l-bcg-shadow-dev` を有効化し、元第3 L0判断完了後に評価。
S49 WAIT→MOVE_AWAY→WAIT、Action 1・S16 OUTCOME 1が予定条件だが、
**今回は未実測**。追加Action/probe、learning/S10/S11、model callは0を維持する。
L-BCGの予想は `DEFER_UNKNOWN`、Goal UNDETERMINED。
観測可能cueは位置・health・food/saturation・S42距離・実在観測Entity距離とcoverage。
欠落する8条件はH2のまま。実WorldでのCHEAP比較・L1改善は未測定。
原S7/S16/Paper照合、session/World/marker、exit/STOP/port/World削除は
将来1回の実行終了後に別監査し、effective clearは証明されるまでNOT_ATTESTED。

### 次段階の条件学習計画（未許可・未実施）

各値のproducer、型、native source、同時点性・鮮度を既存ownerで確認できるまで
該当cellは `SOURCE_NOT_ADMITTED`。欠損を推定値で補わない。

| 条件軸 | 実測sourceの必要条件 | 将来比較する条件 |
| --- | --- | --- |
| Goal残距離・tolerance | 既存Goal ownerと同時点位置の認証済み結合 | 小/大clearance |
| 歩容 | Motor ownerの選択と実行区間、native確認 | 低速/高速 |
| P1疲労 | 既存P1 ownerの時点付き実状態 | 低/高 |
| M energy | 既存M ownerの時点付き実状態 | 低/高 |
| 障害物 | 独立に検証された対象範囲と鮮度 | 有/無 |

初回はshadow比較に限定。計画例は5軸二値の32 cellについて、
各cellで独立training World ≥2、別の独立heldout World ≥2
（例示下限64+64 World、**今回の実行権限や実行予約ではない**）。
実際の数値境界・World数・割付・停止条件はsource資格と専用grant成立後、
観測前に凍結する。初期の縮小計画なら対象軸と未検証cellを明記し、
除外cellへ汎化主張を拡大しない。
現APIの最大48 training Worldを越す64件一括投入は不可。
48以内の事前固定された有界比較に分割し、全cellを学習済みと表示しない。

World/sessionの重複を除き、同一Worldの8 tickは1 Worldとして数える。
訓練凍結後にheldoutを評価し、未知cue値/組合せ・障害物・regime変更・矛盾で
ABSTAIN/DEFERするか確認する。各cellの独立World数、source可用性、
支持/拒否/欠測、Memory OFF・1bit・fixed clearance・recent・exact lookupと
同情報のshadow比較を保存する。残留変位リスクはGoal改善ではない。
将来のAction比較は別途独立Goal証拠・権限が成立した場合のみ。
L0自動昇格、S10/S11 production更新は許可しない。

H4の最終上限は **DEV_OFFLINE_READONLY_PREFLIGHT_READY /
WORLD_GRANT_REQUIRED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**。
