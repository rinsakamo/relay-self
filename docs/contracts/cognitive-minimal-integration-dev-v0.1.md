# Cognitive v0.1 — CPU Schema → SystemOne → native WorldBody DEV

Parent #828 §27 (2026-11-13); children #829, #831, #841, #843.

**Status: OFFLINE_INTEGRATION_PASS / REAL_LLM_NOT_RUN_HERE /
REAL_WORLD_NOT_RUN_HERE / QUAL_NO_GO / SCIENCE_NOT_RUN.**
This is stacked on #842's CPU contracts. It deliberately keeps the
existing single-`CurrentIntent` owner rather than adding a second
Owner/Scheduler or another native Action issuer. Multi-Intent `IntentBook`
remains an explicit separate #843 migration.

## Implemented

- `src/relay_self/cognitive_minimal_dev.py` is a bounded CPU-only
  pattern interpreter. The same typed `SchemaPattern` data shape and
  validator are used for innate and accepted learned patterns. No LLM,
  arbitrary code or Memory retrieval in Schema.
  - HUNGRY → HUNGER_RELIEF/EAT/FOOD (body-threshold controlled)
  - ZOMBIE_NEAR → DEFEND_SELF/ATTACK/ZOMBIE (may be unresolved)
  - FATIGUE_HIGH → goal-less Constraint Sensation (when sensed).
  Multiple Goals share a bounded L1 CURRENT; distant observed threats may
  raise an unresolved defensive Goal without implying immediate FAST reflex.
- CPU-constructed `Goal × Skill@version × Target` options are finite.
  `BoundedChoiceRequest` uses one existing RelayEngine/SystemOne selection,
  with DEFER and ESCALATE_L2; no automatic THINK, second Skill search or
  model-generated target text. RECENT is caller supplied (max three refs),
  RETRIEVED Memory not required per ordinary SELECT.
- L1 may operate on a slightly stale epoch. Selection checks its actual
  Goal/Skill/Target dependencies, not full World/Schema snapshot equality.
  `prepare_existing_owner_action` demonstrates the original
  `IntentCommitment → SkillExecution → ActionLifecycle.PROPOSED`
  offline seam and preserves selected target/session (no native issue there).
- `experiments/cognitive_minimal_minecraft_dev.py` translates genuine
  `MineflayerObservation` snapshots from the existing decoded native bridge:
  source/session/sequence, bounded inventory and nearby entity facts. Known
  edible names, hazard names and physical ATTACK range come from existing
  `ControlledScenario`, **not** from a hardcoded LLM-generated plan.
  Current adapter does NOT expose physical fatigue: mark as UNKNOWN.
  A distant Zombie raises defensive Need but is not an executable ATTACK.
