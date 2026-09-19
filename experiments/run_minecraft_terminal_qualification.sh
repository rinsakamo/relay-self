#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
REPO_ROOT="$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)"
EVIDENCE_ROOT=""
JAVA="/tmp/relay-self-138-java25/jdk-25.0.4.1+1/bin/java"
MINECRAFT_JAR="/tmp/relay-self-minecraft-138/server.jar"
MINECRAFT_SOURCE_ROOT="/tmp/relay-self-minecraft-138"
NODE="/home/rinsa/.nvm/versions/node/v22.22.2/bin/node"
NPM="/home/rinsa/.nvm/versions/node/v22.22.2/bin/npm"
LLAMA="/home/rinsa/src/llama.cpp/build/bin/llama-server"
MODEL="/home/rinsa/models/gguf/gemma-4-12B-it-Q4_K_M.gguf"
REMOTE_REPO="https://github.com/rinsakamo/relay-self.git"
MINECRAFT_PORT=25565
LLAMA_PORT=8080
MINECRAFT_VERSION=26.1
USERNAME=RelaySelf
SELF_ID=relay-self-141

while (($# > 0)); do
  case "$1" in
    --repo-root) REPO_ROOT="$2"; shift 2 ;;
    --evidence-root) EVIDENCE_ROOT="$2"; shift 2 ;;
    --java) JAVA="$2"; shift 2 ;;
    --minecraft-jar) MINECRAFT_JAR="$2"; shift 2 ;;
    --minecraft-source-root) MINECRAFT_SOURCE_ROOT="$2"; shift 2 ;;
    --minecraft-port) MINECRAFT_PORT="$2"; shift 2 ;;
    --llama-port) LLAMA_PORT="$2"; shift 2 ;;
    --minecraft-version) MINECRAFT_VERSION="$2"; shift 2 ;;
    --node) NODE="$2"; shift 2 ;;
    --npm) NPM="$2"; shift 2 ;;
    --llama) LLAMA="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    --username) USERNAME="$2"; shift 2 ;;
    --self-id) SELF_ID="$2"; shift 2 ;;
    *)
      printf 'unknown or incomplete argument: %s\n' "$1" >&2
      exit 2
      ;;
  esac
done

if [[ -z "$EVIDENCE_ROOT" ]]; then
  printf '%s\n' '--evidence-root is required; create a new evidence root before the one-shot run' >&2
  exit 2
fi

REPO_ROOT="$(cd "$REPO_ROOT" && pwd)"
EVIDENCE_ROOT="$(mkdir -p "$EVIDENCE_ROOT" && cd "$EVIDENCE_ROOT" && pwd)"
SERVER_ROOT="$EVIDENCE_ROOT/minecraft"
SERVER_CONTROL="$EVIDENCE_ROOT/server.stdin"
SERVER_LOG="$EVIDENCE_ROOT/minecraft-server.log"
LLAMA_LOG="$EVIDENCE_ROOT/llama-server.log"
LLAMA_ORIGIN="http://127.0.0.1:$LLAMA_PORT"
AUTHORITY_ROOT="$EVIDENCE_ROOT/authority"
AUTHORITY_JSON="$EVIDENCE_ROOT/authority.json"
RUNTIME_ARTIFACTS_JSON="$EVIDENCE_ROOT/generated-runtime-artifacts.json"

