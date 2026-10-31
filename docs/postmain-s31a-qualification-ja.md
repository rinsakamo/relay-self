# RelaySelf S31-A — CI の実 Minecraft / 本物 Mineflayer による限定観測

## Authority

- S30 Draft PR #366、凍結 exact HEAD `5aff6711a33ed91800fb8bdf473ba8aebea25ce6`
- S18–S30 成果物、RelayTheory R6、Paper2 MAIN40 は無変更
- LocalCodex の稼働を前提としない GitHub Actions 独立実験
- 本文は事前登録した設計。**実測結果は CI 実行時生成 JSON が唯一の authority**。

## 研究上の問い

S30 は実 Node bridge 子プロセスと Python JSONL を扱ったが
Mineflayer 本体をテスト用 bot で置換した。S31-A では
**置換を外した Mineflayer 4.39.0** を、
**一時的な Vanilla Minecraft Java Edition 1.21.8** へ TCP 接続して、
実 server 内の source-native World fact が届くことを検証する。

```text
protocol ID echo != World physical truth
real vanilla server + real Mineflayer != independently attested source
source-native Minecraft fact != S27 Action3-bound evidence
World observation != Action proposal/authorization/execution
```

## 環境と供給元

GitHub-hosted Ubuntu runner 内で 127.0.0.1:25565 にのみ server bind。
Minecraft 1.21.8 は Mojang 公式 `version_manifest_v2.json` →
対応 version JSON → 公式 server.jar を取得し、metadata の正確な
ダウンロードサイズと SHA-1 を照合してから Java 21 で起動する。

Node 22 / `npm ci`（既存 lockfile で Mineflayer **4.39.0** 固定）、
Python `MineflayerProcessSession.launch` は凍結済み S29 の
production `bridge.mjs` を変更せず起動する。

CI で `NODE_OPTIONS` を未設定に保ち、S30 preload は使用禁止。
`online-mode=false` はこの runner の loopback server だけ。
RCON なし、max 2 players、一時 flat World。実験終了後は
bridge と Minecraft server を停止し、tempdir を破棄する。
外部 Minecraft server には接続しない。

## 予定プロトコル

1. Mojang metadata, jar サイズ、SHA-1、Java21 majorVersion の一致
2. Java server コンソールで `Done (` を確認
3. 本物の Mineflayer で `spawn` まで到達、実 World 位置を読む
4. `s31a-initial:001` の probe 応答 ID、session、seq を検証
5. server console で mob 自然 spawn を止め、夜にして、
   **NoAI の zombie を bot の約2m先に一体 summon**
6. `s31a-target:xxx` を用いた明示的な bounded probe
7. `nearby_entities` から zombie の source-native ID/位置/距離を採取。
   3D Euclidean 距離一致、16m 範囲、coverage 非切捨てを検証
8. 同じ request ID を再送して `duplicate_probe_request_id`
   の command_error を受信。新しい probe として認めない
9. bridge shutdown / Minecraft stop → 両 process exit 0
10. stdout/stdin 経路の **実測 receipt** を CI artifact として公開

### PASS 判定

次のすべてが成立する場合だけ
`REAL_MINEFLAYER_LOCAL_MINECRAFT_CORRELATED_WORLD_PROBE_QUALIFIED`。

- 公式 1.21.8 jar hash、Java21・Mineflayer 4.39.0 の identity
- 実 server `Done`、実 bot `spawn`、実 World probe 応答
- 明示 ID 一致・native zombie と幾何的距離の整合
- request ID duplicate を実 bridge が拒否
- bridge/server 両方が clean exit 0
- GitHub Actions S31-A の dedicated live job 成功

ダウンロード・依存・server 起動・bot spawn が不可なら `BLOCKED`。
稼働環境は整っていて相関・世界観測・距離・重複拒否に失敗した場合は
`FAIL`。未確認や timeout を PASS に変換しない。

## Source native の bounded 解釈

実験では privileged Minecraft server console が zombie を作る。
よって取得値は **制御された Minecraft 環境における genuine native fact**、
あるいは Mineflayer 内部処理が返した事実に限られる。
改ざんのない物理世界から取得されたという暗号学的証明にはならない。
世界の全脅威・安全性を推論することもない。

S27 の `PostFailureWorldEvidence` は既存 supervised Action3 や
WorldConsequence3 lineage を要求するため、単なる実 World probe では
直接同資格を主張しない。**S31-A は source-native 観測と ID 通信の
資格化であり、S27 Action3 証拠統合や完全 Self cognition を資格化しない。**

## 成果物

- `adapters/mineflayer/s31a_real_server_ci.py` — 公式 download / Java / real Mineflayer / observed World / teardown
- `tests/test_postmain_s31a_real_server_gate.py` — offline protocol/供給元/geometry negative
- `.github/workflows/postmain-capability-s31a.yml` — baseline four jobs + real Minecraft dedicated job
- `docs/postmain-s31a-plan-receipt.json` — outcome-blind static plan
- `docs/postmain-s31a-qualification-ja.md` — 本文

**動的成果物:** `s31a-real-server-receipts/s31a-report.json` と
`minecraft-server.log`。CI PASS/BLOCKED/FAIL の原本。

## 未資格化

LocalCodex WSL2 の再現（S31-B）、開放されたネットワーク、
暗号学的 provenance、Minecraft gameplay 全領域の sensing、
S27 Action3-bound projection、Action 権限/ISSUE、Skill terminal、
LRN retained update、自律的 scheduler/epoch、global replay guarantee。
これらを S31-A の成功から遡及的に主張しない。

本 PR は Draft / 未マージで停止する。
