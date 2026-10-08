# RelaySelf S25 — WAIT は Action ではない：明示的な再評価と境界監査

## Authority
- RelaySelf S24 Draft PR #360、exact frozen HEAD: `103dcaf887c59784baaaee761e5f4086d48e8212`
- S18〜S24 と RelayTheory R6 / Paper2 MAIN40 は一切変更しない。

## Mission
S24 は第3の明示的 cognition epoch で World observation を 180cm とした時
WAIT 4 / MOVE_AWAY 7 を評価し、WAIT を ADMITTED した。
しかし `WAIT selected` は `Action PROPOSED` でも `Action ISSUED` でもない。

S25 は「WAIT を判断記録として受け取る」と
「新しい World evidence による再認知」を、
**異なる caller authority と明示的呼び出し**で分離して検証する。

```text
WAIT ADMITTED != Action authorization != ISSUE
WAIT acknowledgement != timer installation != next epoch
fresh World evidence != automatic reevaluation
reevaluation selected MOVE_AWAY != Action proposed/issued
```

## 実装
`src/relay_self/explicit_wait.py` に既存 owner を読み取る
二段階の bounded seam を追加する。

1. `acknowledge_explicit_wait`: S24 `PostFailureEpochTrace` の
   WAIT/ADMITTED と予測スコア・実行 stage、S23 Action3 terminal OUTCOME、
   S24 WorldConsequence3 ancestry、Current Intent active、Skill3 STARTED、
   retained snapshot rev1/v4 を確認する。
   元の evidence ID に一致する `ACKNOWLEDGE` 権限と caller 時刻
   および valid-until を要求する。
   結果は immutable caller-held `ExplicitWaitGate`。owner stateは変更しない。
2. `reevaluate_explicit_wait`: 別の `REEVALUATE` 権限と
   **別 evidence ID / provenance** を要求する。観測は WAIT 承認後、かつ期限内。
   parent Action3 / Binding3 / World session / WorldConsequence は同じ。
   Intent event-history が変わらず Skill3 と Action3 が現行であること、
   新しい Action が open でないこと、retained snapshotが維持されることを確認し、
   既存 S24 `run_explicit_postfailure_epoch` を再び明示的に呼ぶ。

これは scheduler でも持続的 wait owner でもない。
期限を超えても自動的に再評価しない。再評価の結果が
WAIT のままでも別途 caller ACKNOWLEDGE が必要であり、
MOVE_AWAY になっても発行権限は生まれない。

## Positive qualification
同一 S23/S24 deterministic subject:

- S24: 遠距離観測 180cm、risk_weight 4/rev1 →
  WAIT 4 < MOVE_AWAY 7 → WAIT ADMITTED → 明示 ACKNOWLEDGE at 71ns、
  expiration 110ns。新 Action なし。
- S25: 別 caller 新観測 20cm at 80ns、別権限で
  recheck at 90ns → S24 cognition 8 stages を再実行、
  WAIT 8 > MOVE_AWAY 7 → MOVE_AWAY ADMITTED。新 Action なし。
- 遠距離 250cm at 80ns なら WAIT のまま。暗黙の再帰なし。
- Action1/2/3 は OUTCOME を保持、Skill2 FAILED、Skill3 STARTED、
  Current Intent は同じ、retained risk_weight 4/rev1。

## Negative qualification
- 元の選択が MOVE_AWAY、未 ADMITTED、stage/score 改変
- WAIT 承認の欠落・拒否・誤スコープ権限
- 元 evidence と同じ ID/provenance、他 Action / binding / session
- wait 承認時刻より古い観測、未来の観測、期限超過
- reevaluate に対する欠落・拒否・別スコープ権限・権限ID再利用
- Current Intent の変更や pending reconsideration、Skill3 terminal/stale、
  supervisor に予期しない open Action
- 不正入力は認知前に拒否し、Action を提案・認可・発行しない。

## Scope / Limitations
距離証拠、認可、時刻は信頼された caller 由来で、
World native sensing や暗号学的真正性は未検証。
immutable receipt はグローバルな一意性や replay protection を提供しない。
時刻の deadline は検証境界にすぎず、timer ではない。

S24 固定比較規則以外の general learning / policy discovery、
Minecraft 実環境における「安全な待機」、連続的な自律再入場は
資格化していない。Paper2 MAIN40 の結果にも影響しない。

## Acceptance
`EXPLICIT_WAIT_NONACTION_FRESH_EVIDENCE_RECHECK_QUALIFIED`
は exact S25 final HEAD の S18-S25 pytest、Ruff、
repo contracts、Mineflayer adapter の全成功時にのみ採用。
Draft PR のまま未マージで保持。

S26 候補: WAIT を解除した後の MOVE_AWAY について、
独立した Action authority / issue gate への handoff を
限定的に検証する（自律 event scheduler は別案件）。
