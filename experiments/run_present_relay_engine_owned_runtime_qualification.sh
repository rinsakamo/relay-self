#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
LLAMA="$HOME/src/llama.cpp/build/bin/llama-server"
MODEL="$HOME/models/gguf/gemma-4-12B-it-Q4_K_M.gguf"
EXPECTED_MODEL_SHA256="c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed"
PORT=8080
TIMEOUT=60
READINESS_SECONDS=180
EVIDENCE_ROOT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-root) REPO_ROOT="$2"; shift 2 ;;
    --llama) LLAMA="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --timeout) TIMEOUT="$2"; shift 2 ;;
    --readiness-seconds) READINESS_SECONDS="$2"; shift 2 ;;
    --evidence-root) EVIDENCE_ROOT="$2"; shift 2 ;;
    *)
      printf 'unknown argument: %s\n' "$1" >&2
      exit 2
      ;;
  esac
done

REPO_ROOT="$(cd -- "$REPO_ROOT" && pwd)"
if [[ -z "$EVIDENCE_ROOT" ]]; then
  EVIDENCE_ROOT="/tmp/relay-self-190-$(date -u +%Y%m%dT%H%M%SZ)"
fi
mkdir -p "$EVIDENCE_ROOT"
EVIDENCE_ROOT="$(cd -- "$EVIDENCE_ROOT" && pwd)"

export PYTHONPATH="$REPO_ROOT/src:$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONDONTWRITEBYTECODE=1

ORIGIN="http://127.0.0.1:$PORT"
CANONICAL_LAUNCHER="$REPO_ROOT/experiments/run_present_relay_engine_seam_qualification.sh"
SERVER_LOG="$EVIDENCE_ROOT/llama-server.log"
LLAMA_PID=""

cleanup() {
  set +e
  if [[ -n "$LLAMA_PID" ]] && kill -0 "$LLAMA_PID" 2>/dev/null; then
    kill "$LLAMA_PID" 2>/dev/null
    wait "$LLAMA_PID" 2>/dev/null
    printf '%s\n' "terminated-owned-pid=$LLAMA_PID" >"$EVIDENCE_ROOT/server-cleanup.txt"
  elif [[ -n "$LLAMA_PID" ]]; then
    printf '%s\n' "owned-pid-already-exited=$LLAMA_PID" >"$EVIDENCE_ROOT/server-cleanup.txt"
  fi
}
trap cleanup EXIT INT TERM

if [[ ! -x "$LLAMA" ]]; then
  printf 'llama-server is not executable: %s\n' "$LLAMA" >&2
  exit 2
fi
if [[ ! -f "$MODEL" ]]; then
  printf 'model does not exist: %s\n' "$MODEL" >&2
  exit 2
fi
if [[ ! -x "$CANONICAL_LAUNCHER" ]]; then
  printf 'canonical qualification launcher is not executable: %s\n' "$CANONICAL_LAUNCHER" >&2
  exit 2
fi

cd "$REPO_ROOT"
if [[ -n "$(git status --porcelain)" ]]; then
  printf '%s\n' 'qualification requires a clean repository checkout' >&2
  exit 2
fi
git rev-parse HEAD >"$EVIDENCE_ROOT/repository-head.txt"
git rev-parse 'HEAD^{tree}' >"$EVIDENCE_ROOT/repository-tree.txt"

"$LLAMA" --version >"$EVIDENCE_ROOT/llama-version.txt" 2>&1
MODEL_SHA256="$(sha256sum "$MODEL" | awk '{print $1}')"
printf '%s  %s\n' "$MODEL_SHA256" "$MODEL" >"$EVIDENCE_ROOT/model-sha256.txt"
if [[ "$MODEL_SHA256" != "$EXPECTED_MODEL_SHA256" ]]; then
  printf 'model SHA256 mismatch: %s\n' "$MODEL_SHA256" >&2
  exit 2
fi
nvidia-smi >"$EVIDENCE_ROOT/nvidia-smi.txt" 2>&1

python3 - "$PORT" <<'PY'
import socket
import sys

port = int(sys.argv[1])
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind(("127.0.0.1", port))
PY

"$LLAMA" \
  -m "$MODEL" \
  --host 127.0.0.1 \
  --port "$PORT" \
  -ngl 999 \
  -c 8192 \
  >"$SERVER_LOG" 2>&1 &
LLAMA_PID=$!
printf '%s\n' "$LLAMA_PID" >"$EVIDENCE_ROOT/server.pid"

READY=0
for _ in $(seq 1 "$READINESS_SECONDS"); do
  if curl --max-time 2 --silent --fail "$ORIGIN/health" \
      >"$EVIDENCE_ROOT/health.latest.json" 2>/dev/null \
      && grep -Eq '"status"[[:space:]]*:[[:space:]]*"ok"' \
          "$EVIDENCE_ROOT/health.latest.json"; then
    READY=1
    break
  fi
  if ! kill -0 "$LLAMA_PID" 2>/dev/null; then
    set +e
    wait "$LLAMA_PID"
    SERVER_RC=$?
    set -e
    printf '%s\n' "$SERVER_RC" >"$EVIDENCE_ROOT/server-exit-before-readiness.txt"
    LLAMA_PID=""
    printf '%s\n' 'llama.cpp exited before health readiness' >&2
    exit 2
  fi
  sleep 1
done

if [[ "$READY" != 1 ]]; then
  printf '%s\n' 'llama.cpp /health did not become ready' >&2
  exit 2
fi

curl --max-time 2 --silent --fail "$ORIGIN/health" \
  >"$EVIDENCE_ROOT/health.json"
curl --max-time 2 --silent --fail "$ORIGIN/props" \
  >"$EVIDENCE_ROOT/props.json"
curl --max-time 2 --silent --fail "$ORIGIN/v1/models" \
  >"$EVIDENCE_ROOT/models.json"

python3 - "$EVIDENCE_ROOT/models.json" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
data = payload.get("data") if isinstance(payload, dict) else None
ids = [
    item.get("id")
    for item in data
    if isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"]
] if isinstance(data, list) else []
if len(ids) != 1:
    raise SystemExit(f"expected exactly one served model id; found {len(ids)}")
PY

printf '%s\n' '1' >"$EVIDENCE_ROOT/canonical-launcher-invocations.txt"
set +e
"$CANONICAL_LAUNCHER" \
  --repo-root "$REPO_ROOT" \
  --origin "$ORIGIN" \
  --timeout "$TIMEOUT" \
  >"$EVIDENCE_ROOT/qualification.stdout.txt" \
  2>"$EVIDENCE_ROOT/qualification.stderr.txt"
QUALIFICATION_RC=$?
set -e
printf '%s\n' "$QUALIFICATION_RC" >"$EVIDENCE_ROOT/qualification.exit.txt"

cat "$EVIDENCE_ROOT/qualification.stdout.txt"
cat "$EVIDENCE_ROOT/qualification.stderr.txt" >&2
printf '%s\n' "evidence-root=$EVIDENCE_ROOT"

exit "$QUALIFICATION_RC"
