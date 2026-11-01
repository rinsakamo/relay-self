# L-BCG H8 — Action前に認証可能なowner条件を監査する

2026-11-01。Draft PR #656 / Issue #431 / #537。

## 理由

H5実World（元S49 action 1、S16 outcome 1）の観測からH6/H7では
元Action前 native seq 21/23 と次epoch seq56を分離できた。
H8ではGoal、歩容、P1、M、障害物、source revisionが、
**元Action前**にどのownerから出たかを確認しない限り
「既知の条件」へ昇格させない。

実装: `src/relay_self/l_bcg_h8_owner_availability.py`、
`tools/l_bcg_h8_owner_preflight.py`、
`tests/test_l_bcg_h8_owner_availability.py`。

```bash
PYTHONPATH=src:tests:. python tools/l_bcg_h8_owner_preflight.py \
  docs/evidence/l-bcg-h5-20261101
```

原本 H5 S49 report / 独立監査 / S16 / S7 pre-next native / Paper
に、SHA manifestで束縛されたL16 pre-World operator planを加える。
S7等の検査は既存H6/H7を再利用し、H8でGoal/P1/M資格を新設しない。

## H5で実際に確認できるsource

- 元L0判断 event20/probe21 のMinecraft food=20、
  zombie distance=2.0m、position=(-9.5,-60,-5.5)は**観測source付き**。
  Minecraft food ≠ M energy、zombie ≠ voxel obstacle。
- 元S49 operator plan（`L16_PRE_WORLD_OPERATOR_SPATIAL_GOAL_V1`）は
  target=(0,0)、tolerance=0.49m。
  元native21 positionからoperator計画への**水平幾何距離**
  `hypot(-9.5,-5.5)` ≈ 10.97725mは参考値。
  これは**Actionの実Goal残距離でもGoal成功でもない**。
  `independent_external_goal_owner=false`,
  `authorizes_learning=false`。
- 元Actionは`MOVE_BACKWARD`、方向であって
  `WALK/JOG/RUN/DASH`の所有者確定記録ではない。
- SelfBody M0センサーの既存ownerは
  `adapters/mineflayer/self_body_m0_projection.py` の
  `compose_b0_cognition_views`等。M0はnative observation内の値ではなく
  owner-local ledgerセンサーのsource/epoch pairingが必要。
  H5元S49 event20にはM0 ledger/decision handoffがない。
- P1は
  `adapters/mineflayer/self_body_p1_projection.py` の
  `P1OwnerSensorHandoff` /`P1NativeCorrelation`。
  実P1 owner #626の原readoutをnative seq, request, owner_tick,
  world_source_refで結ぶ必要がある。source pointerは
  physical full-tick WAIT認証ではない。H5元S49に該当原本なし。
- L16/S16のoperator `source_revision=0`は異World間の時系列
  `world_revision`に流用できない。
- H5のPaper reported-input OFF sampleは実効clear
  `NOT_ATTESTED`。有資格post-clear training World0。

H8は上記8条件を、原operator planに数値があっても
`missing_required`として残し、`learned_l1_attention=DEFER_UNKNOWN`。
H8は単一H5 Worldのtrace source availabilityであって、
ownerが将来どのcheckoutでも利用できないと主張しない。

## 次のLocalCodex実World DEV実験（継続grant適用）

Goal/P1/M/G4に跨る「値の読み出し」だけを実装できる可能性があるが、
S49 sole Action issuerと既存L0選択は**変更禁止**。

進行手順:
1. branch・exact HEAD/CI・owner版/asset SHA・World状態・portの
   read-only preflight。親#655/他laneのprotected originalsは不変。
2. 1 Worldごとに目的・seed・source owner/時点・Action上限・
   criteria・evidenceディレクトリを**事前固定**。
   初回のH8実Worldは単一World、元S49 Action最大1件、
   new BCG Action0、native追加probe0、モデル0、更新0、
   retry0で実施。失敗時は原本を保存し、次のWorldは別実験として扱う。
3. 元Action前S49 native event/probeを保存し、
   Goal/G4/P1/M ownerが未存在ならUNKNOWNを記録する。
   Ownerがある場合でもbody/world/session/native seq/owner tick/
   source digestを厳密に結び、`producer-local`を正式物理値にしない。
