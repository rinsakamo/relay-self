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
  python3 - "$target/ruleset.json" <<'PY' || return 1
import json
import sys
from pathlib import Path

ruleset = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if ruleset.get("id") != 23442682:
    raise SystemExit("unexpected main ruleset id")
if ruleset.get("enforcement") != "active":
    raise SystemExit("main ruleset is not active")
if ruleset.get("bypass_actors") != []:
    raise SystemExit("main ruleset unexpectedly has bypass actors")
if ruleset.get("current_user_can_bypass") != "never":
    raise SystemExit("current execution identity can unexpectedly bypass main ruleset")

conditions = ruleset.get("conditions")
if not isinstance(conditions, dict):
    raise SystemExit("main ruleset conditions payload is invalid")
ref_name = conditions.get("ref_name")
if not isinstance(ref_name, dict):
    raise SystemExit("main ruleset ref_name condition is missing")
if ref_name.get("exclude") != [] or ref_name.get("include") != ["~DEFAULT_BRANCH"]:
    raise SystemExit("main ruleset no longer targets exactly the default branch")

rules = ruleset.get("rules")
if not isinstance(rules, list):
    raise SystemExit("main ruleset rules payload is invalid")

by_type: dict[str, dict[str, object]] = {}
for rule in rules:
    if not isinstance(rule, dict):
        raise SystemExit("main ruleset contains a malformed rule")
    rule_type = rule.get("type")
    if not isinstance(rule_type, str):
        raise SystemExit("main ruleset contains a rule without a type")
    if rule_type in by_type:
        raise SystemExit(f"main ruleset repeats rule type: {rule_type}")
    by_type[rule_type] = rule

expected_types = {
    "deletion",
    "non_fast_forward",
    "pull_request",
    "required_linear_history",
    "required_status_checks",
}
if set(by_type) != expected_types:
    raise SystemExit(
        "main ruleset rule types changed: "
        + ",".join(sorted(by_type))
    )

pull_request = by_type["pull_request"].get("parameters")
if not isinstance(pull_request, dict):
    raise SystemExit("main ruleset pull_request parameters are invalid")
if pull_request.get("allowed_merge_methods") != ["squash"]:
    raise SystemExit("main ruleset must remain squash-only")
if pull_request.get("required_review_thread_resolution") is not True:
    raise SystemExit("main ruleset must require review-thread resolution")

checks = by_type["required_status_checks"].get("parameters")
if not isinstance(checks, dict):
    raise SystemExit("main ruleset required_status_checks parameters are invalid")
check_items = checks.get("required_status_checks")
if not isinstance(check_items, list):
    raise SystemExit("main ruleset required status check list is invalid")
actual_checks = {
    item.get("context")
    for item in check_items
    if isinstance(item, dict) and isinstance(item.get("context"), str)
}
if len(actual_checks) != len(check_items):
    raise SystemExit("main ruleset contains malformed or duplicate status checks")
expected_checks = {"repository-contracts", "pytest", "lint"}
if actual_checks != expected_checks:
    raise SystemExit(
        "main ruleset required checks changed: "
        + ",".join(sorted(actual_checks))
    )
PY
  gh pr list --repo rinsakamo/relay-self --state open --base main --limit 100 \
    --json number,title,headRefName,baseRefName,updatedAt,url >"$target/open-prs.json"
  [[ "$(gh pr list --repo rinsakamo/relay-self --state open --base main --limit 100 --json number --jq length)" == "0" ]] || return 1

  for issue_number in 88 141 201 220; do
    gh api "repos/rinsakamo/relay-self/issues/$issue_number" >"$target/issue-$issue_number.json"
    gh api --paginate "repos/rinsakamo/relay-self/issues/$issue_number/comments" \
      >"$target/issue-$issue_number-comments.json"
  done

  [[ "$(gh api repos/rinsakamo/relay-self/issues/201 --jq .state)" == "closed" ]] || return 1
  [[ "$(gh api repos/rinsakamo/relay-self/issues/201 --jq .state_reason)" == "completed" ]] || return 1
  [[ "$(gh api repos/rinsakamo/relay-self/issues/141 --jq .state)" == "closed" ]] || return 1
  [[ "$(gh api repos/rinsakamo/relay-self/issues/220 --jq .state)" == "open" ]] || return 1

  python3 - \
    "$target/issue-220-comments.json" "$local_head" "$local_tree" \
    >"$target/execution-qualification.txt" <<'PY' || return 1
