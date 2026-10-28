# T1q SelfBody 内受容統合 実Minecraft DEV結果 — 2026-10-28

**DEV_ONLY / DEV_WORLD_OBSERVED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**

Branch: `self/dev-t1q-body-interoception-20261028`。実行コードHEAD: `cb2ae34360a08db7e602117b0bbc11f091780901`。このレポートを加える最終delivery commitは実行コードHEADの子孫で、コード変更なし。

## 修正と検証

指定remote HEADとT1p祖先関係、8コミット差分をfetch後確認。隔離worktree使用。SelfBodyは#634指定blobと完全一致し、変更なし。

- T1eの監査用ローカル`rows`が既存Paper marker readerを遮蔽していたため`sensor_rows`へ変更。
- T1qがM0 ledgerおよびP1 stateのsessionを個別に照合するよう修正。foreign P1負対照の初回FAILを保持。
- view/sensor不変性、source session/seq/request不一致、reader遮蔽、M0/P1 session負対照を追加。未観測はUNKNOWNでHALT、ホストguard優先、デフォルトT1p経路を保持。
- import順序・未使用import修正。S49、bridge、Java、M0/P1式は変更なし。

Python 3.12.3 focused **104 PASS**、継承FAST＋T1q **44ファイル717 PASS**、Ruff、484 PythonファイルAST、repository contracts PASS。FULL、Node/Java再ビルドなし。

system python3.12にはpytestがなく初回起動失敗。既存`/home/rinsa/relay-self-s60b1-venv/bin/python`使用。最初のRuff FAILとforeign fatigue FAILを外部phase1へ保存。`test_self_body.py`は存在せずPASSに計上していない。

## 実機・World

Node22.22.2、Java21.0.12.1、Paper1.21.8-60、Mineflayer4.39.0。T1p資産を実機hash再照合し、bootstrapはcache/libraries/versionsの121ファイルだけ使用。物理Node runtimeおよびnode_modulesは実directory、136依存manifestを照合。World本体は新規生成。

新規World **1 PASS / 0 FAIL**、session `b2266cd7-db7f-4666-b408-bd73813d2ddb`、World `bc4cb05c-df68-45b4-acb9-c18915932348`。

## 2 epochの判断と監査値

感覚値はSelfBody INTEROCEPTION。正確なホスト値は外部ledgerから独立再構成した監査値であり認知入力ではない。

| epoch | native seq | Paper WorldTick | M0 tick | Energy感覚 | 疲労感覚 | ホストEnergy（監査） | ホスト疲労（監査） | L0 / Action |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| t1q-epoch-0 | 27 | 1034 | 1 | 12.0 | 0.0 | 11.9989 | 0.0 | MOVE / MOVE_BACKWARD → OUTCOME |
| t1q-epoch-1 | 73 | 1064 | 31 | 12.0 | 0.0 | 11.964250127646546 | 0.0 | MOVE / MOVE_BACKWARD → OUTCOME |

Energy量子化幅0.25、疲労0.01。2回目は更新後のM0/P1状態から再投影。量子化でEnergy感覚が同じになること、WAIT_DEV回復後の疲労感覚が同じ0になることは正常。人工負荷・食事付与なし。

| epoch | dispatch seq | clear ACK seq | settle seq / tick | WAIT後tick | outcome移動量 | 残留移動込み静止位置差 | P1蓄積 / 回復 |
|---|---:|---:|---|---:|---:|---:|---|
| 0 | 29 | 38 | 60 / 1052 | 1064 | 0.6269065734210613 | 0.8571697198364467 | 0.032997447069485555 / 0.032997447069485555 |
| 1 | 75 | 84 | 106 / 1082 | 1094 | 0.6269065734210615 | 0.857169719836447 | 0.03428678879345788 / 0.03428678879345788 |

## 会計・source・cleanup

M0: 12 → 11.929535788206891。basal 0.061、cognition 0.0061、move 0.003364211793147172、合計 0.07046421179314717。食料credit 0。

P1: 蓄積 0.06728423586294344、WAIT_DEV回復 0.06728423586294344、最終 0.0。WAIT_DEV 40 ticks。会計61連続ticks、WorldTick1034–1094。

Paper全80 frame ADMITTED、source違反0。因果年齢上限max 89.357275ms <150ms、receive→evaluation完了max 0.698507ms <25ms（評価本体max 0.267412ms）。same-Node-clockのみ。

元S51 issuer／S49 executor／S16 clear／ActionSupervisorのまま、MOVE2・OUTCOME2・clear2、Action/effect重複0、追加native receive 0。LLM呼出し0、TPS actuator 0。同期Node timing trace OFF、traceファイルなし。

Java/Node exit0、両PID消滅、server保存ログ、transport shutdown ACK＋connection_end、独立port25565再bind PASS。これらを高水準STOP ACKや全tick静止証明に昇格しない。

## 原本

外部原本: `/home/rinsa/work/t1q-evidence-20261028/T1Q-001/t1q_body_loop/`。World全体、native.jsonl、commands.jsonl、paper.log、python_timing.jsonl、t2_ticks.json、report.json内SelfBody decision trace、launch argv/environment/source hashesを保存。

`/home/rinsa/work/t1q-evidence-20261028/originals-manifest.json`、**204ファイル**再読一致。SHA256 `a7cdba55290ec64005e0b35f648862f73cc7caf95c343ce29faea1b23d2a9e75`。外部`audit.py`・`audit.json`でsource/action/ledger/sensorを独立監査。

JSONレポート: [t1q-native-dev-results-20261028.json](t1q-native-dev-results-20261028.json)。

## 主張上限

R-qualified WAIT、高水準STOP ACK、独立source認証、自律的身体認識の科学的実証、疲労感覚の性能向上因果効果、長期生存・自律学習は未成立／未実施。L0は設計されたDEVヒューリスティック。main、#545/#634/#626、S18凍結対象は更新しない。