4. S16 Outcome、Paper独立原本、L-BCG DEFER、S49 no change、
   Java/Node終了/cleanupを監査。H6→H7→H8 CLIを同World原本へ
   実行できるようpathをパラメタ化（固定値H5だけへ過適合しない）。
5. 異なる独立Worldで条件を変える場合は新しい事前宣言を行い、
   training/heldout 世界IDを分離。H5をqualified trainingとして
   入れない。cheap baseline比較は**観測フラグ**の段階。

L-BCG DEV継続grantは#431のユーザー承認により有効だが、他lane
Worldに流用不可。今回のGitHub側H8は**新World0 / Action0 /
new native probe0 / provider calls0**。この文書の作成・CIだけで
実Minecraft試験を実施したとは主張しない。

**H8_DEV_OWNER_SOURCE_AVAILABILITY_ONLY /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**。

## H8実World用の事前実装

H6→H7→H8は既定のH5原本回帰を維持し、`--audit-classification
DEV_H8_ORIGINAL_CHAIN_AND_BCG_DEFER_VERIFIED`を指定した場合だけ
H8独立監査分類を受理する。session、native seq、Action ID、Paper tick、
World UUID、SHAは当該Worldの元原本から照合し、H5数値を期待しない。
現在の読戻しはroute Bの1 Action/3 decisions/8 callbacks形状に限定する。
0 Actionや途中終了はこのPASS形状へ変換せず、原本と失敗結果を保存する。

`--l-bcg-shadow-dev`時だけ、元L0がMOVE_AWAYを選択した後、
唯一のExecutor実行前に、既に受信された同一probeとS7 prefixを診断する。
`capture/h8_preaction_sources.json`をexclusive作成し、元Body/World
projection、session/request/seq、元行SHAとprefix SHAを保存する。
診断は新native probe、ownerセンサー計算、Action権限を持たない。
Goal/gait/P1/M/G4/revision/qualified-trainingのreceiptはroute Bから
渡されていないため8条件をUNKNOWNのまま保持する。
診断エラーも記録し元L0/Executorは継続する。これをDEV PASSとはしない。

独立プロセスの`tools/l_bcg_h8_world_readback.py`は既存S7/S16/Paper/
packet/元L0/cleanup監査を実行し、preaction sidecarを元native prefix
から再計算する。prefixの最終seqがS15-beforeより前であることも検査する。
その後、別CLIでH6/H7/H8を読み戻す。host report自己整合性、保存原本
照合、外部物理認証は別の保証である。

## H8実Minecraft結果（2026-11-01）

実行HEAD `a244f5b2ae92878b337297398f5ff3cb48afbdb5`。
新World1 / 元Action1 / S16 Outcome1 / retry0、追加probe・Action・
model・Learning/S10/S11/Memory更新は各0。
元L0 `WAIT(8→10) → MOVE_AWAY(20→21) → WAIT(56→57)`。
Action前native21と次epoch57を分離し、H5のnative56や座標を転用していない。
Body/World元source、位置(-9.5,-60,-3.5)、health20、food20、saturation5、
S42敵距離2mを取得。独立Goal/gait/P1/M0/G4/revision/post-clearの
8条件はUNKNOWN、preaction/next-epoch両方の診断がDEFER_UNKNOWN。

独立processのS7/S16/Paper/packet/元L0/command全件/source/cleanup監査PASS。
Node/Java exit0、所有PID消滅、World削除、port解放PASS。
Paper ticks254–261はreported-input sampleだけであり、
EFFECTIVE_CLEAR_NOT_ATTESTED / GOAL_UNDETERMINED /
QUALIFIED_TRAINING_WORLDS=0。DEV PASS / QUALIFICATION NO_GO / SCIENCE NOT_RUN。

原本とH9候補・失敗検証ログの詳細は
[H8 evidence](evidence/l-bcg-h8-20261101/README.md)を参照。
H9は元S42が既に提供できる敵距離2.0m/3.5mの1軸を独立Worldで
変える候補とし、同じnative sourceのCHEAP比較、training/heldout World分離を
事前固定する。正式学習資格やL0自動昇格は与えない。今回はH9 World0。
