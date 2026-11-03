# RelaySelf L-Z2c — 後続H2で元H1の予測失敗を再評価する（2026-11-03）

## 到達点と目標

親Draft PR #703（Z2b-P/W/E PASS_DEV）の実Gemma H1原本・Paper1.21.8実Worldと独立監査を**書換えず**に読戻す。実H1は STATIONARY を選択し、Paper tick37時点で xz=(-2.5,-1.5) をtick57に向けて凍結。tick57の実測は xz=(-3.983553173838,-1.525954708854) で水平誤差 1.4837801948120548 m。同じ情報時点のCHEAP停止・等速予測も同値。

元H1の反証文は CONSTANT_VELOCITY を反証対象とし、選択した STATIONARY と不一致。また「準備時にplayer座標がない」と「次WorldのPaper freeze時に取得できる」とを混同した。

Z2cでは、モデルが**後続epochのH2として自分の原本H1と実測を比較**し、規則の適用条件を再検討する。単にホストが誤差を算出した事実と、実Gemmaが誤差を認識した事実は別々に採点する。

## 今回実装した原本経路（オフラインのみ）

- tools/l_zombie_z2c_h2_original_feedback.py：親#703の保存済み68ファイルについて既存独立SHA readbackを再生し、実H1 request/response、実Paper原stdout、31連続tick、同期凍結、exact +20tickを再計算する。次に**実Gemma H2を1 HTTP・再試行0**で呼ぶ入口を持つが、今回GitHub CIで使うHTTPはモックのみ。
- adapters/mineflayer/l_zombie_z2c_feedback_contract.py：native strict JSON Schema、Reasoning OFF、数値誤差・反証対象・準備時/実行時入力の区別・条件見直し・次試験を16フィールドで検証する。H2入力には原予測座標と実測座標を含むが、正解数値の1.483780 mは含めない。Gemma報告値を独立Paper再計算の水平Euclidean距離と±0.02mで比較。
- 既知の不整合をH2が特定できない場合はFAIL。反証対象の不一致、時間によるplayer座標可用性の混同を区別する。次に選択した予測規則と反証対象が一致しない場合も拒否。
- H2選択：KEEP_WITH_LIMITS / RESTRICT_APPLICABILITY / PROPOSE_ALTERNATIVE / ABSTAIN_PENDING_MORE_EVIDENCE。出力は**提案のみ、学習admission・Action・L0昇格すべてfalse**。B2とCを主張しない。
- テスト：誤差数値偽装、別規則の反証、型混同、重複キー、Reasoning混入、将来tickの不整合、棄権・新規戦略、1 HTTP失敗原本保護、保存実World原本68件の再演。

## 次のLocalCodex実Gemma H2（このPRでは未実行）

1. 親#703と現Z2c HEADのCIを確認し独立clean worktreeから始める。保存済み docs/evidence/l-z2b-real-20261102/ の原本を保護し、直接上書きしない。main/他レーン・過去原本は不変。
2. ユーザー環境で実Gemma-4-12B-it Q4_K_M GGUF SHA256 c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed、実llama.cpp build10874、GGUF mmap、context8192、slot1、GPU PIDとVRAM、serving model aliasを**今回のH2開始時点**で別途確証する。#703当時のプロセス証拠を再利用して今回の実体証明としない。
3. native Strict JSON Schema ON / Reasoning OFF（reasoning_effort=none、enable_thinking=false）、temperature0 seed1、max_tokens640、streamfalse、cache_promptfalse。**実H2 HTTP最大1、再試行0。実World 0。**
4. 新規・未使用の絶対パス NEW_H2_EVIDENCE_ROOT と実endpoint/model aliasを選び、以下を実行する（環境変数は検証済み実値）。

    export PYTHONPATH=src:tests:.
    export L_ZOMBIE_Z2C_REAL_H2_DEV=1
    python -m tools.l_zombie_z2c_h2_original_feedback \
      --original-root "$REPO/docs/evidence/l-z2b-real-20261102" \
      --evidence-root "$NEW_H2_EVIDENCE_ROOT" \
      --endpoint "$ENDPOINT" --model "$MODEL_ALIAS"

5. 原本: h2-request-1.raw.json、h2-response-1.raw.json（HTTP応答が届いた場合）、h2-revision-proposal-v1.json（厳格な検証合格時のみ）、h2-original-source-readback.json、h2-status.json。失敗時も保存・再試行しない。
6. 実H2を実行したら、別プロセスによる実モデル帰属・原HTTP SHA・H1+Paper原本SHAの再検査、モデルの数値回答の独立検算と意味監査を実施。H2が規則維持を選んでも改竄せず保存する。次の新Worldはこの試験には含めない。

## 判定境界

| 判定 | 成立範囲 |
| --- | --- |
| Z2c-O | H1実原本68ファイル読戻し＋オフライン負対照PASS |
| Z2c-H2/B1-N | 新しい実Gemmaが座標から約1.48378mの誤差を報告して原本照合できた場合に**限定的DEV** |
| B1-Q | 原H1反証対象と入力時点の混同を診断、かつ次の予測規則・反証文が意味的に整合した場合の限定的候補（独立意味監査要） |
| Z2c-R | 規則維持/適用範囲修正/別案/棄権の**未採用提案**として保存 |
| B2 | 独立した将来Worldで適用条件と修正効果を検証していないため**未成立** |
| C | L2が実験を自律選択・実行していないため**未実施** |

元Gemmaの「1.5m」は科学的に検証された閾値ではない。新閾値は次実験の事前仮説にすぎない。今期の分類は **Z2C_H2_OFFLINE_ONLY / NEW_REAL_GEMMA_0 / NEW_WORLD_0 / NO_LEARNING / CLIENT_TICK_JOIN_UNATTESTED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**。