import json
import re
import sys
from pathlib import Path

comments_path = Path(sys.argv[1])
expected_head = sys.argv[2]
expected_tree = sys.argv[3]
raw = comments_path.read_text(encoding="utf-8")
decoder = json.JSONDecoder()
pages = []
offset = 0
while True:
    while offset < len(raw) and raw[offset].isspace():
        offset += 1
    if offset >= len(raw):
        break
    page, offset = decoder.raw_decode(raw, offset)
    if not isinstance(page, list):
        raise SystemExit("paginated #220 comments payload is not a JSON array")
    pages.append(page)

comments = [
    comment
    for page in pages
    for comment in page
    if isinstance(comment, dict)
]
pattern = re.compile(
    r"(?m)^execution_qualification: "
    r"(QUALIFIED_FOR_NEW_TRANSACTION_SUBJECT|NOT_REQUALIFIED)\s*$"
)
relevant = []
for comment in comments:
    body = comment.get("body")
    comment_id = comment.get("id")
    user = comment.get("user")
    login = user.get("login") if isinstance(user, dict) else None
    association = comment.get("author_association")
    if login != "rinsakamo" or association != "OWNER":
        continue
    if not isinstance(body, str) or not isinstance(comment_id, int):
        continue
    matches = pattern.findall(body)
    if len(matches) == 1:
        relevant.append((comment_id, matches[0], body))

if not relevant:
    raise SystemExit(
        "no trusted-owner machine-readable #220 execution qualification found"
    )

_, state, body = max(relevant, key=lambda item: item[0])
if state != "QUALIFIED_FOR_NEW_TRANSACTION_SUBJECT":
    raise SystemExit(f"latest trusted #220 execution qualification is {state}")

head_matches = re.findall(r"(?m)^subject_head: ([0-9a-f]{40})\s*$", body)
tree_matches = re.findall(r"(?m)^subject_tree: ([0-9a-f]{40})\s*$", body)
if head_matches != [expected_head]:
    raise SystemExit("qualified #220 comment does not uniquely bind current HEAD")
if tree_matches != [expected_tree]:
    raise SystemExit("qualified #220 comment does not uniquely bind current tree")

print(state)
PY

  printf '{"label":"%s","local_head":"%s","local_tree":"%s","remote_main":"%s"}\n' \
    "$label" "$local_head" "$local_tree" "$remote_main" >"$AUTHORITY_JSON"
}

MINEFLAYER_DIR="$REPO_ROOT/adapters/mineflayer"
PACKAGE_LOCK="$MINEFLAYER_DIR/package-lock.json"
EVIDENCE_PACKAGE_LOCK="$EVIDENCE_ROOT/mineflayer-package-lock.json"
DEPENDENCY_TREE="$EVIDENCE_ROOT/mineflayer-dependency-tree.json"
NPM_INSTALL_LOG="$EVIDENCE_ROOT/mineflayer-npm-ci.log"

if ! git -C "$REPO_ROOT" ls-files --error-unmatch adapters/mineflayer/package-lock.json >/dev/null 2>&1; then
  printf '%s\n' 'tracked Mineflayer package-lock.json is required' >&2
  exit 2
fi
if [[ ! -f "$PACKAGE_LOCK" ]]; then
  printf '%s\n' 'tracked Mineflayer package-lock.json is missing' >&2
  exit 2
fi
cp "$PACKAGE_LOCK" "$EVIDENCE_PACKAGE_LOCK"

if ! (
  cd "$MINEFLAYER_DIR"
  "$NPM" ci --omit=dev --no-audit --no-fund
) >"$NPM_INSTALL_LOG" 2>&1; then
  printf '%s\n' 'Mineflayer npm ci failed; transaction not started' >&2
  exit 1
fi
if ! cmp -s "$PACKAGE_LOCK" "$EVIDENCE_PACKAGE_LOCK"; then
  printf '%s\n' 'Mineflayer package-lock.json changed during npm ci' >&2
  exit 1
