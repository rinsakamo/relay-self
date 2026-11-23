# Cognitive v0.1 — CPU Schema → SystemOne → native WorldBody DEV

> **Current migration decision (2026-11-13):** The minimal
> [Physical ActionPort v0.1](physical-action-port-v0.1.md) replaces
> the prior plan to import the entire original S49 runtime. #844 now has
> an offline-tested, **nonissuing** existing-Action `PROPOSED` seam.
> The proven real Gemma/Minecraft EAT `S49_SHADOW_READY` remains a
> read-only source observation, not a physical grant or Outcome. The
> new physical issuer, #767-derived pre-ISSUE durable journal and
> restart/UNKNOWN qualifications remain separate OPEN work.

Parent #828 §27 (2026-11-13); children #829, #831, #841, #843.

**Status: OFFLINE_INTEGRATION_PASS / LOCALCODEX_REAL_L1_AND_WORLD_CONNECT_RECORDED /
TWO_PROBE_REAL_DEV_NOT_YET_REPEATED_ON_THIS_HEAD / QUAL_NO_GO /
SCIENCE_NOT_RUN.**
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
  and validates the returned request ID, World session/sequence and
  selected Target. On READY, the **existing**
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
- `experiments/cognitive_s49_readonly_handoff.py` implements a **read-only**
  original-S49-shaped two-probe Goal/Skill/Target precheck: unique native
  request IDs, one session, bounded seq gap, stable body position, and
  action-specific source constraints. EAT additionally checks no observed
  nearby entity and a stable selected inventory item/slot; ATTACK checks
  exactly the same near single Zombie and bounded entity movement. The
  resulting `S49ReadOnlyHandoff` is explicitly **not** an Action grant.
  It now records the Self identity and **proposed** Intent ID, checks the
  selected Goal still exists with the same Skill, and exposes the current
  Schema registry revision for diagnosis. An unrelated Schema revision
  does not invalidate a still-valid selected Goal/Skill/Target. The original
  Intent is *not* committed, and original S51 food policy and S49 authority
  remain unverified (explicitly false fields in the witness).
  With `--s49-readonly-shadow`, the CLI makes **two new post-L1 read-only
  probes** and reports `S49_SHADOW_READY` or `S49_SHADOW_REJECTED`,
  never a native Action. This is mutually exclusive with `--execute-native`.
- See `docs/contracts/cognitive-s49-preissue-fence-audit-v0.1.md` for
  concrete differences with original S49 #767. The read-only correlated
  two-probe witness is now implemented, but original S49's **actual**
  independent authority, S15/S16 owner, post-move settling, lifecycle
  admission, `NormalSessionActionExecutor` and PRE-ISSUE WAL remain
  unconnected. Do not equate a positive witness with original S49 approval.
- L2 escalation may construct one `RelayEngine.OPEN` request. Strict
  parser accepts only exact innate-format typed CPU patterns and rejects
  arbitrary code/unknown/costly forms. No Self acceptance is presumed.
  CLI can request an **unpublished hypothesis** with
  `--enable-l2-proposal`; real L2/acceptance qualification is open.

## Offline DEV tests

