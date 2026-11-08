# D14 R6 — LocalCodex natural World MOVE smoke / continuation (DEV)

Parent R5 [#809](https://github.com/rinsakamo/relay-self/pull/809);
child R6 [#810](https://github.com/rinsakamo/relay-self/pull/810).
R4 [#808](https://github.com/rinsakamo/relay-self/pull/808) is the
original nonmotion decision owner. **The R6 GitHub Actions workflow runs
OFFLINE tests only; it does NOT launch Minecraft or the full World.**

## Qualification boundary

An explicitly enabled R6 retains the **same natural-survival World,
original S49 Intent, ActionSupervisor, S49 executor, and Paper 10,000-tick
horizon** as R5. It records *actual unsolicited* Mineflayer entity events
encountered during genuine correlated native observations. It will consider
one MOVE only when the original S49 \`NormalWorldL0._check\` sees an
identical close zombie in an older entities event and current real probe.

A MOVE request then passes the existing frozen S49 S14
\`_native_epoch_two\`, source-typed independent operator PROPOSE and
ISSUE authorizations, execution binding, the original
\`NormalSessionActionExecutor.execute\`, and the original
\`OriginalS49PhysicalFence\` persisted **before native ISSUE**.
Only its own original supervisor's matching S16 OUTCOME can close the
fence. Missing/unresolved effects are STOP/UNKNOWN, not retry candidates.

No new standalone movement issuer, mob weakening, NoAI, forced Hunger,
staged zombie, teleport, altered drops, automatic retry, new permission
or learning update is allowed.

**Physical STOP has NOT been implemented or attested.**
An original S15 \`clear_controls\` ACK does not prove a stopped body
over later World ticks. S49's existing post-MOVE EAT fence is retained.
After MOVE, EAT may be denied, and the Self may die in an authentic World.
Do not interpret nonmotion EAT/ATTACK, paper-only continuation, or a
10,000-tick clock as autonomous survival or successful C1 learning.
The nearby-zombie source gate may also reject a natural event. Zero MOVE
is a valid observed outcome, not evidence of a working MOVE capability.

This is one-shot DEV:
\`DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN\`.

## LocalCodex execution (WSL2, ONLY after exact successful R6 CI)

Use a **new detached worktree**. Do not update or replace any previous R4/R5
evidence, existing worktrees, or active grants. If an earlier local branch has
uncommitted modifications, leave it untouched.

Replace \`CI_VERIFIED_R6_HEAD\` below with the **full 40-character SHA**
of the latest successful
[R6 offline CI](https://github.com/rinsakamo/relay-self/actions/workflows/unified-v05-d14-r6-original-motion-offline.yml).
Read the source first, compare that SHA to the PR and the exact workflow
result, and do not run on an unchecked-out or modified HEAD.

\`\`\`bash
set -euo pipefail
cd ~/work/relay-self
git fetch origin dev/d14-r6-original-s49-native-motion-20261109
git worktree add --detach ~/work/relay-self-r6-ci CI_VERIFIED_R6_HEAD
cd ~/work/relay-self-r6-ci
EXPECTED_HEAD=CI_VERIFIED_R6_HEAD
test "$(git rev-parse HEAD)" = "$EXPECTED_HEAD"
test -z "$(git status --porcelain)"
python3 --version; node --version; java -version; mvn -version

python3 -m venv "$HOME/work/.venvs/relay-self-r6"
source "$HOME/work/.venvs/relay-self-r6/bin/activate"
python -m pip install pytest==9.1.1 ruff==0.16.7
export PYTHONPATH=src:tests:.
export PYTHONDONTWRITEBYTECODE=1
python tools/check_repository.py
python -m pytest -q -x tests/test_d14_natural_motion_r6.py \
  tests/test_d14_local_oneworld.py tests/test_d14_natural_active_s49.py \
  tests/test_d14_natural_world.py
ruff check adapters/mineflayer/s31a_real_server_ci.py \
  tools/bug0_d14_natural_motion.py tools/bug0_d14_natural_life.py \
  tools/bug0_d14_natural_world.py tests/test_d14_natural_motion_r6.py
npm ci --omit=dev --no-audit --no-fund --prefix adapters/mineflayer
mvn -B -ntp -f adapters/mineflayer/zombie_respawn_dev/pom.xml clean package
python tools/check_repository.py
test -z "$(git status --porcelain)"
\`\`\`

The Paper JAR must match the **pinned Paper 1.21.8 size and SHA** defined
in \`adapters/mineflayer/s49_p1_paper_server.py\`.
The respawn plugin must be built from this exact checkout and its SHA
attested. Any unexplained change in the World, source, plugin or original
physical ledger is a preflight failure.

\`\`\`bash
export D14_R3_PAPER_JAR="$HOME/work/paper/paper-1.21.8-60.jar"
export D14_R3_RESPAWN_JAR="$PWD/adapters/mineflayer/zombie_respawn_dev/target/relay-zombie-respawn-dev-0.1.0-dev.jar"
export D14_R3_RESPAWN_SHA256="$(sha256sum "$D14_R3_RESPAWN_JAR" | cut -d' ' -f1)"

export S49_REAL_SERVER_CI=1
export D14_10000_TICK_WORLD_ONLY=1
export D14_R3_NATURAL_WORLD_ONCE=1
export D14_R4_NATURAL_S49_ONEWORLD_ONLY=1
export D14_R5_LOCAL_ONEWORLD_ONLY=1
export D14_R6_NATURAL_MOTION_ONEWORLD_ONLY=1

mkdir -p "$HOME/work/relay-self-evidence"
EVIDENCE="$HOME/work/relay-self-evidence/d14-r6-natural-original-01"
test ! -e "$EVIDENCE"
python -B -m tools.bug0_d14_local_oneworld \
  --repo "$PWD" --expect-head "$EXPECTED_HEAD" \
  --evidence-dir "$EVIDENCE" \
  --paper-jar "$D14_R3_PAPER_JAR" \
  --plugin-jar "$D14_R3_RESPAWN_JAR" \
  --max-wall-seconds 3600

# Even on nonzero exit, do not restart/replay; inspect only original artifacts.
(cd "$EVIDENCE" && sha256sum -c SHA256SUMS.txt)
\`\`\`

The output retains original \`paper_original.log\`,
\`d14_natural_events.jsonl\`, \`report.json\`, the original S49
ATTACK/EAT and MOVE fences, and the R5 LocalCodex source manifest and
independent audit if available. The report fields
\`original_s49_move_fence_unresolved\` and
\`original_s49_post_move_settling_unqualified\` are especially important.

Check all original native \`entities\` seqs, exact request IDs, S49 L0
selection, S14 admitted plan, original supervisor Action ID, pre-ISSUE
fence, \`set_control\`, \`clear_controls\`, S16 terminal and World
position. The simulation may stop early due to real death. One World
and no automatic restart regardless of the outcome.

Report separately: **original World run**, **source-only saved evidence**,
**independent audit**, and **unproven physical STOP/Intent/C1**.
Write status to PR #810, Issue #742, #431 and #717 without upgrading
the classification. R7 should connect an *authentic stopped-body owner*
before allowing MOVE→EAT or declaring full autonomous survival.
