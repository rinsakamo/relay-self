# S Lane S3 — original native Outcome → observed Memory → next hint (offline-only)

Authority: product #537, learning integration #426. Stacked on **S2 #597**
exact `c12a7bbc0fd0af4359c55926a0a22ea8c6ef9da6`.
L #594 source `40db58d548ea31c4a70acabcc71b0954c7b6ce42`
is a separate open Draft built from #590; `experience_bridge.py` and its
focused tests were individually **reviewed/copied byte-for-byte** from #594
instead of merging/cherry-picking its branch. This convergence Draft does not
change either original PR or any old A/B/C Draft, Golden #588, protected main.

## Existing owners, no new issuer

- Existing S49 `NormalSessionActionExecutor.execute` already creates the
  original typed `ActionOutcomeInterpretation` for S16. The only change to
  `NormalActionReceipt` is an optional immutable field that exposes that
  **same original S16 value** after the old Action path completes. No new
  Action proposed, authorized, issued, replayed, interrupted or scheduled.
- New `S3ReadOnlyExperience` validates exact receipt and correlated
  observation source session, S16 reason/binding/Action lineage, current
  terminal owner, original decoded native before/effect/clear/after evidence
  and independently recalculated physical movement using existing
  `capture_native_action_evidence`. It retains the **observed execution**
  with an evidence digest and reference to the existing S16 owner in the
  already-implemented `PersistentCognition.retain_memory`. The `near_zombie`
  cue is accepted only from the original independently correlated probe with
  untruncated zombie evidence. A future probe with no zombie has a different
  cue and receives no matching prior escape hint.
- S17 feedback is deliberately **absent**. No S10 update authority, retained
  learning value update, S11 Habit rule or Minecraft goal success label.
- S #592 `s49_callbacks` optionally receives the S3 in-memory observer plus
  the existing append-only source event sink. Upon original Action closure,
  it attempts observational retention. The next independently correlated
  native probe reads `CognitiveHint` before the unchanged L0 selection.
  Only `experience_read_only_hint`, `experience_unavailable`,
  `experience_retained_observation` or `experience_not_retained` is written
  into existing JSONL. No feedback from the hint to the S49 grant or
  `NormalWorldL0.decide`.
- Successful bounded session additionally saves **one** existing owner-format
  Memory snapshot as `s3_observed_memory.json` in the independently fresh
  operator output directory. It cannot overwrite an existing file. All
  Action/OUTCOME and physical cleanup records remain owned by S.

## Scope and scientific meaning

This first S3 adapter deliberately maps L1's historical
`world_revision` field to **Mineflayer native source sequence** because
no independent persistent World-state-revision provider exists in S1.
A bounded lookback (default 32 source messages, maximum 64) permits read-only
historical context; **it is not proof that the World state, hazard, goal,
action efficacy or cue has stayed constant**. If old/reversed/foreign/unknown,
no observation is promoted into fresh authorization; L0 relies on its own
current source and admission. A future stable World revision and genuinely
signed goal result must be independent S-owned evidence. A SHA256 identifies
decoded original evidence within S's already-admitted session, **not a
cryptographic signature** and not authenticity outside that owner.

## Operator commands: shared RSEE, offline only

Run in an independent branch worktree on the WSL2 operator host, using only
preinstalled shared packages. Do not `pip install`, `npm install`, symlink
`node_modules`, copy GGUF, start Java/Mineflayer, llama.cpp or issue Actions.

```bash
BASE=/home/rinsa/.local/share/relay-self/rsee-1.0-20261011
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD"
export PYTHONDONTWRITEBYTECODE=1
"$BASE/venv/bin/python" -m adapters.mineflayer.self_s1_runtime
"$BASE/venv/bin/python" -m pytest -q tests/test_self_s3_experience.py tests/test_experience_bridge.py tests/test_self_s1_runtime.py tests/test_self_continuous_host.py
"$BASE/venv/bin/python" -m pytest -q
"$BASE/venv/bin/ruff" check src tests experiments adapters observability
"$BASE/venv/bin/python" tools/check_repository.py
```

If tools are absent, record BLOCKED; do not install a second environment.
GitHub CI uses ephemeral standard Python/Node runners, **not** the operator
WSL2 shared RSEE. CI source fixtures are not physical World authentication.
The inherited S1 `--run-disposable` path remains explicitly
operator-gated and is **not** authorized by this change, by offline CI, or by
a casual "進めて". Golden #588 physical permissions remain exhausted.

## Negative controls / next gate

Focused S3 tests compare empty Memory vs source-qualified observed
historical hint, save/load through original owner, wrong Action/binding/
session/provenance/S16, tampered terminal, UNKNOWN, replay, future/stale
source revision, no arbitrary long retention. Historical cheap tag baseline
and L1 tests remain unchanged; graph/model superiority is **not** claimed.

Result ceiling if CI green:
`S3_OFFLINE_SOURCE_SHAPED_MEMORY_HANDOFF_ONLY`, no physical learning,
Habit or S11/L2 distillation, actual goal success or new World session.
Before physical testing S needs separate explicit authorization, original
source proof, source sequence and World revision semantics, cleanup,
RSEE check and exact evidence readback. V #544 G3 NO-GO is unchanged.

## Parallel product S2 reconciliation

S2 #597 is the already qualified source-scoped S11 far-WAIT candidate and optional
non-authorizing S60 L2 observer. S3 leaves its `on_candidate` and `on_l2_probe`
callbacks intact. S3 only adds the post-S16 observed Memory sink and the
pre-choice read-only recall sidecar; no prior S2 selection is overwritten.
Draft #598 was retargeted and rewritten by exact expected-head lease solely
because sibling #597 qualified while the first #598 stack was being prepared.
The initial #598 S1-only chain is superseded; no result or Golden claim was
promoted. Review the new exact PR HEAD, not the earlier branch ancestry.
