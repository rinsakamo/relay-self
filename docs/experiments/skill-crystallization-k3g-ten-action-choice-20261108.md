# RelaySelf K3-G — 実Gemmaが最大10 ActionのSKILL / PROBE / ABSTAINを選ぶDEV実験

**分類: DEV_ONLY / REAL_GEMMA_NOT_RUN / SYNTHETIC_SHADOW_ONLY / NO_REAL_S49 / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**

- 親: [Draft PR #796](https://github.com/rinsakamo/relay-self/pull/796)、exact HEAD `8f2212814796f22ca61d18d02a7cadec18b13f8b`。
- 背景: #793 K3-D と #794 K3-E の実GemmaはABSTAINした。ただし「最適化済み」の説明は未証明。
- 目的: Action上限が4→10に変わったとき、同一モデルが新しいSkill、反証可能なPROBE、またはABSTAINのどれを選ぶか確かめる。選択の妥当性とGoal改善を分離する。

## 変更する境界と変更しない境界

既存の `skill_json_schema()`、`validate_skill()`、`run_skill()` の4 Action上限は一切変更しない。K3-Fの実験専用 `budget10_schema()` と `validate_budget10_shadow()` を再利用する。

共通`gemma_l2()` の既定引数も4のまま。K3-Gが明示した場合だけ`max_actions_allowed=10`を送信し、**独立response_schema・専用system_instruction・排他的raw-record_dirの3条件が揃わない呼び出しはPOST前に拒否**する。

実S49やS15/S16の権限、元のIntent予算、Learning/Habit/Memory、自律インストールは変更しない。10回は最大であり、Goal達成時点で停止する。

旧WorldTrialの未来効果は5個しかない。旧原本を事後的に10 Action体験へ延長しない。独立評価だけが、新規の10効果を持つ合成WorldTrialを生成する。

## 入力原本

すべてGitHubの保存済み原本を用いる。

- `evidence/l431-gemma-20261108/first-report.json`
- `evidence/l431-k3b-gemma-20261108/report.json`
- `evidence/l431-k3d-gemma-20261108/report.json`
- `evidence/l431-k3e-gemma-20261108/proposal.json`

K3-Bの既存12観測を元の決定論的source replayで検査し、停止前原本を補完しない。K3-DとK3-EのABSTAINは入力出典として確認する。モデルへの入力には元の観測済み28件（train16 + shift12）、旧Skill、4→10という実験予算の変更、過去にABSTAINしたという事実のみを渡す。

**K3-Fで模擬的に得た4回・5回・8回・10回の成功数、Worldの隠れた運動効果式、将来holdout、PROBE Outcome、人工slowストレスの種別は絶対に渡さない。** 過去の「最適化済み」はモデル出力でありWorldの事実と断定しない。

## 1回限りの実モデル選択

閉じたresponse Schemaで`status: SKILL / PROBE / ABSTAIN`、`reason`、`skill`、`hypothesis`、`probe_id`、`prediction`、`evidence_ids`の全フィールドを要求。独立JSON Schemaと対応するbranch Validatorの双方を通す。

- **SKILL**: `skill`は既存DSLの検証済みフィールドと出典IDを保持し、`max_actions`は1..10。その他のPROBEフィールドはNONE/UNKNOWN/INDETERMINATE。名前・引用だけの変更は`NO_BEHAVIORAL_CHANGE`で終了。
- **PROBE**: Skillはnull。経験ID、検証可能な仮説と予測が必要。今回のPROBEは**提案のみ**で、模擬試行も実Worldも発行しない。
- **ABSTAIN**: Skillはnull、PROBEはNONE、予測UNKNOWN。評価seedは未開封のまま終了。
- Schema不成立・未観測ID・不正予算・矛盾したbranch回答はSkill/PROBE実行なしで停止。モデル回答を手直ししない。

## 独立評価（実Gemmaがvalidで実行意味の変わるSKILLを選んだ場合のみ）

新規の独立seed **20261213**を予約する。このseedはローカルfixtureやHTTP mockのために開かず、適切に検証された**実Gemmaの新Skill**が生成された場合に限って開く。

- 64試行、4条件各16件。normal_changed、normal_slower_stress、normal_reference、ice_changed。
- 初期距離2.10..2.55m（旧Skillの適用範囲外も含む）。全試行10個の新規合成運動効果を準備。
- A: 固定L0の2 Action、B: 既存CHEAP（normal2 / ice3）、C: 旧Skill4＋非適用時L0、D: 実Gemma新Skill最大10＋非適用時L0。
- 固定した同一WorldTrialからペア比較し、Goal達成時は即停止。
- 選択数、Goal成功、模擬Action、guard選択差、Action trace差、失敗時ESCALATE、追加自動fallback0を記録。
- 旧Skillが適用されなかった試行で新Skillが勝つとは限らない。適用範囲の変更とBudget変更は実行意味として区別し、**Goal改善は別集計**。
- 旧物理の真実や外界の安全性、身体Energyの計測値ではない。

### 既開封の予備比較

探索fixture seed **20261210** では、旧K1模擬実行器と上記K3-G新World条件を独立再生した結果は以下（*K3-G全repo統合ではない*）。

| 条件（各16） | 旧4 Action | 旧guardのまま最大10 Action |
|---|---:|---:|
| normal_changed | 1成功 | 1成功 |
| normal_slower_stress | 0成功 | 2成功 |
| normal_reference | 16成功 | 16成功 |
| ice_changed | 0成功 | 0成功 |
| 合計 | 17/64 | 19/64 |

旧guardの適用幅が狭いため、上限拡張だけでは大半のケースで選択されない。これもSkill適用条件を変える学習の必要性を評価するための対照であり、Gemmaの回答を誘導する情報には含めない。

## 未開封／既開封seed

- K3-D Skill holdout: **20261126 未開封、K3-Gから使用禁止**
- K3-E real-probe seed: **20261205 未開封、K3-Gから使用禁止**
- K3-F capacity探索: 20261207 **既開封**
- K3-G fixture: 20261210 **既開封**
- K3-G 実Gemmaのvalid新Skill評価: **20261213 未開封**

## 検証と実行コマンド

実WorktreeのGitHub HEADを固定、旧原本のSHA256SUMSを監査し、同じローカルvenvで実親コード込みの試験を実行する。

```bash
python -m pytest -q \
  tests/test_skill_crystallization_dev.py \
  tests/test_skill_crystallization_k3b_dev.py \
  tests/test_skill_crystallization_k3c_dev.py \
  tests/test_skill_crystallization_k3d_dev.py \
  tests/test_skill_crystallization_k3e_dev.py \
  tests/test_skill_crystallization_k3f_budget_dev.py \
  tests/test_skill_crystallization_k3g_ten_action_choice_dev.py

python -m ruff check \
  experiments/skill_crystallization_dev.py \
  experiments/skill_crystallization_k3f_budget_dev.py \
  experiments/skill_crystallization_k3g_ten_action_choice_dev.py \
  tests/test_skill_crystallization_k3g_ten_action_choice_dev.py
```

実モデルを実行できるLocalCodex側で、事前にGGUF SHA256 `c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`、llama.cpp build10874、専用PIDのargv/mmap/GPU、モデルAPI ID、context8192、slot1、Reasoning OFF、strict JSON Schema経路を確認する。実行時grammar強制の独立計測可否と、回答自体の独立JSON Schema PASSは分けて報告。

preflightとsource監査が通った場合に限り、一回だけHTTP POSTし、自動再試行0回。例:

```bash
python -m experiments.skill_crystallization_k3g_ten_action_choice_dev \
  --first evidence/l431-gemma-20261108/first-report.json \
  --k3b-report evidence/l431-k3b-gemma-20261108/report.json \
  --k3d-report evidence/l431-k3d-gemma-20261108/report.json \
  --k3e-report evidence/l431-k3e-gemma-20261108/proposal.json \
  --mode gemma \
  --endpoint http://127.0.0.1:8080/v1/chat/completions \
  --model VERIFIED_LOCAL_SERVED_MODEL_ID \
  --record-dir evidence/l431-k3g-gemma-20261108/one-shot \
  --out evidence/l431-k3g-gemma-20261108/report.json
```

raw request は既存one-shot clientが排他的に作成し、raw response、usage、elapsed time、独立Validator、模擬評価とSHA256SUMSを監査する。専用サーバーのみcleanupし、他レーンを止めないこと。

**ここまでのPR実装だけでは実Gemma推論未実施**。ChatGPT実行環境からユーザーのWSL/GPUにはアクセスできない。原本・モデル実行の実測値を作り話で補わないこと。

## 判定

`L2_TEN_ACTION_CHOICE_ATTEMPTED` / `PROPOSAL_VALIDATED` / `EXECUTION_SPEC_CHANGED` / `NO_BEHAVIORAL_CHANGE` / `PROBE_SELECTED_NOT_EXECUTED` / `EXPLICIT_ABSTENTION_ACCEPTED` / `PAIRED_MOCK_HOLDOUT_EVALUATED` を厳密に区別する。

valid SKILLとGoal改善・学習・自律実装は別。今回変更されるのはあくまで新たな**DEV研究用Skill予算**だけで、原S49権限は不変。
