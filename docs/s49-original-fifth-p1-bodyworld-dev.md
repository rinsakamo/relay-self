# RelaySelf S49 original fifth epoch after third MOVE — 2026-10-25 DEV

**Result: `DEV_WORLD_ORIGINAL_S49_FIFTH_WAIT_THIRD_P1_MODEL` — DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.**

This engineering milestone extends the isolated DEV original-S49 host, not main,
the protected original action executor, or any R/V evidence. The pre-existing
three-epoch default behavior remains opt-out/default. Additional fifth epoch
requires `dev_next_epoch="MOVE_AWAY"`, `dev_fifth_epoch="WAIT"` and
both explicit DEV environment gates; a second native protocol receiver,
new Action issuer or independent L0 host is never created.

## Verified actual Paper 1.21.8 Java21 / Mineflayer Node22 World

Successful fresh run:
[Actions #40177693117](https://github.com/rinsakamo/relay-self/actions/runs/40177693117)
at source HEAD `9b0593c4e4f31d645ab0be4a82b2b526a8738e05`.
[Original artifact 12592537800](https://github.com/rinsakamo/relay-self/actions/runs/40177693117/artifacts/12592537800);
ZIP read back and the inner `original_s49_report.json` and
`world_first_dev_report.json` were inspected again.

- One original S49 session, original L0 five actual native decisions:
  `WAIT → MOVE_AWAY → MOVE_AWAY → MOVE_AWAY → WAIT`.
  Native event sequences `7,19,47,69,90` and correlated probes
  `8,20,48,70,91`.
- Three original S49 S14/S16-authorized `MOVE_BACKWARD` physical
  Action OUTCOMEs. The last action `s49-native-move-69` measured
  `0.6269065734210617` blocks, with applied S16 clear.
- Original second MOVE → independent Paper idle callback window 8 consecutive
  ticks → original P1 `advance(WAIT)` recovered a **model** fatigue
  of `0.02507626293684247 → 0.0`. The uncertain boundary and gaps
  are not given credit.
- Third original MOVE's separately checked native execution evidence
  and a later **same-owner** correlated probe seq `79` drive original
  P1 `advance(MOVE)` from explicit prior modeled zero:
  `0 → 0.02507626293684247` model units. This is a new DEV model step,
  not a native tick-localized fatigue sensor. The profile and original P1
  implementation are unchanged.
- A new immutable SelfBody with hypothetical P1 sensor 3% and estimated
  capability 98% shares the actual native source/epoch with SelfWorld.
  The same model hypothesis is projected onto the **fresh fifth native
  L0 probe seq 91**, before the existing original `NormalWorldL0.decide`
  selects **WAIT**. No fifth Action request or execution.
- Java/Node exits `0/0`; original and outer DEV reports PASS.
  Python 3.12 focused tests/Ruff/syntax:
  [#40177676344](https://github.com/rinsakamo/relay-self/actions/runs/40177676344)
  SUCCESS and actual full DEV run preworld focused step SUCCESS.

## Attempt, fix and limits

The first real World run
[#40177380678](https://github.com/rinsakamo/relay-self/actions/runs/40177380678)
had original S49 **five decisions and three Action OUTCOMEs PASS**,
but outer DEV review returned BLOCKED_OR_FAILED because the legacy fourth
source check referenced `decisions[-1]` rather than `decisions[3]`.
That original run artifact [12592188006](https://github.com/rinsakamo/relay-self/actions/runs/40177380678/artifacts/12592188006)
is left immutable; source index correction was made in a later commit
and a **fresh new DEV World** run produced the successful outcome above.
The previous error is not retroactively upgraded.

The original `s49_normal_session_real_ci.py` has a **protected-source
change in this isolated DEV branch** relative to historical S49. It
requires explicit scoped owner/source adoption review before any PR #545/
#634/main integration; do not relax protected manifests or claim byte
equivalence. The original `normal_action.py`, original P1 calculus,
single receiver/issuer, S14/S16 authorization and cleanup remain
unchanged; other Draft heads and main were not updated.

**Crucial epistemic boundary:** Third MOVE P1 is a **fallible model
hypothesis** from measured aggregate distance, not physical fatigue telemetry
or a continuous World tick ledger. The fifth L0 policy still uses its
original S42/native geometry only; P1 does **not** change selection or
mint Action authority. There is no R-qualified `SourceBoundTick`,
R-admitted WAIT count is zero, R P1 recovery zero, no S10 update,
no V trials, no qualification or science claim.

**Next engineering step:** For true fatigue-sensitive behavior, add
an explicitly budgeted DEV-only policy comparison against the same fifth
native World input, retain original S42 as the safe baseline, and only
consider an opt-in original-host policy change with separately authorized
S14/S16 Action and negative controls. Do not infer fatigue caused the WAIT.
