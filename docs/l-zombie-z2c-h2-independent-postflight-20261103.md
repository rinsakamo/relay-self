# RelaySelf L-Z2c — 実Gemma H2と独立原本監査の実機実行手順

2026-11-03 / 親Draft PR #706。Z2b実World原本は#703に保存済み。

## このレーンで証明したいこと

H1実GemmaはSTATIONARYを選択したが、保存済み実Paper tick37→57で約1.483780mの予測誤差を生んだ。元反証文は選択したSTATIONARYではなくCONSTANT_VELOCITYを名指し、準備時に未知のplayer座標と新World freeze時に取得できる座標も混同した。

今回の実H2は**実測後のGemma自身が予測誤差を計算し、どの適用条件や反証対象を修正するかを説明できるか**の試験。H2には予測座標と実測座標を与えるが、誤差1.483780mの正解数値は含めない。Strict Schemaの列挙フィールドを正しく埋めたことだけでは独立の意味理解証明としない。

## 既存原本と新実H2の予算

- 親#703 H1実Worldは**再実行しない**。保存済み68ファイルは読み取り専用、SHA不変。
- 今回の実Gemma H2 HTTP要求は**1回のみ**。再試行0。初回出力が長すぎる・スキーマ不成立・モデル拒否の場合も**失敗原本**として保全する。
- 新規Minecraft World **0**。元Action、Learning admission、L0昇格はすべて**0**。
- 他レーン/main/過去Z2b証拠・親PRを変更しない。独立worktreeで開始し、実行HEADを固定する。
- GGUF SHA256 `c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`、llama.cpp build10874、GPU RTX3060、ctx8192/slot1。**今回実際に使うモデルPID・GGUF mmap・serving alias**を改めて独立確認する。#703の過去PID/mmapは現在の実モデル証明にはならない。
- native strict JSON Schema / Reasoning OFF: `reasoning_effort=none`, `enable_thinking=false`, temperature0、seed1、streamfalse、cache_promptfalse、max_tokens640、finish_reason=stopが必要。
- 既存H2 runner `tools/l_zombie_z2c_h2_original_feedback.py` は**ローカルloopbackモデルへのPOSTのみ**を行う。生成済みH2原本フォルダは別ディレクトリに排他的作成する。実HTTPの失敗もrequest/statusと届いたresponseを保存する。

## 0 — 実行前の原本確認（通信なし）

Repo `rinsakamo/relay-self`、ブランチ `dev/l-z2c-independent-readback-20261103` の最新HEADと子PRを確認する。日本語で履歴に原本SHAの検証と全CIを書き出す。

```bash
export PYTHONPATH=src:tests:.
python -m pytest -p no:cacheprovider -o addopts='' -q \
  tests/test_l_zombie_z2c_feedback_contract.py \
  tests/test_l_zombie_z2c_h2_independent_audit.py

python - <<'PY'
from pathlib import Path
from tools.l_zombie_z2c_h2_original_feedback import original_z2b_h2_sources
root = (Path.cwd() / 'docs/evidence/l-z2b-real-20261102').resolve()
h1, world, receipt = original_z2b_h2_sources(root)
assert receipt['archived_files_checked'] >= 68
assert h1['strategy'] == 'STATIONARY'
assert world['issued_tick'] == 37 and world['target_tick'] == 57
assert abs(world['prepared_policy_error_m'] - 1.4837801948120548) < 1e-9
print('READ_ONLY_OLD_H1_AND_PAPER_SOURCE_PASS', receipt['archived_files_checked'])
PY
```

通信なしの原本確認・モデルID確認・オフラインCIがPASSするまで**H2の実HTTPを呼ばない**。旧原本は保護し、GIT cleanを確認。

## 1 — 新しい実GemmaでH2を1回のみ実行

ローカルで実際に起動・確認済みのllama.cpp endpointとaliasを使う。モデルを勝手に別サーバーへすり替えない。出力先は存在しない一意な絶対パスで、その親ディレクトリは事前作成する（既存原本へは出力しない）。

```bash
export PYTHONPATH=src:tests:.
export L_ZOMBIE_Z2C_REAL_H2_DEV=1

python -m tools.l_zombie_z2c_h2_original_feedback \
  --original-root "$REPO/docs/evidence/l-z2b-real-20261102" \
  --evidence-root "$NEW_H2_EVIDENCE_ROOT" \
  --endpoint "$ENDPOINT" \
  --model "$MODEL_ALIAS"
```

**この1回の結果だけを保存する**。原応答が不整合でも修正再生成しない。実モデルであること、原HTTP要求・応答が原本として採れたことと、内容が正しいことは別々に判定する。

## 2 — 新しい独立プロセスでH2原本を再読込

保存済み原本の作成とは別のPythonプロセスで実行する。監査レポートは未使用パスへの排他的作成。

```bash
python -m tools.l_zombie_z2c_h2_independent_audit \
  --original-root "$REPO/docs/evidence/l-z2b-real-20261102" \
  --h2-root "$NEW_H2_EVIDENCE_ROOT" \
  --report "$NEW_H2_EVIDENCE_ROOT/h2-independent-original-audit.json"
```

監査内容：
- 親#703の**68ファイル**SHA・生H1 HTTP・Paper31連続tick・H1元予測と実測の再算出
- 新H2 HTTP request原本を決定的に再構成して同一bytes/SHA検証
- H2 responseのnative finish_reason=stop、Reasoning OFF、無重複JSON
- H2自発数値誤差がPaper実測からの水平距離と0.02m以内
- 数値回答だけPASSで反証対象等が不整合なら**数値のみ限定評価／定性的評価FAIL**を区別
- 完全H2契約PASSでも、**実際のrationaleと次の反証文の意味は別途独立レビュー**。enum一致だけでB1-QをPASSにしない
- H2保存済み提案とHTTPから再構成した提案のbytes一致、学習/Action/L0昇格すべて禁止
- 使用した新GGUF process/mmapの証拠は**監査スクリプトだけでは取得しない**。実機側の別原本を添付

独立監査で`H2_FULL_CONTRACT_SOURCE_REPLAY_PASS_SEMANTIC_REVIEW_PENDING`でもB1-Q/B2を勝手に昇格しない。B2には次の別Worldの事前登録された反事実/適用条件holdoutが必要。

## 3 — GitHub納品

独立証拠用の子PRを起こす場合は#706を親にし、履歴のH1/H2原本を分離する。Issue #693/#431/#653、PR #703/#706 と実機子PRへ日本語で報告し**投稿内容の読戻し**まで行う。

必須報告：実行HEAD/最終HEAD、実GGUF SHA/PID/mmap・build・ctx/slot、H2 HTTP要求数・再試行数、元H1のSTATIONARY・予測/実測座標、H2自発誤差（失敗なら不成立）、適用条件・反証文の修正／棄権、別プロセスの原本監査、H2保存ファイル別SHA、cleanup、旧原本不変・main不変、B1-N/U/Q/B2/Cの独立判定。

**現在の状態：Z2C独立監査オフラインPASS／新規実H2未実施／新World0／CLIENT_TICK_JOIN_UNATTESTED／DEV_ONLY・QUALIFICATION_NO_GO・SCIENCE_NOT_RUN。**
