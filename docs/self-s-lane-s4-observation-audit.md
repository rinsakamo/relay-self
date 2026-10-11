# S Lane S4 — native observation accounting for the zero-decision World run

Authority: Self product Issue #537. This is a **new offline-only** child of S3
Draft #598 exact HEAD `6f493b7a559dd72ea365998b9eadbd35fd7eb9b4`.
Its ancestry includes S2 Draft #597 exact `c12a7bbc0fd0af4359c55926a0a22ea8c6ef9da6`.
Do not merge or mutate #598, #597, #592, main, R/L/V, old A/B/C or #544.

## What the one physical S2 permission actually measured

The user-authorized run on 2026-10-12 consumed exactly one S2 permission and
ended `S2_ONE_SHOT_WORLD_OBSERVED_ZERO_DECISION_ACTION_CLEAN_EXIT` on
exact S2 HEAD. Operator report: Issue #537 comment #6114955246.

- 181 **outer driver-delivered** native observation frames over 180 seconds;
  no native correlated probe, L0 decision, L1 review, Action or terminal OUTCOME.
- One Java and Mineflayer session lifetime; Java, Node and CLI exit 0; owned
  processes/listener cleaned. No GPU/model/LLM POST.
- Original `session_events.jsonl` hashes and audit were preserved; the
  executable did NOT individually archive each skipped native observation.
  Therefore the existing 181 total **does not say** how many were
  `health`, `time`, `move`, `entities` without targets or snapshots
  with registry truncation. Reconstructing those from the count would invent
  data. It also does not establish a zombie was absent from the entire World.
- User authorization was **consumed**; no retest or World staging is authorized.

## What S4 adds

`S4NativeObservationAudit` is an owner-local, bounded read-only counter
attached to `BoundedSessionDriver.run` **after** its only original
`session.receive()` yields a typed native observation and **before** its
existing event-kind/target filtering. It never calls `receive()`, probes,
starts Node/Java or a model, issues a grant, alters L0, or touches S10/S11.

One new fsync'd `native_observation_audit` JSONL row is appended just before
`session_terminal` (or where available just before `session_failed`).
It reports:
- total outer observations and first/last original native sequence;
- counts per original observation kind;
- `entities` with and without zombie vs zombie recorded in other kind's
  snapshot (a *non-triggering* observation);
- original snapshot entity-registry truncation, near/multiple zombie
  snapshot counts; and existing `NativeObservationOnly` filter counters
  for duplicate targets, ignored hurt events and observed non-targets.

Possible diagnostic classifications are intentionally bounded:
`NO_OUTER_NATIVE_OBSERVATIONS`,
`NO_ZOMBIE_IN_OUTER_OBSERVED_SNAPSHOTS`,
`NO_TARGET_OBSERVED_WITH_TRUNCATED_REGISTRY`,
`ZOMBIE_ONLY_IN_NON_ENTITY_SNAPSHOTS`,
`ENTITY_TARGET_OUTER_SEEN_BUT_NO_DECISION`,
`S49_DECISION_PATH_ENTERED`.

None means global World safety or complete Mineflayer observation coverage.
Native frames consumed by S49's internal probe or S16 Action execution are
not covered by the outer audit. `ignored_hurt_frames` and duplicate entity
events are counted by the existing filter but were not source-frame archived.
S4 does not create any new physical observation or make the old run retroactively
more discriminating.

## Tests and handoff

S4's offline synthetic **181-observation/zero-decision** fixture checks the
negative outcome, not historical recreation. Separate tests demonstrate the
critical difference between a zombie contained in a `health` snapshot and
an actual `entities` event, and verify that the original correlated S49
WAIT/MOVE_AWAY→Action/OUTCOME remains unchanged.

```bash
BASE=/home/rinsa/.local/share/relay-self/rsee-1.0-20261011
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD"
export PYTHONDONTWRITEBYTECODE=1
"$BASE/venv/bin/python" -m adapters.mineflayer.self_s1_runtime
"$BASE/venv/bin/python" -m pytest -q \
  tests/test_self_s4_observation.py tests/test_self_s3_experience.py \
  tests/test_self_s2_integration.py tests/test_self_s1_runtime.py
"$BASE/venv/bin/python" -m pytest -q
```

Use the existing central RSEE only. Neither these tests nor GitHub runner
CI require or have permission for a physical session. No new S4 CLI opt-in;
the original gated `--run-disposable` command must NOT be launched under
the consumed S2 approval. A future physical run requires its own fresh
one-shot authorization and exact new HEAD confirmation.

Result ceiling when focused + full inherited CI pass:
`S4_OFFLINE_OBSERVABILITY_QUALIFIED / PRIOR_WORLD_ZERO_DECISION_UNRESOLVED /
NO_NEW_PHYSICAL_RUN / NO_PRODUCTION_GO`.
