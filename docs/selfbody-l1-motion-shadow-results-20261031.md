# Issue #653 SelfBody → L1 shadow 実World DEV結果

**DEV_LIVE_L1_MOTION_SHADOW_ORIGINAL_AUDIT_PASS / CHEAP_EQUIVALENT**。
実行コードHEAD `ba83256a80370878748316e145855bf928f1aaac`。
新規World **1回 / PASS 1 / FAIL 0 / retry 0**。
PR #654の隔離branchで実施し、mainと過去原本は維持した。

## CI・FAST修正と検証

最新CIの2 FAILは、shadowが`prior_native_ref`に`present:`を要求した一方、
元`BodyObservation.source_ref`が`native-probe:<session>:<seq>:<request>`を
返していた不一致。元ownerの形式を使い、同一session・現在より古い非負seq・
非空requestを検証するよう修正。NaN/Infも拒否する。
テストのchoice書換えを除き、同じtyped probeから元selectorが返すchoiceを使う。
正例とforeign/future/malformed source、非有限sampleの負例を追加した。

全FASTで発見した既存互換性不備も修正した。W4 subclassは親が渡す既存
`native_receipt`を同じ元sessionへ転送する。reader・Action権限は追加しない。
旧W4 v2承認manifest・歴史blobは変更しない。歴史承認原本を検証したうえで、
Issue指定の経路B親HEAD `e6be517f0b25dcfddbeb035ccef7830705989efe` から
既に導入済みのS7記録/S15 probe相関付け4ファイルだけを厳密照合する。
残り15ファイルの現行保護と、全19ファイルの変造負例は維持した。
この比較は新しいW4承認・資格を付与するものではない。

- FAST全65ファイルを4分割再実行: **1,710 PASS / 0 FAIL / 0 SKIP**。
- L1/source/L10 focused: **142 PASS**。
- 周辺修正確認: **309 PASS**、別途完全JDK21でnative OS custody **12 PASS**。
- Node22 packet witness: **6 PASS**。Ruff、compile、repository contracts PASS。
- 実行HEAD CI: [L1 + W4 regression](https://github.com/rinsakamo/relay-self/actions/runs/41210385609)、
  [経路A](https://github.com/rinsakamo/relay-self/actions/runs/41210385696)、
  [経路B](https://github.com/rinsakamo/relay-self/actions/runs/41210385652) すべてSUCCESS。

初回CI 2 FAIL、全FAST初回84 FAIL/1,625 PASS、および修正途中のFAILログも保存。
native OS検証でJDK未指定だった5 FAILは完全JDK21指定で全12件PASSにした。
FAIL原本を上書きせず、期待値・source鮮度・権限境界は緩和しない。

## 新規実Worldと注意候補の比較

| 項目 | 実測結果 |
| --- | --- |
| 元L0 event→probe / 判断 | 7→9 WAIT、18→19 MOVE_AWAY、55→56 WAIT |
| 実Action / S15 clear ACK / S16 OUTCOME | 1 / 1 / 1 |
| S16 before→after | native seq 21→29 |
| 同一session次epochの元probe | seq 56、元第3 WAIT完了後にshadow記録 |
| Paper WAIT/INPUT callback | 各8、連続tick 251–258 |
| 報告入力OFFでsample変位あり | tick 251、252、253 |
| 経験なし | ABSTAIN_NO_PRIOR_MOTION_EVIDENCE |
| 経験あり | RECHECK_SAMPLED_POST_CLEAR_MOTION |
| 同情報の単純1ビット規則 | 経験ありと一致、CHEAP_EQUIVALENT |
| 追加probe / Action / model call | 0 / 0 / 0 |
| full S7受信 / 送信 | 57行 / 14行、旧prefix byte一致 |
| Node motion write return / player_input | 34 / 0 |
| Node footer | TRACE_END、complete=true、lost=false |
| cleanup | Node/Java exit0、所有PID消滅、World削除、port再bind PASS |

session `3da31d96-95bf-49db-ac5e-5fabe8f35b38`、
World `0dcf8a5d-b8da-4863-bc0d-641d0abc1260`、
Action `s49-native-move-18`。
Paper provisional prefix **142218 bytes**、SHA256
`38f2857d43f9e744edf57c6f1b31903eac17950b6e9fdc93aa3e889bf3a4fc37`。
元typed S16/SelfBody/Worldと元L0 choiceの同一性は実行中ownerで検証。
保存JSONからtyped authorityを復元したとは主張しない。

元L0の選択、閾値、issuer、S16/STOP/clear ownerは変更していない。
経験あり/なしは同一Worldの同じ元判断後の非実行注意候補比較であり、
別のAction armや学習済みpolicyではない。注意資源を実際に割当てる機能や
L1独自優位性の実証も行っていない。

## 独立原本監査・保存

別processの `tools/selfbody_l1_shadow_readback.py` が、元経路B監査、
全native/Paper/Node原本、S16、S7 receipt、prefix一致、cleanupを再検証し、
PaperからOFF-motion tickと1ビット結果を独立計算してshadow記録と照合。PASS。
元経路B14件とshadow7件の変造負例 **21件すべて拒否**。
変造は隔離コピーだけ。過去原本 **6,784ファイルすべてSHA一致**、main不変。

[Git保存証拠](evidence/issue653-l1-motion-shadow-20261031/) /
[独立原本監査](evidence/issue653-l1-motion-shadow-20261031/run1/independent-l1-original-readback.json) /
[負例結果](evidence/issue653-l1-motion-shadow-20261031/negative-original-readback.json) /
[SHA256SUMS](evidence/issue653-l1-motion-shadow-20261031/SHA256SUMS)。
外部原本root `/home/rinsa/work/issue653-l1-shadow-evidence-20261031/`。
変造入力全コピーと過去原本の全SHA inventoryは外部rootに保持。

## 残課題と判定上限

**Goal UNDETERMINED / P1 WAIT=0 / L10=0 / S10=0 / S11=0 /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**。
判断時の前Action窓は **PROVISIONAL_PAPER_ONLY**。
完全Node/Paper監査は終了後の別ゲートであり、判断時の証拠を遡及昇格しない。
effective clear tick、全tick入力idle、物理安定、Paper/Node時計同期はNOT_ATTESTED。
単純1ビット規則と同じ結果なので、正式学習・知能・L1の固有価値は主張しない。
独立Goal原本や複数の資格ある訓練例を揃える学習採用は別の未着手課題。