Run:
```bash
PYTHONPATH=src:. python -m pytest tests/test_cognitive_minimal_dev_v01.py \
    tests/test_cognitive_minimal_minecraft_dev.py \\
    tests/test_cognitive_s49_readonly_handoff.py \\
    tests/test_cognitive_minimal_world_cli.py -q
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

Minecraft 1.21.8 and the configured llama.cpp backend must be available,
with Node 22/Mineflayer 4.39.0 dependencies and explicit operator grants.
**LocalCodex should independently start an isolated test World and the
real Gemma backend if they are absent**, using the operator's verified
local server/model artifacts and only after checking ownership and active
listeners. This Python runner itself intentionally does not auto-launch
Minecraft or llama.cpp. It launches the existing Mineflayer bridge process
for the one-shot connection; no second Mineflayer daemon is necessary. From the repository root, for a
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

For an additional **non-issuing** two-probe S49-shaped precheck, add
`--s49-readonly-shadow` to the command above. With an L1-selected physical
Goal/Skill/Target the returned witness includes two distinct correlated
probe sequences/request IDs and the food slot or Zombie entity ID. If L1
chooses a nonphysical option such as `ESCALATE_L2` with **zero physical
options**, shadow mode still performs **two read-only probes**, records their
exact decoded native snapshots, and **retains `ESCALATE_L2` with no S49
handoff**. It never invents a Goal or retargets L1. Distinct probe IDs are
not evidence of distinct Minecraft physics ticks. Issuing remains disabled.

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

With `--evidence-path`, the CLI now first checkpoints the **complete typed
and decoded spawn observation** (session, seq, source, health, food, inventory,
nearby entities/coverage, time, oxygen, position) *before* asking Gemma.
The completed output includes this initial native observation, initial/current
CPU Schema frames, full bounded source-qualified `native_probe_trace`,
explicit scenario capability inputs, and selection/outcome. This is not the
original adapter stdout byte stream; the evidence format is
`TYPED_DECODED_MINEFLAYER_OBSERVATION_V1`. When L1 escalates with zero
physical options, the initial snapshot is required to distinguish absent
physical opportunities from scenario/configuration/sensor coverage effects.

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

CI additionally runs complete fake-process CLI composition for shadow,
read-only S49-shaped two-probe EAT/ATTACK and movement refusal, **zero-option
L2 escalation with two read-only correlated probes but no Target/Action**,
pre-L1 native checkpoint durability on handled model failure, native EAT,
and a disconnected-in-flight failure. The fake sessions and
model provider do not constitute physical World/GPU evidence.

Record exact HEAD, model artifact hash, llama.cpp runtime SHA, GPU driver,
actual World session, native timestamps, Action/Skill outcomes and
L1 token/prefill/decode latency separately. This CLI currently captures
total L1 wall latency and whatever aggregate prompt/decode token counts
the provider reports; it **does not separately measure prefill/decode
durations, CPU utilization, or long-run p95**.

## LocalCodex test-World lifecycle (operator-approved DEV)

2026-11-13 first measured real run at PR #844 HEAD
`e5d107a17adb79576ed9ba1523488e9b3beefb6f`: local
Minecraft 1.21.8 and Mineflayer connected, Gemma 4 12B generated bounded
L1 selected `ESCALATE_L2` in 1,201.173 ms (304 prompt/17 completion
tokens), CPU Schema 4.098 µs, physical options zero, native Actions zero.
The old runner skipped both probes because L1 selected a nonphysical
option. This is a **real DEV observation**, not an EAT/ATTACK or S49
2-probe qualification. Source: [PR #844 real World report](https://github.com/rinsakamo/relay-self/pull/844#issuecomment-6852458825).

For the *next* local run, do not require the user to separately start a
World. LocalCodex owns the following lifecycle under explicit operator
grants and existing repository DEV rules:

1. Preflight the exact checkout/CI, running listeners, Java 21, verified
   Minecraft 1.21.8 jar, Node 22, Mineflayer 4.39.0, real Gemma model,
   llama.cpp endpoint, GPU resources and prior World evidence. Do not
   assume a previous test World is still running or silently attach to an
   unrelated production World.
2. If absent, start an **isolated** existing-version test World on a
   free localhost port using the locally verified server jar and a
   dedicated test directory. Start the real Gemma backend only if absent;
   record the command, PID, log, model hash, listener and GPU state. Use
   only processes created or explicitly owned by this DEV to clean up.
   `MineflayerProcessSession.launch` creates the one-shot bridge itself.
3. Run a single read-only CLI with both grants,
   `--s49-readonly-shadow`, `--evidence-path`, and the **actual** host,
   port and served model name. Do **not** specify `--execute-native` or
   `--acknowledge-unfenced-dev`. In the **natural World observational arm**,
   do not artificially give food, change Hunger, spawn a Zombie or invent
   a source readback to obtain `S49_SHADOW_READY`. Its EAT/ATTACK targets
   are contingent on actual natural World conditions. The **separate,
   explicitly labeled controlled World positive arm** is documented below.
4. Preserve the final JSON including decoded initial source snapshot,
   scenario inputs and two source-correlated post-L1 probes. If selected
   target is absent, report `ESCALATE_L2 / native transport observed /`
   `S49 handoff NOT_ATTESTED`; if EAT/ATTACK is selected and the two
   source-qualified snapshots agree, report the read-only witness **only**.
   Preserve exact World session, source refs and elapsed time.
5. Stop only the server/model/bridge PIDs this run started, verify
   exit/readback and released GPU compute resources, retain original
   evidence and issue comments. If an owned process cannot stop, report
   that explicitly. Do not claim earlier successful World runs can be
   reconstructed from missing source observations.


## Controlled World EAT positive control (NOT natural World)

**Goal:** independently confirm real Gemma chooses the source-qualified
`HUNGER_RELIEF → EAT → inventory:bread` when the isolated *test server*
owns and presents a genuinely hungry Self with bread, then the existing
read-only S49-shaped post-L1 two-probe window gives a typed
`S49_SHADOW_READY`. **No EAT, ATTACK or other Self Action** is issued. Do
not count this controlled result as evidence of naturally learned hunger
seeking or of original S49 physical authorization.

The first real natural World probe on exact HEAD
`9081754f572a945cc818e5c0c1fd36896b406b2e` attested a fresh
source-qualified snapshot, no physical option, L1 `ESCALATE_L2` in
1,221.750 ms and two independently correlated native probes (seq 30 and
31, combined 4.346 ms) but **no Target or S49 handoff**.
See [PR #844 real two-probe report](https://github.com/rinsakamo/relay-self/pull/844#issuecomment-6852963571).

To prepare a **distinct positive-control World**, LocalCodex starts a
dedicated, disposable Minecraft 1.21.8 instance with its server console
owned by the test. The player connects; only the **isolated test server
operator**, not the Self ActionPort or L1, sets up a real bread item in
inventory and a genuinely low food bar. Use server-native supported
commands/procedures; do not synthesize adapter JSON, inject a fake probe,
change source provenance, patch CPU Schema/LLM choices or issue native
Self Actions to prepare the fixture. Let the player finish joining and
inventory sync. Keep Self stationary, alive and with **zero nearby entity
candidates** within the native 16m coverage for both post-L1 probes.
Read back the *actual* native `food < hunger_threshold`, bread count
`> 0`, stable slot, position, health and coverage before claiming the
positive control. The user has approved test World startup for DEV; do
not touch unrelated or production server instances.

Use the same one-shot real-World runner on this isolated World but with a
**new opt-in read-only pre-L1 native probe**. The runner checkpoints the
initial `spawn` observation immediately, optionally allows a bounded
server setup window, then sends `observe(request_id)` to obtain a
correlated **pre-L1** `probe`, checkpoints this as the *cognition starting
snapshot*, and only then asks real Gemma. The pre-L1 probe must have the
same session, increasing seq, native source and echoed request ID.
The model-selected Goal/Skill/Target is subsequently rechecked with
**two additional, separately correlated read-only probes**. Example:

```bash
PYTHONPATH=src:. python -m experiments.run_cognitive_minimal_world \
  --grant-real-world --grant-real-llm --s49-readonly-shadow \
  --pre-l1-native-probe --pre-l1-wait-s 20 \
  --mc-host 127.0.0.1 --mc-port YOUR_OWNED_TEST_WORLD_PORT \
  --mc-version 1.21.8 --model YOUR_SERVED_GEMMA_MODEL \
  --llama-endpoint http://127.0.0.1:YOUR_PORT/v1/chat/completions \
  --edible-item bread --hazard-name zombie --fight-max-distance 3 \
  --hunger-threshold 10 --evidence-path ./controlled-eat-readonly.json
