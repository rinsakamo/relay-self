# L-BCG H9b — 実Minecraft 8 World DEV経験予測結果

**8 World原本・凍結境界・採点監査成立。線形候補はCHEAP thresholdと同等、CHEAP globalのMAEが小さい。**

branch `dev/l-bcg-conditional-motion-shadow-20261101`。実行HEAD `5a29da666f3692c02dbdb03ed0694ce088f124de`。継続grant [#431](https://github.com/rinsakamo/relay-self/issues/431#issuecomment-6552384315)、Draft [#656](https://github.com/rinsakamo/relay-self/pull/656)、Self統合 [#537](https://github.com/rinsakamo/relay-self/issues/537)。

新規独立World **8 / 成功8 / 失敗0 / retry0**。元Action/S16各8、各World各1。順序・距離・用途を維持。追加Action/native probe/provider/model/Learning/Memory/S10/S11更新は各0。既存H5/H8/H9a原本はFIT/EVALに不使用。旧H9a pair REJECTEDは不変。

## 固定と凍結

- [protocol](protocol.json) raw SHA `4aad68c2ae4ccd8b7ca0e8970376fc1ab9d5efcca89621bc743eb4fdb8f1a73e`。World1前にexclusive保存。
- [凍結モデル](frozen-model.json) raw SHA `8d649801d565f729868bc2933cabd68bed099470f6bcd72a052e327573ea9306`。
- [凍結境界](frozen-model.boundary.json): `2026-11-01T08:42:55.505096+00:00`。FIT4件の各独立監査完了後、EVAL4件の宣言・開始前。EVAL markerはすべて凍結SHAに結合。
- global `0.08026498631431511` m。threshold（元S42 <3m）A `0.09628337111966934` / B `0.06424660150896089` m。
- linear `y = 0.09628337111966934 + (-0.021357846407138965) * (S42 - 2.0)`。FIT4原本だけから凍結。評価は保存係数をdeserializeし、fit APIは不使用。FIT整合の数値検査は行うが再fit・モデル書換えはない。

## 各Worldの元原本

全World元L0 `WAIT → MOVE_AWAY → WAIT`、元Action/S16各1、native距離は要求と一致。下表のseqはevent/probe順。

|Slot|用途|元S42 m|Paper代理変位 m|元native event/probe|Action ID|S16 before/after|
|---|---|---:|---:|---|---|---|
|A-F1|FIT|2.0|0.128320140730378|8/9 → 20/21 → 56/57|s49-native-move-20|22/30|
|B-F1|FIT|3.5|0.06424660150896067|7/9 → 19/20 → 55/56|s49-native-move-19|22/30|
|B-F2|FIT|3.5|0.06424660150896111|7/9 → 18/19 → 53/54|s49-native-move-18|21/29|
|A-F2|FIT|2.0|0.06424660150896067|21/22 → 32/33 → 66/67|s49-native-move-32|34/41|
|B-E1|EVAL|3.5|0.01475441320763693|7/8 → 19/20 → 54/55|s49-native-move-19|22/30|
|A-E1|EVAL|2.0|0.06424660150896067|7/9 → 19/20 → 54/55|s49-native-move-19|22/29|
|A-E2|EVAL|2.0|0.064246601508961|8/9 → 19/20 → 55/56|s49-native-move-19|22/29|
|B-E2|EVAL|3.5|0.06709170283354737|8/9 → 19/20 → 56/57|s49-native-move-19|22/30|

## EVAL4の固定予測・絶対誤差

単位m。thresholdとlinearは全4件で同値。EVAL outcomeは採点だけに使用。

|Slot|実測代理|global予測|threshold/linear予測|global絶対誤差|threshold/linear絶対誤差|
|---|---:|---:|---:|---:|---:|
|B-E1|0.01475441320763693|0.08026498631431511|0.06424660150896089|0.06551057310667818|0.04949218830132396|
|A-E1|0.06424660150896067|0.08026498631431511|0.09628337111966934|0.016018384805354446|0.03203676961070867|
|A-E2|0.064246601508961|0.08026498631431511|0.09628337111966934|0.016018384805354113|0.03203676961070834|
|B-E2|0.06709170283354737|0.08026498631431511|0.06424660150896089|0.013173283480767739|0.0028451013245864853|

|予測器|EVAL MAE m|
|---|---:|
|CHEAP global|0.02768015654953862|
|CHEAP threshold|0.029102707211831863|
|DEV linear|0.029102707211831863|

|条件|global MAE m|threshold/linear MAE m|
|---|---:|---:|
|A (2.0m)|0.01601838480535428|0.032036769610708504|
|B (3.5m)|0.03934192829372296|0.026168644812955222|

**判定 `EQUIVALENT_WITHIN_1E-9_M`**。今回の未使用4 Worldに固定予測を適用し採点できたが、条件付き線形候補の優位は確認されなかった。globalは線形より約0.0014225506622932427m小さいMAE。A-F1の代理変位は同じA条件のもう1件と異なり、2条件・FIT各2件だけの平均は変動の影響を受ける。距離による因果効果や、その変動の原因は推定しない。

## 原本・runtime・cleanup監査

各 `worlds/<slot>/predeclared.json` と raw SHA、`run1/WORLD_ATTEMPT_STARTED.json` をWorld開始前保存。実行環境HEAD・事前資材SHA・protocol SHA・slot/role・frozen SHA・UTC順を照合。元S7受信/送信、元S16、H8 preaction source、Paper全ログ/8 tick prefix、packet原本、全native command、runtime設定原本を保存し、別processのH8監査を各Worldで実施。host reportと原本を分離。`original-sha256.json`全項目再照合PASS。

8 session / 8 Paper World UUID / 8 report原本SHAは相互独立。各Worldは新しいTemporaryDirectoryで作成し、既存World再使用なし。各runのNode/Java exitは0/0、全所有子PID消滅、World削除、port25565再bind PASS。詳細は [最終原本summary](postflight/final-source-summary.json) と各 `independent-audit.json`。

固定critical runtime raw SHA:

|資材|SHA256|
|---|---|
|server|`8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e`|
|plugin|`405657013fa315d76aab3730c6324b3583f9b30facf9233ef0b88fda9026585a`|
|config|`2fd8f5bac2fea7fe857b1e7712a6979a2b76b78f626c374af7fbc7fee44e72d0`|

`server.properties`は各Worldの原本raw SHAをruntime manifestとoriginal manifestに照合。World間では生成日時の2行目だけ相違し、その他の全byte一致。Paper jar/plugin jar/RelayMetabolismDev configは上記raw SHA一致。各runの全補助runtime manifestも保存しており、全manifestの同一性や外部TCP認証は主張しない。Paper pluginは既存 `ACTIVE_METABOLISM_NOT_PASSIVE` profile。Minecraft foodはM energyに転用しない。

|Slot|session|Paper World UUID|server.properties raw SHA|
|---|---|---|---|
|A-F1|b7ee73fd-24a0-41ae-afab-143c9533a93e|443cf647-6d6e-4110-a45f-5d241d49d882|`93c88afbe37c57511edcbbd0f397795891f4207170ba4f68d8f6f73eb9bba1ba`|
|B-F1|b5078125-bdce-473a-8eac-c335cef6407c|85754a10-36f4-4a7b-b949-380ec341dc85|`8aaa4e451e1b4752d5c08d278d09d93cbaa10c16c31f60ea80639a6b03a506d6`|
|B-F2|11dfa9f7-b999-4123-af53-54b7e8c22e85|0eb870fb-5539-4ecc-a3fa-3d5e5a9804be|`08a79c403c367878988e1d6f6c8f96e37182e2b88faf3d34a3c4bf9aa72a00e1`|
|A-F2|d7ec71ce-0e1e-45ae-ac4f-f08f83440b75|948fe828-184b-4aea-8a9c-45aa12d214dd|`d36959979c1c6b2bc7495a253c83f4d213bd8f50eae6c5d9c7952ed4f9023be6`|
|B-E1|a1bf8e67-c36f-4394-b20e-e10a5905c7bc|20b400eb-915b-473e-a9b3-e5df29ad3f79|`e7c9a856d4c7630ddbc8b00041cf5443dd24c8ad6f4c968e060deb15d47cb579`|
|A-E1|05d19d97-7e46-41dd-84d8-95fa8ce3fd72|dbec9d82-c173-45d8-ab3f-60cebdced7fc|`9a7de55f535a78e82f8b3f31cff60c6b1cd5aa6f0fc4ab66b6c694ffd652c64f`|
|A-E2|59b18385-f1e3-4e89-9673-c29baf38447c|2c175120-b08c-4e43-8149-d70a5c19b358|`6335eada8c4a2bb48c140ba12027e1d05bfa0da13279a8f98b9d37d6920b533b`|
|B-E2|65a09a60-77dd-49d1-961a-f0ecd806bdaf|f424aa25-03fb-4985-81ea-b4036e22c764|`b9ba6adb2b21a485c208bc8d53e917986ed3f644b814599513a8a9c0f9f6eb62`|

## 検証と証拠上限

World前 Python3.12 focused/周辺298 PASS、H9b最終35 PASS。周辺初回214 PASS/5 FAIL（javac PATH欠落）は原ログ保持、既存JDK21のcompilerをPATHに追加し該当群12 PASS。World後 focused＋周辺 **375 PASS**、公開原本コピーの再採点も同一結果。結果は [postflight](postflight/focused-regression.log)。Ruff/compileall/contractsと変更コードdiff-check PASS。原本ログの既存末尾空白・CR等は保持し、証拠ディレクトリだけ `-text` でGit改行変換を無効化。実行HEADの関連6 CIすべてSUCCESS、[H9b focused](https://github.com/rinsakamo/relay-self/actions/runs/41289242220) / [L-BCG full](https://github.com/rinsakamo/relay-self/actions/runs/41289242209)。報告HEADの最終CIはGitHub結果コメントに記録。

元S7はNode stdout JSONL、Paperは既存sole collectorのログ。独立readbackは保存された元原本の相関監査であり、外部Minecraft TCP認証・全tick/subtickの実効clear認証ではない。指標は `DEV_REPORTED_INPUT_OFF_SAMPLED_DISPLACEMENT_M`、正式MotorOutcomeの新規生成はない。

`LEARNED_L1_ATTENTION=DEFER_UNKNOWN / GOAL_UNDETERMINED / EFFECTIVE_CLEAR_NOT_ATTESTED / QUALIFIED_TRAINING_WORLDS=0 / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`。敵距離をGoal残距離に流用しない。L0/sole executor/Action判断は不変更。DEV FIT/EVALは正式training/heldout資格ではなく、この4件の誤差だけで因果的改善・汎化・L1認知能力獲得・Action改善を証明しない。

最終分類 **`H9B_8_WORLD_DEV_PROXY_FIT_EVAL_ONLY / CHEAP_THRESHOLD_EQUIVALENT / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`**。
