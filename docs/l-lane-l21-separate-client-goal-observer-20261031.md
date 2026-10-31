# RelaySelf L21 — Separate read-only Minecraft client observing first S49 Goal

Date: 2026-10-31 JST. Parent L20 HEAD `bf3c3e3cfd03f046baaf0fc928a597457895e321`.

## Actual experiment and physical boundary

Existing S49 starts a disposable **vanilla Java 1.21.8** Minecraft server, with `max-players=2`, then a real Mineflayer 4.39.0 `RelaySelf` Action client. L16/L18 capture the first S49 motor Action plus S15 clear, S16 closure and two native S7 Goal probes, while an existing second S49 Action occurs later. L20 rejects uncommitted Goal criteria **before** Java starts. Previous L20 only compared a source-generated Self pose with an operator Goal; it lacked a different World observer's result.

L21 adds an **optional second Mineflayer client**, `RelayGoalObserver`, connected via its own Minecraft TCP session. Its Node program `adapters/mineflayer/l21_goal_observer.mjs` only implements `sample` and `shutdown` commands. It does **not** implement motor, attack, equip, look, chat, Minecraft command or S49 Action/grant authority. The observer identifies the other player from its own Mineflayer `bot.players.RelaySelf.entity.position`; it never reads or copies S49 native position data.

The client is launched **after the disposable Java server is ready and before S49's Self client begins**. S49 asks the observer for its first sample **after** original S16 control clearance and before the first original S7 Goal probe. It asks for a second sample between the S7 Goal probes, then ends/seals the observer process **before** issuing S49's later second Action. The observer computes its own `REACHED`/`NOT_REACHED`/`UNDETERMINED` from two positions, fixed L20 criterion and stability threshold; no retrospective Goal coordinates.

The observer itself writes an exclusive-create, append-only, fsync-on-each-row `l21_separate_client_goal_original.jsonl` in a **separate** absolute capture directory. The original contains `start`, `ready`, two `sample` frames (physical observed target entity ID, x/y/z or null), `goal_result`, and `closed`. The Python S49 source reader only asks for samples, checks ACKs, reads the complete sealed original and **recomputes** the Goal status and exact first Action/session request IDs, S7 diagnostic comparison and file SHA. An unexpected event, missing sample, foreign target, forged Goal label, malformed source or unclean observer process fails closed.

**Critically:** another Mineflayer client is still another player in the World (a possible physical intervention), not an independently attested Paper-side source or a certified absence-of-intervention proof. The S49 host launches the observer and requests the two sample times; it can affect timing, and both can share local infrastructure. Minecraft protocol observation and client presence have not been verified on this branch by an actual new World test. Output has `separate_external_goal_owner_authenticated=false`, `independently_attested_nonintervention=false`, `qualified_real_learning_pairs=0`, `s10_updates=0` and `s11_grants=0`. A disagreement between the observer source and S7 is visible as `diagnostic_agreement=false`, **not** auto-turned into a reward.

## Physical run, with explicit user grant on WSL2 host only

First, a separate reviewer should provide and independently preserve a prospectively authored `L20_PRE_WORLD_EXTERNAL_GOAL_COMMITMENT_V1` original and publicly or independently timestamp its SHA before World. The independent source file must be outside the S49 capture and L21 observer directories, and Goal coordinates must be physically meaningful **before** the run. See L20 docs for the canonical JSONL schema.

After preparing the original in an external location and selecting a disposable World, on the user's physical WSL2 with Java 21, Node 22 and Mineflayer 4.39.0 already installed:

```bash
cd ~/work/relay-self
git fetch origin
git switch integration/l21-separate-client-physical-goal-observer-20261031
export PYTHONPATH=src:tests:.
export S49_REAL_SERVER_CI=1
unset NODE_OPTIONS
: "${GOAL_X:?preselected x}" "${GOAL_Z:?preselected z}"
: "${EXTERNAL_GOAL_ORIGINAL:?absolute reviewer-owned .jsonl}"
: "${EXTERNAL_GOAL_SHA256:?reviewer-owned lowercase sha256}"
RUN_ROOT="$HOME/work/relay-self-dev/l21-$(date +%Y%m%d-%H%M%S)"
mkdir -m 700 -p "$RUN_ROOT/capture" "$RUN_ROOT/observer"
python -m adapters.mineflayer.s49_normal_session_real_ci \
  --report "$RUN_ROOT/s49-report.json" \
  --server-log "$RUN_ROOT/server.log" \
  --l16-capture-root "$RUN_ROOT/capture" \
  --l16-goal-target-x "$GOAL_X" \
  --l16-goal-target-z "$GOAL_Z" \
  --l16-confirm L16-S49-FIRST-ACTION-ORIGINAL-DEV \
  --l20-external-goal-original "$EXTERNAL_GOAL_ORIGINAL" \
  --l20-admitted-sha256 "$EXTERNAL_GOAL_SHA256" \
  --l21-observer-root "$RUN_ROOT/observer"

python -m adapters.mineflayer.l17_saved_original_goal_readback \
  --root "$RUN_ROOT/capture" \
  --s49-report "$RUN_ROOT/s49-report.json"
```

The observer is optional. S49 without `--l21-observer-root` follows the preexisting L20 behavior. L21 will only accept a fresh, absolute, non-symlink observer directory disjoint from the native S7/L16 capture root; it requires paired L20 pre-World external criterion and SHA. The separate client uses its own username but still shares the disposable vanilla Java server. Observer process end conditions, source loss, an absent tracked RelaySelf entity, protocol errors and network delays may yield `BLOCKED`, `FAIL`, or `UNDETERMINED`: preserve those original results; never infer learning or fill missing positions.

No LocalCodex or other remote tool is granted to start this World by the GitHub implementation alone. No new Java/Node physical World was actually run in this GitHub session.

## Why L21 is not yet an L10 training pair

L13/L14 requires additional independent per-Action Goal owner admission, S16 source/World/Body lineage, R/V provenance, chronological and nonintervention qualification; simply having two Mineflayer clients agree is not sufficient. A new, distinct current cognition epoch is still required to test memory retention ON/OFF, compare S choice and cheap L1 suggestions and show learning. L21 does **not** mint `L13_EXTERNAL_PER_ACTION_GOAL_V1` or `L14_PREDECLARED_SPATIAL_GOAL_V1` (their original session/action IDs did not exist when the external pre-World Goal was fixed), and never updates S10 or S11.

Tests: Node 22 syntax/pure tests for bounded protocol, no motor, native target selection and stability; Python 3.12 exact original synthetic positive and numerous adversarial controls; S49 opt-in preflight blocks invalid paths before Java/Action. Real Mineflayer Node dependency and actual other-player entity tracking still require **an explicitly authorized physical World trial**.

Classification: `DEV_ONLY / L21_SECOND_CLIENT_SOURCE_CODE_AND_SYNTHETIC_TEST / REAL_WORLD_0 / EXTERNAL_GOAL_INDEPENDENT_AUTHENTICATION_0 / QUALIFIED_L10_PAIRS_0 / S10_S11_0 / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.

## Exact-head synthetic DEV validation

**Successful code/test/workflow HEAD:** `13faa98ffccfba8d28acc822d7779c793bb6547d`.
[GitHub Actions #41163510447 SUCCESS](https://github.com/rinsakamo/relay-self/actions/runs/41163510447): Python 3.12 **99 PASS / FAIL 0 / SKIP 0**, Node 22 **4 PASS / FAIL 0**, Ruff, Python compileall, Node syntax checks, repository contract checker PASS. Exact tests include the prior L19/L20 source + S49 pre-World gates, L21 independent-client source replay/adverse checks and no-Java block tests. Java/Minecraft and actual Mineflayer Node package/server communications were **not** started in CI. A previously failed Ruff revision is preserved in GitHub Actions history; the above exact HEAD is the successful run.

The documentation-only final commit after this successful code HEAD is not asserted as separately tested. Deployment/push and Issue report do not imply World execution.
