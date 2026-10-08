# RelaySelf S24 — 失敗後の明示的な再認知と World evidence A/B

## Authority
- Frozen S23 PR #359 exact HEAD `e519af52d2b7aa8a910f096df04d0a4802ccc823`
- S18〜S23 全 frozen artifact は参照のみ。RelayTheory R6/Paper2 MAIN40 に変更なし。

## 問題
S23 は失敗済み Skill2 から別 Skill3 を起動し、Action3 を閉じた。
しかし失敗後の認知を作り直さず S19 PLAN を再投影しただけだった。
今回は Action3 terminal OUTCOME の **後**、別の caller が明示的に新しい
World 観測を与えて ATT→BLF→CNC→PRD→PLAN→ROUTE→ADMISSION
の既存 stateless mechanism をもう一度実行することを検証する。

```text
WorldConsequence3 != fresh World observation
fresh World observation != automatic decision epoch
new decision != Action authorization != ISSUE
recomputed cognition != learned policy
```

## 実装
`src/relay_self/postfailure_cognition.py` に二つの境界を作った。

1. `PostFailureWorldEvidence` は Action3・binding・session・
   WorldConsequence provenance、別 observation provenance、距離（cm）、
   observed_at_ns を持つ immutable caller input。Action3 terminal かつ
   recovery Skill3 STARTED、Current Intent active、retained 4/rev1 で、
   observation が Action3 closure 後であることを必須とする。
2. `run_explicit_postfailure_epoch` は検証後に既存の
   `compile_epoch_plan` / `coordinate_planned_epoch` で
   ATT/BLF/CNC/PRD/PLAN/ROUTE/S13 admission を起動する。
   owner は増やさない。認知の途中に World state や retained state
   の変更権限はない。

S19 と同様に `Concept → PredictionState → fixed comparison score` を
使う。比較規則は caller がここで明示した **固定 fixture policy**：

- `clearance_cm <= 100`: WAIT score `2 * risk_weight`
- `clearance_cm > 100`: WAIT score `risk_weight`
- MOVE_AWAY score `7`
- 最小スコア選択。risk_weight 4/rev1 は固定。

観測値だけが判断を変える。これは学習済み policy の更新ではない。

## A/B qualification
S23 `_completed()` を独立 fixture で再現し、
Action3 session / Skill3 / Intent / frozen retained を一致させる。

A：反事実の近距離観測 20cm → WAIT 8 vs MOVE_AWAY 7 → MOVE_AWAY

B：別 caller が与えた後続遠距離観測 180cm → WAIT 4 vs MOVE_AWAY 7 → WAIT

いずれも ATT、BLF、CNC、PRD 2分岐、PLAN、ROUTE、S13 の
同一演算子・criterion・候補集合を通り、fresh admission は ADMITTED。
A は独立反事実であり、実際の Action authority へ転用しない。
B が実際の明示 invoke fixture。モデル呼び出しはゼロ。

## Negative controls
- observation が Action3 terminal より前か同時、または epoch より後
- wrong Action / binding / session / WorldConsequence provenance
- invalid negative, bool, float distance
- stale retained owner revision、終了した Skill3
- Intent の pending reconsideration / release
- Action3 owner mismatch または non-EXECUTED consequence
- WorldConsequence と observation を同一 provenance とする偽装
- 意図しない自動次 epoch、Action propose/issue、Learning commit がないこと

## Trust limit と未資格化
距離 cm は **信頼された caller が与えた構造化入力**であり、
Minecraft 実Worldの independent threat tracking でも
Mineflayer nearby-entity observation でもない。
Action3 の観測済み移動は安全確認に等しくない。
距離証拠の Source lineage は provenance にすぎず、
物理的な独立認証の証明でもない。

WAIT を決定しても、WAIT の物理 Action は実行していない。
連続自律再入場、World-event scheduler、Skill3 自動完了、
新しい learned policy、追加 retained update、real Minecraft は
未実装 / 未資格化。

## Qualification gate
`EXPLICIT_POSTFAILURE_WORLD_EVIDENCE_RECOGNITION_QUALIFIED`
は exact final HEAD の CI 4 job 全成功時に限り採用。PR は Draft /
未マージ。

S25 候補は「第三 epoch の候補決定を実際の実行または待機条件に接続」
あるいは「World evidence の取得・freshness の真正性」を、
どちらか一つの bounded 試験として進める。
