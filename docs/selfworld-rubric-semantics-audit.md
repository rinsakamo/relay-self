# W4 SelfWorld 評価基準・認知判断分離監査（2026-10-23）

判定: `W4_SELF_WORLD_RUBRIC_SEMANTICS_DEV_AUDITED`

`DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`

## 対象と証拠

監査開始HEAD `3e2b04ef0877a1b272a7ee60a43e7e76c80b66bb`。
[RSEE #575](https://github.com/rinsakamo/relay-self/issues/575)、[SelfWorld #633の設計監査](https://github.com/rinsakamo/relay-self/issues/633#issuecomment-6364854121)、Draft #634を読み取り確認。
原SEM証拠 `/home/rinsa/work/w4-selfworld-host-semantic-probe-evidence-20261023` は不変。
派生証拠 `/home/rinsa/work/w4-rubric-semantics-audit-evidence-20261023` はrepo外exclusive-new。
独立ブランチ `dev/w4-rubric-semantics-audit-20261023` に監査器・負対照テスト・本文だけを追加。
元の5対象ファイル、SelfWorld core、ATT、PRD、RelayEngine、renderer、provider、model owner、A/B harnessは変更していない。

`load_sources` は保存済み実W4 strict replayと元の4合成factoryをそのまま再利用する。
`validate_frozen` で固定要求全体（source receipt、型付き要求、rendered body、schedule、rubricを含む）を再生成結果と照合。
監査器は既存 `prepare_w4_offline_cognition_inputs` のATT/PRD再検証を使用し、LLM文からレビューを推測しない。
100行・100呼び出し・402 journal events（warmup20を含む）を読み取り、順序、開始/終了、source epoch、request/response hash、choice、元採点flagを照合した。
予測・現在観測の再生成ではなく、保存sourceのオフライン再構成である。合成4ケースはWorld原証拠ではない。

## 現行契約

- `experiments/self_world_model_ab.py`: `CognitionCase.expected_*` とsynthetic normative rubricが、MISMATCH followingをDEFERとしている。report説明は「missing or discrepant positive evidence calls for DEFER_RECHECK」。
- `adapters/mineflayer/self_world_observation_only_cognition.py::_request_pair`: instructionはobserver-local比較、unobservedはUNKNOWN、World action禁止。選択肢は `INSPECT_SOURCE = Inspect only positively observed source`、`DEFER_RECHECK = Defer claims unsupported by current source`。MISMATCH時の優先順位・INSPECTによる旧予測採用は定義していない。
- `experiments/self_world_host_semantic_probe.py`: SEMは選択された観測とhost reviewをallowlist投影する。instructionとchoicesはRAWから維持し、rubricはケースから継承する。pseudo provenanceにはWorld/Action/Memory source権限がない。
- `src/relay_self/self_world.py`: reviewは元PRDとlater sourceから再検証。MATCH/MISMATCHは比較可能な値に限り、対象/属性未観測等はUNDETERMINED。action_successはNoneであり報酬/Action成否ではない。
- `src/relay_self/relay_engine.py`: 既存BOUNDED→必要時THINK、許可choice IDの検証を所有する。選択IDの解決は予測の真偽証明ではなく、MISMATCH優先順位も追加しない。

rubricの説明とmodel-facing instructionは別のsurfaceである。後者へ前者の優先規則が十分に表現されていないことが今回の曖昧性であり、元rubricそのものを変更する理由にはしない。

## 10 epoch 二軸表

Observation axisは**現在sourceからATTが肯定的に選択した観測**の有無。0はWorld内不存在・安全性を意味しない。
Prediction axisは当該epochのhost-verified review状態。`NO_REVIEW` はレビュー未添付で、必ずしも予測なしではない。priorのMATCH/MISMATCH/UNKNOWNケースにはsource内にforecastがあるが、laterとの照合はまだない。empty両ケースには予測自体がない。
following view自身はforecastを持たなくても、reviewはpriorの予測を参照する。

| # | case / epoch | selected positive数 / label | Prediction axis | 当該view内forecast | review値・理由 |
|---|---|---|---|---|---|
| 0 | w4-original-empty / prior | 0 / 選択なし | NO_REVIEW | なし | — |
| 1 | w4-original-empty / following | 0 / 選択なし | NO_REVIEW | なし | — |
| 2 | match / prior | 1 / zombie | NO_REVIEW | あり | — |
| 3 | match / following | 1 / zombie | MATCH | なし | zombie → zombie; observed_prediction_match |
| 4 | mismatch / prior | 1 / zombie | NO_REVIEW | あり | — |
| 5 | mismatch / following | 1 / skeleton | MISMATCH | なし | zombie → skeleton; observed_prediction_mismatch |
| 6 | unknown / prior | 1 / zombie | NO_REVIEW | あり | — |
| 7 | unknown / following | 0 / 選択なし | UNDETERMINED | なし | zombie → None; target_or_property_unobserved |
| 8 | synthetic-empty / prior | 0 / 選択なし | NO_REVIEW | なし | — |
| 9 | synthetic-empty / following | 0 / 選択なし | NO_REVIEW | なし | — |

NO_REVIEWとUNDETERMINEDは異なる。UNKNOWN followingは旧zombie予測が存在し、`target_or_property_unobserved`のため判定不能であり、予測なしでもMISMATCHでもない。
各行のexact source receipt SHA256、full review（source refs含む）、両arm集計、warmup choiceは派生 `audit.json` に保存した。

## 元rubric対応（正式値は変更なし）

I/DはINSPECT/DEFERの各件数、後半は**元rubric**一致数。各arm/epochの本測定4件、warmup1件は除外。warmupを含む100件全体の照合も実施した。

| # | original expected | RAW I/D; 元一致数 | SEM I/D; 元一致数 |
|---|---|---|---|
| 0 | DEFER_RECHECK | 4/0; 0/4 | 0/4; 4/4 |
| 1 | DEFER_RECHECK | 4/0; 0/4 | 0/4; 4/4 |
| 2 | INSPECT_SOURCE | 4/0; 4/4 | 4/0; 4/4 |
| 3 | INSPECT_SOURCE | 4/0; 4/4 | 4/0; 4/4 |
| 4 | INSPECT_SOURCE | 4/0; 4/4 | 4/0; 4/4 |
| 5 | DEFER_RECHECK | 4/0; 0/4 | 4/0; 0/4 |
| 6 | INSPECT_SOURCE | 4/0; 4/4 | 4/0; 4/4 |
| 7 | DEFER_RECHECK | 4/0; 0/4 | 0/4; 4/4 |
| 8 | DEFER_RECHECK | 4/0; 0/4 | 0/4; 4/4 |
| 9 | DEFER_RECHECK | 0/4; 4/4 | 0/4; 4/4 |

原成績 **RAW 20/40 → SEM 36/40** を保持。原reportのempty false INSPECT 12→0、positive INSPECT 16/16維持も元分類のまま。
MISMATCH followingはRAW・SEMとも4/4 INSPECTで、元rubric一致0/4。再採点した新正答率は作成していない。

## MISMATCHの曖昧性と判断の意味

1. **INSPECTは現在sourceの検査として許容される。** 現在sourceが肯定的に選択したのはskeletonであり、過去予測zombieではない。INSPECTの定義に沿ってskeletonを調べる読みが成立する。ただしchoice IDだけからモデルの内的理由がその読みだったと確定することもできない。
2. **INSPECTだけで旧zombie予測の採用を認定できない。** hostはzombie→skeletonをMISMATCHと確定済み。旧予測はこの比較について現在sourceの支持を得ていない。新観測の検査可否と旧予測を採用できるかは独立であり、旧予測採用を測る出力欄がない。4/4はrubric不一致の事実であり、4/4の断定的な認知判断失敗とは言えない。
3. **UNKNOWN followingのDEFER理由。** 現在の選択肯定観測が0で、旧zombie予測への観測的支持も確定しないため、未支持のclaimを保留して再確認する意味に合う。これはWorldにzombieがいない、予測が間違った、のいずれも意味しない。
4. **positive MATCHでINSPECT維持の理由。** 現在のzombieはsourceで選択され、旧zombie予測との比較もMATCH。現在sourceを検査する選択と、当該label予測が限定的に支持されることは整合する。一般的予測能力、永続的World法則、Action成功を支持しない。
5. **二択の情報損失。** MISMATCHではskeletonをinspectすることとzombie claimをdeferすることを同時に行える。単一IDは「観測利用の可否」「どのclaimを保留したか」「過去予測への依存」「優先した規則」を失う。DEFERでも正当なskeletonを捨てたかは分からず、INSPECTでも旧zombieを採用したかは分からない。モデル内的認知失敗の有無はこのarchiveだけでは同定不能。

## 既存RelayEngineを維持する設計比較

| 観点 | 案A: 判断を2つに分離 | 案B: 単一BOUNDED＋優先規則 |
|---|---|---|
| 意味 | 現在sourceの検査可否と、過去予測への依存可否を別request/choiceで表す | MISMATCHなら旧予測claimの保留を優先、とinstruction・rubric双方に一般規則を定義 |
| 情報 | inspect可＋旧予測非採用を両立して記録。NO_REVIEW/UNDETERMINEDはhost状態として別保持 | 単一choice自体ではinspect可の情報が消える。hostの二軸side dataを併記して損失を可視化 |
| 認知コスト | LLMへ2問なら最大2倍のBOUNDED呼出と各問THINKの可能性。事実照合をhostで行えばその再推論は不要 | 1問の呼出数を維持できるが、優先規則を理解する負担と表現長が増える。時間/tokenの優劣は未測定 |
| API整合 | 既存BoundedChoiceRequestを同じRelayEngineへ2回渡し、source/epochと各結果を外部で結ぶ。coreに第二の機構を作らない | 既存1 request/1 choice形式を維持。変更は将来DEV surfaceとrubricだけ |
| 誤答の曖昧性 | 軸別に判定可能。ただしforecastなしと判定不能を単なるNOへ潰さず、hostの4状態を保持 | 明示規則への手続的不一致は評価できるが、DEFERから観測理解の保持や旧予測不採用を個別認定できない |
| 制約 | 二問目がhost reviewの丸写しなら認知実験として弱い | 「MISMATCH→DEFER」を覚えさせただけでは認知改善の証拠にならない |

**hostが確定した事実をLLMに再認定させる必要はない。** ATT選択、source binding、PRD比較は既存hostのまま保持し、LLMの判断で上書きしない。製品上の事実gateなら二軸をhostで返すだけで足りる。LLMを用いる理由があるのは、それらを前提に「何を検査するか」「どの仮説に依存せず説明/計画するか」という別の認知利用を評価するときである。
案Aを次期DEV設計の優先候補とするが、host比較を再回答する2問だけでは実験価値が不足する。案Bは優先順位遵守試験として成立しても、両軸理解の代用にはならない。

## 最小の次期DEV実験案（未確定・未実行）

まずLLMなしで、固定sourceに対するhost二軸出力と、2つの既存BOUNDED requestへのsource/epoch結合を検証する。次の契約を事前登録してから、必要性を判断する。

- source inspection問: 現在の肯定観測を使うか保留するか。MISMATCHでもskeleton sourceを保持する。空観測で不存在を主張しない。
- forecast reliance問: host reviewを前提に、過去予測を現在の判断の根拠として用いるか保留するか。MATCHは当該observableに限定、MISMATCH/UNDETERMINEDは依存保留。NO_REVIEWは独立host状態で保持し、比較不能と混同しない。
- 成功要件は**MISMATCHで正当な新観測保持＋旧予測不採用**。positive MATCHとpositive priorを含め「いつでもDEFER」を負対照で失格にする。empty、UNKNOWN、label反転を使い、ケース名やzombie/skeleton単語の暗記と規則適用を区別する。
- 実LLMを必要とする場合のみ、案A/案Bのinstruction/rubric、host gate、source refs、正答条件、repeat/warmup/budget、再試行方針、モデル/runtime条件を新しい独立DEV preregistrationで固定する。元100呼出とは別の実験であり、元成績へ合算しない。
- 予測/観測の事実正答の教え込みは改善と呼ばない。曖昧性解消と選択表現の検証、実際の認知利用、効率を別に報告する。条件確定まで実LLM試験は行わない。

## 検証と境界

Python **3.12.3** focused: **175 PASS / 0 FAIL / 0 ERROR / 0 SKIP**（追加16件を含む6ファイル）。Ruff **PASS**、repository contracts **PASS**。
検証の具体的結果とSHAはrepo外 `verification.json` / `integrity-before.json` / `integrity-after.json` / JUnitに保存する。
新規監査器はprovider/RelayEngineを呼ばず、出力先も受け取らない読み取り専用関数。保存は外部driverがexclusive-newで実施。
追加テストはempty代替fixtureのfollowingが既定zombieになっていたため1件失敗。`later_kind='missing'` は `target_before=False` の場合には適用されず、2回目も同じ1件が失敗した。既存fixture factoryは不変とし、当該テスト用のraw observationだけを両epochともemptyにした。両失敗・診断ログを保持し、修正後focusedを再実行した。
82保護対象、770歴史索引と索引自体、原SEM全60ファイル、先行model-only/A-B/factorial/neutral原証拠の前後一致を確認した。
CI・FULL・新規実LLM推論・GPU・Minecraft・Action・OUTCOME・S10・Memory・SCIENCEはすべて実施0。
PR #634はHEAD `f0751b915411e89f1d3dffe941461a308fcf2512` のDraft/open/unmergedを維持し、更新しない。
この監査はDEVの評価意味論を扱い、物理資格・科学的効果・PR統合PASSへ昇格しない。
