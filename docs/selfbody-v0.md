## 2026-10-24 — P1 original-owner reconciled sensor readout handoff

PR #626 now has a candidate pure exporter
`experiments/p1_selfbody_export.py`: it recomputes the original
`reconcile(profile, before, prepared, SourceBoundTick)` result before
calling the existing quantized `sensed_for_self`. This has a strict
**producer-local, not independently World-attested** classification.

Product adapter `handoff_from_p1_owner_readout` accepts only that
original typed `P1SelfBodyReadout`, not arbitrary dicts or true Fatigue,
and checks native self/session/probe source through the existing
`project_p1_sensor`. Until PR #626's actual module exists in the
product checkout, this conversion **fails closed**, and the current
S51 B0 path keeps P1 UNKNOWN. A synthetic compatibility test uses a
stand-in type only to check the readout's shape; it is *not* original
P1 verification, physical WAIT attestation, or proof of fatigue recovery.

Original P1 physics, Paper tick source, full-tick WAIT inactivity
verification, blocked MOVE treatment, S49/S51 Action ownership, M0
basal metabolism and S10 grants are **unchanged**. No executable
full-Self loop or live P1 producer installation is claimed.

---

## 2026-10-24 — P1 sensor handoff to the existing M0/SelfBody view (DEV)

**PRODUCT ADAPTER ONLY / UNATTESTED P1 INPUT / DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.**
P1 physical-fatigue ownership remains in the separate unmerged Draft
[#626](https://github.com/rinsakamo/relay-self/pull/626), specifically
`experiments/fatigue_p1.py` and `experiments/fatigue_p1_boundary.py`.
Their physiology, WAIT recovery, profile and World-tick verification are **not**
copied, edited or bypassed by this work.

The optional `P1OwnerSensorHandoff` supplies a **sensor reading**, not true
fatigue or physical recovery, and an original-owner **source pointer**, not
independent authenticity. `project_p1_sensor` correlates session, original
native seq/request/provenance, source owner World tick, profile SHA256 and
activity/wait-witness pointer. A WAIT-shaped report without its idle-interval
reference is rejected; a MOVE/FIGHT report carrying WAIT witness is also
rejected. **The existence of a string witness is not an attestation that a
full physical tick was idle**. The S/R executor and P1's existing
`SourceBoundTick` / `reconcile` gate alone may establish physical semantics.

`compose_b0_cognition_views(..., p1_handoff=None)` keeps legacy B0 behavior
and `P1 UNKNOWN` by default. When an explicit producer-local handoff is
supplied, `SelfBody.sensed("p1_fatigue_sensor")` has
`BodyOrigin.INTEROCEPTION`, alongside the original observed native
`food/health` and separate `m0_energy_sensor`; it **never** becomes
`BodyOrigin.OBSERVATION` nor grants movement/WAIT/S10/M0 permissions.
The optional summary labels this as `PRODUCER_LOCAL_UNATTESTED`, never
qualified native source. The existing S51 entry does **not** enable this
optional handoff: until the P1 owner can supply a genuinely correlated
and source-checked tick, real product fatigue remains UNKNOWN.

Added offline positive/negative tests cover the unchanged default,
separate P1/M0 origins, invalid session, native seq/request, profile,
World tick, nonfinite sensor, REST smuggling, false WAIT witness and
blocked/MOVE non-recovery. Original physical P1 invariants:
**physical WAIT recovers fatigue only on authenticated full World ticks;
blocked MOVE is not WAIT; M0/Paper BASAL continues during WAIT.**

This is an implementation seam, not a runtime-qualified P1 integration.
Next owner handoff requires #626/S/R original verified tick and Action state,
then exact-HEAD Python3.12 FAST and explicitly authorized disposable DEV World.
No unqualified sensor can be used to award physiological or scientific success.

---

## 2026-10-24 — B0/S51 owner-local multi-epoch cognition trace (DEV)

**Implementation candidate, not independently tested or qualified.** The
existing S51 owner now projects each original hunger/appetite L0 decision,
then the existing post-EAT next-L0 decision, into a bounded array
`dev_b0_cognition_epochs` (1–16 existing appetite probes plus 1 successor).
Each projection reads the already selected `B0Decision` and original
`B0EnergyLedger` sensor; it does not call `decide()` again, advance
metabolism, add native probes, move or authorize any Action.

The original Self DEV receipt compares each array entry to the corresponding
original `ground_appetite_trace`: session/seq/request, L0 kind, native Food,
M0 sensor reading and tick, explicit UNKNOWN P1, and the no-authority flags.
The final entry must equal the separately validated
`dev_b0_cognition_next_epoch` and preserve strictly increasing native seq
with nondecreasing owner ticks. Incorrect, re-ordered or forged arrays fail
the DEV receipt; missing arrays remain `NOT_OBSERVED` for older sources.
The positive classification is **ORDERED_PRODUCER_LOCAL_DEV**, never
independent native attestation or behavioral gain.

The original appetite trace does not independently preserve every Health
field, and M0 owner ticks are decision ticks rather than Minecraft World
time. Hence no physical-fatigue WAIT recovery or long-run viability claim.
The B0 and S49 owners are still separate existing run routes; neither this
trace nor a HOLD S10 update joins their physical owners.

These new tests are synthetic; the final exact HEAD still requires local
Python3.12 focused/FAST and real disposable DEV proof before a product
runtime claim. R qualification and V science remain NO_GO / NOT_RUN.

---

## 2026-10-24 — M0 owner-local interoception DEV integration

**Current scope: implementation candidate, DEV_ONLY / QUALIFICATION_NO_GO /
SCIENCE_NOT_RUN; source-origin and cognition semantics are distinct.**

SelfBody now has optional `BodyInteroception` entries with a separate
`BodyOrigin.INTEROCEPTION` / `SelfBodyView.sensed(key)` accessor. This is NOT
the native `observed(key)` path: a local M0 sensor reading cannot claim native
Minecraft observation or grant knowledge of the true simulated M0 Energy.
Every sensor is joined to an already typed Present by session, native seq,
request ID and native provenance, and records a separate M0 owner/tick
provenance. An absent P1 physical fatigue input remains UNKNOWN.

The B0-specific adapter `self_body_m0_projection.py` accepts the **existing**
S51/B0 owner `B0EnergyLedger`, its **already selected** `B0Decision` and the
same correlated native probe. It checks the exact B0 owner session,
M0 decision tick, native source, positive nonterminal status and owner sensor
recalculation before producing one immutable joint SelfBody/SelfWorld view.
This is **producer-local DEV linkage**, not independent physical source
attestation, or a second policy that can request/issue Minecraft Action.

The existing S51 native EAT→M0-credit→next native L0 decision path publishes
a small extra read-only `dev_b0_cognition_next_epoch` record **only under its
existing `dev_only` mode**. No new native observation, movement, EAT,
resource credit, S10 permission or L2 model request is made. The enclosing
Self product DEV receipt checks this sensor value, world/body original probe
sources, M0 tick and next L0 against the unmodified owner report. Missing
sensor record is recorded as NOT_OBSERVED; an inconsistent present record
makes that DEV trial fail closed.

**Limit:** This is a first real M0-to-SelfBody *information* edge.
It does NOT join the separate S49 native Action owner and S51 M0 owner into
one continuous Full Self; P1's physical fatigue implementation lives in
unmerged Draft #626. Never manufacture fatigue, treat blocked MOVE as WAIT,
equate M0 simulation units with Minecraft health, or call this a scientific
homeostasis result. Tests are synthetic until exact HEAD Python 3.12 FAST and
explicit local DEV World evidence exist. No real Minecraft/LLM/W4 activity
is requested by this document.

---

# SelfBody v0 — read-only cognitive body view (#632)

## Purpose and authority

SelfBody is a **temporary Self-side composition** of fallible bodily beliefs,
hypotheses, existing predictions, and source-addressed Present observations.
It is not an executable Body, World copy, persistent SelfImage semantic owner,
or S18 owner replacement. Historical [Grand Null #31](https://github.com/rinsakamo/relay-self/issues/31)
remains in force. The interface has no Action admission, issue, retained learning,
or physical resource adjustment API. Physical truth stays on the external side of
the Embodied Boundary. This name does not claim neuroscience equivalence with
Body Image, Body Schema or a forward model.

## Source boundaries

| Element | Existing owner | Permitted meaning | Prohibited promotion |
| --- | --- | --- | --- |
| `BodyObservation` | qualified Present | selected native fields with session, native seq, request and source provenance | World truth / Paper tick |
| `BeliefAssessment` | BLF | fallible body proposition and its existing evidence | measured physical ability |
| `BodyHypothesis` | caller-local PRD `PredictionState` | even physically impossible imagined morphology | physical change / authorization |
| `BodyPrediction` | PRD `PredictionResult` | conditional prediction under exact hypothesis | observed Action result |
| `UNKNOWN` | missing/blocked readback | information unavailable | zero or successful movement |
| `ActionOutcomeInterpretation` | S16 | known, unknown or unavailable Action closure | intrinsic position, movement, or LRN update |

`compose_self_body_view` creates a frozen `SelfBodyView` for one explicit
session and epoch. `observed`, `hypothetical`, `predicted`, and
`beliefs_about` deliberately expose separate origins. L0/L1/L2 can receive
the view as optional read-only cognition context; v0 does not change the L0
initial admission or any Action issuer. No state is retained.

The Mineflayer adapter `project_body_present` maps only x/y/z, health, food
and food saturation from an already projected `MinecraftPresent`.
Minecraft food is **not M Energy**. Neither P1 physical fatigue nor L cognitive
fatigue is fabricated. x/y/z are coordinates, not authoritative movement distance.

For an Action readback, `project_body_action_readback` joins an existing S15
`WorldConsequence` with matching S16 `ActionOutcomeInterpretation`. It
requires `EXECUTED` / `OUTCOME`, reason `observed_execution`, exact
action/binding/ref/session/provenance, and ordered before/after native probes.
Only the native after-probe is projected. ACK, `UNKNOWN`, `UNAVAILABLE`,
adapter rejection and requested distance cannot mint movement evidence.

## Freshness and clocks

`minimum_native_seq` and `seen_observation_refs` are explicitly
caller-supplied, not new persistent cursors. Foreign-session, stale and duplicate
readings fail closed. `native_seq` is not Paper `World.getFullTime`,
elapsed time or logical `epoch_id`. The upstream source adapter must
authenticate and qualify source evidence: a Python object constructor alone
does not establish real World truth. The base BLF/PRD provenance is preserved,
not relabeled as native observation.

## Data flow and owner boundaries

```text
World → single existing Executor → native Present / S15 consequence → S16
                              → Mineflayer SelfBody projection (read only)
                              → SelfBodyView (Present + BLF + PRD + imagination)
                              → Self cognition L0/L1/L2 (optional view)
                              → existing S17/S10 learning gate (unchanged)
                              → existing ROUTE / ADMISSION / EXEC_BIND / Executor
```

Predicted versus observed differences remain separately attributed. They do
not automatically commit to MEM/LRN, change Energy/fatigue, create a WAIT tick,
or justify a new physical Action.

## Verification status and remaining gaps

`tests/test_self_body.py` tests phantom wings, actual-vs-predicted x,
UNKNOWN/UNAVAILABLE, stale/foreign/duplicate Present, mismatched scenario,
BLF fallibility, L0 independence, and hypothetical M/P1 isolation. Fixtures
are **offline-only**; no new World, Action or science qualification.

Not yet qualified: Paper full-time and effective control tick correlation;
independent native evidence authentication; M/P1 source-bound observation;
a live L0/L1/L2 consumer; prediction-mismatch LRN update through S17; actual
model-benefit test. These remain under the appropriate existing owners.
**DEV_ONLY / NO_PHYSICAL_RUN / NO_SCIENCE_CLAIM.**
