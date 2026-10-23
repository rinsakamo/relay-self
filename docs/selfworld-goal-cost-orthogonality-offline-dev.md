# W4 Goal × Cost orthogonality — offline DEV

`DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`

事前登録: https://github.com/rinsakamo/relay-self/issues/633#issuecomment-6367069007
固定基点: `9240af4fc3e27ab531677a28c6447c95eeae8621`。
追加対象は本書、新規offline分析モジュール
`experiments/self_world_goal_cost_orthogonality.py`、その専用テストのみ。
既存 evidence-use / strict replay / factory / core / owner / rubric は変更しない。
PR #634 は Draft / 未merge / HEAD `f0751b915411e89f1d3dffe941461a308fcf2512` を維持する。

## Phase A: 既存owner監査

`GoalSpec` はkind、importance、有限非負costを検証する。Goalはsource証拠ではない。
`prepare_evidence_use` は元strict sourceを再読込し、host軸digest・source bindingを検証する。
C（現在肯定観測）はATT positiveのみ、M（MATCH支持）は同一対象・比較属性・値のみ、
R（追加証拠proposal）とW（不支持主張の保留）は常時admissible。
利用可能性はadmissibleとcost上限の積集合。Rのみ合成proposal cost 0.5、他は0。
Goal kindとimportanceは候補適格性・host事実に介入しない。

2候補未満はDEFERでrequestなし。既存`BoundedChoiceRequest`も2候補未満を拒否する。
従って40条件は40 typed `FactorialRecord` / `EvidenceUseCandidates`であり、
40個の`BoundedChoiceRequest`を無理に作る意味ではない。
`validate_selected_strategy`は受理前に元sourceから候補・要求・custody全体を再生成する。
同じ静的要求への反復応答は区別できず、一回限りの消費leaseを新設しない。

モデルへ渡し得るのは`candidates.request`だけ。分析row、host_record、custody、SHAはhost専用。
要求には固定DEV擬似provenanceがあるが、実source provenanceは投影されない。
`request_id`は既存のcase ordinal / epoch category / goal / budgetによるDEV名で、
実source request ID、self/session/epoch identity、receipt/digestとは別物。
実source IDをrequest IDやinstructionへ混入した場合も負対照で拒否する。

## Phase B: 直交性と事実境界

元saved replay `1e86a714f3ea3374`と既存4 factoryの10 epochに対して、
kind={EXPLAIN_OBSERVED, ASSESS_FORECAST} × cost={0.0,0.5}、importance=2を固定する。
source pinは元replay receiptから求め、各条件でstrict readerと既存gateを通す。
分析器はsource issuerではなく、生成した40行の不変条件を検査する。

同一source/costの20 Goalペアではhost record、custody、候補、statusが一致し、
requestはgoal.kindとそれに対応するrequest IDだけが異なる。
同一source/Goalの20 costペアではRだけが追加される。既存C/M/Wの脱落はない。
positiveなしのcost 0はWのみでDEFER。cost 0.5ではR/WによりREADYとなる。

MATCHは比較済み対象の`entity_label=zombie`だけを支持する。
他対象・属性・World安全・Action成功・報酬へ一般化しない。
MISMATCH followingでは現在のskeleton肯定観測と旧zombie予測の不支持を同時保持する。
UNKNOWN/NO_REVIEWやpositive 0をabsence、安全、予測FALSEに変換しない。
GoalはSource truth、保持Memory、Action authorityを変更しない。処理にはそれらのwrite経路がない。

## Phase C: Goal-fit設計とモデル必要性の停止判定

事実適格性とGoal-fitは別軸とする。適格なstrategyが複数あることは判断能力の証明ではない。
以下は将来評価の候補基準で、今回の選択・採点・生成実行ではない。

| Goal | Goal-fitの評価基準候補 | 許容され得る複数戦略 |
|---|---|---|
| EXPLAIN_OBSERVED | 現在肯定観測の対象・属性を正確に説明し、未観測を留保する。予測との一致を説明する場合は比較範囲を限定する | Cで現在事実を説明、Mで一致した属性だけ説明、Wで不支持部分を留保。Rは具体的未解決問いと情報価値が別途示される場合 |
| ASSESS_FORECAST | 旧予測と現在観測の比較状態・対象・属性・時点を区別する。MISMATCHでは現在肯定を消さず旧予測の不支持を保持する。UNKNOWNを失敗へ変換しない | Mで限定MATCH、Cを使い現在観測から不一致を説明、Wで評価不能部分を留保。Rは予測の未解決属性を識別できる場合 |

将来の評価は「関連事実の網羅」「比較範囲の正確さ」「不確実性の扱い」
「未解決問いへの情報価値」「追加cost」を別々に記録し、単一正答strategyや合成点を強制しない。
事実適格性の失敗と、適格だが目的への説明が不足する場合を分ける。
strategy IDだけでは説明の網羅性を採点できない。特にWは肯定観測を捨てる意味ではなく、
Cも旧予測を肯定する意味ではない。IDへの恣意的な得点付けはしない。

