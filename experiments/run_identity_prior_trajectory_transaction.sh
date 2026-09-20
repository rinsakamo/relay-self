#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_PATH="$SCRIPT_DIR/$(basename "$0")"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
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
SELF_ID=relay-self-220

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
    *) printf 'unknown or incomplete argument: %s\n' "$1" >&2; exit 2 ;;
  esac
done

if [[ -z "$EVIDENCE_ROOT" ]]; then
  printf '%s\n' '--evidence-root is required and must be a new empty directory' >&2
  exit 2
fi

REPO_ROOT="$(cd "$REPO_ROOT" && pwd)"
mkdir -p "$EVIDENCE_ROOT"
EVIDENCE_ROOT="$(cd "$EVIDENCE_ROOT" && pwd)"
if find "$EVIDENCE_ROOT" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then
  printf 'evidence root must be empty: %s\n' "$EVIDENCE_ROOT" >&2
  exit 2
fi

if [[ ! -x "$JAVA" || ! -x "$NODE" || ! -x "$NPM" || ! -x "$LLAMA" ]]; then
  printf '%s\n' 'runtime identity path is not executable' >&2
  exit 2
fi
if [[ ! -f "$MINECRAFT_JAR" || ! -f "$MODEL" ]]; then
  printf '%s\n' 'Minecraft jar or GGUF model path is missing' >&2
  exit 2
fi
if [[ "$SELF_ID" != "relay-self-220" ]]; then
  printf '%s\n' '#220 self-id is frozen as relay-self-220' >&2
  exit 2
fi

SERVER_ROOT="$EVIDENCE_ROOT/minecraft"
SERVER_CONTROL="$EVIDENCE_ROOT/server.stdin"
SERVER_LOG="$EVIDENCE_ROOT/minecraft-server.log"
LLAMA_LOG="$EVIDENCE_ROOT/llama-server.log"
LLAMA_ORIGIN="http://127.0.0.1:$LLAMA_PORT"
AUTHORITY_ROOT="$EVIDENCE_ROOT/authority"
AUTHORITY_JSON="$EVIDENCE_ROOT/authority.json"
RUNTIME_ARTIFACTS_JSON="$EVIDENCE_ROOT/generated-runtime-artifacts.json"

export PATH="$(dirname "$NODE"):$PATH"
export PYTHONPATH="$REPO_ROOT/src:$REPO_ROOT"
export PYTHONDONTWRITEBYTECODE=1

capture_authority() {
  local label="$1"
  local target="$AUTHORITY_ROOT/$label"
  local local_head
  local local_tree
  local remote_main
  mkdir -p "$target"

  git -C "$REPO_ROOT" status --porcelain >"$target/working-tree.txt"
  if [[ -s "$target/working-tree.txt" ]]; then
    printf '%s\n' 'tracked checkout is not clean' >&2
    return 1
  fi
  local_head="$(git -C "$REPO_ROOT" rev-parse HEAD)"
  local_tree="$(git -C "$REPO_ROOT" rev-parse 'HEAD^{tree}')"
  remote_main="$(git ls-remote "$REMOTE_REPO" refs/heads/main | awk 'NF {print $1; exit}')"
  printf '%s\n' "$local_head" >"$target/local-head.txt"
  printf '%s\n' "$local_tree" >"$target/local-tree.txt"
  printf '%s\n' "$remote_main" >"$target/remote-main-head.txt"
  [[ "$local_head" == "$remote_main" ]] || return 1

  gh api repos/rinsakamo/relay-self/rulesets/23442682 >"$target/ruleset.json"
  [[ "$(gh api repos/rinsakamo/relay-self/rulesets/23442682 --jq .enforcement)" == "active" ]] || return 1
  gh pr list --repo rinsakamo/relay-self --state open --base main --limit 100 \
    --json number,title,headRefName,baseRefName,updatedAt,url >"$target/open-prs.json"
  [[ "$(gh pr list --repo rinsakamo/relay-self --state open --base main --limit 100 --json number --jq length)" == "0" ]] || return 1

  for issue_number in 88 141 201 220; do
    gh api "repos/rinsakamo/relay-self/issues/$issue_number" >"$target/issue-$issue_number.json"
    gh api --paginate "repos/rinsakamo/relay-self/issues/$issue_number/comments" >"$target/issue-$issue_number-comments.json"
  done

  [[ "$(gh api repos/rinsakamo/relay-self/issues/201 --jq .state)" == "closed" ]] || return 1
  [[ "$(gh api repos/rinsakamo/relay-self/issues/201 --jq .state_reason)" == "completed" ]] || return 1
  [[ "$(gh api repos/rinsakamo/relay-self/issues/141 --jq .state)" == "closed" ]] || return 1
  [[ "$(gh api repos/rinsakamo/relay-self/issues/220 --jq .state)" == "open" ]] || return 1
  gh api --paginate repos/rinsakamo/relay-self/issues/220/comments --jq '.[].body' \
    | grep -q 'NO MATERIAL CONFLICT' || return 1

  printf '{"label":"%s","local_head":"%s","local_tree":"%s","remote_main":"%s"}\n' \
    "$label" "$local_head" "$local_tree" "$remote_main" >"$AUTHORITY_JSON"
}

PACKAGE_LOCK="$REPO_ROOT/adapters/mineflayer/package-lock.json"
if [[ -f "$PACKAGE_LOCK" ]]; then
  if git -C "$REPO_ROOT" ls-files --error-unmatch adapters/mineflayer/package-lock.json >/dev/null 2>&1; then
    printf '%s\n' 'package-lock.json is tracked unexpectedly' >&2
    exit 2
  fi
  mv "$PACKAGE_LOCK" "$EVIDENCE_ROOT/mineflayer-package-lock.json"
