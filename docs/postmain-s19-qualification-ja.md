# RelaySelf S19 — 明示的な二つの decision epoch と retained-state 再利用

## Authority / 範囲

S18 Draft PR #354 / frozen HEAD `b5eb5d3416a9c303b855250adea4323e7611f350` を親とする S19。
RelayTheory R6 PR #477 / HEAD `9a134b25380c4302830c8d567e5ff52870a7b9ef` は参照のみ。
S18 の `docs/postmain-architecture.{json,md}` は一切変更しない。

## 実装

`epoch_continuation.read_retained_preference` は owner-local LearningPreferenceState の
immutable snapshot だけを読む。caller が渡した現行 owner snapshot と読取対象の
**同一インスタンス**、target ID、revision、rev>0 の commit evidence を照合する。
返値の RetainedPreferenceRead は read provenance、origin provenance、
last_update commit record を保持する immutable envelope であり、retained owner でも
authorization token でも scheduler でもない。caller が正しい最新 owner snapshot を
渡すことが前提であり、外部からの真偽証明までは提供しない。

## 二 epoch の実行 trace

1. Caller が `coordinate_decision_epoch` を **1回明示起動**。
2. S18 の構造化 deterministic apparatus により、
   ATT → BLF → CNC → PRD → PLAN / HABIT → ROUTE → ADMISSION →
   EXEC_BIND → Skill STARTED → Action PROPOSED → AUTHORIZED → ISSUED →
   WorldConsequence.EXECUTED → Action OUTCOME → 明示 FEEDBACK →
   S10 learning proposal → 明示 LearningUpdateAuthority →
   `risk_weight 3/rev0 → 4/rev1` → **STOP**。
3. 自動 reentry はない。Caller が別途 due_items と EpochBinding を作成。
4. `compile_epoch_plan` と既存 `coordinate_planned_epoch` を明示起動。
   正しい最新 snapshot を PLAN step で消費し、
   PLAN → ROUTE → **新規 ADMISSION** → **STOP**。
5. Epoch 2 の比較は同一の caller-owned bounded projection:
   `WAIT score = 2*risk_weight`, `MOVE_AWAY score = 7`, MINIMIZE。
   rev0 では WAIT=6 < 7 なので WAIT、rev1 では WAIT=8 > 7 なので MOVE_AWAY。
   **唯一の差分**は governed retained-state の値。投影ルール自体は学習していない。
6. Epoch 2 は認知判断と fresh admission で停止。別の Skill/Action の発行は行わない。

## 所有権 / 権威 / fail closed

- S10 `commit_learning_update` のみが retained transition を作れる。
  feedback != proposal != commit。
- selection != admission != authorization != execution。
- ActionSupervisor / IntentCommitment / SkillExecution / ActionLifecycle の
  S18 境界を変更しない。
- 旧 revision、同値だが別オブジェクトの snapshot、owner target mismatch、
  rev1 の commit record 欠落、欠落・拒否・別 owner の learning authority は拒否。
- 追加 module はコールバック、モデル、背景 task、次 epoch、hidden registry、
  central executive、mutable semantic store、任意の cross-owner mutation を持たない。
- deterministic test provider/model calls = 0。

## 検証と証拠

`tests/test_postmain_two_epoch_continuation.py` で positive、no-change control、
no-auto-entry、stale、unauthorized、no-hidden-scheduler を検査する。
`docs/postmain-s19-receipt.json` は期待 trace と証拠区分を machine-readable に固定。
CI 成功が得られた場合のみ結果を資格化する。緑の CI は live Minecraft 実験ではない。

## 明示的な限界と S20

S19 は「二つの **明示呼出し** にまたがる、有限単一 target の retained reuse」のみ。
continuous autonomy、trigger policy、複数の epoch を横断する long-horizon learning、
実 Minecraft、learned projection、二回目の Action 実行、Paper2 実証拡張は未資格化。

S20 の候補は caller-owned 明示呼び出し契約を保持したまま、
Epoch 2 の fresh admission から独立の Skill/Action 発行・観測・terminal closure
まで行い、replay / duplicate issue / late outcome / wrong lineage を監査すること。
自律 scheduler の導入は S20 にも自動的には含めない。
