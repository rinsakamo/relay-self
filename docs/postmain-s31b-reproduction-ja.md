# S31-B WSL2 独立再現手順

Issue #391 の実環境契約に従う。資格化 runner は凍結 S31-A
`2f3af780508a51b66513043b4cfedf80d20ff1a0` の
`adapters/mineflayer/s31a_real_server_ci.py` を直接使用する。
S31-B 用サーバー、production bridge の複製や shim は追加しない。

## 開始前の authority と独立領域

毎回 Issue #391 全文、PR #368 の HEAD・Draft 状態・実測 receipt、main、
現在の PR/branches/ruleset、primary checkout の状態を fresh に読み、
凍結 SHA の不一致は実行前に停止して照合する。過去の SKIPPED は変更しない。
以下の `CHECKOUT` と `EVIDENCE` は、既存領域を指さない新しい絶対パスにする。

```bash
git status --porcelain=v1
git rev-parse HEAD HEAD^{tree}
gh issue view 391 --repo rinsakamo/relay-self --comments
gh pr view 368 --repo rinsakamo/relay-self --json headRefOid,isDraft,state
gh api repos/rinsakamo/relay-self/issues/368/comments
gh api repos/rinsakamo/relay-self/branches/main
gh api repos/rinsakamo/relay-self/rulesets
gh pr list --repo rinsakamo/relay-self --limit 100
git fetch origin self/postmain-s31a-ci-real-minecraft-20261009
git worktree add --detach "$CHECKOUT" 2f3af780508a51b66513043b4cfedf80d20ff1a0
mkdir "$EVIDENCE"
cd "$CHECKOUT"
git status --porcelain=v1
git rev-parse HEAD HEAD^{tree}
```

HEAD は上記 SHA、tree は `c7bb81a82416ac92505f3a643b3b009d8273731f`、
worktree は clean であること。実行が終わるまで追跡ファイルを編集しない。

## Runtime・port・注入の preflight

`uname -a`、`/etc/os-release`、Windows OS identity、Java/Node/Python/npm の
バージョン・実行ファイル SHA256、空きディスク、MemAvailable を証拠領域に保存する。
Java 21 / Linux Node 22 / Python 3.12 が必要。Windows Node を代用しない。
既存のユーザー管理 Node 22 の `bin` を PATH に追加してよい。
今回使用した Node は v22.22.2、Java は Ubuntu OpenJDK 21.0.12.1。
サーバーは 512MiB 初期 / 1536MiB 最大 heap。少なくとも 3GiB MemAvailable と
2GiB 空きディスクを見込み、満たさなければ BLOCKED として実行を止める。

```bash
python3 - <<'PY'
import os, platform, socket
if 'microsoft-standard-WSL2' not in platform.release():
    raise SystemExit('BLOCKED: intended WSL2 host required')
keys = ('NODE_OPTIONS', 'NODE_PATH', 'PYTHONPATH', 'PYTHONHOME',
        'JAVA_TOOL_OPTIONS', 'JDK_JAVA_OPTIONS', '_JAVA_OPTIONS')
if any(os.environ.get(k) for k in keys):
    raise SystemExit('BLOCKED: runtime injection environment present')
with socket.socket() as s:
    s.bind(('127.0.0.1', 25565))
    s.listen(1)
print('loopback preflight PASS')
PY
java -version
node --version
npm --version
python3 --version
free -m
df -h .
```

port 使用中なら BLOCKED。外部プロセスを停止せず、port を変更しない。
bind 検査後の競合は runner の server-start 結果と log で判断する。
権限昇格、preload、fake package、mock server、TLS 検証無効化、
取得 URL の差し替えは禁止。ネットワーク利用不可なら BLOCKED。

## Locked package と一回の実測

```bash
npm ci --omit=dev --no-audit --no-fund --prefix adapters/mineflayer > "$EVIDENCE/npm-ci.log" 2>&1
node --input-type=module -e "import {createRequire} from 'node:module'; const r=createRequire(new URL('./adapters/mineflayer/bridge.mjs',import.meta.url)); const p=r.resolve('mineflayer/package.json'); console.log(p,r(p).version); if(r(p).version!=='4.39.0')process.exit(2)"
PYTHONPATH=src python3 -B -m adapters.mineflayer.s31a_real_server_ci --help
PYTHONPATH=src S31A_REAL_SERVER_CI=1 python3 -B -m adapters.mineflayer.s31a_real_server_ci \
  --report "$EVIDENCE/s31a-report.json" \
  --server-log "$EVIDENCE/minecraft-server.log" > "$EVIDENCE/runner.log" 2>&1
s31b_exit=$?
printf '%s\n' "$s31b_exit" > "$EVIDENCE/runner-exit-code.txt"
```

各コマンドの exit code を保存し、`npm ci`、package identity、runtime 検査失敗時は
runner に進まない。この手順には自動再試行を置かない。
EULA acceptance はこの要求で認められた使い捨て World に限定される。
runner は公式 Mojang HTTPS metadata / server.jar の version、size、SHA1、
Java major を検査し、実 Node bridge と localhost TCP を起動する。
サーバーは offline-auth / loopback / RCON 無効。永続 World を扱わない。
一回の runner 内の最大五回 target 観測は凍結契約の bounded polling であり、
失敗後に runner を再起動する retry ではない。

## 結果保存と判定

JSON 原本、server log、runner stdout/stderr、各 identity、コマンド/exit code、
実測 HEAD/tree、pre/post checkout 状態、後処理の port 状態を保存し SHA256 を記録する。
元 JSON の `milestone=S31-A` / `QUALIFIED_LOCAL_CI_SANDBOX` は凍結 runner の文字列。
書き換えず、別 S31-B envelope に LocalCodex / WSL2 provenance を記録する。
PR に含める証拠は個人パスや秘密を検査してから公開する。

- PASS: 実 World、相関 ID、単一 zombie、座標と約2m距離、native session/seq、
  非切詰め16m coverage、重複拒否、両 process exit 0 が原本から成立。
- BLOCKED: runtime、port、権限、ネットワーク、公式 artifact、server bootstrap 不可。
  起動できなかった場合は `PENDING_LOCAL_EXECUTION` も明記する。
- FAIL: 解釈可能な環境で protocol/native evidence/teardown 契約不成立。

凍結 runner は test-owned process の shutdown を担当する。
外部プロセス停止や隠れた再実行を行わない。非ゼロ終了や cleanup 不明は PASS にしない。
次は既存 receipt の offline consistency 検査だけで、物理資格化を開始しない。

```bash
python3 -B -m adapters.mineflayer.s31b_receipt_check "$EVIDENCE/s31a-report.json"
```

S31-A 二つの CI artifact の原本を読み、公式 jar identity / versions / distance /
correlation / exit を比較する。World の spawn、entity ID、非要求 frame 数は変動し得る。
チェックサムは保存 byte の整合性であり独立暗号学的 source attestation ではない。
