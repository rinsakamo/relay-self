# RelaySelf S21 — 第二エポック Skill terminal evidence gating

## Authority
- S20 Draft PR #356 / exact base `b8d663527d58124fba6b2d00064750dfe30a8c88`
- S19 #355 / S18 #354 の frozen artifacts に変更なし
- RelayTheory R6 PR #477、Paper2 MAIN40 に変更なし

## 問題
S20 は第二 Action が terminal OUTCOME に達したことを示したが、
SkillExecution（escape-movement）は STARTED のままだった。
primitive Action の観測済み実行は、上位 Skill の目的達成を含意しない。

```text
Action OUTCOME != Skill SUCCEEDED
Action UNKNOWN != Skill FAILED
Skill terminal != Intent terminal
```

## S21 の最小変更
`src/relay_self/skill_terminal_closure.py` は新たな owner を作らず、
2つの純粋な境界を追加する。

1. `assess_skill_terminal`: supervisor の現行 Action terminal snapshot、
   S16 ActionOutcomeInterpretation、現行 STARTED Skill、明示的な
   SkillTerminalCriterion、別の provenance を持つ SkillGoalEvidence
   を照合する。SATISFIED / VIOLATED / UNDETERMINED という evidence
   をそれぞれ SUCCEEDED / FAILED / UNDETERMINED に評価する。
   Action UNKNOWN は goal evaluation が SATISFIED でも UNDETERMINED とする。
2. `commit_skill_terminal`: decisive な assessment を再評価し、
   一致する明示 SkillTerminalAuthority の granted を要求した上で
   既存の `SkillExecution.succeed/fail` だけを実行する。
   評価だけでは Skill owner は変化しない。

CANCELLED は依然として独立した caller-driven 遷移であり、
S21 は Action outcome から自動導出しない。

## Deterministic qualification
S20 `_two_completed_actions()` を実際に再実行した fixture を起点に、
第二 Action OUTCOME 後でも Skill2 STARTED であることを検査する。

- SATISFIED + scoped authority -> Skill2 SUCCEEDED
- VIOLATED + scoped authority -> Skill2 FAILED
- UNDETERMINED -> STARTED 維持、commit 拒否
- UNKNOWN Action -> Goal SATISFIED でも Skill2 未確定
- Action / Skill / Intent / binding / session / criterion / goal ID が
  不一致なら fail-closed
- 不適切な時刻、world provenance の差し替え、Action outcome を
  goal evidence と偽った同一 provenance は拒否
- 欠落・拒否・別 scope の terminal authority は拒否
- stale Skill snapshot、replay commit、assessment の verdict 偽装は拒否

Action1 と Action2 の既存 terminal snapshot は変更されず、
Current Intent は維持される。LearningPreferenceState は 4/rev1 のまま。
暗黙の Epoch3/新規 LearningFeedback/新規 Action はない。

## 権限と観測限界
新しい authority object は caller-granted の **限定ガード**であり、
権限の取得方法や認証機構を新設するものではない。
SkillGoalEvidence は明示的で型付けされた外部評価入力であり、
ActionOutcomeInterpretation から導出しない。

異なる Provenance を要求することは、同じ Action result の
自動再利用を防ぐための最低限の構造チェックに過ぎない。
独立した physical witness や情報源の真正性は検証していない。
実 World の達成評価、複数 Action をまたぐ Skill criterion、
Skill 成功に基づく Current Intent 終了、continuous autonomy は未資格化。

## Acceptance
`EXPLICIT_SECOND_SKILL_TERMINAL_EVIDENCE_GATING_QUALIFIED` は
専用 S21 CI の exact final HEAD 成功後に限って採用する。
失敗時は narrower result とブロッカーを記録する。Draft のまま未マージ。

## 次の候補
S22 は Skill terminal 後の Intent 維持・再計画・明示的再考要請の
分岐を、Current Intent owner の権限を保ちながら検証する候補。
自律的再入場を先行させない。
