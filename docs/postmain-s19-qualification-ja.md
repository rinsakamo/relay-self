# RelaySelf S19 — Explicit two-epoch retained-state reuse / Japanese qualification

## 1. Authority

- S18 frozen PR #354 / HEAD b5eb5d3416a9c303b855250adea4323e7611f350。
- RelayTheory R6 PR #477 / HEAD 9a134b25380c4302830c8d567e5ff52870a7b9ef は引用のみ。
- S18 canonical frozen docs/postmain-architecture.json と .md を変更しない。
- 新しい認知能力、retained owner、persistent cognition scheduler は追加しない。

## 2. Epoch 1 — single explicit invocation

Caller が既存 coordinate_decision_epoch を明示呼出しして、
S18 deterministic test apparatus の既存機構を実行する。

ATT → BLF → CNC → PRD/PLAN/HABIT → ROUTE → ADMISSION →
EXEC_BIND → Skill STARTED → Action PROPOSED → AUTHORIZED →
ISSUED → deterministic Mineflayer WorldConsequence.EXECUTED →
Action OUTCOME → S17 explicit LearningFeedback → S10 proposal →
explicit LearningUpdateAuthority → governed commit → STOP。

Retained owner は risk_weight を 3/rev0 から 4/rev1 に更新。
LearningCommitRecord は feedback ID / rule ID と版 / authority ID /
feedback・authority・commit provenance / revision 0→1 を保持する。
記録された Action outcome は observed_execution、外部 Minecraft field ではない。

## 3. Epoch 2 — independent explicit caller invocation

Epoch 1 の STOP は epoch scheduler を起動しない。
Caller が *新たに* due_items と EpochBinding を列挙し、
compile_epoch_plan → coordinate_planned_epoch を通して既存の deadline-first
coordinator に入場させる。

Epoch 2 は同じ structured nearby-zombie evidence から既存の
ATT → BLF → CNC を再実行する。次に typed owner-local retained
LearningPreferenceState を exact object / target / revision / update-record guard
越しに読む。取得した値を caller-owned comparison projection に明示使用し、
既存の prediction_state_from_concept / predict_transition を実行。

実行順は:
ATT → BLF → CNC → PRD(WAIT) → PRD(MOVE_AWAY) →
PLAN → ROUTE → fresh ADMISSION → STOP。

両候補とも plan_candidate_from_prediction から生成し、
select_plan の既存 MINIMIZE comparison を利用する。
新しい planner、learned weight policy、cognitive owner、
実行 authority やモデル由来の Action permission は導入しない。

## 4. Strict paired A/B counterfactual

同じ Epoch 1 から分岐した2件の明示 Epoch 2 を比較する。

| 条件 | owner-local risk_weight | WAIT score | MOVE_AWAY score | PLAN |
| --- | --- | --- | --- | --- |
| A (isolated historical pre-commit) | 3/rev0 | 6 | 7 | WAIT |
| B (actual governed post-commit) | 4/rev1 | 8 | 7 | MOVE_AWAY |

共通の非 retained 入力:
PropositionKey / BeliefEvidence / AttentionCandidate と criterion /
BeliefCriterion / ConceptCriterion / 意図 owner / 候補順。
両方の TransitionRule オブジェクトの値、PLAN criterion、
ROUTE criterion、admission guard も完全一致する。
WAIT score = 2 × retained risk_weight、MOVE_AWAY score = 7 という
明示固定 projection のみが retained 値を読む。変更されたのは
retained snapshot の value / revision と、そこから導出される
prediction input と lineage pointer である。
PRD 自体に算術演算能力や学習 semantics は追加していない。

A は **isolated counterfactual** として歴史的 rev0 をその分岐の
caller-owned owner snapshot に指定したテスト。実 owner が rev1 となった後に
rev0 を live current owner と偽って読むことを認めるものではない。
current rev1 に対する stale rev0 は別テストで拒否する。

## 5. Exact provenance handoff

S19 の PredictionState.source_refs に
learning-target、learning-revision、learning-feedback、
learning-rule/version、learning-authority、learning-commit-revision
という構造化 provenance pointer を含める。
source_provenance に origin / retained-read provenance と
LearningCommitRecord.feedback_provenance、authority_provenance、
update_provenance を含める。

PRD や PLAN はこれらの pointer を権限として扱わず、
Action authorization / issue / retained-state commit は一切行わない。
この lineage は既存 S10/S17 の真正な commit を caller が渡すという
明示的な trust boundary の範囲でのみ検証できる。
署名済み永続台帳・暗号学的認証・自己更新は主張しない。

## 6. Negative qualification

- Explicit Epoch 2 invocation なしなら second epoch は存在しない。
- Missing、denied、wrong-target LearningUpdateAuthority は commit 不可。
- Wrong target、stale revision、stale instance、同値再構成 snapshot、
  未証明 rev1、provider text、無効 provenance/type は fail closed。
- Stateless operators は Intent / ActionSupervisor / LearningPreferenceState
  を変更しない。2回目の Action PROPOSED/AUTHORIZED/ISSUED は起きない。
- Dynamic import、global mutable cognition store、central executive、
  implicit LRN→next epoch、background scheduler、generic event bus は導入しない。
- Model/provider calls=0（deterministic apparatus）。

## 7. Machine evidence and qualification

- docs/postmain-s19-receipt.json : bounded overall qualification record。
- docs/postmain-s19-counterfactual-ab.json : A/B scores、candidate order、
  exact structured feedback ID、authority ID、update provenance、
  Epoch 2 source refs、work order、explicit non-claims。
- tests/test_postmain_two_epoch_continuation.py :
  existing S18 closure、A/B control、retained lineage、stale/authority
  negative、source-type error、no-auto-reentry、no-cross-owner-mutation。
- .github/workflows/postmain-capability-s19.yml :
  repository-contracts / pytest / lint / mineflayer-adapter。

最終 classification は final exact HEAD 上の CI に成功した場合のみ
EXPLICIT_TWO_EPOCH_RETAINED_STATE_REUSE_QUALIFIED とする。

## 8. Boundaries and S20

本資格化は単一 owner-local bounded preference の2回の明示 invocation
に限定。Epoch 2 は新しい admission までで STOP、2回目の物理 Action はない。
連続的 epoch、autonomous cognition、learned policy、
一般化された global credit assignment、live Minecraft、
Paper2 empirical MAIN40 の再解釈は含まれない。

S20 候補:
fresh Epoch 2 admission 以降も明示 authority を分離して
別個の Skill / Action の発行、bounded WorldConsequence、
Action outcome closure まで検証する。
Replay、duplicate issue、late consequence、wrong lineage、
retained owner の独立性を negative control に加える。
自動 reentry は S20 にも黙示導入しない。
