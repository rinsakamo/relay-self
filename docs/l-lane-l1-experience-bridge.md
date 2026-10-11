# L Lane L1 — Experience retention and read-only reuse bridge

**Scope:** #426 / #421 / #431 / #432 / #544; product #537.
**Implementation base:** #590 exact `c361aeb546bb437b99362f6bf381902a15a955da`.
S #592 (`75054188f1c7e8141690697794b6e705495de205` at audit) is a
**separate Draft**, not imported or merged. L1 is offline-only.
Protected main, old A/B/C branches, and Golden #588 are untouched.

## Existing owners and Grand Null inventory

| Scope | Existing authority, not copied or replaced | L1 contribution / bounded result |
|---|---|---|
| World Action / OUTCOME | S15/S16 ActionLifecycle, ActionSupervisor, ActionOutcomeInterpretation, S49 native evidence; #590 controller / #592 proposed wire | Validate typed S16 terminal lineage as **one input**. No Action issue, grant, source attestation or physical session |
| Memory | `PersistentCognition`, `Memory`, `retain_memory`, save/load and source/integration `Provenance` | Immutable JSON Memory content `L1_SOURCE_EPISODE_V1`; one full-scan/tag read-only query. No new owner, database, graph, serializer version, or additional index |
| S17 feedback | `interpret_action_outcome_as_learning_feedback`, source-bound explicit `ActionFeedbackCriterion` | Optional S17-produced `LearningFeedback` returned separately; no implicit training label |
| S10 update | `LearningFeedback`, `LearningUpdateAuthority`, `LearningPreferenceState`, `propose_learning_update`, `commit_learning_update` | **No S10 update**; retaining an observation never authorizes an update |
| S11 Habit | `HabitRepertoire`, `HabitCue`, `select_habit` | **No Habit promotion or rule creation** |
| A #421, D1–D4 / #544 | Deterministic exact cheap families, G3 science NO-GO | Never claim a model/world-model advantage from a change in candidate hints |
| B #431 | Memory/retention works in bounded offline cases, but cheap dictionary/tag often matches; B29 completion POST=0 due to wrapper | Reuse the actual owner, no S11 live Habit qualification |
| C #432 | Some bounded learned cheap adaptation; C11 `VALUE_GATE` and `ALWAYS_L2` lose to cheap L1 under registered simulated utility | No learned allocator or GPU compute bridge; resource study deferred to L4 |
| R #575/#586 | Standard RSEE runtime/environment | Use shared Python for focused/full/lint; no worktree-local dependencies |
| V / #544 | Scientific null/negative adjudication | No scientific GO, actual learning gain, physical goal success or measured model value |

Grand Null: source-matched full scan and tags already suffice for L1's small
offline examples. `cheap_tag_baseline` intentionally uses identical evidence
and yields identical hints; this is **not** an independent performance gain.

## Input, qualification, retained schema

`qualify_episode(action, outcome, world_revision, evidence_sha256, cue_tags,
feedback=None, hypothesis=None)` accepts a **current** ActionLifecycle with
terminal OUTCOME or UNKNOWN matching the exact S16 Action/Skill/Intent IDs and
terminal `world_provenance`. It rejects UNAVAILABLE, untyped text, foreign
Action IDs, non-current owners, and malformed digest/tag/revision fields.
`QualifiedEpisode.feedback` may be non-null **only** when typed S17 produced
source-matching, observed OUTCOME feedback. UNKNOWN never supplies feedback
through this bridge even if an S17 criterion could match UNKNOWN.

**Trust boundary:** typed S16/S17 input and SHA256 *format* do not independently
authenticate physical Mineflayer frames. The S owner must first verify original
evidence, digest, source session, source revision, and World lineage. On reading,
the S owner must provide its independently admitted digest set.
`admitted_evidence_sha256` is a supplied scope, **not** an attestation issued
by L1. This project has no cryptographic source signing in this bridge. An
unverified or unverifiable digest cannot yield `RECALL`.

`retain_observation(existing_cognition, qualified, integration_provenance)`
creates one existing `Memory` via `retain_memory`, preserving the original
`source_provenance` and a distinct integration provenance. Memory identity is
`l1:<session>:<action_id>:<world_revision>`; duplicates fail in existing owner.
All retained fields live inside the existing Memory string and use its normal
schema v2 snapshot serializer. No retained-owner revision is invented:
`PersistentCognition` has no memory-snapshot revision field. The embedded
`world_revision` is *S-supplied source state revision*, not S10 retained
learning revision.