fi
printf '{"node_modules":"%s","package_lock_relocated":%s}\n' \
  "$REPO_ROOT/adapters/mineflayer/node_modules" \
  "$(test -f "$EVIDENCE_ROOT/mineflayer-package-lock.json" && echo true || echo false)" \
  >"$RUNTIME_ARTIFACTS_JSON"

python3 -m experiments.identity_prior_trajectory_transaction \
  --phase plan --repo-root "$REPO_ROOT" --evidence-root "$EVIDENCE_ROOT" \
  --model "$MODEL" --self-id "$SELF_ID"

capture_authority initial || {
  printf '%s\n' 'pre-spend authority capture failed; transaction not started' >&2
  exit 1
}

python3 -m experiments.minecraft_terminal_qualification \
  --phase prepare --repo-root "$REPO_ROOT" --evidence-root "$EVIDENCE_ROOT" \
  --server-root "$SERVER_ROOT" --server-source-root "$MINECRAFT_SOURCE_ROOT" \
  --minecraft-jar "$MINECRAFT_JAR" --minecraft-version "$MINECRAFT_VERSION" \
  --minecraft-port "$MINECRAFT_PORT" --model "$MODEL"

mkfifo "$SERVER_CONTROL"
MINECRAFT_PID=""
LLAMA_PID=""
SERVER_FD_OPEN=0

cleanup() {
  set +e
  if [[ -n "$MINECRAFT_PID" ]] && kill -0 "$MINECRAFT_PID" 2>/dev/null; then
    [[ "$SERVER_FD_OPEN" == 1 ]] && printf 'stop\n' >&3
    for _ in $(seq 1 20); do
      kill -0 "$MINECRAFT_PID" 2>/dev/null || break
      sleep 1
    done
    kill "$MINECRAFT_PID" 2>/dev/null || true
    wait "$MINECRAFT_PID" 2>/dev/null || true
  fi
  if [[ "$SERVER_FD_OPEN" == 1 ]]; then exec 3>&-; fi
  if [[ -n "$LLAMA_PID" ]] && kill -0 "$LLAMA_PID" 2>/dev/null; then
    kill "$LLAMA_PID" 2>/dev/null || true
    wait "$LLAMA_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

(cd "$SERVER_ROOT" && "$JAVA" -jar server.jar --nogui) \
  <"$SERVER_CONTROL" >"$SERVER_LOG" 2>&1 &
MINECRAFT_PID=$!
exec 3>"$SERVER_CONTROL"
SERVER_FD_OPEN=1

"$LLAMA" -m "$MODEL" --host 127.0.0.1 --port "$LLAMA_PORT" -ngl 999 -c 8192 \
  >"$LLAMA_LOG" 2>&1 &
LLAMA_PID=$!

for _ in $(seq 1 180); do
  if curl --max-time 2 --silent --fail "$LLAMA_ORIGIN/health" \
      | grep -Eq '"status"[[:space:]]*:[[:space:]]*"ok"'; then break; fi
  kill -0 "$LLAMA_PID" 2>/dev/null || exit 1
  sleep 1
done
curl --max-time 2 --silent --fail "$LLAMA_ORIGIN/health" \
  | grep -Eq '"status"[[:space:]]*:[[:space:]]*"ok"'

capture_authority final || {
  printf '%s\n' 'final pre-spend authority capture failed; transaction not started' >&2
  exit 1
}

PREFLIGHT_ARGS=(
  --repo-root "$REPO_ROOT" --evidence-root "$EVIDENCE_ROOT"
  --server-root "$SERVER_ROOT" --server-log "$SERVER_LOG"
  --minecraft-version "$MINECRAFT_VERSION" --minecraft-port "$MINECRAFT_PORT"
  --minecraft-pid "$MINECRAFT_PID" --server-control "$SERVER_CONTROL"
  --java "$JAVA" --node "$NODE" --npm "$NPM" --llama "$LLAMA"
  --llama-origin "$LLAMA_ORIGIN" --llama-port "$LLAMA_PORT"
  --llama-pid "$LLAMA_PID" --model "$MODEL" --served-model "$MODEL"
  --authority-path "$AUTHORITY_JSON"
  --runtime-artifacts-path "$RUNTIME_ARTIFACTS_JSON" --self-id "$SELF_ID"
)
python3 -m experiments.identity_prior_trajectory_transaction \
  --phase preflight "${PREFLIGHT_ARGS[@]}"

printf 'bash %q --repo-root %q --evidence-root %q --model %q\n' \
  "$SCRIPT_PATH" "$REPO_ROOT" "$EVIDENCE_ROOT" "$MODEL" \
  >"$EVIDENCE_ROOT/canonical-command.txt"

python3 -m experiments.identity_prior_trajectory_transaction \
  --phase run --repo-root "$REPO_ROOT" --evidence-root "$EVIDENCE_ROOT" \
  --minecraft-version "$MINECRAFT_VERSION" --minecraft-port "$MINECRAFT_PORT" \
  --username "$USERNAME" --node "$NODE" --llama-origin "$LLAMA_ORIGIN" \
  --llama-port "$LLAMA_PORT" --model "$MODEL" --served-model "$MODEL" \
  --server-control "$SERVER_CONTROL" --self-id "$SELF_ID"

python3 -m json.tool "$EVIDENCE_ROOT/scientific-report.json" \
  >"$EVIDENCE_ROOT/scientific-report.pretty.json"
printf 'scientific evidence: %s\n' "$EVIDENCE_ROOT/scientific-report.json"
