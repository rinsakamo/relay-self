# L-BCG H7 — 元S49 Action前cueの時系列分離（DEV）

2026-11-01。Learning #431 / S49 integration #537 / Draft PR #656。

## H7で増やしたもの

`src/relay_self/l_bcg_h7_preaction.py` は既存H5実Worldの元バイトを
H6のsource束縛読戻しへ渡し、**元S49のAction前**に既に見えていた
cueだけを独立した `H7PreActionAudit` に保持する。

- 元S49 L0の MOVE_AWAY 選択：event20 → native probe **seq21**。
- 元S49 ExecutorのS15 Action前probe：**seq23**。
- Action後S16 probe：**seq30**、次L0 WAIT：event55 → probe **seq56**。
- 初回の選択時に観測した元zombie距離 **2.0m**、
  Minecraft food **20**、health / saturation / positionを
  seq21のrequest_id・session付きnative参照へ束縛。
- 別時点のseq23 foodは別のsource参照に保持する。
  **seq56の距離10mや位置は絶対に「Action前の条件」としない**。
- `cheap_native_food_low`（food≤10）と
  `cheap_native_threat_near`（敵距離≤4m）は既存L10／S42の
  安価な**DEV観測フラグ**の比較用であり、M0 low energyや
  Goal remaining distance、障害物確証を意味しない。
- 世界／セッション重複・時点混同・原本digest差替え・
  偽Goal/physical clearを拒否するfocusedテスト。
  一つのWorldから得た複数probeを別Worldとしない。

## 観測できないL-BCG条件（現時点）

`goal_remaining_m`、`goal_tolerance_m`、`selected_gait`、
`p1_fatigue_high`、`m_energy_low`、
`verified_obstacle`、`world_revision`、
`verified_post_clear_training` の8条件は未知。
**Goalのoperator-local planを独立Goal認証としない**。
元Action名 `MOVE_BACKWARD` は
WALK/JOG/RUN/DASHのどれを実際に選択したかの証拠ではない。
食料≠エネルギー、敵≠障害物幾何、元ActionのS16変位≠入力実効clear後物理変位。

H7は既存H5の保存原本を再利用しており、今回新規Minecraft Worldは0。
LocalCodex側で後続実Worldを実施する場合も、まず各Worldで
原S49選択時の既存native PresentとM/P1/G4 source owner、Goal
ownerの取得タイミングとsession/world/source revisionを
**事前固定**する。揃わない軸はUNKNOWN、L1評価をDEFERさせる。
別WorldにおけるDEV cheap傾向は統計として出せても、
認証済み `MotorOutcome` と学習済みAction価値には昇格させない。

## 工学・科学的な上限

H6のSHA照合とH7のnative参照結合は、保存済み原本の相互整合を示すが、
独立TCP wire受理・Paper物理clear・Goal独立判定は証明しない。
`H7PreActionAudit` と `H7ObservedCue` はMemoryやL1/Actionの権限ではない。
同一Worldの後続結果は学習条件の作成に利用していない。

**H7_DEV_PRE_ACTION_NATIVE_SOURCE_CUES /
H5_ORIGINAL_WORLD_REUSED / H7_NEW_WORLD_0 /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**。
