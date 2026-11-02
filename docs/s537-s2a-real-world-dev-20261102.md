# S2-A 実World DEV検証（2026-11-02）

分類：`DEV_ONLY / S2A_REAL_WORLD_SOURCE_JOIN_PASS / SOURCE_UNATTESTED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`。

新規使い捨てWorld **1回、成功1、失敗0、再試行0**。同一Self/sessionで元S49 Action → 元S16 → 次native probe → WB L1 → 直前S16付きL2入力候補を確認した。モデル実行・学習成立は主張しない。

## Sourceと変更範囲

- Branch `dev/s537-s2a-source-bound-readonly-l2-20261102`、開始HEAD `f9fd87f9af4069581fba3e1b3a42eb33900366bb`。
- 実行HEAD `4da911f8158e3c89c7ac5f808c4db3f1e88f8ca7`。納品HEADは本書・証拠を収録した後続commitであり、WorldをそのHEADで実行したとは扱わない。
- 元S49 #674 `702f75c9fab3c42053ca0c89af670db1e306c892`。Executor、実World runner、native verifier、completion bridgeをbyte照合、不変。
- M #676 `9afce6bde1079f8a42aaf3c4e515ef35fc6b0396`、WB #669 `944db858186a4d9449946b6acdcb8c8e5998e071`。新規独立detached worktreeでexact clean確認。親S1 #690、main、他branch refs不変。
- S2-A変更は監査出力のみ。入力生成／元S16 closure callbackの発生順をその場でappendし、既存S1 WB/M結合reportをS2-A reportに保存。入力候補の生成条件・元owner受理条件は変更しない。
- 許可：Issue #537の2026-10-14 DEV運用規則と現行S-I0.5、本mission。所有する新規ローカルWorld、元Action最大2件、モデル0件。消費済one-shotやR/V grantの再利用なし。

## オフライン検証

Python 3.12 focused **68 PASS**（元S49/S0 47＋固定M/WB S0/S1/S2-A 21）。Ruff、compile、repository contracts PASS。失敗0。元callback契約・型identity、同一session/Action/probe/request、未来S16、異session、異Action、重複closure、逆順closure、replay/古いprobe、observer例外後の元owner継続、default-OFF gateを検証。合成fixtureは物理証拠ではない。

## 実World結果

session `db48a963-5de7-4b1a-8bd3-3557edd20d33`、Self `self-s537-s1-native`。
元判断 **WAIT → MOVE_AWAY → MOVE_AWAY**。元Action **2**、S15 clear **2**、S16 OUTCOME **2**、両Actionのterminal確定により未解決 **0**。追加issuerなし。

| epoch | native event/probe | 入力生成時Previous S16 | 後続の元Action |
| --- | --- | --- | --- |
| native-9 | 8 / 9 | NONE | WAIT、Actionなし |
| native-21 | 20 / 21 | NONE | s49-native-move-20 |
| native-51 | 50 / 51 | s49-native-move-20、after29 | s49-native-move-50 |

| 元Action | before | dispatch | S15 clear | S16 after | xz変位 |
| --- | --- | --- | --- | --- | --- |
| s49-native-move-20 | 22 | 23 | 28 | 29 | 0.6269065734210617 m |
| s49-native-move-50 | 52 | 53 | 58 | 59 | 0.6269065734210617 m |

host記録は **input9 → input21 → closure(Action20, after29) → input51(Previous Action20) → closure(Action50, after59)**。
入力候補 **3**、closure callback **2**、Previous S16付き **1**。
初回と2回目入力はNONEのまま。最後のAction50について次epochを捏造していない。入力は既存live_probe処理中にimmutable objectとして作られ、completed_l0や終了後readoutから過去入力へ結合する処理はない。

WBの本物L1 CognitionSlice **3/3**が元probe objectとsession/epoch/seq/request、SelfWorld/SelfBody source ref一致。M original batchは **RECORDED / ORIGINAL_PYTHON_BATCH_RECORDED**、completed callback **1**、observer error **0**。S42/B0/L8は **NOT_SUPPLIED**のまま。

## 原本監査と限界

別Pythonプロセスで固定S49 native verifierをbyte照合し、元reportの2 Actionのsession/Action ID/before→dispatch→clear→after/変位を再検証PASS。異session・異Action・clear失敗・逆S16順序の変更コピー **8/8拒否**。元reportは書換えなし。S2-A host記録・元S49 report・WB/M結果を照合PASS。

追加native reads / model calls / S60 submissions / Action issues / learning updates / energy debitsは **各0**。実行コードの接続先とreportを照合した追加操作数であり、未測定の実model費用・身体Energyを0と認定するものではない。M model usageはUNKNOWN。

WSL2 Ubuntu24.04、Python3.12.3、Java21.0.12.1、Node22.22.2、Mineflayer4.39.0、Minecraft Java1.21.8。元runnerの公式Mojang serverを使用。NODE_OPTIONS shimなし。独立Paper/W3時系列認証・raw TCP custodyはないため **source_attested=false**。元S49の分類語QUALIFIEDをR資格と解釈しない。

Python PID149474 / Java PID149482 / Node PID149553はexit **0**、全PID消滅。World `/tmp/relay-self-s49-xhwy1jva` 削除、port25565通常bind PASS。S1旧原本37ファイルのSHA一致、保護branch refsとM/WB cleanを確認。

外部原本：`/home/rinsa/work/s2a-world-evidence-20261102`。
元[S49 report](evidence/s537-s2a-world-20261102/s49.json)、別[S2-A report](evidence/s537-s2a-world-20261102/s2a.json)、[独立監査](evidence/s537-s2a-world-20261102/audit.json)、[lifecycle](evidence/s537-s2a-world-20261102/lifecycle.json)、[SHA256索引](evidence/s537-s2a-world-20261102/SHA256SUMS.json)。過去失敗原本は再使用・上書きなし。

## 次のS2-Bに必要な最小契約（今回未実装・未実行）

既存 `BestEffortDisplacement`（S60-A）、`LoopbackDisplacementAdapter`（S60-B1）を使い、一つのS2AReadOnlyInputを、同一session/native world_seqに加えて元ownerのintent_revision・retained_revisionを持つ `CognitionContext` に束縛する。S2-A入力にはrevisionがないため、元ownerから受け取る必要があり推測で補わない。self/epoch/probe/request/source ref/previous Actionをwork IDとgenerationへ一対一に記録し、元S60 ownerがadmit/submit/acceptを所有する。L0を待たせず、L2にAction/Memory/Learning権限を与えない。

新native probe、session/self/source不一致、intent/retained revision変更、期限超過、superseded generation、replay、取消・不正応答・通信不確定でcurrent入力を失効。遅延結果は過去epoch reviewのみ。host cancellationはbackend STOP ACKやGPU解放ではない。不確定送信後はretryせず、既存leaseを強制解放しない。

次回の提案予算は**新規DEV World最大1、元Action最大2、実L2 call最大1、出力最大256 token、timeout最大60秒、retry0**。これは今回の使用許可ではない。将来の正確な実行HEAD、モデルartifact SHA/owned runtime/API identity、canonical payloadとB1五key契約の型整合、deadline/timeoutと実call消費境界をoffline検証し、適用可能なモデル予算を確認してから実行する。モデル起動・S2-Bコード・実callは今回0。

残る未成立：独立source attestation、L2利用・効果、学習・自己改訂・L0結晶化、認知省資源、QUALIFICATION、SCIENCE。

納品先：[Draft PR #691](https://github.com/rinsakamo/relay-self/pull/691) / [Issue #537](https://github.com/rinsakamo/relay-self/issues/537)。mergeなし。
