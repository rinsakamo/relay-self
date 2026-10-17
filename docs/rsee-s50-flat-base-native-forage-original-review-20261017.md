# R #575 — S50 FLAT BASE_ON native採食ループ独立原証拠監査（2026-10-17）

## 識別・目的と境界

自然地形のV8科学試験を一切変更せず、別の seed 63101 / `minecraft:flat`
の停止済みDEV Worldから、**BASE_ON 1条件**だけ新規隔離コピーを起動。
L0 SEEK、既存S50 MOVE、食料PICKUP観測、S51 EATを動かせるか調べた。
新しい行動owner・代謝ledger・World上の自動補正は禁止。

S実装 `adapters/mineflayer/m02_paper_dev/s50_flat_base_foraging_dev.py`、
負対照 `tests/test_s50_flat_base_foraging_dev.py`。
旧V8の初期native markerに自然地形seed62101がハードコードされていたため
FLAT seed63101で拒否する開発失敗を経て、source定数で照合するよう修正。
過去失敗を改変せず全試行を保存する。

## 履歴（DEVのみ、いずれも別run）

- [S #38990210588](https://github.com/rinsakamo/relay-self/actions/runs/38990210588):
  プリJava単体テストのexpected error message不一致で停止。Java0。
- [S #38990264510](https://github.com/rinsakamo/relay-self/actions/runs/38990264510):
  原archiveとJAR PINを通過したが、Paper書き換え後のflat `level-type`
  表記を過剰に限定してPREJAVA拒否。Java0。
- [S #38990369268](https://github.com/rinsakamo/relay-self/actions/runs/38990369268):
  Java1+Node1、STOP/終了と原アーカイブ保存はSUCCESS。
  **行動FAIL**: source markerが自然地形のseed62101を期待していた。
  R別runner[source-only triage #38990527431](https://github.com/rinsakamo/relay-self/actions/runs/38990527431)
  はアーカイブ79件のSHA一致／初期marker欠落／native observation2件、
  `CloneDevRejected: native World seed mismatch` を判定。
  実食料/PICKUP/Actionは開始前。R以前の失敗runを科学成果に使わない。
- [S #38990613628](https://github.com/rinsakamo/relay-self/actions/runs/38990613628):
  ソースHEAD `0f5d639b0ce2dedbc61051f473daa1032c25a4e9`、
  attempt1、Java1+Mineflayer Node1、**terminal workflow SUCCESS**。
  保持したアーカイブ #12084378433（90日）、
  GitHub provider digest
  `sha256:0e2d4f45a35de6f101bd409274122fd87a37805422b6e72cb7f13920265b0fb4`。

## native S source 実観測

初期server tick marker: seed63101、XYZ=(0.5,-60.0,0.5)、
yaw=0/pitch=0、food20/saturation5.0/health20。
最初のnative Hunger effectは**operator fixture**で、food13まで低下。
調理済み牛肉1個をnative spawnから相対
`(3.0,-59.8,0.5)` にsummon。
この世界では地表草ブロックY=-61、空気Y=-60/-59を25/25地点で
元のPaper server sourceにより事前確認。

既存PaperNativeL0は item観測entity44に対してSEEKを選び、
S50 Action OUTCOMEを2件閉鎖:
`PROGRESSED` progress0.8322911817508138 block、
`ARRIVED` progress1.2828913533098645 block。
観測entityが消失し、調理済み牛肉の**native inventory countが0→1**。
検証器は
`PICKUP_SOURCE_CONSISTENT`、
`ITEM_DISAPPEARED_AND_INVENTORY_ROSE_ONLY`。
厳密なplayerCollect event因果は **UNKNOWN** のままで、
食料entity metadata由来のitem種別確証も無い。
既存S51 EATも完了報告あり。
Java/Node exit0、STOP ACK、connection_end、全dimension保存、
所有PID消滅、25565再bind、初期ソースWorldの不変性確認。
L1/L2 OFF、B1 memoryなし、仮想エネルギーledgerなし。
新plugin JAR SHA
`d620935f6f03f3239cebbef0b931ba97482f596e5457feec9b680fe2e14da486` は旧R
工学資格済みのJARではない。

## 別R runnerによる独立原証拠照合

初回R [#38990884515](https://github.com/rinsakamo/relay-self/actions/runs/38990884515):
sym-link負対照のfixture欠損件数のテスト不備で**PRE-SOURCE FAIL**、
物理世界・原証拠の変更なし、履歴を維持。

修正した[R independent #38990943990](https://github.com/rinsakamo/relay-self/actions/runs/38990943990)、
attempt1 **terminal SUCCESS**。
S source実World + 元flat停止原Worldを別runnerに再取得し、
`s50_flat_base_original_audit.py` が**S parserをimportせず**
初期13ファイルのSHA256とNBT seed、実行コピーindex、
**実行アーカイブの80/80 file SHA256（missing0, mismatched0）**、
インストール済みDEV plugin JAR SHA、原server/nativeと3以上の
発行Action、2つのS50 OUTCOME、食料entity/inventory source contrast、
S51 EAT完了、STOP/host cleanupを再検査。
native frame 118件（observation107件）。
Rが新しく起動したJava/Nodeは0。
結果は
`R_FLAT_BASE_ON_ORIGINAL_NATIVE_PICKUP_EAT_READBACK_DEV_ONLY`。
[R receipt #12085376143](https://github.com/rinsakamo/relay-self/actions/runs/38990943990/artifacts/12085376143)
provider SHA `9395435856861fd97ae6c8ee8c1152fb6574c80a89932d6401b7669e12c6f3ec`。
元のGitHub ZIP全体を直接独立ハッシュしたのではなく、
provider metadata＋内部全ファイルを実際に独立SHA再計算した。

## 判定／次の分岐

**採食という一連の工学機構が、平坦な実World内のDEVで作動できることを
Source-backed positiveとして保持**。このDEV PASSを、自然地形での
食料回収成功、十分な食料機会での生存改善、因果的適応、科学的成果、
新JAR工学QUALIFICATIONへ昇格させない。

次の開発分岐はSでFLAT BASE_ONの成功原本を固定し、
**別の独立クローン**から5条件へ拡張する場合、開始World tick・
native spawn姿勢・食料落下/消滅・plugin配置・各arm全原証拠を保持し、
V8自然地形旧run・元World・消費grantを変更しない。
S/P1 WAIT資格は独立したまま。
V8 SCIENCE0、V7 SCIENCE0/20、G3/production NO_GO。
