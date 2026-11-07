# D7-F: 本物のゾンビ自然腐肉から初回のS49/S51実食事（DEV）

親: D7-E Draft PR #786。子: D7-F Draft PR #787。対象: RelaySelf Bug-0 #742。

## 成立させる1周期

元S49が実Paper zombieをATTACK（独立killer照合）→自然ItemSpawn→既存D6の元S49 MOVE_BACKWARD→実Paper Item UUID Pickup→元S49が当該World稼働中にS50とPaperの静止を照合→元S49発行のEATを既存S51へ委譲。equip/consume、Food増加、腐肉在庫減少、物理PREPARE永続台帳/S16 OUTCOMEが揃った場合のみ初回自然食事DEV PASS。

配置されたのは攻撃対象のNoAI/低HPゾンビだけ。腐肉は一切ステージ・give・inventory編集しない。WorldのdoMobLoot=trueから独立Paperが実死亡/生成/拾得を採集。Selfの新たな物理issuerは作らない。オペレータはWorld標準のhunger effectを攻撃前に与え、実native Food<14を待つ。元L0閾値・WorldBodyの物理係数は不変。

## 完全性と限界

先行ATTACK（S49 nonmotion PREPARE）、MOVE（C1 PREPARE）、後続EAT（同じS49 nonmotion PREPARE）は同一session/Intent/元ActionSupervisorに結合される。元S49が受け取るMOVE receiptは同一Python参照であり、外部で作ったreport dictではSTOP/EAT再開不可。

Paper自然モードは死亡・spawn・pickupのWorld/zombie/item/killer UUID、tick、腐肉数1を要求。S50同一クライアントの元S15 -s15-clear ACK後8+ physicsTicksの7入力OFF、Paperの真のPickup後で直近8+ serverTicksの7入力OFF/ほぼ静止、Native二つのfresh probeで生存/危険/food/在庫/位置安定を確認する。

初回資格は自然腐肉ちょうど1個。0個は真の0個としてEAT NOT_EXERCISED、2個は初回1個EAT資格の対象外でNOT_EXERCISED。方向・Item UUID・owner・STOP不成立はFAIL/DEFER、旧Actionの再発行なし。自然RNGは変更しない。次ゾンビはWorldの600tickルールを独立検証する。

PaperのgetCurrentInput()は最終受信値であり、元S49のS15 clearがサーバーで有効になった厳密tickの因果ACKではない。DEV身体静止の工学判定のみ。QUALIFICATION_NO_GO / SCIENCE_NOT_RUNを維持する。

## 手順

Offline: D7-F自然Paper death/spawn/pickupの負対照、Stage偽装拒否、既存D4/D6/D7回帰、Paper respawn/drop witnessビルド。成功HEADだけをone-use PRトリガーで新規Disposable Paper 1.21.8 Worldへ投入。Native/Paper/台帳/監査原本をSHA256固定。合格しても完全2周期・長期連続生存・自律学習は未証明。

Status: DEV_ONLY / D7_F_REAL_NATURAL_S49_S51_ONE_CYCLE_UNPROVEN / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