The record stores terminal disposition/reason/source_status separately from
the optional `hypothesis`; hypotheses are not treated as observed outcomes.
It intentionally stores **no** goal-success label, S17 feedback direction,
learning authorization, inferred counterfactual truth, or Habit qualification.
Real #588 movement 0.627m and Action OUTCOME are not qualified goal results.
Historical `S49_OBSERVED_ACTION_OUTCOME` demo Memory entries stay legacy
records and do not silently become L1 source-qualified decisions.

## Read-only reuse API to S Lane

`retrieve_experience(snapshot, ReuseQuery(session_id, world_revision,
cue_tags, admitted_evidence_sha256, max_revision_lag=0))` returns
`CognitiveHint(status, memory_ids, observed_action_refs, examined, reason)`.

- `RECALL` references a matched **observed Action type**, not a recommended,
  authorized, successful or goal-completing Action. S may pass the memory
  reference as optional evidence to its next **candidate** evaluation only.
- `RECONSIDER` for a matched UNKNOWN; `CONTRADICTORY` for disagreeing observed
  terminal reason/source_status on the same action/cue; `STALE` for source
  revision outside an explicit bounded lag; `UNVERIFIED` for missing S-owned
  admitted digest; `UNKNOWN` for missing/invalid records.
- A different source session is not reusable. The revision lag defaults to 0;
  S must explicitly allow any continuity across revisions. The cue list is
  sorted/unique and matched by bounded set inclusion, with no model extraction.
- An opaque `CognitiveHint` holds no grant, ActionLifecycle, issuer, authority,
  authorization, or executable command. S keeps decision/Action admission,
  World ownership and the L0 safety reflex unchanged.

L1 uses simple full scan and tags; no graph advantage was established. A
`NO_RETENTION` arm is represented by an empty owner snapshot and yields no
evidence/UNKNOWN. `cheap_tag_baseline` uses the *same* admissible source
evidence and currently gives identical results, including negatives. Upgrade
to a graph/index only after measured latency/recall and negative controls
justify it.

## Negative tests / scientific limits

`tests/test_experience_bridge.py` covers original owner retention/save/load;
zero-retention vs cheap tags vs L1 equal comparison; duplicate identity;
wrong session, stale/future revision, missing source-admitted digest, wrong
cues, malformed L1 memory; contradictory outcomes; UNKNOWN; forged Action
lineage; S17 mismatch and UNKNOWN feedback; invalid tag/digest; stale
Action owner. All fixtures are offline synthetic typed fixtures, **not** real
World evidence. No observed positive task reward is implied.

The independent A/B/C Drafts are frozen; #544 G3 science NO-GO remains. L2
prediction/conditional consequence, L3 Habit/distillation and L4 adaptive
allocation are explicitly **not** implemented. No Minecraft S11 Habit
acquisition, L2→L1 distillation, L1→L0 compilation, L2 model call benefit, or
production source/goal/learning qualification is established.

## Operator runbook / RSEE (offline only)

On the actual WSL2 host, in an isolated checkout of the L1 branch:

```bash
BASE=/home/rinsa/.local/share/relay-self/rsee-1.0-20261011
PY="$BASE/venv/bin/python"
test -x "$PY" || exit 1
export PYTHONPATH="$PWD/src:$PWD"
"$PY" -m pytest -q tests/test_experience_bridge.py
"$PY" -m pytest -q
"$BASE/venv/bin/ruff" check src tests experiments adapters observability
"$PY" tools/check_repository.py
```

If Ruff is not present at that shared location, mark local lint **BLOCKED**;
do **not** install dependencies or create a new venv. This branch has no need
to run Node, Java, Minecraft, a GPU model or an LLM POST. CI on an ephemeral
GitHub-hosted Python runner is separate from the shared WSL2 runtime and
cannot certify RSEE runtime identity. Inspect each CI status at exact PR HEAD.

## S handoff / next physical gate

1. S verifies the original World session, action binding, native receipt and
   digest against its own source evidence; S alone decides allowed revision
   scope. A S49 projection or mere movement must not become goal success.
2. After existing owner-approved retention, S passes the immutable snapshot
   and admitted digest set to `retrieve_experience` at its next epoch.
3. S uses `memory_ids` and `observed_action_refs` **only as evidence for an
   otherwise independent candidate**. S must use existing Action
   selection/admission/authorization and S49 issuer.
4. A future authenticated goal criterion can flow through S17 to S10 only with
   existing `LearningUpdateAuthority`; S11 Habit promotion is still gated
   separately by independent World results and repetition.
5. Contradiction, UNKNOWN, stale, digest failure or scope mismatch asks for
   re-observation/reconsideration without issuing Action. No L0 modification.

**Classification:** `L1_OFFLINE_RETENTION_REUSE_BRIDGE_ONLY`. Engineering
integration is separable from scientific efficacy or a real source/goal pass.
