# RelaySelf S26 — WAIT 解放後の第四 Action outcome closure

## 凍結 Authority
- S25 Draft PR #361 / exact base `dce5fe3bf33ed2fd450ab5e4ccea076e628ad938`
- S24 #360 / S23 #359 / S18〜S22 は凍結。RelayTheory R6、Paper2 MAIN40 は変更しない。

## 研究上の境界
S25 は WAIT を非 Action の判断として保持し、別の新 World evidence により
MOVE_AWAY を再選択できることを示した。ただし MOVE_AWAY 選択や S13 admission は
Action 権限ではなく、発行・物理実行までの証拠でもなかった。

S26 は、明示的 caller が S25 の **新たな reevaluation** に対して
別個の proposal authority を提示した場合だけ、S13/S14 と S14 ActionLifecycle
の既存境界を通じて Action4 を PROPOSED にする。続く AUTHORIZED / ISSUED /
WORLD_EXEC / OUTCOME は各既存 owner の権限を使い、独立 closure を行う。

```text
S24 WAIT selected != Action proposed
S25 WAIT acknowledged != Action authorized
S25 new MOVE_AWAY selected/admitted != Action proposed/authorized/issued
S26 proposal permission != Action authorization != Action issue != World outcome
Action4 OUTCOME != Skill3 SUCCEEDED
```

## 認知・比較規則と admission の扱い
S24 が保持する `PostFailureEpochTrace` は上位の selected candidate、
スコア、証拠と admission 結果のみで、内部の PlanSelection / S12 RouteDecision /
S13 AdmissionDecision 実体は外に返さない。

そのため S26 は新規認知を起動せず、S24 固定規則
`WAIT=2*risk_weight` if clearance <= 100cm, else `risk_weight`、
`MOVE_AWAY=7`、retained `risk_weight=4/rev1` を
新 evidence の値から再計算する。S25 結果の source provenance、
選択、スコア、stage IDs が一致することを検査する。

その上で別 `PlanSelection` → S12 route / ControlCandidate →
独立の S13 AdmissionDecision → 既存 S14 `resolve_execution_binding` を再実行し、
必要な Action4 ID、Binding ID、既存 STARTED Skill3、Current Intent ID、
MOVE_AWAY→MOVE_BACKWARD の限定 mapping を一致させる。

これは **S24 の内部 Plan object を再取得したと主張しない**。
またモデルが新しい運動戦略を考案したことも意味しない。

## 三層の caller/owner authority
- S25 `ACKNOWLEDGE` は WAIT の非行動受領だけ。
- S25 `REEVALUATE` は新 evidence に対する再認知だけ。
- S26 `WaitReleaseActionAuthority` は新 Action4 の PROPOSE を許容する
  **限定 caller grant**。これまでの authority_id を再利用できない。
- 別の Action4 authorization が `ActionLifecycle.authorize` を通る。
- `ActionSupervisor.issue` が別 deadline で正式 ISSUE する。
- S15 Mineflayer deterministic adapter と S16 Action outcome interpreter が
  WorldConsequence4、独立 terminal OUTCOME を作る。

## 正例
- S24 遠距離180cm→WAIT4/MOVE_AWAY7→WAIT。
- S25 WAIT 明示 ACK at 71ns、有効期限110ns、Actionなし。
- S25 新 World 観測20cm at 80ns → 別 caller 再評価 at 90ns →
  WAIT8/MOVE_AWAY7→MOVE_AWAY。
- S26 別 caller proposal grant → 95ns Action4 PROPOSED。
- 別 Action authority → 96ns AUTHORIZED → 97ns ActionSupervisor ISSUED
  （deadline180ns）。別 World session4 で S15 MOVE_BACKWARD を実行し、
  S16 が 105ns terminal OUTCOME へ閉じる。

既存 Action1/2/3 は terminal OUTCOME のまま。Skill2 は FAILED、
Skill3 は STARTED のまま、Current Intent は escape-threat、
retained risk_weight は 4/rev1 を維持する。

## 否定試験
- 再評価が WAIT のままなら Action PROPOSED を許さない
- 未認可・拒否・誤 scope・異なる evidence・Action/Binding/Skill の各 grant
- score / World parent / provenance / stage / decision 改変を拒否
- WAIT 期限超過と epoch 時刻の逆行を拒否
- Skill3 terminal/stale、Intent reconsidered/released を拒否
- Action3 ID 再使用、重複 ISSUE、terminal outcome replay、別 session World を拒否
- Action PROPOSED から直接 ISSUE できないことを検査

## 非主張・残余限界
S26 は同じ `MOVE_BACKWARD` の deterministic Mineflayer double であり、
別の物理プリミティブの実装やリアル Minecraft の資格化ではない。
World 距離、caller time、権限 token の真正性は信頼された caller に依存する。
グローバル exactly-once Action proposal、再起動を跨ぐ replay 防止、
自律 scheduler / World listener、持続的 cognition、Skill3 自動成功や
新 Learning commit は **未資格化**。

S26 で第4 Action が閉じても、4つの Action が自律的4エポックとして
起動されたと読み替えない。Paper2 MAIN40 の測定結果も更新しない。

## 受け入れ
全 regression pytest、repo contracts、Ruff lint、Mineflayer adapter の
最終 HEAD CI 成功時に限り
`EXPLICIT_WAIT_RELEASE_FOURTH_ACTION_OUTCOME_CLOSURE_QUALIFIED`
を bounded deterministic test として採用。Draft 未マージ。

次の S27 候補は、Source-native World evidence の真正性・freshness
資格化、または explicit WAIT gate の replay-safe ownership を
どちらか一つに限定して検討。自律再入場は先行しない。
