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
