# D10 R1 — 最初の本物の腐肉ドロップまで2体を狩猟：DEV PASS

- 新World実Worldジョブ: [Actions #42448101239](https://github.com/rinsakamo/relay-self/actions/runs/42448101239)
- 改変していない原本: [GitHub Artifact #13604901329](https://github.com/rinsakamo/relay-self/actions/runs/42448101239/artifacts/13604901329)
- 実行HEAD: `86e95b5ad9d83a2468140e6e9598e0c40a6a8ddf`
- 事前オフラインソースHEAD: `ad90c79ef0addf8d3d313c061b31f937b7d5b2b4`
- 同一Paper World UUID: `c5ebfcc1-bcec-4eeb-87dc-cd839ffb7515`
- 同一native session: `10eb4ff3-d1f7-4a1a-a623-f3a93f9832ff`

## 元World・S49の事実
1. 初回管理ゾンビUUID `b22428eb-9967-45d1-a3c9-d480872e105c`、Paper tick71にSelfが元S49 ATTACKで死亡させ、バニラ腐肉0。native inventory 0を記録。S16 OUTCOME。
2. World-ownedリスポーン: tick671、厳密 **71+600ticks**。別ゾンビUUID `d0f3fe13-7202-40eb-b6bf-40e98d59182c`、元native entity ID28→38。同一元S49 ActionSupervisorで前Intent完了→次Intent新規commit→再arm、過去Action ID再利用なし。
3. 第2ゾンビはtick695にSelfが元S49 ATTACKで死亡。元のPaper `RSELF_NATURAL_DROP_DEATH` は `rotten_count=2`、真のItem UUID `f0ffe0ed-cff8-480e-a155-e1678a92d9a9` がtick695にspawn。
4. 同じ元S49の方向照合MOVE_BACKWARD 2回（各約0.6269m）後、同じItem UUIDをtick749にSelfが本当にPICKUP。新しいnative腐肉在庫2。**ここで狩猟停止**（食事は発行していない）。
5. 物理Actionは元S49 ATTACK2＋C1 MOVE2、合計4件すべて `S16_OUTCOME`。非MOVE/C1両台帳 `unresolved=false`、別Action issuerなし。Node exit0、Java exit0、cleanup true。

## 独立監査
`independent_source_audit.json`: `status=PASS_DEV`、`classification=D10_TRUE_NATURAL_DROP_AND_ORIGINAL_S49_PICKUP_PASS`、`natural_counts=[0,2]`、`first_positive_generation=2`、`all_real_respawns_world_600_ticks=true`、`same_supervisor_retained=true`。原本SHA256SUMS **7/7一致**（監査JSON、Paper原ログ、report、両永続台帳、lock2件）。

**限界**：成功は「0個だったため次のゾンビを狩り、初の真正腐肉を拾った」まで。S51 EAT、食事後の継続生存、第三世代以降、無期限生存、完全なexactly-once物理的因果は実証しない。DEV testの12世代上限は未到達、SelfのGoal終了条件ではない。

`DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`。D8 #788、D9 #795、mainの原本・境界不変。
