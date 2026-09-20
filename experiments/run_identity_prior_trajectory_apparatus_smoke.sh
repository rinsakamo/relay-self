#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_PATH="$SCRIPT_DIR/$(basename "$0")"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
EVIDENCE_ROOT=""
JAVA="/tmp/relay-self-138-java25/jdk-25.0.4.1+1/bin/java"
MINECRAFT_JAR="/tmp/relay-self-minecraft-138/server.jar"
NODE="/home/rinsa/.nvm/versions/node/v22.22.2/bin/node"
NPM="/home/rinsa/.nvm/versions/node/v22.22.2/bin/npm"
MINECRAFT_PORT=25565
MINECRAFT_VERSION=26.1

while (($# > 0)); do
  case "$1" in
    --repo-root) REPO_ROOT="$2"; shift 2 ;;
    --evidence-root) EVIDENCE_ROOT="$2"; shift 2 ;;
    --java) JAVA="$2"; shift 2 ;;
    --minecraft-jar) MINECRAFT_JAR="$2"; shift 2 ;;
    --minecraft-port) MINECRAFT_PORT="$2"; shift 2 ;;
    --minecraft-version) MINECRAFT_VERSION="$2"; shift 2 ;;
    --node) NODE="$2"; shift 2 ;;
    --npm) NPM="$2"; shift 2 ;;
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

if [[ ! -x "$JAVA" || ! -x "$NODE" || ! -x "$NPM" ]]; then
  printf '%s\n' 'provider-free smoke runtime path is not executable' >&2
  exit 2
fi
if [[ ! -f "$MINECRAFT_JAR" ]]; then
  printf '%s\n' 'Minecraft jar path is missing' >&2
  exit 2
fi
if [[ "$MINECRAFT_VERSION" != "26.1" ]]; then
  printf '%s\n' '#220 apparatus smoke is frozen to Minecraft 26.1' >&2
  exit 2
fi

export PATH="$(dirname "$NODE"):$PATH"
export PYTHONPATH="$REPO_ROOT/src:$REPO_ROOT"
export PYTHONDONTWRITEBYTECODE=1

MINEFLAYER_DIR="$REPO_ROOT/adapters/mineflayer"
PACKAGE_LOCK="$MINEFLAYER_DIR/package-lock.json"
SERVER_ROOT="$EVIDENCE_ROOT/minecraft"
SERVER_CONTROL="$EVIDENCE_ROOT/server.stdin"
SERVER_LOG="$EVIDENCE_ROOT/minecraft-server.log"
NPM_LOG="$EVIDENCE_ROOT/mineflayer-npm-ci.log"
RUNTIME_JSON="$EVIDENCE_ROOT/apparatus-smoke-runtime.json"

if [[ -n "$(git -C "$REPO_ROOT" status --porcelain)" ]]; then
  printf '%s\n' 'apparatus smoke requires a clean checkout' >&2
  exit 2
fi
git -C "$REPO_ROOT" rev-parse HEAD >"$EVIDENCE_ROOT/local-head.txt"
git -C "$REPO_ROOT" rev-parse 'HEAD^{tree}' >"$EVIDENCE_ROOT/local-tree.txt"

if ! git -C "$REPO_ROOT" ls-files --error-unmatch adapters/mineflayer/package-lock.json >/dev/null 2>&1; then
  printf '%s\n' 'tracked Mineflayer package-lock.json is required' >&2
  exit 2
fi
cp "$PACKAGE_LOCK" "$EVIDENCE_ROOT/mineflayer-package-lock.json"

if ! (
  cd "$MINEFLAYER_DIR"
  "$NPM" ci --omit=dev --no-audit --no-fund
) >"$NPM_LOG" 2>&1; then
  printf '%s\n' 'Mineflayer npm ci failed; apparatus smoke not started' >&2
  exit 1