決定的baselineを以下の通り定義する（今回実行しない）。

- 常時W: READYではW。DEFERは要求を作らず保留。根拠不足の留保には合理性があるが、説明網羅性はIDだけでは不明。
- 現在肯定優先: READYでCがあればC、なければW。現在観測説明に適合し得るが、forecast比較を語った証拠にはならない。
- MATCH優先: READYでM、なければC、なければW。比較範囲を守るなら予測評価に適合し得るが、MISMATCH/UNKNOWNの説明能力は未測定。

いずれもDEFERを一択要求にしない。Rの0.5は実測token/latencyや情報価値ではない。
現入力にはGoal別の独立した効用、未解決問い、情報取得結果、対照課題や
説明応答の採点契約がない。上の基準候補だけでは、固定source/cost下の非自明な
Goal判断差を単純baselineから独立に測定できる課題は成立しない。

**MODEL_NECESSITY_UNDETERMINED**。
ここで認知必要性の追究を停止し、モデル選択・生成・判断へ進まない。
将来は独立課題、複数の許容応答、説明採点と情報価値、単純ルールとの対応比較を
先に登録する必要がある。モデル投入・優位性・科学的因果効果の権限は生じない。

## Phase D/E: 実機検証と保存

Python 3.12.3 / Ubuntu 24.04 / WSL2、Windows 11実機でoffline検証する。
新規テストは全40条件、Goal/cost入替、foreign identity/digest/source、request ID/custody漏洩、
NaN/負cost、未許可source改変、MATCH範囲、MISMATCH同時保持、DEFER迂回を扱う。
元選択受理経路への入替拒否テストはprotocol負対照であり、認知判断ではない。

repo外exclusive-new evidence:
`/home/rinsa/verification-evidence/w4-goal-cost-20261023T143500Z`。
82保護対象（元所在と新worktree）、770歴史索引と索引自体、先行7証拠ツリー、
追加10 owner/source paths、直前cognitive証拠ツリーと既存adapterを前後照合する。
元SEM 100 calls / RAW20/40 → SEM36/40は保存原本のまま、再実行・再採点しない。

CI / FULL regression / 実LLM / GPU / Minecraft / 物理Action / OUTCOME /
Memory/S10 / QUALIFICATION / SCIENCEを実行しない。
既存focusedのfake providerやsynthetic outcome単体テストは物理・モデル結果ではない。
実測件数、40条件行列、SHA結果と最終commitはIssue #633と外部reportで報告する。
`[skip ci]`を付け専用ブランチだけへ非force pushし、remote HEAD・3変更パス・投稿本文を読み戻す。

## 実測40条件（10行 × 4条件）

| Case / epoch | positive / review | Explain 0 | Explain 0.5 | Assess 0 | Assess 0.5 |
|---|---|---|---|---|---|
| w4-original-empty / prior | 0 / NO_REVIEW | DEFER: W | READY: R,W | DEFER: W | READY: R,W |
| w4-original-empty / following | 0 / NO_REVIEW | DEFER: W | READY: R,W | DEFER: W | READY: R,W |
| match / prior | 1 / NO_REVIEW | READY: C,W | READY: C,R,W | READY: C,W | READY: C,R,W |
| match / following | 1 / MATCH | READY: C,M,W | READY: C,M,R,W | READY: C,M,W | READY: C,M,R,W |
| mismatch / prior | 1 / NO_REVIEW | READY: C,W | READY: C,R,W | READY: C,W | READY: C,R,W |
| mismatch / following | 1 / MISMATCH | READY: C,W | READY: C,R,W | READY: C,W | READY: C,R,W |
| unknown / prior | 1 / NO_REVIEW | READY: C,W | READY: C,R,W | READY: C,W | READY: C,R,W |
| unknown / following | 0 / UNDETERMINED | DEFER: W | READY: R,W | DEFER: W | READY: R,W |
| synthetic-empty / prior | 0 / NO_REVIEW | DEFER: W | READY: R,W | DEFER: W | READY: R,W |
| synthetic-empty / following | 0 / NO_REVIEW | DEFER: W | READY: R,W | DEFER: W | READY: R,W |

C=現在肯定、M=比較済みMATCH、R=追加証拠proposal、W=不支持主張留保。

実機focused **289 PASS / 0 FAIL / 0 ERROR / 0 SKIP**（新規44 + 既存245）、Ruff / contracts **PASS**。
保護82・歴史770と索引・先行7tree・追加10pathsの前後SHA一致。
判定: **W4_SELF_WORLD_GOAL_COST_ORTHOGONALITY_OFFLINE_DEV_RESULT**。
認知必要性: **MODEL_NECESSITY_UNDETERMINED**。
初回matrixは既存factoryのtests import path不足で停止し、PYTHONPATHにtestsを明示して再実行。
Ruff初回は作業directory指定漏れのE902、正しい独立worktreeで再実行PASS。
いずれも失敗ログを保存し、既存source/coreは修正していない。
