# D14 R5 — LocalCodex / WSL2 one-use natural World endurance (DEV)

Parent: natural active R4 Draft PR #808, source HEAD
`594ee92a50bd4f9fa2a9455be20c6950f927afea`. R3 #807 and D14
#805 remain separate history. **GitHub Actions executes offline tests only in
this R5 branch; it does not automatically create a Paper World.**

## Scope and exclusions

R5 adds a local one-use entry to the already existing R4 `NaturalLifeLoop`,
original S49, S16 and Paper horizon. It changes no Paper zombie AI/Health,
natural drops, Self Health/Hunger, natural terrain or 600 server-tick managed
respawn. The original R4 process uses a **20-minute host watchdog**; R5 accepts
a separately granted local override from 600 to 7200 seconds, default 3600.
It is still bounded: one Self, one disposable World, no auto-reroll/respawn,
max 10,000 Paper ticks, 1024 L0 read-only decisions, 32 nonmotion Actions.
Actual Self death and native loss are not signs of a failed benchmark to
retry. Watchdog exhaustion is not tick completion.

The **MOVE_AWAY / physical STOP route remains unconnected in R4/R5**;
ATTACK requires a stable close zombie and EAT requires original native food,
steady safe Body and S49 admission. A safe-stop can leave the World-side
Paper clock running *without* active Self Action. R5 is therefore a
local endurance **measurement harness**, not a claim of full autonomy,
learning, closed C1 Intent experiences or L2 activity. No Gemma is launched.
Explicit classification: `DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.

## LocalCodex repo-first preparation

Run from a **clean checkout** on Windows 11 WSL2 Ubuntu 24.04. A fresh
detached worktree is preferred so that earlier uncommitted LocalCodex changes
remain untouched. Verify the exact source HEAD against a **successful R5
offline CI run**. A version string, an unverified branch tip, or an older
R4 success is not sufficient.

The commands below are a template, to be executed in a local shell by
LocalCodex after fixing `CI_VERIFIED_SHA` to the full SHA from the
successful R5 offline GitHub Actions run:

```bash
set -euo pipefail
cd ~/work/relay-self
git fetch origin dev/d14-r5-localcodex-natural-longrun-20261109
# Use a new, separate disposable worktree if you have uncommitted changes.
git worktree add --detach ~/work/relay-self-r5-ci CI_VERIFIED_SHA
cd ~/work/relay-self-r5-ci
EXPECTED_HEAD=CI_VERIFIED_SHA
test "$(git rev-parse HEAD)" = "$EXPECTED_HEAD"
python3 --version
node --version
java -version
mvn -version

# Keep the Python test venv OUTSIDE the worktree.
python3 -m venv ~/work/.venvs/relay-self-r5
source ~/work/.venvs/relay-self-r5/bin/activate
python -m pip install pytest==9.1.1 ruff==0.16.7
export PYTHONPATH=src:tests:.
export PYTHONDONTWRITEBYTECODE=1
python tools/check_repository.py
python -m pytest -q -x \
  tests/test_d14_local_oneworld.py \
  tests/test_d14_natural_active_s49.py \
  tests/test_d14_natural_world.py \
  tests/test_d14_tick_horizon.py \
  tests/test_d12_experience_bridge.py \
  tests/test_d12_third_intent_rearm.py
ruff check tools/bug0_d14_local_oneworld.py \
  tools/bug0_d14_natural_world.py \
  tools/bug0_d14_natural_life.py \
  tools/bug0_d14_natural_active_post.py \
  tests/test_d14_local_oneworld.py

