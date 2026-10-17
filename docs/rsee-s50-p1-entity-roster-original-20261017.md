# R — S/P1 entity UUID/type 原ロスターの独立照合 (2026-10-17)

## 前提と Authority
- S product #537 / physical boundary #627 / 既存 Draft #545
- R original #575 / 既存 Draft #610
- P1 Body #620 / 既存 Draft #626（**変更なし**）
- DEV / engineering QUALIFICATION / SCIENCE を分離。旧R一回限りgrantと既資格JARを一切流用しない。

## Prospective S DEV original

[S DEV #38978685310](https://github.com/rinsakamo/relay-self/actions/runs/38978685310) attempt 1 **SUCCESS** (新しい disposable Paper World 1件)、source HEAD `c1d1004f8b748b2e848b8db6a89ae6c91599891a`。Source artifact [#12080510466](https://github.com/rinsakamo/relay-self/actions/runs/38978685310/artifacts/12080510466) 2026-11-15期限。ZIP独立ハッシュ `41cf0b085a47a87a93eba05cef03bb1f1f4503c64710289cefd75b9d329bedce`。新プラグインJAR `51a1d76405e69c77b9d59e39a6e00dc3dc3b953382f1196cfc1e1f6bf3b9df54` は **R未資格**。前回の5条件M0.2工学資格の固定JARとは異なる。

新しい `S50_DEV_WAIT_ENTITY` は、全ロード済みチャンクに対しWorld UUID・chunk X/Z・Entity UUID・Entity TYPEを原サーバーログに **1個体1行** 記録（各tick全件、計96行、8 tick×12）。`S50_DEV_WAIT_SCOPE` には主体player UUID・行数・既存SHA256を保持。S検証器は生ロスターから完全再計算し、欠落・余分な行・重複UUID・型不一致・Self UUIDの他個体への置換を拒否する。

原 Paper tick70–77（8連続）、S50 Action正規OUTCOMEの後、8/8 sampled Self XYZ静止、活動イベントカウンター増分0、M0.2 BASAL継続、STOP/Java/Node出口正常。source observerはP1 Fatigueを更新せず `p1_wait_ticks_admitted=0` / `p1_fatigue_recovered=0`。

## R independent offline original audit

既存R独立アーカイブ監査を継承しつつ、Sの検証器を呼ばない `experiments/standard_env/s50_p1_roster_original_audit.py` と `tests/test_rsee_s50_p1_roster_original_audit.py` を追加。原World/JAR/Action発行→OUTCOME/native ACK/STOP/sessionとserver logを照合したうえで、全96行のロスター・型・entity/world/source UUID・tick・辞書順・SHA256とproducer集約を **Rが独立再計算**。

[R source-only run #38979160504](https://github.com/rinsakamo/relay-self/actions/runs/38979160504) SUCCESS。独立判定 [artifact #12080560809](https://github.com/rinsakamo/relay-self/actions/runs/38979160504/artifacts/12080560809) 90日（2027-01-14まで）。初回 [R #38979093044](https://github.com/rinsakamo/relay-self/actions/runs/38979093044) は synthetic test の「別WorldのMobを同一Worldと扱った期待値」誤りで **pre-source FAIL**。失敗は保存し、修正後のfreshオフラインrunのみPASS。追加Java/Node/物理World 0。

原証拠からの8サンプル各回の完全な**loaded cohort**:
- Self が存在する World: `PLAYER=1` (Selfのみ)
- 別の World: `END_CRYSTAL=10`
- さらに別の World: `STRIDER=1`
- 他online players=0。8回すべてUUID/type/World/chunkダイジェスト同一。

以前の「Self以外11 entities」は**異なる3 Worldsの合算**で、同一World内の他エンティティ11という意味ではない。10体のEnd Crystalは自律型Mobではない。Striderは遠隔の別Worldに存在する。ただし `P1-C SOLO` の正式な定義によって、同一World・同チャンク・全ロード領域・全dimension・生成/消滅のいずれを判定対象にするかを混同してはならない。

## Claim ceiling

R結果 `R_P1_ENTITY_UUID_TYPE_ROSTER_ORIGINAL_REVIEW_ONLY_NOT_SOLO` は、個体ロスターの **8 sampled callbacks限定** の原証拠確認。新JARおよびP1 full-tick WAITはR資格化していない。

`same_world_only_self_at_sample=true` は正しいが、**全World tickのSOLOを証明しない**。tick間のentity lifecycle、未ロード個体、client held controls、並列S Action発行、非イベント由来の運動、被覆外のworld機構は引き続き `NOT_ATTESTED`。セルフWorldだけの単独性から、Body `SourceBoundTick(WAIT)` を生成してはならない。Blocked MOVE≠WAIT、M0.2 BASAL継続、P1 recovery=0、V7 0/20、production NO_GO。

## 次の明示的な開発ゲート

1. S/P1-C: Paper source-native **entity spawn/death/load/unload/teleport** と online player join/quitを同一World tickへ紐付けたイベント履歴。ただしイベントAPIで捕捉できない個体変化は `NOT_ATTESTED` とし、全entity lifetimeを擬似証明しない。
2. S Action issuer / Mineflayer: cleared control ACK後の held controls readback、全 S/L0/L1/L2 発行Action の占有区間をWorld full-timeへ相関。World tickの不在だけではheld-controlの不在を証明しない。
3. R: 事前登録したsource channelの被覆範囲、サンプルとevent log順序、全個体差分・process STOP・同一JAR configの独立QUALIFICATIONを実施。
4. P1: R-qualified `wait_interval_ref` と現実のBASAL/Body状態を受けて初めてWAIT tick回復（REST Action新設禁止）。V科学試験は別事前登録とgrantが必要。
