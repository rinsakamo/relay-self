# RSEE 1.0 WSL2 実機準備 — 2026-10-11

**ローカル依存・artifact検査 PASS / Golden Run BLOCKED / NOT_RUN。**
検査対象は #579 HEAD `7b768f9dfe98d4037f3573bdfaa59ee15dc012e7` の独立子ブランチ。
#575/#576、#537/#545、#577、#578、#579 はいずれも統合済みと扱わない。
main、親Draft、Lane A/B/C、S49 Action、S60推論権限を変更しない。

## 実機と再現手順

検査時の実体: Windows 11 Home build 26200、WSL2 Linux 6.18.33.2、
RTX 3060 12288 MiB、driver 591.44、CPython 3.12.3、
Node v22.22.2、OpenJDK 21.0.12.1、Mineflayer 4.39.0。
Nodeは通常PATHにない。既存S60-B1 venvはhttpx不足のため流用しない。

このホストの専用runtimeは `/home/rinsa/.local/share/relay-self/rsee-1.0-20261011`。
別ホストではローカルパスを明示的に再拘束する。必要パッケージは
[requirements-host.lock.txt](../experiments/standard_env/requirements-host.lock.txt) に全解決版を固定。
これはバージョンlockでありwheelバイト同一性の証明ではない。

```bash
export PATH=/home/rinsa/.nvm/versions/node/v22.22.2/bin:$PATH
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD"
# 別の新規runtimeを準備する場合のみ。失敗したら停止、再試行しない。
python3.12 -m venv /absolute/new/runtime/venv
/absolute/new/runtime/venv/bin/python -m pip install --retries 0 \
  -r experiments/standard_env/requirements-host.lock.txt
npm ci --prefix adapters/mineflayer --ignore-scripts --omit=dev \
  --no-audit --no-fund --fetch-retries=0
```

node_modulesはこのworktreeに物理インストールする。既存World・node_modulesへの
symlinkやNODE_OPTIONS shimは使用しない。preflightはインストールを行わない。
`--verify-product` は元ランチャーのPython/S49 import、bridge起点の実Mineflayer・
minecraft-protocol importだけを再利用する。Node/Javaの版検査とNode importは実行するが、
createBot、Javaサーバー、llama-server、モデルPOSTは実行しない。

```bash
/home/rinsa/.local/share/relay-self/rsee-1.0-20261011/venv/bin/python \
  -m experiments.standard_env.preflight --verify-local --verify-product \
  --model /home/rinsa/models/gguf/gemma-4-12B-it-Q4_K_M.gguf \
  --llama-server /home/rinsa/src/llama.cpp/build/bin/llama-server \
  --llama-sha256 ad5d4787bc739ad88a55b614c18d29580b3ec071cad632edb0ebb42b89f78536 \
  --minecraft-jar /home/rinsa/.local/share/relay-self/rsee-1.0-20261011/minecraft-1.21.8.jar \
  --minecraft-sha256 2349d9a8f0d4be2c40e7692890ef46a4b07015e7955b075460d02793be7fbbe7
```

このexit 0はファイル・依存検査だけのPASS。出力の`golden_run_readiness=BLOCKED`、
`physical_execution_authorized=false`を必ず独立して読む。

## artifactと設定の拘束

| 項目 | 検査結果と限界 |
|---|---|
| GGUF | 7,381,384,864 bytes、SHA256 `c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed`、canonical profile一致 |
| llama-server | SHA256 `ad5d4787bc739ad88a55b614c18d29580b3ec071cad632edb0ebb42b89f78536` |
| llama.cpp tree | `e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d`、検査時clean。commitだけではビルド再現性を証明しない |
| CUDA | ldd解決実体とlibcuda、libdxcore、libnvidia-ml等25 artifactをSHA256化。ロード済みmaps/実GPU計算の証明ではない |
| Minecraft jar | 57,555,044 bytes、上記SHA256。内部version.jsonは1.21.8/Java21。新規取得した公式version metadataのSHA1 `6bce4ef400e4efaa63a13d5e6f6b500be969ef81`・sizeと一致 |
| ctx/slot/shift | 元owned launcherソースのRSEE opt-in: ctx8192、parallel1、gpu layers999、no-context-shift。静的auditでgaps=[] |
| Thinking/cache | 元S60-B1 opt-in requestはreasoning_effort=none、cache_prompt=false。実バイナリでの意味・実wireは未検証 |
| schema | 現製品L2は自由文コメント。strict JSON-schemaの物理資格はない |

llama-serverの`--help`/`--version`を含め、モデルバイナリは一度も起動していない。
1234/25565 listenerは検査時空。実行直前に再確認する必要がある。

## World標準化の契約と未解決境界

