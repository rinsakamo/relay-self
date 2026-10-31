# RelaySelf S23 — 同一 Intent の局所 Skill 回復から3番目の Action outcome まで

## Authority / 凍結
- S22 Draft PR #358 / exact base `7b815217db5be4402a88090d04a22e61f5ea05c7`
- S18〜S22 の frozen files と RelayTheory R6 #477 / MAIN40 は未変更。

## Research question
S22 は、Skill2 FAILED 後に Current Intent を維持して
別の Skill3 を明示的に STARTED にできると示した。
ただし Action を生成しなかった。S23 は、その **既存 STARTED Skill**
から正確な S13 admission と S14 binding を通した別 Action を
PROPOSED にし、独立 authorization / ISSUE / WorldConsequence / OUTCOME
まで閉じられるか検証する。

ここで区別すべきなのは

```text
Skill2 FAILED != Intent FAILED
local recovery start != Action proposal
Action proposal != authorization != ISSUE != World execution != outcome
Action3 OUTCOME != Skill3 SUCCEEDED
```

## Narrow integration
既存 S14 `start_and_propose_bound_execution` は **新しい Skill を
start する** ため、S22 で既に STARTED の Skill3 に直接使うと
Skill owner root を重複生成する。

そのため S23 では純粋な `propose_explicit_recovery_action` が

1. S22 assessment / matching granted authority / exact terminal Skill2 / fresh
   Skill3 / Intent event-history の各々を再照合。
2. 既存 S19 PLAN を別 caller の S12 adjudication で再投影し、
   **新しい独立** S13 criterion / admission を実行。
3. 既存 S14 `resolve_execution_binding` を再利用して route/control/
   Current Intent と Action3 / Skill3 mapping を検証。
4. 新たな Skill root を開始せず、既存 `ActionLifecycle.propose` の
   明示 seam を実行。S14 `ExecutionBindingResult` を作る。
5. Action3 について caller が別の権限で AUTHORIZE、既存
   ActionSupervisor が ISSUE、S15 が deterministic Mineflayer
   adapter double で WorldConsequence、S16 が terminal OUTCOME を記録。

S23 guard に authority を創設する権限や常駐実行責任はない。

## Positive trace
S20 Action2 OUTCOME → S21 Skill2 FAILED → S22
`LOCAL_RECOVERY_CANDIDATE` → caller が Skill3 STARTED →
新 S12 route + S13 ADMISSION →
S14 binding check → Action3 PROPOSED →
別 authorization → ActionSupervisor ISSUED →
S15 `MOVE_BACKWARD` on session 3 →
WorldConsequence3.EXECUTED → S16 Action3.OUTCOME → STOP。

3つの Action ID / Binding ID / World session を別にし、
Action1, Action2 はいずれも terminal のまま。
Skill2 FAILED は維持され、Skill3 は STARTED のまま。
Current Intent は escape-threat、保持 risk_weight は 4/rev1 のまま。

## Fail-closed scope
- S22 matching authority 欠落・拒否・違う経路
- fake S22 assessment・stale Skill2・Skill3 stale / terminal
- Action2 が supervisor の現行 OUTCOME でない場合
- 以前の S13 admission の再利用・criterion/provenance 不一致
- S14 candidate vs binding 不一致 / Skill・Intent ID 不一致
- pending reconsideration / Intent release
- Action2 ID の再利用・未承認 issue・二重 issue・terminal replay
- 別 World session と Action/binding 誤対応

## 重要な限定
S15 の現行実装は `MOVE_BACKWARD` 一種類のみ。
「代替 Skill」とは **別 Skill execution identity / capability label**
であり、別の運動プリミティブ・戦術の実装の証拠ではない。
S19 の PLAN 出力を別 S12 / S13 判定に投入するが、
**失敗後の ATT/BLF/CNC/PRD/PLAN の再実行はない**。
したがって fresh cognition / post-failure plan discovery は未資格化。

S22 の新 Skill start のグローバルな exactly-once 保護、持続的
replay 防止、実 Minecraft での行動や目標達成は未証明。
caller-supplied authority / provenance / time / session を信頼する。
継続的自律性、3番目の認知 epoch、Skill3 自動完了・再学習は含まれない。

## Qualification gate
Exact final HEAD で repo contracts、pytest、Ruff、Mineflayer CI が成功する
場合のみ `EXPLICIT_LOCAL_RECOVERY_ACTION_OUTCOME_CLOSURE_QUALIFIED`。
PR は Draft / 未マージで保持。

次の候補 S24 は、新しい World evidence により認知を明示的に再入場
させて真に別の候補を再選択できるか、あるいは新たな Mineflayer
primitive を安全に導入するかのどちらかを限定して検証。
