# S50 → SelfBody: sampled physical movement and client control source

**Owner:** S50 [#627](https://github.com/rinsakamo/relay-self/issues/627).
**Consumer:** SelfBody [#632](https://github.com/rinsakamo/relay-self/issues/632)
and existing S [Draft #634](https://github.com/rinsakamo/relay-self/pull/634).
**Status:** DEV / read-only source candidate, **not** SelfBody owner adoption.

## Source motivation (actual new Paper 1.21.8 World)

The user-run DEV experiment in [Draft #643](https://github.com/rinsakamo/relay-self/pull/643)
has a preserved exact HEAD `2afb7250952ae490bcddc8244c19264ff1f73bf5`:
S49 Action 1, S15 clear seq32 applied, S16 after seq34, post-S16 5 move
callbacks and 0.12287857661821566m.
Paper WAIT_TICK/INPUT_TICK world fullTime 251–258 (8 each) with last-reported
7 inputs OFF; Paper `PlayerInputEvent=0`.
Paper sampled position changed **251: 0.0590357932m** and
**252: 0.0052108083m**, then 253–258 had sampled zero deltas.
The **existing** Mineflayer bridge had control back ON → all OFF,
position-write returns 22 / position_look 1, `player_input=0`;
sidecar footer complete/no loss. Native Node record index and Paper fullTime
are not synchronized; write-return is not wire receipt.
This run used an active M0.2 exhaustion-modifying Paper plugin.

**Consequence:** Treat client-local control intention, Paper's
*last-reported input* state and actual sampled World movement as **three
distinct, fallible observation classes**. A false input flag plus
nonzero movement is not contradictory. A false input flag plus zero
motion in a small callback window still does not attest an entire
World tick of input-idle, effective S15 clear, physically stopped, Goal,
P1 WAIT or L10 learning.

## Implemented source contract

S-owned module
`adapters/mineflayer/m02_paper_dev/s50_selfbody_motion_source.py`
validates **original** Paper and Node JSONL bytes with the existing S50
read-only `review_s50_input_samples` and
`inspect_s50_client_packets`, then checks the external original
L23 readback claim against raw Paper SHA256 and marker/session/World/tick
identities. It never grants original L23 provenance by itself.

It produces frozen `S50SelfBodyMotionSource` fields:

- `paper_samples`: 8 ordered World fullTime callback samples,
  Euclidean distance between `from_x/y/z` and `x/y/z`, and
  whether **last reported** Paper input was active in that same
  callback. The S50 input updates and positions must have matching
  World fullTime. Motion is *sampled displacement*, not actual
  continuous physical velocity.
- `client_effects`: original same-session Node control-state
  samples in Node record-index order, restricted to existing
  `set_control`, `clear_controls` and
  `shutdown_clear_controls`; an all-OFF clear sample is still
  local client state, **not** effective server clear.
- `client_*_write_returns` and `paper_player_input_callbacks`:
  two separate producer-side diagnostic counts, never packet-level
  identity or synchronized time. `observed_motion_while_reported_input_off_ticks`
  labels *same-Paper-source* activity only.
- `source_scope`, `session_id`, `marker_id`, `paper_world_uuid`,
  `subject_uuid`, SHA256, schema and provenance ceiling.
- Invariants always fixed:
  `cross_clock_alignment=NOT_ATTESTED`;
  `effective_s15_clear_world_tick=NOT_ATTESTED`;
  `full_tick_input_coverage=false`;
  `physically_stopped_attested=false`;
  `goal_admitted=false`;
  `p1_wait_ticks_admitted=0`,
  `l10_pairs_admitted=0`,
  `s10_updates_admitted=0`,
  `s11_grants_admitted=0`.

Crucially, the module **never creates**
`relay_self.self_body.BodyObservation` or
`BodyInteroception`: those types have different S/L owner qualification
and require independent original Present / sensor pairing.
This S50 diagnostic is *supplementary* and is not passed to cognition
in the shipping/DEV host without S/SelfBody owner adoption.

The `tools/s50_selfbody_motion_readback.py` CLI requires a sealed
S49/L23 one-Action DEV PASS with original report, Paper console,
client sidecar and exact Paper subject UUID.

## Replay against the preserved real World (no new World)

Use a fresh read-only checkout of exact evidence HEAD
`2afb7250952ae490bcddc8244c19264ff1f73bf5`
and a separate checkout of this S50 source branch. Do **not** edit
historic evidence or either original owner. Run the S50 tool with
Python3.12, `PYTHONPATH=src:tests:.` and the S50 checkout in import
path. All input paths should be absolute files from the evidence
checkout:

```bash
python tools/s50_selfbody_motion_readback.py \
  --s49-report /path/to/evidence/run2/s49-report.json \
  --paper-original /path/to/evidence/run2/server.log \
  --client-original /path/to/evidence/run2/client-packet-original.jsonl \
  --subject-uuid dcae346d-e66f-331a-b459-a5a5370e9738 \
  --output /path/to/new-evidence/s50-body-candidate.json
```

Replace path placeholders only after confirming exact filenames in the
saved original artifact. The output belongs in a **new** review
directory, not the protected originals. If source files are unavailable
or missing, fail closed and do not manufacture a real-World PASS.
One known 2026-10-31 DEV report is the source of the example values;
the synthetic negative tests do not substitute for that replay.

## Acceptance and next boundary

Accept this S50 module only as a **read-only diagnostic source**
after source hash/tick/marker and input/pose continuity checks.
In SelfBody #632, do not silently add it to the native Present fields,
action outcome or fatigue/energy owner. If useful, S owner can later
pass an immutable, one-epoch source-bound diagnostic *beside* the
existing `SelfBodyView` with explicit provenance limits; SelfBody
owner decides the consumer API and its lifespan.

Keep S49 sole issuer, S16 original outcome authority, M/P1 energy/fatigue
ownership, Goal and L8 learning gates, preserved S7/S16/Paper originals,
and no main merge.

`DEV_ONLY / READ_ONLY_SOURCE_CANDIDATE /
REAL_WORLD_REPLAY_NOT_CLAIMED /
EFFECTIVE_CLEAR_NOT_ATTESTED / STABILITY_UNPROVEN /
GOAL_UNDETERMINED / P1_WAIT_0 / L10_0 /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
