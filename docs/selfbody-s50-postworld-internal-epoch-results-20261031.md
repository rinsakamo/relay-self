# SelfBody × S50 World終了後の内部認知epoch 実World DEV結果

2026-10-31、経路Aを新規World **1回**で実測し、
`DEV_POSTWORLD_INTERNAL_EPOCH_PRIOR_EXPERIENCE_READ_PASS`。

- Branch: `dev/selfbody-s50-postworld-internal-epoch-20261031`
- 実行exact HEAD: `9e9bcb98b50228aa81c9dbd7aa99a9eb0e4f13d2`。開始HEADは指定`afa69c588125dd05881b5c56d56fee4beff0e90c`とremote/PR #649で一致。
- SelfBody #632/#647、S50 #627/#645/#646、L23 #640、#648/#649の最新ownerを照合。
- 最小修正: prior OUTCOMEのsession一致検査、前後epoch/現在outcome診断、負対照5件。
- FAST: 基準115 PASS、追加後120 PASS、S50/L23原本38 PASS、Python計158 PASS。Node22 packet6 PASS。Ruff/compileall/contracts PASS。
- 前処理launcherのPath型誤り1件をPREWORLD_BLOCKED（Java/Node/World0）として保存。修正後新規World1回、World FAIL0、retry0。

## 実Actionとsource

- session: `fdc7213d-ba3f-4608-9e09-18472d6971b4`
- Action: `s49-native-move-18`、MOVE_BACKWARD、**1件**、実測変位0.7342911432182304 m。
- native before / dispatch / clear / after: **21 / 22 / 27 / 29**。同一session/Action、before-after request ID、provenance照合PASS。
- S15 clear ACK applied、S16 OUTCOME / observed_execution / executed。
- 元typed closure→既存projection→SelfBodyView生成PASS。S16/Body/source identityを実行中assert。
- 同じPythonプロセスで元SelfBodyViewを保持したMotionCompanion結合PASS。
- Paper World: `120eb29f-9a47-4c45-9f1e-dafa161fdbb7`。
- WAIT_TICK / INPUT_TICK: **253–260、各8件連続**。7入力は全サンプルOFF、INPUT_EVENT0。
- tick253/254/255の変位: 0.049492188301323736 / 0.009543604920851934 / 0.00521080828678544 m。256–260は各0。
- Node: back ON→clear全OFF→shutdown clear全OFF。physics242連続サンプル。
- packet write-return: player_input0 / position22 / position_look1 / flying1 / look0 / entity_action0。
- sidecar269記録＋TRACE_END、complete=true / lost=false。独立CLI2本・原本再読PASS。
- Node exit0、Java exit0を既存ownerの実returncodeから取得。

## 新しい内部epochで実際に参照した内容

- 前epoch: `s49-original-after-29`
- 新epoch: `internal-after-closed-world-29-s49-native-move-18`
- 前Action: `s49-native-move-18`
- native source: `native-probe:fdc7213d-ba3f-4608-9e09-18472d6971b4:29:s15:fdc7213d-ba3f-4608-9e09-18472d6971b4:s49-native-move-18:after`
- Paper原本SHA256: `783740601bb231fe4d4569d6f2db442cc7914d6f9248a0797b03ad413a509f58`
- World IDは上記、観測8サンプル、入力OFF中の変位tick **253,254,255**を元companionから実際に1回read。
- lease: INTERNAL_EPOCH_PRIOR_EXPERIENCE_READ_ONCE / internal_epoch_reads=1。二重consume拒否はFASTで確認。
- 新Body.observation=None / Body.outcome=None / World.observation=None、現在位置UNKNOWN。
- 過去経験を現在位置や新Action結果へ昇格しない。typed原本の真正性は実行中identity検査、独立監査は保存診断と原本対応の検査。

## 環境・独立監査・cleanup

Python3.12.3 / Node22.22.2 / Java21.0.12.1 / Mineflayer4.39.0 / Paper1.21.8 build60。
既存成功World3の座標・引数・JAR・config・Node依存を引継ぎ、opt-inを追加。
完全M0.2設定はexhaustionへの**能動介入**として維持。

- server SHA256: `8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e`
- plugin SHA256: `405657013fa315d76aab3730c6324b3583f9b30facf9233ef0b88fda9026585a`
- config SHA256: `2fd8f5bac2fea7fe857b1e7712a6979a2b76b78f626c374af7fbc7fee44e72d0`

別PythonプロセスでS7/S16/事前plan/Paper/NodeからL22/L23/S50を再計算し、reportとの一致、内部epochのAction/native/SHA/World/tick参照を照合PASS。
原本byteコピーへの欠損・TRACE_END欠落・別Worldの5負対照はすべて拒否。
内部epoch参照後の最終cleanup: runner0、所有PID全消滅、使い捨てWorld削除、port25565再bind PASS。他レーンprocessは終了していない。
前回成功・失敗原本6650ファイルのmanifest照合で変更0。

外部全文原本: `/home/rinsa/work/selfbody-postworld-epoch-evidence-20261031/`。
[Git保存証拠](evidence/selfbody-postworld-epoch-20261031/) / [独立監査](evidence/selfbody-postworld-epoch-20261031/run1/independent-original-readback.json) / [SHA256SUMS](evidence/selfbody-postworld-epoch-20261031/SHA256SUMS)。

## 判定上限と残る最小課題

内部epoch以降: NEW_NATIVE_PRESENT=0 / NEW_L0_DECISION=0 / NEW_ACTION=0 / MODEL_CALLS=0 / LEARNING_UPDATES=0。
P1_WAIT=0 / L10_PAIRS=0 / S10_UPDATES=0 / S11_GRANTS=0。
EFFECTIVE_CLIENT_CLEAR_TICK=NOT_ATTESTED / FULL_TICK_INPUT_COVERAGE=NOT_ATTESTED /
PHYSICAL_STABILITY=UNPROVEN / GOAL=UNDETERMINED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN。
Node write-returnは到達保証ではなく、Paper入力OFFは完全入力停止保証ではなく、変位0は完全静止証明ではない。Node時計とPaper tickの直接同期なし。

経路AのDEV参照実測は完了。経路B（稼働中Worldの次の本物native/L0 epoch）は未実装・未実施であり、別の最小課題として残る。Goal/学習/疲労/エネルギー/Action選択の変更なし。
報告先: SelfBody #632、Draft #649、関連Draft #648、S50 #627。