fi
if ! (
  cd "$MINEFLAYER_DIR"
  "$NPM" ls --omit=dev --json
) >"$DEPENDENCY_TREE" 2>>"$NPM_INSTALL_LOG"; then
  printf '%s\n' 'Mineflayer dependency tree capture failed; transaction not started' >&2
  exit 1
fi

python3 - "$MINEFLAYER_DIR/node_modules/mineflayer/package.json" <<'PY'
import json
import sys
from pathlib import Path

package_path = Path(sys.argv[1])
package = json.loads(package_path.read_text(encoding="utf-8"))
if package.get("version") != "4.39.0":
    raise SystemExit(
        f"unexpected Mineflayer version after npm ci: {package.get('version')!r}"
    )
PY

python3 - \
  "$RUNTIME_ARTIFACTS_JSON" "$MINEFLAYER_DIR" \
  "$PACKAGE_LOCK" "$EVIDENCE_PACKAGE_LOCK" "$DEPENDENCY_TREE" \
  "$NPM_INSTALL_LOG" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

output = Path(sys.argv[1])
mineflayer_dir = Path(sys.argv[2])
source_lock = Path(sys.argv[3])
evidence_lock = Path(sys.argv[4])
dependency_tree = Path(sys.argv[5])
install_log = Path(sys.argv[6])

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()

source_lock_sha256 = sha256(source_lock)
evidence_lock_sha256 = sha256(evidence_lock)
if source_lock_sha256 != evidence_lock_sha256:
    raise SystemExit("evidence package lock does not match tracked source lock")

output.write_text(
    json.dumps(
        {
            "artifacts": [
                {
                    "kind": "node_modules",
                    "path": str(mineflayer_dir / "node_modules"),
                    "tracked_source": False,
                    "gitignored": True,
                },
                {
                    "kind": "tracked_package_lock",
                    "path": str(source_lock),
                    "sha256": source_lock_sha256,
                    "tracked_source": True,
                    "used_for_resolution": True,
                },
                {
                    "kind": "evidence_package_lock",
                    "path": str(evidence_lock),
                    "sha256": evidence_lock_sha256,
                    "matches_tracked_source": True,
                },
                {
                    "kind": "resolved_dependency_tree",
                    "path": str(dependency_tree),
                    "sha256": sha256(dependency_tree),
                    "tracked_source": False,
                },
                {
                    "kind": "npm_ci_log",
                    "path": str(install_log),
                    "tracked_source": False,
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

python3 -m experiments.identity_prior_trajectory_transaction \
  --phase plan --repo-root "$REPO_ROOT" --evidence-root "$EVIDENCE_ROOT" \
  --model "$MODEL" --self-id "$SELF_ID"

capture_authority initial || {
  printf '%s\n' 'pre-spend authority capture failed; transaction not started' >&2
  exit 1
}

python3 -m experiments.minecraft_terminal_qualification \
  --phase prepare --repo-root "$REPO_ROOT" --evidence-root "$EVIDENCE_ROOT" \
  --server-root "$SERVER_ROOT" \
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

capture_authority final || {
  printf '%s\n' 'final spend-gate authority capture failed; transaction not started' >&2
  exit 1
}

python3 -m experiments.identity_prior_trajectory_transaction \
  --phase run --repo-root "$REPO_ROOT" --evidence-root "$EVIDENCE_ROOT" \
  --minecraft-version "$MINECRAFT_VERSION" --minecraft-port "$MINECRAFT_PORT" \
  --username "$USERNAME" --node "$NODE" --llama-origin "$LLAMA_ORIGIN" \
  --llama-port "$LLAMA_PORT" --model "$MODEL" --served-model "$MODEL" \
  --server-control "$SERVER_CONTROL" --server-log "$SERVER_LOG" --self-id "$SELF_ID"

python3 -m json.tool "$EVIDENCE_ROOT/scientific-report.json" \
  >"$EVIDENCE_ROOT/scientific-report.pretty.json"
printf 'scientific evidence: %s\n' "$EVIDENCE_ROOT/scientific-report.json"
