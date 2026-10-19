# RelaySelf Self 1.1 × Lane C C15 — source-bound spatial observation

## Scope / ownership

This integration branch starts at Self product #545 exact frozen
f1f908d68c46f1315230171737fb9d8cb08f6df3.
The C15 spatial reducer, its manifest and original tests are copied UNCHANGED
from independent Lane C #525 HEAD 5e738596b805522d8516b43fa1b7ee001bfc5b2b,
with exact git blob equality checked by CI.
C16 #531 remains a separate optional operator-gated physical experiment.
No predecessor branch, main, Minecraft protocol or existing host
Action/S10/S11 source changes in this integration.

New API in adapters/mineflayer/self_lane_c_witness.py:

    qualify_self_action_spatial(report, action_id=..., spec=..., source_lines=...)

report is an already saved S49 native_report.json with its exact decoded
execution_evidence originally captured from S16 WorldConsequence. This
function does NOT request new World observations or start a game or LLM.

spec is an explicit C15 SpatialContract with preselected disjoint GOAL
and ALTERNATIVE regions and exact S49 source references: session_id,
action_id, and stop action_id = action_id + "-s15-clear".
A spatial specification is caller-supplied, NOT proof that autonomous intent
specified this goal before an Action.

source_lines is optional COMPLETE UNMODIFIED ORIGINAL Mineflayer bridge
JSONL stream from adapter_started seq=0, with original source seq.
The strict MineflayerStreamDecoder validates the original stream, then the
four S16 decoded source frames (before, applied set, applied clear, after)
must match the independently supplied stream exactly. Only then does the
unchanged Lane C EndpointReducer adjudicate the spatial region.

## Important: current Self S49 evidence is NOT sufficient for C15 positive status

Self product #545 stores one pre-Action observation, applied dispatch,
applied cleanup and ONE post-Action observation. C15 requires TWO stable,
distinct post-stop native probe frames. No missing probe can be generated,
copied from an existing frame, guessed, resequenced, or silently obtained
by invoking Minecraft in this offline adapter.

- No full original bridge JSONL: UNDETERMINED.
- Legacy S49 report without original S16 frames: UNDETERMINED.
- Only one post-stop source probe: UNDETERMINED / INCOMPLETE_TRANSACTION.
- Foreign session/action, noncontiguous stream, mismatch with S16,
  differing ACK, unstable two post-stop endpoints: UNDETERMINED.
- Full validated offline source-shaped fixture with two matching probes,
  qualifying region: GOAL_REGION_OBSERVED or ALTERNATIVE_REGION_OBSERVED.

Both qualified region values mean ONLY an observed spatial endpoint under
the specified boxes. They are NOT signed goal/task success, action causality,
reward, S17 LearningFeedback, S10 learning or S11 Habit permission.
A caller-supplied JSONL alone does NOT physically attest real World identity.

This is a read-only API and offline test only: NO automatic demo wiring or
second-poststop probe instrumentation. A future separately authorized,
explicitly source-capturing physical S49 run would be required to physically
qualify a positive C15 endpoint. The historic Self 1.1 physical attempt on
2026-10-11 remains FAILED (Mineflayer dependencies) and is NOT repaired.

## Verification

- tests/test_ac_c_c15_goal_witness.py — unchanged C15 adverse/positive suite.
- tests/test_self_lane_c_witness.py — Self source-frame correlation,
  missing second probe and adversarial source/authority negatives.
- .github/workflows/self-lanec-bridge.yml — Self exact ancestor, exact C15
  blobs, focused/full pytest, lint, contracts and Node adapter.

Never merge the integration Draft into frozen Self #545 or main without
reconciling independent Lane C authority and physical source evidence.


## Self product timeline integration (read-only)

A second optional CLI now projects existing completed native World/L0/L2/Memory
rows and appends two typed Lane C observations directly after the corresponding
S16 Action outcomes:

    PYTHONPATH="$PWD/src:$PWD/tests:$PWD" python -m \
      adapters.mineflayer.self_lane_c_timeline \
      --native-report /path/to/native_report.json \
      --spatial-questions /path/to/retrospective-questions.json \
      --live-l2 /path/to/live_l2.jsonl \
      --memory /path/to/observed_memory.json \
      --format jsonl

The optional --bridge-jsonl argument accepts only an original bounded regular
source file if one really exists. It never obtains fresh World data, alters
a sealed evidence directory or launches a server. An absent --bridge-jsonl is
allowed, producing UNDETERMINED evidence for the selected spatial questions.

A sample shape for a bounded retrospective-questions.json is:

    {
      "schema": "SELF_LANEC_C15_SPATIAL_QUESTIONS_V1",
      "session_id": "<EXACT_NATIVE_S49_SESSION>",
      "questions": [
        {
          "action_id": "<FIRST_EXACT_NATIVE_ACTION_ID>",
          "goal": {"low": [50, 62, 20], "high": [52, 66, 22]},
          "alternative": {"low": [-52, 62, 20], "high": [-50, 66, 22]}
        },
        {
          "action_id": "<SECOND_EXACT_NATIVE_ACTION_ID>",
          "goal": {"low": [50, 62, 20], "high": [52, 66, 22]},
          "alternative": {"low": [-52, 62, 20], "high": [-50, 66, 22]}
        }
      ]
    }

Those positions are EXAMPLE QUESTIONS ONLY, not real goal locations,
Minecraft measurements, or preauthorized task target regions. Any region
selected after observing an Action remains a retrospective question; never
promote that choice into a precommitted goal. Both exact Action IDs must be
present; foreign, duplicate, overlapping and out-of-session specs are denied.

The output preserves every original action_outcome spatial_goal_success=UNKNOWN,
and emits separate lane_c_spatial_observation events with the C15 result,
source references/digest, retrospective-question provenance and explicit
physical_source_attested=false, goal_success_attested=false,
s17_feedback_issued=false, s10_updates=0, s11_habit_promotions=0.

C15's frozen reducer expects a single complete strict original stream starting
at adapter_started seq=0 and only its accepted per-Action event order. A real
multi-epoch S49 bridge stream can contain unrelated observations and two
separately issued actions; this alone does NOT qualify as the C15
single-transaction stream. No filtering, rewriting source seq, recomposing,
or reconstructing missing Action events is performed. Even if future S49
receipts contain two post-stop source observations, the cross-owner
multi-action temporal decoding contract still needs explicit future design
and qualification before a physical C15 positive result can be claimed.

This CLI supports text and JSONL, not HTML; the existing original Self
timeline/HTML remains unchanged.
