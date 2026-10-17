# SelfWorld v0 — source-bound observer-local Present composition (#633)

**Status:** OFFLINE DEVELOPMENT. Not physical World qualification, not science, not a permanent world model.

## Why a view, not a new owner?

Existing [Present projection](../adapters/mineflayer/present_projection.py) already
owns the bounded native observation translation; existing
[PersistentCognition](../src/relay_self/persistent_cognition.py) owns governed
Memory, [Belief](../src/relay_self/belief.py) owns fallible evidence assessment,
and [Prediction](../src/relay_self/prediction.py) owns bounded hypothetical
transitions. ATT handles candidate selection; S16/S17 handle Action result and
learning-feedback authority. No additional semantic, database, execution,
inference, or memory owner is justified merely by viewing these together.

`src/relay_self/self_world.py` composes an immutable one-epoch
`SelfWorldView` for **one observer identity, one session, and one epoch**.
No World reconstruction, global map, mutable state, observation polling,
inter-Self transport, or Action issuing takes place.

| Origin | Actual input | Meaning |
| --- | --- | --- |
| OBSERVED | `WorldObservation` from scoped target Present | exterior details actually in that bounded, attributed probe (not currently authoritative truth) |
| REMEMBERED | explicitly selected `Memory` from **own** `PersistentCognition.identity.self_id` | past governed content, not current measured reality |
| INFERRED | existing `BeliefAssessment` with source evidence | fallible BLF assessment; conflict/undetermined -> UNKNOWN |
| HYPOTHETICAL | scenario-local existing PRD `PredictionState` | possibly impossible imagined environment |
| PREDICTED | exact scenario-linked `PredictionResult` | conditional model forecast, never measured World |
| UNKNOWN | no qualified input, missing target, unqualified inference | ignorance, not evidence of physical absence |

The target-specific adapter `adapters/mineflayer/self_world_projection.py`
projects native-observable entity identifier, label, 3D position and distance.
Optional visible Action is representable but not invented if absent. It does
**not** project other Self's cognition, intent, body resource, memory or secret
attributes. Core code never imports Mineflayer packets.

## Coverage, freshness and privacy

All observations retain their source reference and
`observer_id/session_id/native_seq/request_id`, bounded coverage
scope/radius/cap/candidates/truncation, and optional source-supplied
`observed_at_ns`. This value cannot be invented by the adapter; caller-provided
timestamp is *not* self-authenticating. `minimum_native_seq`,
`seen_observation_refs`, and an optional inspected-time/max-age check fail
closed on stale/foreign/replayed evidence. These cursors are caller-owned
inputs, **not** a second persistent store. Native seq, monotonic nanoseconds,
decision epoch and Paper `World.getFullTime` are different clocks.

An unlisted entity remains UNKNOWN even when the bounded source reports
no nearby candidates: **no global absence or safety conclusion** can follow
from limited Minecraft registry coverage. A stored OBSERVED fact describes the
historical observation, not the actual present World.

For Memory, `memory_ids` must be explicitly chosen from a
`PersistentCognition` snapshot whose identity matches `self_id`;
passing private B memories as A is rejected. Two Selfs can each compose
views for the same World without automatic dissemination. B's actual
SelfBody/SelfWorld/Memory is never fetched to model B from A. A may create
a *hypothetical* estimated B perspective, explicitly attributed to A, but
cannot read B's real internal experience.

## SelfBody join and action isolation

[SelfBody v0](selfbody-v0.md) retains exclusive scope over own bodily
representation. Its existing frozen view now supports an **optional**
`self_id` (legacy callers remain valid). Joining it to SelfWorld requires
explicit identical owner/session/epoch, plus identical native
seq/request/provenance when both share a Present observation. This is a
read-only reference, not a duplicated physical Body store. Without qualified
owner attribution, SelfBody cannot be joined; legacy L0/Action paths remain
unchanged.

```text
Physical World (external) -> existing Executor / readback / Present
              -> observer-local read-only projection
                   + own governed Memory
                   + existing BLF / PRD
                   + optional matching SelfBodyView
              -> one-epoch SelfWorldView for A
              -> existing ATT / L0-L1-L2 / S12-S17 authority (unchanged)
```

Hypotheses, predictions and memory never grant Action, mutate physical
World, alter M/P1 resources, or update governed learning. S16 `OUTCOME`
remains distinct from source observation, BLF update and LRN commit.
No new controller, FLY, message channel, intent issuer, or communication
protocol exists in this work.

## Tests and limits

`tests/test_self_world.py` uses offline synthetic fixtures for two observers
in one imagined World, private state non-leakage, stale/foreign/duplicate
source, bounded/truncated coverage, memory ownership, BELIEF provenance,
impossible counterfactual, SelfBody owner and source ID mismatch, and
no dependency on SelfWorld for existing L0. The test does **not** execute
the Java/Node World, qualify physical causality, test communication or show
coordination benefit.

Unresolved: independently authenticated native observation/time/World ID,
explicit L1/L2 runtime consumer, S17/LRN learning from failed predictions,
source-warranted other-Self action observations, authorized communication
and social/coordination experiments, Paper tick/control attribution and
R/V qualifications. Only future source-warranted integration may address them.
