# RelaySelf S20 — 2回目 Action の独立実行・Outcome 閉鎖（日本語）

## Authority と採用契約

- Exact S19 base `8ea0365f48b5e58bdbca503a120ea8bf5818e2ec`、Draft PR #355。
- S18 frozen `b5eb5d3416a9c303b855250adea4323e7611f350`、Draft PR #354。
- RelayTheory R6 `9a134b25380c4302830c8d567e5ff52870a7b9ef`、Draft PR #477 は **参照のみ**。
- S18 / S19 の既存 architecture/test/receipt を変更しない。
- 根本原則：selection != admission != commitment != binding != proposal != authorization != issue != physical execution != Action outcome != LearningFeedback != retained update。

## 二つの明示的 transaction

**Epoch 1** — S19 実装済みの qualification apparatus をそのまま実行：
ATT → BLF → CNC → PRD/PLAN/HABIT → ROUTE → ADMISSION →
EXEC_BIND → Skill 1 STARTED → Action 1 PROPOSED/AUTHORIZED/ISSUED →
S15 deterministic WorldConsequence 1 EXECUTED → S16 Action 1 OUTCOME →
S17 explicit LearningFeedback → S10 proposal → LearningUpdateAuthority →
`risk_weight=3/rev0 → 4/rev1` → **STOP**。

**Epoch 2** — 別の caller-owned `compile_epoch_plan → coordinate_planned_epoch`
呼出しが retained rev1 を厳密に読み、
ATT → BLF → CNC → PRD WAIT / MOVE_AWAY → PLAN MOVE_AWAY →
ROUTE → fresh S13 ADMISSION まで既存 S19 路を実行。
その caller の **同じ epoch 2 transaction 内の明示的 continuation** により、
既存 S14 `resolve_execution_binding` →
`start_and_propose_bound_execution`（Skill 2 STARTED、Action 2 PROPOSED） →
caller の **別個の explicit authorize** →
既存 ActionSupervisor ISSUE → S15 `build_mineflayer_command` →
bounded deterministic `execute_mineflayer_command` →
WorldConsequence 2 EXECUTED →
`interpret_world_consequence` → `record_interpreted_action_outcome` →
Action 2 **OUTCOME** → **STOP**。

Epoch 2 の認知→Action は既存 S19 の `_epoch_two` apparatus に
caller が同期的・明示的に後続 S14–S16 を接続したもので、新たな
認知 epoch 呼出し・隠れた loop・scheduler は追加しない。
この資格化用 composition は production autonomous dispatcher ではない。

## 独立性の実証

| | Epoch 1 | Epoch 2 |
| --- | --- | --- |
| Action ID | action-move-backward-1 | action-move-backward-2 |
| Skill execution ID | skill-exec-escape-1 | skill-exec-escape-2 |
| Binding ID | binding-move-away-1 | binding-move-away-2 |
| World session | s18-session | s20-session-2 |
| Action terminal | OUTCOME | OUTCOME |
| Learning retained | rev1 commit | rev1 unchanged |

Action 1 と Action 2 は同じ既存 supervisor の別 Action owner slot。
Action 1 は Outcome 2 の後も current terminal OUTCOME のまま。
Action 2 の before/dispatch/cleanup/after 全証拠は別 session に閉じている。
S16 への入力は第二 session と ID の照合を終えた typed WorldConsequence。
Outcome2 を記録した時点で Supervisor に open Action はない。

## 因果 provenance

Epoch 1 の structured feedback ID → S10 rule/version → update authority
→ LearningCommitRecord revision=1 → S19 PredictionState.source_refs /
source_provenance → PLAN candidate → fresh S13 admission → S14 binding →
Action 2 proposal event の明示 provenance → Action 2 ISSUE →
WorldConsequence 2 → S16 outcome までをテストで追跡。

S20 の `SecondEpochLineage` は読み取り専用の監査 pointer であり、
Action/Skill あるいは LRN の実行・承認権限ではない。
新しい `second_epoch_action.py` は２つの純粋検証関数のみ：
`validate_second_epoch_lineage`（前 Action current terminal、真正な既存
feedback/commit refs、PLAN source、ID 独立性）と
`require_fresh_second_consequence`（現行 supervised ISSUED、別 session、
Action/binding 一致、時刻・既存 deadline 内）である。
S14–S16 そのものは一切変更していない。

## fail closed・負対照

- 同じ Action/Skill/Binding ID 再利用、異なる PLAN candidate、Intent 不一致。
- 不正な retained revision、feedback/authority/update lineage の欠落。
- fresh admission / binding candidate 不一致。
- 未承認 Action 発行、不正な authority、二重 issue、stale Action snapshot。
- terminal Skill を経由した stale Skill proposal。
- WorldConsequence の Action ID / Binding ID / session 不一致。
- 内部 World evidence の session 不一致、型破損、movement 欠落。
- Deadline 以降の遅延 consequence と terminal outcome の重複記録。
- Epoch 2 の Feedback/LRN commit は **存在しない**。Epoch 3 の自動呼出しはない。

## データと範囲

- `docs/postmain-s20-receipt.json`：機械可読の qualified claim と限界。
- `docs/postmain-s20-cross-epoch.json`：２本の Action/session、learning lineage、
  deadline、outcome、provenance の機械可読照合。
- `tests/test_postmain_second_action_closure.py`：S19 を再利用した
  新しい deterministic 正常・異常系。
- `.github/workflows/postmain-capability-s20.yml`：CI。

**根本限界**：Model calls = 0 の deterministic apparatus であり、
本物の Minecraft world を操作していない。Action OUTCOME は観測済みの
terminal disposition であり一般的 reward/success と同一視できない。
Skill2 の自動 SUCCEEDED / FAILED closure は資格化されない。
World session の真正性・壁時計時刻は trusted caller/session に依存し、
単独で外部世界の真実を証明するものではない。
Owner-local retained risk_weight は rev1 のまま。継続自治、複数 Action
への temporal credit assignment、Paper2 MAIN40 の変更は一切ない。

## S21 推奨

Action2 の terminal closure と **別の Skill2 lifecycle** を
独立した明示 criterion で統合するか否かを資格化し、
WorldConsequence が terminal Action になっても Skill SUCCEEDED
とは自動推論できない境界を fail closed で監査する。
必要なら「二回目の World consequence → 新しい explicit LearningFeedback →
別の authority による rev2」を **別 issue / 明示資格化** として検討する。
S21 で自律 reentry は前提にしない。
