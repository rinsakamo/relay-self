# V7 prescience ledger — 20 fixed prospective slots

Authority: [V #619](https://github.com/rinsakamo/relay-self/issues/619).
This is an **offline metadata completeness check**, not a source reviewer,
new experiment, or amendment to the frozen V7 M0.2 preregistration.

## What changed

- `experiments/validation/v7_m02_trial_roster.py` derives exactly four
  registered seeds × five registered arms from the V7 manifest.
- Every prospective science slot is `NOT_RUN`; all twenty must be present.
- V independently pins the five S-created candidate profile SHA256 values
  (BASE_ON and SHAM_ON must have the **same** full configuration digest).
- **DEV** and **QUALIFICATION** candidate attempts can be recorded without
  counting as a science trial. Each attempt has a globally unique ID, retained
  outcome (including FAILED/BLOCKED/UNDETERMINED), optional original bundle
  digest reference, and explicit R-review *claim*.
- A source digest string, R PASS label, or reported DEV success **does not
  authenticate original bytes, World identity, elapsed server ticks, motion
  packets, or changed-configuration engineering validity**. The checker
  always outputs `REVIEW_ONLY` and science=0.
- Duplicate/missing slots, duplicate attempt IDs, foreign arm/config hashes,
  mutated preregistration, false science trials, and consumed-grant reuse
  fail closed.

Run the static roster checker:

```sh
PYTHONPATH=src:tests:. python -m pytest -q tests/test_validation_v7_m02_trial_roster.py
PYTHONPATH=src:tests:. python -m experiments.validation.v7_m02_trial_roster
```

To review a separately retained JSON registry (without running Minecraft),
import `read_roster(Path(...))` and `review_roster(...)`; do not mistake
self-reported JSON fields for independent original-byte verification.
Preserve even failed or interrupted attempted runs in the registered slot.

## Remaining gates

1. **S (DEV):** five actual disposable Paper World arms using the pinned
   configuration generator; immutable original source bytes, fresh clone
   identity, per-arm server clock and physical `PlayerMoveEvent` paths.
2. **R (QUALIFICATION):** independent originals/config/world/process review
   for the changed profiles. The 2026-10-15 third one-shot qualification
   only covers its original unchanged configuration. Do not reuse its grant.
3. **V (SCIENCE):** native real World tick/path/billing evidence plus a
   separately authorized, prospective **20-trial** run and independent scoring.
   Historical V6 remains 0/48; V7 remains 0/20.
4. **Interpretation:** BASAL/WALK billing isolation tests instrumentation,
   *not* ecological coefficient optimality, cognition, learning, or
   production readiness.

No Java, Paper, Node, Minecraft, model or GPU process is started by this ledger.
Do not edit V2–V6 frozen sources, old evidence, R/S branches, or protected main.
