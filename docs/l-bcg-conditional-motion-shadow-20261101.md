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