```

The optional 20-second **post-spawn/pre-L1** wait is just a window for
the owned test server to establish state before the fresh probe; it is
not an assertion that the World has reached the desired state. The
operator should monitor the `INITIAL_NATIVE_OBSERVED_BEFORE_L1`
checkpoint and apply test-World setup through the server console during
the wait. Time can be set from 0 to 60 seconds; a nonzero wait requires
`--pre-l1-native-probe`, and this flag requires
`--s49-readonly-shadow` with no `--execute-native`. After the probe,
the file advances to `PRE_L1_NATIVE_PROBE_OBSERVED_BEFORE_L1` before L1;
the final JSON retains **both** `spawn_native_observation` and the
`initial_native_observation` used for cognition, plus the two post-L1
records in `native_probe_trace`.

A positive result requires **all** of:
- Source-provenance, request ID, native seq and session validation for
  pre-L1 and both post-L1 probes; their request IDs must all differ.
- Current **pre-L1** WorldBody actually hungry, bread observed and
  listed in configured edible items, CPU Schema Goal `HUNGER_RELIEF`
  and one `EAT@1/inventory:bread` option.
- **Actual real Gemma** selected that L1 option (not a mock provider,
  forced numeric ID, or post hoc retargeting).
- S49-shaped witness `skill_id=EAT`, `food_item=bread`,
  `food_slot` stable, `S49_SHADOW_READY`, while
  `original_s49_intent_committed=False`,
  `original_s49_authorized=False`,
  `physical_action_issued=False`, native Action/Outcome counts zero.

If this fails, preserve the real current facts and classify the
failure: server fixture not reflected in pre-L1 probe, Schema target
missing, Gemma alternative choice, changed inventory/body/coverage,
uncorrelated probe, or S49 shadow refusal. Do not retry indefinitely
or silently forge a Target. The two post-L1 probes might have
**identical Minecraft World time**: they do not prove distinct physics
ticks, STOP, prior MOVE settling or safety. Original S51 food policy,
S49 Owner/grants/S15-S16 and #767 pre-ISSUE WAL remain separate OPEN
integration requirements.

## Controlled EAT real DEV failure: native pre-L1 event backlog/horizon

LocalCodex's real controlled-World attempt on PR #844 HEAD
`769e7e565112ac228f00e193bde264a5ae64f69b`
([read-only DEV report](https://github.com/rinsakamo/relay-self/pull/844#issuecomment-6853945121))
did **not** reach L1, CPU Schema, post-L1 probes or S49 handoff.
Spawn seq1 was healthy/food20/bread absent. The independent test-World
console accepted giving bread and applying Hunger, but **no qualified
native readback of these changes was retained**. The pre-L1 observer
consumed **32 received messages** and refused
`no qualified probe within bounded event horizon`.
The original code did not preserve the probe request ID, event kinds
or last observed seq in that failure path. Event backlog during the
30-second operator setup window is **plausible but not proven**; no
source-qualified EAT positive was measured. Action/Outcome count remained
zero; this was an appropriate fail-closed result.

The DEV remediation remains strictly read-only:

- `read_correlated_native_probe()` now exposes a bounded
  `NativeProbeFailure.diagnostics` plus an optional caller-held live
  diagnostics dictionary. The data includes exact requested ID,
  native World session, initial seq, whether send completed, received
  count, event kind histogram, first/last six event summaries
  (kind/session/seq/request ID), most recent *diagnostic-only*
  decoded observation (never a qualified handoff), elapsed time,
  exception class/limited message when applicable, and the
  terminal refusal reason. The exact probe request ID is written to
  `--evidence-path` **before** sending the request, then retained in
  a handled failure audit. The last diagnostic observation is **not
  substituted for a correlated probe**.
- **Only the pre-L1 observer** explicitly raises the event bound
  from the shared default 32 to **4,096** to tolerate a passive event
  backlog after the bounded World setup wait. Its original read
  timeout still applies (`--evidence-timeout-s`, default 8s).
  No unbounded retries, synthetic probes, dropped/assumed request IDs,
  alternate Action issuer, or change to the post-L1/S49-shaped 32-event
  horizon. 4,096 events or expiry without a matching response still
  fails closed with telemetry.
- Synthetic full-CLI regression reproduces a wait-borne 51-event
  queue followed by a genuinely correlated pre-L1 EAT snapshot,
  L1 EAT choice and two post-L1 probes, without any native Action.
  Additional negatives prove the original 32-event post-L1 horizon
  is unchanged and a pre-L1 stream failure retains the request ID,
  source, last seq, event counts and no-Action audit.

**Next local real DEV**: inspect the exact PR HEAD/CI, launch the isolated
Minecraft 1.21.8 + Mineflayer + real Gemma as necessary, repeat exactly
one EAT positive-control attempt with a real post-setup native observation
and compare the new probe telemetry to the test-World logs. The
`pre_l1_probe_diagnostics.received_count` and histogram show whether a
backlog preceded the matched probe. Do not infer source success from
console ACKs, and do not silently turn this into an EAT action.

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
