# RelaySelf S22 — Skill 終了後の局所回復と Intent 再考の明示分岐

## 凍結権限
- S21 Draft PR #357、exact base `04816df243e53af0349b14e478bf96d5ff52277a`
- S20 #356 / S19 #355 / S18 #354 の frozen 成果物を変更しない
- RelayTheory R6 #477 は参照のみ、Paper2 MAIN40 に変更なし

## 課題と原則
S21 は Action2 OUTCOME と Skill2 terminal SUCCEEDED/FAILED/CANCELLED を
異なる owner で扱うことを示した。

しかし Skill が終了しただけでは次の次元は決まらない。

```text
Skill FAILED != Current Intent FAILED
Skill SUCCEEDED != Current Intent COMPLETED
Skill CANCELLED != Skill FAILED
local recovery candidate != new Skill STARTED
reconsideration candidate != admitted request
admitted request != reconsideration decision != Intent replacement
```

S22 は #107 の局所回復優先原則を一つの限定された明示経路で検証する。
永続 coordinator や普遍的な優先度・驚き度を導入しない。

## 最小実装
`src/relay_self/skill_exit_routing.py` は次の3つの関数を提供する。

1. `assess_skill_exit`：既存 SkillExecution の現行 terminal snapshot と
   IntentCommitment の現行 Current Intent を読取り、明示 criterion、
   Skill terminal event の time/provenance、caller-supplied な別系統の
   local feasibility と Intent impact 証拠を照合する。どの owner も変更しない。
2. `start_explicit_local_recovery`：FAILED、別の局所 Skill が AVAILABLE、
   Intent NOT_CHALLENGED の場合のみ、明示 matching authority と fresh
   Intent owner event-history checkpoint で入場し、
   既存の `SkillExecution.start` に別 execution ID / skill ID を渡す。
   Current Intent を保存し、Action は生成しない。
3. `request_explicit_reconsideration`：FAILED、局所経路 EXHAUSTED、
   Intent MATERIALLY_CHALLENGED の場合のみ、別の明示 matching authority
   を要求し、既存の `IntentCommitment.request_reconsideration` により
   REQUESTED イベントだけを記録する。Intent はまだ current。

別の caller が `IntentCommitment.reconsider(CONTINUE/RELEASE)` を
呼ばない限り再考判定・解放は行わない。

評価規則はこの限定試験向けであり、一般的な状況分類・推論 policy ではない。
`AVAILABLE + MATERIAL_CHALLENGE` など矛盾・競合の可能性がある
証拠は `HOLD_FOR_EVIDENCE` に留める。

Skill 成功は `CONTINUE_INTENT_ONLY`、明示キャンセルは
`HOLD_FOR_EVIDENCE` と分類し、Intent の完了や失敗は推論しない。

## 正例
S20 の二番目の Action terminal trace → S21 の Skill2 FAILED
(`skill-exec-escape-2`) を動かした上で、同一 Current Intent
`escape-threat` を保って独立の回復証拠を照合する。

- A: 別の局所候補があり Intent が維持可能 →
  `LOCAL_RECOVERY_CANDIDATE` →
  明示権限 → 既存 SkillExecution.start →
  `skill-exec-escape-recovery-3` STARTED。元 Skill は FAILED のまま。
- B: 局所候補なし・Intent が重大に成立しなくなったとの明示証拠 →
  `RECONSIDERATION_CANDIDATE` →
  明示権限 → 既存 IntentCommitment.REQUEST_RECONSIDERATION →
  pending。続く CONTINUE / RELEASE は別の caller 判定・イベント。

いずれも新しい Action、automatic epoch、LearningFeedback、
retained state commit を生まない。S19/S20 の rev1 保持は不変。

## 負例と authority audit
- stale Skill snapshot / 改変された terminal event 時刻と provenance
- 意図 ID・Skill ID・criterion の不一致、別の/同じ Skill ID の代替
- 未確定・矛盾した実行可能性 / Intent impact の HOLD
- missing/denied/wrong-route/wrong-intent/wrong-criterion authority
- 観測より早い時刻の handoff
- assessment 後に変化した Intent owner の event history
- reconsideration 要請の replay・重複
- route 文字列を書き換えた forged assessment
- Skill 失敗・成功・取消しによる自動 Intent 終了がないこと

## 実装の制約と残余リスク
- Path availability、material challenge、authorization は全て
  信頼された caller が与える。World に対する真正性を証明しない。
- 任意の caller が別の SkillExecution.start root を複数作れる既存契約は
  変えていない。新 local Skill 開始の global exactly-once は **未証明**。
- local recovery による Action 発行、Intent 再考結果による次の
  認知エポック、外部Minecraft稼働、永続的自律性は **未資格化**。
- no global semantic store / scheduler / generic event bus / new
  Current Intent owner。
- Paper2 MAIN の測定分類を実装結果から変更しない。

## 採否ゲート
最終 HEAD の repository contracts、pytest（S18–S22回帰）、
Ruff lint、Mineflayer adapter が全成功した場合のみ、

`EXPLICIT_SKILL_EXIT_LOCAL_RECOVERY_OR_RECONSIDERATION_QUALIFIED`

を限定された deterministic result として主張する。

次の S23 候補は local recovery Skill の新しい admission / Action 発行と
結果確認、または admitted reconsideration 後の別起動 Epoch を
一段ずつ検証すること。自律再入場を前提にしない。