npm ci --omit=dev --no-audit --no-fund --prefix adapters/mineflayer
test "$(node -p "require('./adapters/mineflayer/node_modules/mineflayer/package.json').version")" = "4.39.0"
mvn -B -ntp -f adapters/mineflayer/zombie_respawn_dev/pom.xml clean package
python tools/check_repository.py
test -z "$(git status --porcelain)"
```

Paper JAR must be the **pinned Paper 1.21.8 build** whose exact size and
SHA256 are defined in
`adapters/mineflayer/s49_p1_paper_server.py`.
Use the previously source-verified local JAR or download that exact pinned
artifact, *not* an arbitrary latest Paper release. Maven compiles the
GitHub-verified R5 plugin source; pin the built JAR digest, and do not edit
World config to make actions succeed.

## Explicit one-World DEV launch

```bash
# Continue in the exact clean R5 detached worktree and selected venv.
export D14_R3_PAPER_JAR="$HOME/work/paper/paper-1.21.8-60.jar"
export D14_R3_RESPAWN_JAR="$PWD/adapters/mineflayer/zombie_respawn_dev/target/relay-zombie-respawn-dev-0.1.0-dev.jar"
export D14_R3_RESPAWN_SHA256="$(sha256sum "$D14_R3_RESPAWN_JAR" | cut -d' ' -f1)"

# Explicit grants required by original R3/R4 and separate local R5.
export S49_REAL_SERVER_CI=1
export D14_10000_TICK_WORLD_ONLY=1
export D14_R3_NATURAL_WORLD_ONCE=1
export D14_R4_NATURAL_S49_ONEWORLD_ONLY=1
export D14_R5_LOCAL_ONEWORLD_ONLY=1

# Evidence is outside the source checkout; this directory MUST NOT exist.
mkdir -p "$HOME/work/relay-self-evidence"
EVIDENCE="$HOME/work/relay-self-evidence/d14-r5-natural-original-01"
test ! -e "$EVIDENCE"
test -z "$(git status --porcelain)"

python -B -m tools.bug0_d14_local_oneworld \
  --repo "$PWD" \
  --expect-head "$EXPECTED_HEAD" \
  --evidence-dir "$EVIDENCE" \
  --paper-jar "$D14_R3_PAPER_JAR" \
  --plugin-jar "$D14_R3_RESPAWN_JAR" \
  --max-wall-seconds 3600

# If the command returns nonzero, DO NOT retry the same World.
(cd "$EVIDENCE" && sha256sum -c SHA256SUMS.txt)
```

This launcher refuses a dirty or wrong-HEAD repo, a preexisting evidence
directory, missing grants, non-pinned Paper/plugin, NODE_OPTIONS, and
a conflicting local port. Before creating a World it validates source
hashes and paths. A failed or interrupted execution is saved as a partial
source result, not recast as successful.

The runner produces `local_run_source.json`, `report.json` (if the
underlying runner got far enough), `paper_original.log`,
`d14_natural_events.jsonl`, the original S49 nonmotion ledger (when
created), `local_partial_source_only.json` and `SHA256SUMS.txt`.
After clean original completion it also attempts the existing independent
`audit_active`, writing `independent_audit.json` or a separate error
file. Its failure does **not** rewrite the original report.

If the operator must interrupt, use a normal Ctrl-C rather than SIGKILL;
preserve the resulting directory even when a process is unqualified.
Never re-execute with the same output directory and never claim that
continued Paper ticks after L0 safe-stop prove an actively surviving Self.
Do not auto-restart the Mineflayer player after natural death.

## Audit and GitHub handoff

Collect `git rev-parse HEAD`, the local command exit code, all manifest
checksums, World UUID, start/tick/end markers, physical ATTACK/EAT IDs and
S16 closures, native safe-stop/death reason, decision counts, and
source-only C1/Learning=0. Report original status and independent audit
separately, with the original logs intact.

Attach evidence/manifest to child Draft PR #808's successor and link
Issue #742 and #431. Do **not** merge to main or declare a scientific
result. The following feature work is a separate branch: native event-driven
S49 MOVE/STOP + durable MOVE fence, new Intent results as C1 experience
and optional subsequent L2/L1 learning. An 8-minute World limit by itself
is not evidence of adaptive autonomy.
