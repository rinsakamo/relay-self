# L-Z2c 実Gemma H2 認知修正検証 — 数値限定PASS・定性的修正FAIL

2026-11-03。親PR #708（その親#706、Z2b原本#703）。Refs #693 / #431 / #653。

## 結果

実Gemmaへ元H1と完了済みPaper経験を新しいH2 epochとして渡した。実HTTP POST **1回、再試行0**、新World/Action/Learning admission/L0昇格はすべて0。Strict JSONは生成されたが、自己説明の矛盾を認識できず、修正案にも矛盾が残った。契約FAILの最初の原応答を保持し、再生成・回答修正なし。

| 評価 | 判定と根拠 |
| --- | --- |
| Z2c-H2 | PASS_DEV：今回検証した実Gemmaが原本由来の経験を受信し回答 |
| B1-N | 限定PASS：回答1.483553173838m、独立Euclidean値1.4837801948120548m、差0.0002270209740549145m、事前許容±0.02m以内 |
| B1-U | PARTIAL / NOT_ESTABLISHED：未解決条件と因果未証明を選択したが、準備時とfreeze時の座標可用性の差を説明文で明確に対比していない |
| B1-Q | FAIL：旧反証対象をSTATIONARYと誤答。元H1のCONSTANT_VELOCITYとの食い違いを説明していない |
| Z2c-R | 未採用の生候補は保存。型付きrevisionは契約拒否で生成なし。PROPOSED_NOT_ADMITTED |
| B2 | NOT_ESTABLISHED：構造・適用条件の変更効果を新Worldで検証していない |
| C | NOT_RUN：自律的な実験選択・実行なし |

数値回答は実際には|Δx|と一致する。±0.02mを満たすという限定評価であり、z差を含めたEuclidean計算を理解した証明ではない。ホストがschema/promptで診断候補、時間境界、因果警告を供給しており、enum選択だけでは自発的発見を主張しない。

## 実行・原本

Branch `dev/l-z2c-real-h2-validation-20261103`。実行HEAD `381f937d0ef957e3173bb2c458995f2614436ea2`。最終納品HEADは新子PRのhead SHAと投稿本文で固定する（この文書自身のcommit SHAを自己埋込しない）。独立worktree `/home/rinsa/relay-self-l-z2c-real-h2-20261103`。

保存原本は `docs/evidence/l-z2b-real-20261102/`。既存SHA manifestの68件を再演し、manifest自体を含む69ファイルを実行前後で全件照合。親#703 HEAD `58d72e8e2a3e5c3c633e196ac8ee43cd43eba20e`の同パスと差分なし。生H1要求/応答SHA、policy SHA、31連続Paper tick、tick37 freeze→tick57実測、同一World/ゾンビUUID、CHEAP同一情報条件は[実行前読戻し](evidence/l-z2c-real-h2-20261103/preflight-original-readback.json)および[別プロセス監査](evidence/l-z2c-real-h2-20261103/h2-original/h2-independent-original-audit.json)に保存。

- H1 policy SHA `5ab25d00180e72b739474f4aaca93317421b2f275975cb737775b7061dbde4ed`
- Paper原本SHA `1c20c9e7aa456cdf163edf56a3caab3eead2431febb3f40743896054730e4815`
- H1選択 STATIONARY、予測(-2.5,-1.5)、実測(-3.983553173838,-1.525954708854)。CHEAP_STATIONARYとCHEAP_CONSTANT_VELOCITYも同値。
- 元H1反証原文：`If zombie moves > 1.5m from start_xz_m, then CONSTANT_VELOCITY is false.`
- 元H1理由原文：`Limited evidence; chase_causality is NOT_ATTESTED and no current player coordinates are available for TARGET_APPROACH.`

## 実モデル帰属・HTTP

Gemma-4-12B-it Q4_K_M。実GGUF `/home/rinsa/models/gguf/gemma-4-12B-it-Q4_K_M.gguf` SHA256 `c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`を今回3回全読検証（起動前・実HTTP前・終了後の別プロセス）。llama.cpp build10874/e2d2c0d6a、実バイナリSHA `ad5d4787bc739ad88a55b614c18d29580b3ec071cad632edb0ebb42b89f78536`。

今回専用PID **195850**、開始stat/argv/exe/GGUF mmap/CUDA mappingを記録。別監査プロセスPID195953で同一starttime/argv/mmapとGGUF SHAを確認。RTX3060 12GB、context8192、slot1、loaded VRAM8599MiB、推論中8611MiB・GPU60%。競合モデルなし。endpoint `http://127.0.0.1:18083/v1/chat/completions`、alias `relay-self-gemma4-12b-q4km`。health/models/propsへのGETは生成ではなく状態確認。

Strict JSON Schema ON、reasoning_effort=none、enable_thinking=false、temperature0、seed1、streamfalse、cache_promptfalse、max_tokens640。保存requestで確認。応答model alias一致、system_fingerprint `b10874-e2d2c0d6a`、finish_reason=stop、462 completion tokens、cached_tokens0、Reasoning混入なし。入力は原予測・実測座標を含み、正解誤差数値は含まない。

