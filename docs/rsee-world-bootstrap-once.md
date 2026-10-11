# RSEE 1.0 初期Worldの独立bootstrap（LocalCodex引継ぎ）

Owner: #575 / #537。Parent #581（stop済み snapshot binding）。
本子Draft #582 は **source / CI のみ**。
**Minecraft・Java・Mineflayer実プロセス・llama-server・GPU・LLM POSTは起動していない**。
Golden Runは引き続き BLOCKED / NOT_RUN。

## 安全な実行単位

World初期化は Self/Action/LLMから独立した **1回の物理bootstrap**。
`python -m experiments.standard_env.world_bootstrap` は import / `--help`
では実機を起動しない。実起動には、以下の全てが別々に必要：

- 当該exact HEAD、jar SHA256、出力先、Minecraft port25565の再検査
- **この1回だけ**のdisposable Minecraft Java server起動と
  Mineflayer bridge起動への明示的な許可
- Minecraft EULAへの独立したユーザー同意
- CLI exact `--confirm RSEE-ONE-DISPOSABLE-WORLD-BOOTSTRAP`
- CLI `--accept-minecraft-eula`。このフラグはユーザー本人の同意を表す
  入力で、LocalCodexが許可なしに代行・推定してはいけない
- Git外の新規・空の `--output-dir`。
- 全依存(import、Java21、Node22、pytest、httpx、
  GGUF不要、Mineflayer Node dependencies)事前PASS。
- 元EULA済みsnapshot/他レーンWorld/runを使い回さない。

**実機許可/EULA同意がない場合は、以下のコマンドを実行せず
READ_ONLY_PRECHECK_BLOCKED で停止。** 以前の別の試験許可は流用しない。

```bash
# 実行前にこのHEAD・artifact・host・listener・grantを再照合。
# 世界生成の明示許可とユーザー自身のEULA同意が揃った時だけ：
export PATH=/home/rinsa/.nvm/versions/node/v22.22.2/bin:$PATH
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD"
PYTHON=/home/rinsa/.local/share/relay-self/rsee-1.0-20261011/venv/bin/python
mkdir -m 700 /new/empty/rsee-world-bootstrap-run-ID
"$PYTHON" -m experiments.standard_env.world_bootstrap \
  --jar /home/rinsa/.local/share/relay-self/rsee-1.0-20261011/minecraft-1.21.8.jar \
  --output-dir /new/empty/rsee-world-bootstrap-run-ID \
  --confirm RSEE-ONE-DISPOSABLE-WORLD-BOOTSTRAP \
  --accept-minecraft-eula
```

`/new/empty/rsee-world-bootstrap-run-ID` は説明用の未作成パス。
別runでは完全に異なる証拠ディレクトリを使用する。
デフォルト `--jar` はない。jarは固定SHA256
`2349d9a8f0d4be2c40e7692890ef46a4b07015e7955b075460d02793be7fbbe7`。

## 1回の権限範囲

1. #580のhost/module/node/Java/jar SHA確認、Minecraft port25565の排他確認
   （この時点までは read-only、モデル/GPUなし）。
2. 保存先`game`に検証済みjarコピー、元S31Aのdisposable `eula.txt` /
   `server.properties` 書き込み、`level-seed=575` だけ追加。
3. 既存の元S31A `_ready_server`でvanilla serverを **1回**起動、
   Mineflayer bridgeを **1回**起動。相関付き `probe`を **1回**。
   Self Action 0、LLM 0。
4. Mineflayer bridgeを正常shutdown。vanilla `stop` を送ってJava exit 0。
   失敗/期限切れ/kill fallback は **clean-stop qualifiedでない**。
5. stopped `level.dat` / `playerdata/*.dat` をnative NBTで復号、
   WorldGenSettings.seed=575、全GameRules、raining/thundering、
   WorldTime/DayTime、player yaw/pitch/position/health/food/inventoryを記録。
   相関付きMineflayer probeで観測したHealth/Food/位置/Inventory/時刻と
   stopped NBTを照合。異なる場合fail closed。
6. `game/s31a-ephemeral`を **サーバー停止後** `snapshot`へコピー。
   全ファイルpath/size/SHA256とmanifestの厳密照合。
   `initial-observation.json`, `manifest.json`,
   `bootstrap_receipt.json`, `minecraft_server.log` を保存。
   所有外プロセスや既存run/Worldに触れない。

現実のMinecraftバージョンによってNBT schemaが変化していたら
その**初回の失敗とNative evidenceを維持し停止**。
必要なスキーマ差分を新たなオフライン修正として別にレビューする。
元の1回を二度実行・replay・fallbackしてはいけない。

## 責務と証拠上限

- `status=PASS` はこのbootstrap手順でnative Mineflayer/停止済みNBTと
  manifestが一致したことだけを指す。独立した第三者監査、物理GPU、
  Self Action、認知的World状態の同一性、Golden Run成功は含まない。
- `status=BLOCKED/FAILED` は未資格化。FAILEDの
  `game/`, server log、receiptsは書き換えず保持する。
- *止めたWorldを後で起動するとゲーム時間・entity更新等があり得る*。
  byte同一性は runtime状態の同一性を保証しない。
- もし初期`snapshot`が有効でも、次のS49 Golden Runには独立した
  exact HEAD / model / loader / GPU / Java/World / Action / L2 POST grantと
  EULA条件が必要。仮に1回のbootstrapが成功しても勝手に継続しない。
- 元S49/S31Aが隠れた合意や実行権限を生み出すことはない。
  `self_owned_llama`は今回**起動禁止**。

## LocalCodexへの次報告

ブランチ/HEAD、必要な明示同意の取得有無、前段バイナリ・jarのhash、
グラント対象の出力先、bootstrap実試行回数、Java PID/port/終了コード、
Mineflayer接続とprobe seq、stopped NBT全GameRules/姿勢/天候、
snapshot manifest SHA256、テスト結果、cleanup、予期せぬ挙動を
NO_PHYSICAL_GOLDEN_RUN として報告。
