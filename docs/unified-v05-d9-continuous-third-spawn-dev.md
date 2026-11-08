# Unified v0.5 D9-A — 2食事後も同じSelfが生きて次のWorld世代を認識する（DEV）

親：[D8 Draft PR #788](https://github.com/rinsakamo/relay-self/pull/788) の実World R15 [#42442353621](https://github.com/rinsakamo/relay-self/actions/runs/42442353621) / source HEAD `3586182aa881aca2cb283e64e89564784f407f67`。

## D9-Aの厳密なスコープ

- D8の元S49 ATTACK→自然腐肉 Item UUID の拾得→真のS51 EATを**同じWorldで2周期**再実行し、既存の独立監査で再検証する。
- 第2死亡の正規tickからWorldが**600 server tick後に第3個体を生むまで、同じWorld、同じMineflayer native session、同じ元S49 owner / ActionSupervisorを閉じずに**保つ。
- その間に元のnative SelfBody（food/health/腐肉在庫）、native SelfWorld（nearby entities）を**read-only**で連続採取。World-owned死亡・spawnのUUID/tick、元のATTACK/MOVE/EAT台帳と同じsession証拠で照合する。
- 第3世代のnative zombie entity ID が先行2世代と異なることを観測し、読取中の身体Health/Foodがともに正、S49物理Action追加ゼロ・元Action ID集合不変・原本二台帳SHA不変を確認する。
- 第3世代に **ATTACK / EAT / MOVE の新規発行はしない**。第3世代を認識するだけのD9-Aであり、3周期成功とは名乗らない。第2世代の腐肉0個を2回目のEATと数えない。
- 既存Paper server tickの入力OFF観測は **passive WAIT / 身体の静止期間**。Selfが明示的RESTを選んだ証拠ではない。真のWorldBody疲労係数・回復率は未知。
- 初回の自然ドロップ0個：初回EATがないのでD9経路は `NOT_EXERCISED`。第2世代ドロップ0個：**D8の食事2周期は不成立**、しかし元S49の第2実死亡/S16 OUTCOMEと在庫不変を検証後、同一Worldの第3リスポーンを読取専用で確認する試験は継続できる。この場合D9の「3世代目までの生存観測」だけを `PASS_DEV` とし、`two_real_natural_food_cycles=false` を維持する。

## 次の接続 (D9-B/C)

D9-Aで生存と第三世代観測が成立して初めて、別の明示的grant・offline負例・保存済み原本監査を伴って、元S49の第3Intent再arm → 第3 ATTACK/MOVE/STOP/EAT → REST/疲労による選択と物理効果の因果照合 → 4周期以上の持続に進む。

operator-managed World環境であり、自然環境での完全自律・無期限生存・資源収支黒字・科学的検証を主張しない。ドロップ率/`doMobLoot`/Food/Health/WorldBody物理則/L0権限は変更しない。

**分類:** `DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`。D8原本とmainは不変。