fi
if ! cmp -s "$PACKAGE_LOCK" "$EVIDENCE_ROOT/mineflayer-package-lock.json"; then
  printf '%s\n' 'Mineflayer package lock changed during npm ci' >&2
  exit 1
fi

JAVA_VERSION="$("$JAVA" -version 2>&1)"
NODE_VERSION="$("$NODE" --version)"
NPM_VERSION="$("$NPM" --version)"
if [[ "$JAVA_VERSION" != *"25.0.4.1"* ]]; then
  printf 'unexpected Java identity: %s\n' "$JAVA_VERSION" >&2
  exit 1
fi
if [[ "$NODE_VERSION" != v22.* ]]; then
  printf 'unexpected Node identity: %s\n' "$NODE_VERSION" >&2
  exit 1
fi

python3 - "$RUNTIME_JSON" "$JAVA_VERSION" "$NODE_VERSION" "$NPM_VERSION" <<'PY'
import json
import sys
from pathlib import Path

Path(sys.argv[1]).write_text(
    json.dumps(
        {
            "provider_free": True,
            "llama_started": False,
            "model_loaded": False,
            "java_version": sys.argv[2],
            "node_version": sys.argv[3],
            "npm_version": sys.argv[4],
        },
        indent=2,
        sort_keys=True,
    )
    + "\n",
    encoding="utf-8",
)
PY

python3 -m experiments.identity_prior_trajectory_apparatus_smoke \
  --phase prepare --repo-root "$REPO_ROOT" --evidence-root "$EVIDENCE_ROOT" \
  --server-root "$SERVER_ROOT" --minecraft-jar "$MINECRAFT_JAR" \
  --minecraft-port "$MINECRAFT_PORT" --node "$NODE"

mkfifo "$SERVER_CONTROL"
MINECRAFT_PID=""
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
}
trap cleanup EXIT INT TERM

(cd "$SERVER_ROOT" && "$JAVA" -jar server.jar --nogui) \
  <"$SERVER_CONTROL" >"$SERVER_LOG" 2>&1 &
MINECRAFT_PID=$!
exec 3>"$SERVER_CONTROL"
SERVER_FD_OPEN=1

SERVER_READY=0
for _ in $(seq 1 120); do
  kill -0 "$MINECRAFT_PID" 2>/dev/null || {
    printf '%s\n' 'Minecraft process exited before apparatus smoke' >&2
    exit 1
  }
  if python3 - "$MINECRAFT_PORT" <<'PY'
import socket
import sys

try:
    with socket.create_connection(("127.0.0.1", int(sys.argv[1])), timeout=0.25):
        pass
except OSError:
    raise SystemExit(1)
PY
  then
    SERVER_READY=1
    break
  fi
  sleep 1
done
if [[ "$SERVER_READY" != 1 ]]; then
  printf '%s\n' 'Minecraft listener did not become ready for apparatus smoke' >&2
  exit 1
fi

printf 'bash %q --repo-root %q --evidence-root %q\n' \
  "$SCRIPT_PATH" "$REPO_ROOT" "$EVIDENCE_ROOT" \
  >"$EVIDENCE_ROOT/canonical-apparatus-smoke-command.txt"

python3 -m experiments.identity_prior_trajectory_apparatus_smoke \
  --phase run --repo-root "$REPO_ROOT" --evidence-root "$EVIDENCE_ROOT" \
  --server-root "$SERVER_ROOT" --server-log "$SERVER_LOG" \
  --server-control "$SERVER_CONTROL" --minecraft-port "$MINECRAFT_PORT" \
  --minecraft-pid "$MINECRAFT_PID" --node "$NODE"

python3 -m json.tool "$EVIDENCE_ROOT/apparatus-smoke-report.json" \
  >"$EVIDENCE_ROOT/apparatus-smoke-report.pretty.json"
printf 'provider-free apparatus smoke evidence: %s\n' \
  "$EVIDENCE_ROOT/apparatus-smoke-report.json"