capture_authority() {
  local label="$1"
  local target="$AUTHORITY_ROOT/$label"
  local working_tree
  local local_head
  local local_tree
  local remote_line
  local remote_main

  mkdir -p "$target"
  working_tree="$(git -C "$REPO_ROOT" status --porcelain)"
  printf '%s\n' "$working_tree" >"$target/working-tree.txt"
  if [[ -n "$working_tree" ]]; then
    printf '%s\n' "tracked checkout is not clean before authority capture" >&2
    return 1
  fi
  if ! local_head="$(git -C "$REPO_ROOT" rev-parse HEAD)"; then
    return 1
  fi
  if ! local_tree="$(git -C "$REPO_ROOT" rev-parse 'HEAD^{tree}')"; then
    return 1
  fi
  if ! remote_line="$(git ls-remote "$REMOTE_REPO" refs/heads/main)"; then
    return 1
  fi
  remote_main="$(printf '%s\n' "$remote_line" | awk 'NF { print $1; exit }')"
  if [[ -z "$remote_main" ]]; then
    printf '%s\n' 'remote main HEAD was not returned' >&2
    return 1
  fi
  printf '%s\n' "$local_head" >"$target/local-head.txt"
  printf '%s\n' "$local_tree" >"$target/local-tree.txt"
  printf '%s\n' "$remote_main" >"$target/remote-main-head.txt"
  if [[ "$local_head" != "$remote_main" ]]; then
    printf 'local HEAD %s does not equal remote main %s\n' "$local_head" "$remote_main" >&2
    return 1
  fi

  if ! gh api "repos/rinsakamo/relay-self/rulesets/23442682" \
      >"$target/ruleset.json"; then
    return 1
  fi
  if ! gh pr list \
      --repo rinsakamo/relay-self \
      --state open \
      --base main \
      --limit 100 \
      --json number,title,state,headRefName,baseRefName,updatedAt,url \
      >"$target/open-prs.json"; then
    return 1
  fi
  if ! gh issue list \
      --repo rinsakamo/relay-self \
      --state open \
      --limit 100 \
      --json number,title,state,labels,updatedAt,url \
      >"$target/open-issues.json"; then
    return 1
  fi
  for issue_number in 136 138 140 141; do
    if ! gh api "repos/rinsakamo/relay-self/issues/$issue_number" \
        >"$target/issue-$issue_number.json"; then
      return 1
    fi
    if ! gh api --paginate --slurp \
        "repos/rinsakamo/relay-self/issues/$issue_number/comments" \
        >"$target/issue-$issue_number-comments.json"; then
      return 1
    fi
  done

  python3 - "$target" "$REPO_ROOT" "$REMOTE_REPO" "$local_head" "$local_tree" "$remote_main" "$AUTHORITY_JSON" <<'PY'
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

target = Path(sys.argv[1])
repo = Path(sys.argv[2])
remote = sys.argv[3]
local_head = sys.argv[4]
local_tree = sys.argv[5]
remote_main = sys.argv[6]
combined_path = Path(sys.argv[7])

def load(name):
    return json.loads((target / name).read_text(encoding="utf-8"))

tracked = subprocess.run(
    ["git", "-C", str(repo), "ls-files", ".ai/README.md", "docs"],
    check=True,
    capture_output=True,
    text=True,
).stdout.splitlines()
authority_files = []
for relative in tracked:
    path = repo / relative
    if not path.is_file():
        continue
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    authority_files.append({"path": relative, "sha256": digest})

authority = {
    "captured_at": datetime.now(timezone.utc).isoformat(),
    "repository": {
        "remote": remote,
        "local_head": local_head,
        "local_tree": local_tree,
        "remote_main_head": remote_main,
        "working_tree": (target / "working-tree.txt").read_text(encoding="utf-8"),
    },
    "ruleset": load("ruleset.json"),
    "open_prs": load("open-prs.json"),
    "open_issues": load("open-issues.json"),
    "issues": {
        str(number): {
            "issue": load(f"issue-{number}.json"),
            "comments": load(f"issue-{number}-comments.json"),
        }
        for number in (136, 138, 140, 141)
    },
    "authority_file_sha256": authority_files,
}
combined_path.write_text(
    json.dumps(authority, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
(target / "authority.json").write_text(
    json.dumps(authority, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY
}

if [[ ! -x "$JAVA" || ! -x "$NODE" || ! -x "$NPM" || ! -x "$LLAMA" ]]; then
  printf '%s\n' 'runtime identity path is not executable' >&2
  exit 2
fi
if [[ ! -f "$MINECRAFT_JAR" || ! -f "$MODEL" ]]; then
  printf '%s\n' 'Minecraft jar or GGUF model path is missing' >&2
  exit 2
fi
if [[ ! "$USERNAME" =~ ^[A-Za-z0-9_]{1,16}$ ]]; then
  printf '%s\n' 'username must be a Minecraft-safe offline username' >&2
  exit 2
fi

export PATH="$(dirname "$NODE"):$PATH"
export PYTHONPATH="$REPO_ROOT/src:$REPO_ROOT"
export PYTHONDONTWRITEBYTECODE=1

PACKAGE_LOCK="$REPO_ROOT/adapters/mineflayer/package-lock.json"
if [[ -f "$PACKAGE_LOCK" ]]; then
  if git -C "$REPO_ROOT" ls-files --error-unmatch adapters/mineflayer/package-lock.json >/dev/null 2>&1; then
    printf '%s\n' 'package-lock.json is tracked unexpectedly; refusing to alter the checkout' >&2
    exit 2
  fi
  if [[ -e "$EVIDENCE_ROOT/mineflayer-package-lock.json" ]]; then
    printf '%s\n' 'generated package-lock evidence path already exists' >&2
    exit 2
  fi
  mv "$PACKAGE_LOCK" "$EVIDENCE_ROOT/mineflayer-package-lock.json"
fi
python3 - "$RUNTIME_ARTIFACTS_JSON" "$REPO_ROOT" <<'PY'
import json
import sys
from pathlib import Path

output = Path(sys.argv[1])
repo = Path(sys.argv[2])
output.write_text(
    json.dumps(
        {
            "artifacts": [
                {
                    "kind": "node_modules",
                    "path": str(repo / "adapters" / "mineflayer" / "node_modules"),
                    "tracked_source": False,
                    "gitignored": True,
                },
                {
                    "kind": "generated_package_lock",
                    "path": str(output.parent / "mineflayer-package-lock.json"),
                    "tracked_source": False,
                    "relocated_out_of_checkout": (output.parent / "mineflayer-package-lock.json").is_file(),
                },
            ]
        },
        indent=2,
        sort_keys=True,
    )
    + "\n",
    encoding="utf-8",
)
PY

if ! capture_authority initial; then
  printf '%s\n' 'pre-spend authority capture failed; terminal transaction not started' >&2
  exit 1
fi

MINECRAFT_PID=""
LLAMA_PID=""
SERVER_FD_OPEN=0

cleanup() {
  set +e
  if [[ -n "$MINECRAFT_PID" ]] && kill -0 "$MINECRAFT_PID" 2>/dev/null; then
    if [[ "$SERVER_FD_OPEN" == 1 ]]; then
      printf 'stop\n' >&3
    fi
    for _ in $(seq 1 20); do
      if ! kill -0 "$MINECRAFT_PID" 2>/dev/null; then
        break
      fi
      sleep 1
    done
    if kill -0 "$MINECRAFT_PID" 2>/dev/null; then
      kill "$MINECRAFT_PID" 2>/dev/null
    fi
    wait "$MINECRAFT_PID" 2>/dev/null
  fi
  if [[ "$SERVER_FD_OPEN" == 1 ]]; then
    exec 3>&-
    SERVER_FD_OPEN=0
  fi
  if [[ -n "$LLAMA_PID" ]] && kill -0 "$LLAMA_PID" 2>/dev/null; then
    kill "$LLAMA_PID" 2>/dev/null
    wait "$LLAMA_PID" 2>/dev/null
  fi
}
trap cleanup EXIT INT TERM

python3 -m experiments.minecraft_terminal_qualification \
  --phase prepare \
  --repo-root "$REPO_ROOT" \
  --evidence-root "$EVIDENCE_ROOT" \
  --server-root "$SERVER_ROOT" \
  --server-source-root "$MINECRAFT_SOURCE_ROOT" \
  --minecraft-jar "$MINECRAFT_JAR" \
  --minecraft-version "$MINECRAFT_VERSION" \
  --minecraft-port "$MINECRAFT_PORT" \
  --model "$MODEL"

if [[ -e "$SERVER_CONTROL" ]]; then
  printf '%s\n' "server control path already exists: $SERVER_CONTROL" >&2
  exit 2
fi
mkfifo "$SERVER_CONTROL"
(
  cd "$SERVER_ROOT"
  "$JAVA" -jar server.jar --nogui
) <"$SERVER_CONTROL" >"$SERVER_LOG" 2>&1 &
MINECRAFT_PID=$!
exec 3>"$SERVER_CONTROL"
SERVER_FD_OPEN=1

(
  "$LLAMA" \
    -m "$MODEL" \
    --host 127.0.0.1 \
    --port "$LLAMA_PORT" \
    -ngl 999 \
    -c 8192
) >"$LLAMA_LOG" 2>&1 &
LLAMA_PID=$!

for _ in $(seq 1 180); do
  if curl --max-time 2 --silent --fail "$LLAMA_ORIGIN/health" \
      | grep -Eq '"status"[[:space:]]*:[[:space:]]*"ok"'; then
    break
  fi
  if ! kill -0 "$LLAMA_PID" 2>/dev/null; then
    printf '%s\n' 'llama.cpp exited before health readiness' >&2
    exit 1
  fi
  sleep 1
done

if ! curl --max-time 2 --silent --fail "$LLAMA_ORIGIN/health" \
    | grep -Eq '"status"[[:space:]]*:[[:space:]]*"ok"'; then
  printf '%s\n' 'llama.cpp /health did not become ready' >&2
  exit 1
fi

if ! capture_authority final; then
  printf '%s\n' 'final pre-spend authority capture failed; terminal transaction not started' >&2
  exit 1
fi

python3 -m experiments.minecraft_terminal_qualification \
  --phase preflight \
  --repo-root "$REPO_ROOT" \
  --evidence-root "$EVIDENCE_ROOT" \
  --server-root "$SERVER_ROOT" \
  --server-log "$SERVER_LOG" \
  --minecraft-version "$MINECRAFT_VERSION" \
  --minecraft-port "$MINECRAFT_PORT" \
  --minecraft-pid "$MINECRAFT_PID" \
  --java "$JAVA" \
  --node "$NODE" \
  --npm "$NPM" \
  --llama "$LLAMA" \
  --llama-origin "$LLAMA_ORIGIN" \
  --llama-port "$LLAMA_PORT" \
  --llama-pid "$LLAMA_PID" \
  --model "$MODEL" \
  --served-model "$MODEL" \
  --authority-path "$AUTHORITY_JSON" \
  --runtime-artifacts-path "$RUNTIME_ARTIFACTS_JSON" \
  --self-id "$SELF_ID" \
  --persistent-path "$EVIDENCE_ROOT/persistent-cognition.json"

{
  printf 'cd %q\n' "$REPO_ROOT"
  printf 'bash %q' "$SCRIPT_PATH"
  printf ' --repo-root %q' "$REPO_ROOT"
  printf ' --evidence-root %q' "$EVIDENCE_ROOT"
  printf ' --java %q' "$JAVA"
  printf ' --minecraft-jar %q' "$MINECRAFT_JAR"
  printf ' --minecraft-source-root %q' "$MINECRAFT_SOURCE_ROOT"
  printf ' --minecraft-port %q' "$MINECRAFT_PORT"
  printf ' --llama-port %q' "$LLAMA_PORT"
  printf ' --minecraft-version %q' "$MINECRAFT_VERSION"
  printf ' --node %q' "$NODE"
  printf ' --npm %q' "$NPM"
  printf ' --llama %q' "$LLAMA"
  printf ' --model %q' "$MODEL"
  printf ' --username %q' "$USERNAME"
  printf ' --self-id %q\n' "$SELF_ID"
} >"$EVIDENCE_ROOT/terminal-command.txt"

COMMON_ARGS=(
  --repo-root "$REPO_ROOT"
  --evidence-root "$EVIDENCE_ROOT"
  --minecraft-version "$MINECRAFT_VERSION"
  --minecraft-port "$MINECRAFT_PORT"
  --username "$USERNAME"
  --node "$NODE"
  --llama-origin "$LLAMA_ORIGIN"
  --llama-port "$LLAMA_PORT"
  --model "$MODEL"
  --served-model "$MODEL"
  --server-control "$SERVER_CONTROL"
  --self-id "$SELF_ID"
  --persistent-path "$EVIDENCE_ROOT/persistent-cognition.json"
)

python3 -m experiments.minecraft_terminal_qualification \
  --phase first \
  "${COMMON_ARGS[@]}"

python3 -m experiments.minecraft_terminal_qualification \
  --phase restart \
  "${COMMON_ARGS[@]}"

python3 -m json.tool "$EVIDENCE_ROOT/terminal-report.json" >"$EVIDENCE_ROOT/terminal-report.pretty.json"
printf '%s\n' "terminal evidence: $EVIDENCE_ROOT/terminal-report.json"