- After L1, the bridge requests a newly correlated native
  `probe(request_id)` (adapted from original S49 #767's read-only protocol)
  and validates the returned request ID, World session/sequence, and
  session and bound Target. On READY, the **existing**
  `experiments.controlled_minecraft_vertical.execute_decision` is used
  directly for EAT/FIGHT with original
  `IntentCommitment → SkillExecution → ActionLifecycle →
  ActionSupervisor → Mineflayer` effect/outcome. No duplicate Skill start
  from `prepare_existing_owner_action`. Native accepted/rejected effects
  are known Action Outcomes, not automatically successful Skills.
  `issue_native=False` by default: fresh observation and READY without
  Action issuance is possible and test-covered.
- `experiments/run_cognitive_minimal_world.py` provides a one-turn,
  explicit-grant real llama.cpp + Mineflayer CLI (below). It does not start
  a Minecraft server, invent item stock, change world Hunger, or silently
  retry. The actual local WSL2 GPU/World session has NOT been accessed
  from GitHub CI / this environment.
- The main experimental `controlled_minecraft_vertical` checks food
  increase but does not require consumed-item inventory decrement. #844 now
  independently reports `native_eat_consequence_attested`, which requires
  two applied native child ACKs, a later increased food value, and a
  reduced count of the selected inventory item. This does not rewrite
  legacy SkillState or seal #767's original S49 fence.
- `experiments/cognitive_cpu_l1_stall_shadow.py` is a read-only bounded
  *offline* CPU tick simulator. Under a stalled L1 thread, it traces
  per-epoch Pattern checks, FAST cues, source session changes, CPU wall
  latency/p50/p95 and simulation deadline misses. The 48-epoch adversarial
  test has no native Action, no actual GPU preemption, and is not a
  production L0 Scheduler or a real FAST deadline guarantee.
- See `docs/contracts/cognitive-s49-preissue-fence-audit-v0.1.md` for
  concrete differences with original S49 #767: current main-based
  `MineflayerObservation` now supports the **read-only** correlated
  native `request_id` backport. However the original S49 two-probe/steady
  window, independent grants and `NormalSessionActionExecutor` are still
  not wired into this stacked runtime, and nothing writes a pre-ISSUE WAL here.
- L2 escalation may construct one `RelayEngine.OPEN` request. Strict
  parser accepts only exact innate-format typed CPU patterns and rejects
  arbitrary code/unknown/costly forms. No Self acceptance is presumed.
  CLI can request an **unpublished hypothesis** with
  `--enable-l2-proposal`; real L2/acceptance qualification is open.

## Offline DEV tests

Run:
```bash
PYTHONPATH=src:. python -m pytest tests/test_cognitive_minimal_dev_v01.py \
    tests/test_cognitive_minimal_minecraft_dev.py -q
```

Synthetic D1 EAT with inventory → original supervisor two effects/outcomes
and observed later food increase. D2 hunger + Zombie → L1 ATTACK option →
original FIGHT effect/attributed hurt path. D3 no food → ESCALATE_L2
without Action. D4 native probe discovers vanished target → reject.
D5 CPU epoch can continue on asyncio event loop while L1 runs in a
thread (not a real GPU contention or sustained L0 scheduler proof).
D6 goal-less Body fatigue sensation on synthetic input; native physical
fatigue sensor UNKNOWN. D7 unaccepted/bad L2 Pattern rejected.
D8 unrelated observation/Goal does not invalidate selected EAT.
Additional negatives: action grant gate, native default no issue,
wrong World session, rejected equip != Skill success, unqualified
distant ATTACK, invalid/unknown hunger and busy original owner.

These tests use scripted `MineflayerObservation` and model responses.
The tests DO NOT make real physical Minecraft or Gemma calls.

## Real DEV execution (only on explicitly approved local host)

The Minecraft 1.21.8 World and the configured llama.cpp backend must already
be running, Node 22/Mineflayer 4.39.0 dependencies installed, with explicit
operator grant under repo rules. From the repository root, for a
**non-issuing native probe/shadow** first:

```bash
PYTHONPATH=src:. python -m experiments.run_cognitive_minimal_world \
  --grant-real-world --grant-real-llm \
  --model 'YOUR_SERVED_GEMMA_MODEL' \
  --llama-endpoint http://127.0.0.1:8080/v1/chat/completions \
  --systemone-endpoint http://127.0.0.1:8080/v1/systemone \
  --mc-host 127.0.0.1 --mc-port 25565 --mc-version 1.21.8 \
  --edible-item bread --hazard-name zombie --fight-max-distance 3 \
  --llama-timeout-s 30 --evidence-path ./cognitive-dev-evidence.json
```

Only after confirming the actual World/readback/Item/target and grant
conditions, add **both** `--execute-native` and
`--acknowledge-unfenced-dev` to permit the bounded main-branch EAT/FIGHT
Action path. The latter is explicit acknowledgment that the original #767
S49 pre-ISSUE durable fence is **not** connected; this is a DEV-only risky
physical boundary and must never be counted as S49 durability or QUAL. The runner defaults to a single turn and
**does not automatically choose or invent another Action**. The scenario
values are *examples*, not claims about a specific World or a confirmed
physical ATTACK reach. If the local runtime lacks the Jev endpoint,
omit `--systemone-endpoint` for the supported generated bounded path.
For L2 hypothesis-only output, add `--enable-l2-proposal`.

The CLI writes an atomic JSON result at `--evidence-path` on normal exit
and handled failure. A disconnect after an Action has been issued but before
its receipt is reported as `UNKNOWN_POSSIBLY_ISSUED` with the still-open
Action IDs, **not as an OUTCOME or Skill success**. The CLI now also
retains the original supervisor's read-only `recorded_actions` history,
including already-closed child effects such as a successful equip followed by
an unresolved consume; a closed equip ACK must not be mistaken for complete
physical EAT. This is only in-process
exit-path evidence: a host power loss or `SIGKILL` before write still loses
the file. Pre-ISSUE durable reservation in the full S49/#767 Action path
must remain a separate qualification gate. `--llama-timeout-s` limits a
provider HTTP request, **not** a guaranteed GPU abort or hard CPU deadline.

CI additionally runs complete fake-process CLI composition for shadow and
native EAT plus a disconnected-in-flight failure. The fake sessions and
model provider do not constitute physical World/GPU evidence.

Record exact HEAD, model artifact hash, llama.cpp runtime SHA, GPU driver,
actual World session, native timestamps, Action/Skill outcomes and
L1 token/prefill/decode latency separately. This CLI currently captures
total L1 wall latency and whatever aggregate prompt/decode token counts
the provider reports; it **does not separately measure prefill/decode
durations, CPU utilization, or long-run p95**.

## Remaining boundaries

1. **Real world + model measurements:** Run grant-backed CLI on operator
   WSL2/RTX 3060, capture native target/Action Outcome and performance.
   Current environment cannot reach that local host.
2. **Original full S49 optional adapter:** The main-branch bounded
   `controlled_minecraft_vertical.execute_decision` is an
   already-existing verified ActionSupervisor issuer, not the unmerged
   long-run S49 WorldBody adapter. No second native path was added here,
   but matching long-run S49 epochs/owner receipts is still open.
3. **True CPU continuous FAST/L0:** The one-shot caller awaits L1 using
   `asyncio.to_thread`, leaving the event loop available, but does NOT
   independently run a sustained fast sensory loop during model calls.
   The bounded 48-epoch shadow simulation only shows CPU work can continue
   in the event loop during a blocked model thread, not physical FAST,
   host load/SLO or native concurrent read ownership.
   GPU L2 preemption/release and independent CPU load measurements are open.
4. **L2 and learned Self:** A typed candidate parser / immutable data
   registry is an offline contract, not actual Self acceptance, persistent
   learned Schema installer, GPU preemption or autonomous Skill generation.
5. **Multi-Intent:** The existing main `IntentCommitment` is single-slot.
   A second physical issuance cannot be requested while its owner
   or ActionSupervisor is busy; true IntentBook/parallel SkillRun is
   still #843's implementation work.

DEV/QUAL/SCIENCE are strictly separate. Do not claim real World DEV from CI.
