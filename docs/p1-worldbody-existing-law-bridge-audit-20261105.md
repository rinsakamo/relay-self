# P1 × WorldBody — 既存疲労法則再利用の監査・統合契約（2026-11-05）

> **DOCS-ONLY / IMPLEMENTATION NOT RUN / DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.** 本文は既存repoを読んだ後の差分監査と次の実装受入条件。現行 #738 の成功・失敗World原本、main、P1 owner、R/V資格、S49 Action権限は変更しない。新しい実World/LLM実行権限を発生させない。

## 参照した正本（読了した実装）

- P1 owner: [Draft #626](https://github.com/rinsakamo/relay-self/pull/626), exact `0ab76b4e46efd914877e543a65de58b6cfc71326`; `experiments/fatigue_p1.py`, `experiments/fatigue_p1_boundary.py`, `docs/p1-fatigue-rest-recovery.md` を読取。P1 HEADの offline CI #38883095344 成功。**P1は現在Pythonの決定論的virtual Body評価器であり、Paperでの独立した実装済み物理法則ではない。**
- WorldBody DEV: [Draft #738](https://github.com/rinsakamo/relay-self/pull/738), exact `86f5a0342d288af3916d7527e0d9bb95a7b221ae`; Paper `RelayWorldBodyDev.java`, `worldbody_direct_selfbody.py`, original S49 runnerを読取。#42011766214 と #42011801141 は個別の旧World法則によるDEV実World成功で、P1準拠の成功ではない。
- Owner境界: S #537 / S50 #627 / M #616 / R #575 / V #619 / Unified v0.5 #717。#738/baseにもmainにも `experiments/fatigue_p1.py` は**存在しない**。P1は別未merge branch上にあり、無断コピーやP1/Mスタックの独立mergeをしない。

## 既存仕様対照（同じ法則ではない）

| 量・条件 | P1 #626 (standard, enabled=trueの候補) | #738 DEV Paper |
|---|---|---|
| 身体状態 | [0,1] fatigue、profile SHAで固定 | Paper内のprivate fatigue [0,1] |
| MOVE蓄積 | 実観測path blocks × `0.04` | horizontal event distance × `2.0` |
| FIGHT蓄積 | 観測FIGHT events × `0.20` | 未実装 |
| WAIT回復 | source-verified **full-tick inactive** WAIT × `0.10` | `horizontalThisTick < 0.005` で `0.003/tick` 回復 |
| 能力低下 | `max(0.20, 1 - 0.70 × fatigue)` 、prospective per-tick cap | fatigue≥0.25で歩速等を切替、低下中水平eventへ×0.35 |
| 回復閾値 | fatigueに連続的に依存 | fatigue≤0.05でnormal復帰 |
| オフ/初期 | default `enabled=false`, `initial=0` | DEV opt-inのみ |

係数値が違うだけではない。P1では **blocked MOVE / displacement=0 は MOVE のまま、WAIT回復しない**。#738 Javaはmotor eventが無いtickを回復としているので、Action lifecycleを見ないままP1へ流用すると偽WAITを作る危険がある。P1の休息は物理的に観測されたWAITによる自然回復であって、Selfが回復係数を書き込むことではない。

## 統合の単一責任・不変条件

1. **法則の正本 = P1**。`FatigueProfile`, `FatigueFrame`, `advance`, `capability`, `observe` とP1-B `preflight/reconcile/SourceBoundTick` の原義を保持。Javaへ移す場合も新係数や閾値を創作せず、元Python pinned HEADの同入力tick列と数値的parityを固定fixtureで検査する。P1はunmerged M ancestryに載るため、ownerレビュー・依存解決なしに源ファイルを他branchへコピー/統合しない。
2. **物理権威 = World/Body**。World開始時に明示し固定したprofileのみが疲労実状態を遷移させる。Self/L0/L1/L2/REST選択はrate、capacity、impairment、true fatigueを書換え・注入できない。Paperでの実際の運動能力制限は、original S49の単一Action issuerの外で新しいActionを発行せず、World側の実制約として作用する。
3. **活動分類 = true World tick**。連続World tick、真正MOVE/FIGHT/WAITの相互排他分類、MOVE実path、FIGHT events、S Action/effector/OUTCOME、full-tick WAIT witnessをS/Rで相関。コマンドが無い、probeが静止、最終位置差0、blocked MOVEという理由だけでWAITとみなさない。証拠欠損時はUNKNOWN/拒否。
4. **予測制限と実結果を分離**。P1-B capはSに対するprospective physical constraintでありgrantではない。Paper `PlayerMoveEvent` のdestination変更だけを成功とせず、元S16でreal displacement/settlingを観測。cap超過・no-progress・client correction差は原本保持しfail-closed。S49 owner以外の発行経路は禁止。
5. **SelfBodyは不完全な読み取りview**。Selfはnative movement/outcomeと正当な有限・量子化センサーのみ観測。World内のtrue fatigue、profile coefficients、Paper private truth logを読み込まない。疲労の推定/予測/学習はbeliefとして別型にし、World lawへfeedbackしない。
6. **REST/WAIT用語の調停**。P1 #626にphysical REST Activity/Actionはない。#717の認知上のREST目的を将来採るとしても身体側はsource-verified WAITとして扱い、REST発行で回復をクレジットしない。P1文書の『RESTは独立Intentではない』と#717の『REST Intent』の差はS/P1 ownerレビュー対象。無断でどちらかを物理仕様に昇格しない。
7. **Mと分離**。WAIT中もM0.2 BASALは継続。P1 Fatigue、Minecraft hunger/exhaustion/HP、研究用Energy、計算コストを合算・二重請求・REST免除しない。

## 次の実装スライス（順番厳守）

### A. OFFLINE source & dependency audit

- P1 exact source, branch ancestry, pytest/CI、#738 JVM bridge/World runner/Java event lifecyclesを比較してowner差分と受理可能な移植方法を確定。最初から新規fatigue engineを書かない。
- 既存P1 Pythonに固定入力tick列を供給し、累積・回復・cap・センサーのexpected traceを保存。profile SHAと出典を明示する。P1 `enabled=false` 対照も含める。

### B. Java World bridge（P1 parity優先）

- #738の専用DEV物理モジュールを、P1 profileのimmutability・per-World-tick state・WAIT/MOVE/FIGHT・continuous capabilityと一致させる。係数選択のSelf用APIを増やさない。
- 移動中でもイベント間の静止tickを安易にWAIT扱いしない。S/R owner由来の真正full-tick idle witnessが接続できない段階は **P1_PHYSICAL_WAIT_UNATTESTED** でブロックする。偽のREST回復よりDEV未成立を優先。
- 原P1では標準MOVE 0.04/block、WAIT 0.10/tickなので、短いMOVEの間に真正WAITが挟まると疲労低下が観測されない可能性がある。成功させるために標準rateやthresholdを書き換えず、運動条件と観測時間を事前固定する。

### C. Native observation / limited policy

- 元S49 ActionSupervisor → S16 OUTCOME → fresh correlated Present → SelfBody の系譜を維持。感覚化の先行実装は強制しない。
- P1に基づくphysical constraintの結果をS16で測り、Bodyの観測低下 → native L0側のWAIT/休息選択 → World側回復 → **第三の元S49 MOVE/S16で再観測**、を最後に検証。第三MOVEのgrant/STOP安定性は別ゲート。
- 回復はWorldのルールで起き、Selfが知り得るのは回復前後のnative実効差に限る。

## 最低限の負対照 / DoD

| Case | 必須結果 |
|---|---|
| P1 standard/Fatigue OFFの同tick列 | 原P1とJava計算のtrace一致、OFFで能力低下ゼロ |
| consecutive observed MOVE, path length, FIGHT | 原P1の0.04/block, 0.20/eventの増分一致 |
| genuine full-tick WAIT | 0.10/tickを上限clipで回復、M BASAL継続 |
| blocked MOVE / command absent only / missing full-tick witness | WAIT回復を作らずUNKNOWN/拒否 |
| tick gap / replay / foreign session / profile SHA変更 / old S16 / stale probe | fail-closed、truthをSelfへ渡さない |
| cap applied but client native output unchanged | 実身体能力低下を未成立に分類 |
| third post-WAIT MOVE が無い | SELF_POST_REST_MOTOR_CONFIRMATION_NOT_RUN |

## 結論 / 証拠上限

**#738のlegacy固定法則 (2.0/m, 0.003/tick, thresholdと0.35固定制限) をP1と呼んではならない。** 旧#738の2実World PASSは『別のWorld法則による物理的低下→SelfBodyの低下観測→L0 REST→World回復』に限って保持する。この文書の追加だけではP1準拠のWorldBodyは実装されず、実World/R資格/V科学は未実施。最初に必要なのは新法則ではなく**既存P1 ownerとPaper実行境界の接続**である。