- H2要求SHA `5f72e67b04aee0bf12d282a2efa6d1cfcdf2d344d6d9c7382fcee285ea8f670e`
- H2応答SHA `66e47bcf99f72fea9e32ca49ad3dc806cd5794f56d6fbdb050a6c97b7ee51a78`
- runner exit2 / H2_NOT_ESTABLISHED。独立監査exit0は監査処理の成功であり認知全体PASSではない。
- 独立分類 `H2_NUMERIC_WIRE_MATCH_QUALITATIVE_OR_SCHEMA_REJECTED`。

## Gemma H2回答原文

以下は保存HTTPのmessage.contentをそのまま展開したもの。生HTTP envelopeは[原応答](evidence/l-z2c-real-h2-20261103/h2-original/h2-response-1.raw.json)に保持。

```json
{
  "cheap_relation": "TIED",
  "diagnosed_issues": [
    "PREPARATION_VS_WORLD_FREEZE_COORDINATES_CONFUSED",
    "CHASE_CAUSALITY_UNATTESTED"
  ],
  "error_basis": "ORIGINAL_PAPER_EXACT_TICK_XZ",
  "evaluated_prior_strategy": "STATIONARY",
  "evidence_ids": [
    "Z2B_ORIGINAL_MODEL_H1",
    "Z2B_ORIGINAL_PAPER_T37_T57"
  ],
  "measurement_target": "ZOMBIE_XZ_AT_EXACT_PLUS_20_PAPER_TICKS_M",
  "next_falsification_target": "TARGET_APPROACH",
  "next_falsification_test": "If zombie_xz_m_at_t57 differs from target_approach_prediction_xz_m by > 0.5m, then TARGET_APPROACH is false.",
  "next_test_error_threshold_m": 0.5,
  "observed_horizontal_error_m": 1.483553173838,
  "old_falsification_named_strategy": "STATIONARY",
  "proposed_applicability": "CONDITIONS_UNRESOLVED",
  "proposed_speed_m_per_tick": null,
  "proposed_strategy": "TARGET_APPROACH",
  "rationale": "H1 prediction remains immutable. Stationary and Velocity predictions were identical at source. Target_Approach was the potential acquisition at freeze; must be tested against the actual movement observed in the completed world.",
  "reconsideration": "ABSTAIN_PENDING_MORE_EVIDENCE"
}
```

## 説明文と修正仮説の監査

元H1はSTATIONARYを選び、反証文ではCONSTANT_VELOCITYを名指しした。H2は旧反証対象をSTATIONARYと答え、`OLD_FALSIFICATION_NAMES_OTHER_RULE`を選ばず、理由文でも矛盾を説明しなかった。B1-QはFAIL。

H2はfreeze時取得の可能性に言及し、CONDITIONS_UNRESOLVEDとCHASE_CAUSALITY_UNATTESTEDを選択した。追跡因果の成立は主張していない。ただし準備時に未知だった座標と実行時に取得可能な座標を明確に対比していないためB1-Uは部分的証拠に留める。

次戦略と反証文はともにTARGET_APPROACHを指すが、ABSTAIN_PENDING_MORE_EVIDENCEとの矛盾、必要speedのnullが残る。さらに反証文は既存t57を指し、理由もcompleted worldでの検証を求めるため、別の将来Worldでのfreeze→+20tick検証条件を十分に定義していない。0.5mは未検証候補として保全する。確定閾値や採用済み規則にはしない。型付きrevisionを捏造しない。

自動原本監査は別Pythonプロセスで実施した。説明の意味監査は保存H1/H2を照合したホストレビューであり、別モデル・別人による独立意味査読ではない。[意味レビュー](evidence/l-z2c-real-h2-20261103/semantic-review.json)に根拠と限界を明記。自動監査のB1_Q=NOT_INDEPENDENTLY_ESTABLISHEDは書き換えない。

## 検証・後処理

実HTTP前の関連テスト141 PASS、Ruff PASS、repository contract PASS。最初のsystem Pythonにはpytestがなく実行できなかった記録も保存し、専用外部venvへCIと同じpytest9.1.1/ruff0.17.0を導入してテストを通した。この不備はHTTP開始前に解消。実装コード修正なし。

子PRのCIは保存原本SHAとこの失敗応答を通信なしで再監査し、数値限定PASS／契約FAILが再現することを確認する。CI SUCCESSを実World・認知全体のPASSと混同しない。

専用モデルPIDへ同一性確認後SIGTERMを送り、endpoint閉鎖・GPUプロセスなし・VRAM706MiBへの復帰を確認。[cleanup](evidence/l-z2c-real-h2-20261103/cleanup.json)。新規Paper/Node/World起動なし。main作業ツリー・既存PRソース・他レーンは変更なし。GitHub報告コメントのみ明示承認に基づいて追加する。

外部原本保存先 `/home/rinsa/evidence/l-z2c-real-h2-20261103T030200Z/`。新証拠の全件SHAは[manifest](evidence/l-z2c-real-h2-20261103/SHA256SUMS.json)、旧69ファイル全件SHAは[前後照合対象](evidence/l-z2c-real-h2-20261103/original-all-files-before.json)。最初のHTTP失敗結果・request/response/status・独立監査を保持。

次の候補は、まずオフラインで旧選択規則と反証文の明示対比を要求する設計、別途承認されたH2で完全な棄権または速度を含む仮説、さらに別承認Worldで座標・速度を事前固定した+20tick holdout検証。本試行の再実行はしない。

**DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN / CLIENT_TICK_JOIN_UNATTESTED**。
