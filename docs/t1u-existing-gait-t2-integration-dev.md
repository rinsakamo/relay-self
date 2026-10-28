# T1u: existing gait model in the original single-P1 T2 owner (DEV)

**DEV_ONLY / DEV_WORLD_OBSERVED / NATIVE_GAIT_UNVERIFIED /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**

The offline integration passes, and the native refusal boundary was observed.
The requested two-MOVE **T1u gait-accounting loop has not passed**. A successful
legacy-accounting witness World is not a successful T1u World.
See [measured results](t1u-native-dev-results-20261028.md).

## Model and ownership

Baseline `fa61ca9fe1c84fd8886db8ed6e5cf7e124b67f4a` descends from successful
T1s HEAD `946708c2daab0741b34f3b669efafb4622262a43`.
The adopted model comes from `self/dev-p1-matched-boost-7ticks-20261027`,
HEAD `d2ecdb5c2609615c84ef55a75b1ca2bfb8b382b1`:

- `experiments/p1_gait_dev.py`: unchanged blob
  `d241978d0eba1843e3a6caed96c90e3c16e8dc39`.
- `tests/test_p1_gait_dev.py`: unchanged blob
  `4887ccc32b7e0aede95b0301d7778fe9a16f9c45`.

`TickAccounting.fatigue` remains the sole fatigue state. An uncharged admitted
anchor initializes its clock. Each subsequent admitted consecutive source tick
calls either existing `fatigue_p1.advance` (legacy default) or existing
`advance_gait_dev` (opt in), never both. Gait mode rejects the T1s recovery tau.
The original B0 energy ledger, T1e native reader, S49 issuer and Motor writer
retain ownership. Exceptions latch the accounting owner and forbid new Actions.
A refused gait records its source sequence, predecessor and tick without
advancing P1 or M0; no subsequent tick may bypass that refusal.

The existing normalized equation is `dF/dt = L(g,p) - k(g)*F`, evaluated
analytically per 0.05 World seconds. WAIT uses `(L=0,k=.12)`, WALK
`(0,.10)`, JOG `(.002,.06)`, RUN `(.004,.025)`; DASH has the existing
output-dependent load and `.02` recovery. Moving recovery is internal to this
same transition. These rates are engineering parameters, not human physiology.
Forward DASH extra M0 is still only a charge proposal: T2 rejects a positive
unposted charge. No additional fatigue state, free boost or second M0 ledger.

## Applied evidence path

`gait_source` is a provider contract, not an authenticator. The native case
binds the provider to `t1u_gait_source_dev.applied_gait_source_dev`, which uses
actual observations rather than treating a supplied `GaitTickDev` as proof.

The default-OFF `t1u-gait-dev` plugin flag adds passive `gait_dev` facts to the
**existing** Paper snapshot callback/channel: entity sneaking/sprinting,
movement-speed base/effective values, and modifier count. No new callback owner,
reader, command channel or actuator is added. Both Node and Python validate the
optional fields strictly; legacy snapshots retain their original schema.
When these facts are enabled, the original Node callback also reads
`bot.getControlState()` for seven controls into `applied_controls_dev`, inside
the existing evaluation budget. This is an observation of applied Mineflayer
control state, not a copy of Action arguments or a requested gait.

In the measured Mineflayer 4.39.0 runs, Paper's input bitmap stayed **0 even
while the player moved**. Therefore bitmap 0 alone cannot certify direction or
stillness. The first Paper-only witness run certified no JOG ticks. The later
witness combines two consecutive observations of back-only applied controls,
Paper speed base/effective value near vanilla `.1`, no modifiers, no
sneak/sprint, causal stable MOVING generation, and positive Paper displacement.
This supports bounded DEV JOG/back observations; it is not independent source
authentication or R full-tick gait proof. Nonzero contradictory Paper inputs
are rejected. The old `motor_mode=WALK` label remains legacy presentation only.

WAIT additionally requires the original T2 post-terminal/clear causal boundary,
both stationary input/pose/motion-counter endpoints and absent threats, plus
observed inactive Mineflayer controls. Input OFF or zero movement alone never
certifies WAIT. Unknown initial, onset, clear/residual, blocked or unsupported
mode intervals remain UNDETERMINED. WALK/RUN/DASH native classification is not
implemented by this bounded back-movement provider; their existing mathematics
is verified offline only.

## Native terminal and remaining boundary

The opt-in T1p runner installs its ledger before its start barrier. The second
initial stationary snapshot has no preceding Action terminal/clear, so it is
neither attested movement nor causal WAIT_DEV. The first T1u attempt refused before dispatch. In the final attempt, the
barrier returned after the anchor, one MOVE was dispatched, and its onset
tick was refused: S49 retained an UNKNOWN terminal and applied clear ACK.
Both attempts had zero P1 transitions and normal resource cleanup. Moving
the anchor repeatedly, dropping this tick, relabelling it JOG/WAIT or granting
recovery would hide the missing boundary. No such repair was made.

The two witness-only cases explicitly retain **legacy P1 accounting** so the
same reader can collect the full original two-MOVE/WAIT sequence. Their
successful physical execution cannot establish native `advance_gait_dev`
accounting. Saved originals are independently reduced using each run's exact
source snapshot. Native integrated-gait replay is explicitly NOT_EXERCISED;
unknown intervals are never stitched into a continuous gait series.

Next work must establish a source-grounded, model-compatible accounting rule
for the initial and transition intervals while retaining the single state,
consecutive clock and conservative WAIT boundary. It also needs separate
WALK/RUN applied evidence and atomic original-owner DASH charging before those
native modes can proceed. SelfBody-to-L0 feedback, main adoption, protected
Draft HEAD changes, QUALIFICATION and SCIENCE remain outside this result.

## Verification

Use the existing Python 3.12 venv with `PYTHONPATH=src:tests:.` for the nine
requested focused files plus `tests/test_t1u_gait_source_dev.py`. The final
focused/FAST counts, first failure logs, Node tests, build and contracts are
recorded in the measured results. FULL regression was not run.

main, Draft #545/#634/#626 HEADs, S18 and historical T1q/T1r/T1s original
manifests are preserved. No force push or R/V owner mutation.