元S49は毎回公式jarを取得し、S31Aのconfigを用いてTemporaryDirectoryを作成・削除する。
ローカルで確認したjarを渡す引数、固定level-seed、snapshot保存・復元の入力がない。
元設定はloopback25565、flat、creative、force-gamemode、easy、max-players2、
spawn-protection0、simulation/view-distance4、online-mode=false、RCON=false。
S49 stagingはdoMobSpawning=false、zombie削除と3回のNoAI zombie召喚を行う。
初期Health/Food/位置/時刻/天候・その他gamerulesは固定値として証明されていない。

標準化候補は **固定seed 575** と上記既存設定を用いた新規disposable World。
まだ元runnerに接続されていない候補であり、生成済みsnapshotや初期状態を捏造しない。
実機Golden Run準備完了には製品World owner側で次を拘束する必要がある:

1. 公式確認済みjarのexact SHA256を元S49実行jarに拘束し、不一致ならJava起動前に停止。
2. level-seed=575を元configに明示し、native level.datの実seedと生成設定を保存。
3. Health/Food/位置/向き、inventory、time/weather、全gamerulesをnative初期観測で保存。
   他gamerulesを暗黙変更せず、意図した値と実値を明示する。
4. 初期状態確定後にserverを正常停止してWorld全ファイルの相対パス・size・SHA256 manifestを
   新規run専用領域に保存。動作中Worldのコピーを基準snapshotにしない。
5. リセットは停止済み・新規disposable run領域への検証済みsnapshotコピーだけ。
   コピー前後manifest一致を確認。既存Worldを上書きせず、失敗runを保存して再試行しない。
   snapshotがない現在はリセットを実施しない。

本作業はサーバー起動禁止のため、初期Worldの生成・native照合・snapshot捕捉はNOT_RUN。
この子DraftではWorld/Action ownerの実装を代替しない。

## Golden Run コマンド候補 — 現在実行禁止

下記は**元製品owned runner**の実CLIに対応するが、現時点では標準World条件が未充足。
元runner自身はこれらWorld差分を停止ゲートにしていないため、コマンドを実行しない。
標準化修正をレビュー後、exact HEAD/binary/libs/jar/grantsを再拘束するまでBLOCKED。

```bash
# 本準備では実行しない。FRESH_DIRは新規かつ空のGit外証拠ディレクトリ。
export PATH=/home/rinsa/.nvm/versions/node/v22.22.2/bin:$PATH
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD"
/home/rinsa/.local/share/relay-self/rsee-1.0-20261011/venv/bin/python \
  -m adapters.mineflayer.self_owned_llama \
  --rsee-required --run-disposable \
  --confirm SELF-DEMO-I-OWN-DISPOSABLE-WORLD --output-dir "$FRESH_DIR" \
  --llama-server /home/rinsa/src/llama.cpp/build/bin/llama-server \
  --gguf /home/rinsa/models/gguf/gemma-4-12B-it-Q4_K_M.gguf \
  --gguf-sha256 c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed \
  --model-alias rsee-gemma4 --model-port 1234 --ctx-size 8192 --gpu-layers 999 \
  --ready-timeout 90 --model-timeout 12
```

必要な許可は、新exact HEAD・artifact・出力先に拘束された一回限定のモデル/GPU起動と
一回のL2推論、disposable World起動・元S49 Actionの実行許可、独立したMinecraft EULA同意。
既存Issue・Draft・過去S49/S60結果やローカルPASSは今回の許可にならない。
標準化追加のWorld初期化/snapshot捕捉も許可範囲に明記する。

停止条件: preflight差分、import不足、artifact/hash差分、既存listener/lease、
モデルreadiness期限、alias/props/slots不一致、World初期状態不一致、request controls差分、
原native Action terminal/receipt欠落、backendまたはcleanup不明。
一回目のterminalを保持し、自動再起動・再POST・fallback・失敗runリセットを禁止する。
元readiness処理はhealth/modelsを反復観測するがモデル推論の再試行ではない。
現在のprops/slots gateはcontext_shift実値、Thinking意味、template/hash、GPU offload実値を
全ては確認しない。これも実行前の拘束・将来native証拠の対象。

所有PID/groupのみの停止とwaitを行い、元receipt、server log、native_report.json、
live_l2.jsonl、self_trace.jsonl、Memory、World manifest、raw provider envelope、
loaded-library maps、前後PID/listener/GPU観測を保存する。
Ctrl-CやPID終了だけをSTOP_ACK/VRAM解放/科学的成功と報告しない。

## 証拠保存

今回のGit外保存先: `/home/rinsa/.local/share/relay-self/rsee-1.0-20261011/evidence`。
artifacts.json、ldd.txt、mojang-version.json、jar-provenance.json、python-freeze.txt、
local-preflight.jsonとexact argv/exitを保存。jarは同runtime内へ独立コピーし、
既存E8 Worldのバイト・履歴は変更しない。
将来のGolden Runは別の新規run ID/ディレクトリを使用する。
