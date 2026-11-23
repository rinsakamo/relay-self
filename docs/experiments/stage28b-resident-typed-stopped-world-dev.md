# Stage28b — original resident A/B retired → stopped Paper typed World/Self cut (DEV)

Parent [#966](https://github.com/rinsakamo/relay-self/issues/966); stacked on Stage28a Draft PR #967.
This is an intermediate **real-World-capable** step before any 60-second
in-World online autosave and before Stage28c fresh cognitive continuation.

## Why this stage is separate

Stage24g used `ResidentCognitiveWorkOwner` as the **only** canonical Self
owner. Its original `CheckpointedCognitiveOwner` instances are already
attached to this resident gate; attaching `CognitionOwnerCohort` a second
time would create an invalid double cognition authority. Existing
`CoordinatedCheckpointHost` presently requires `CognitionOwnerCohort`,
so it cannot simply be dropped into the original resident runner without
a source-qualified adapter to the same owner. This stage **does not**
claim to run `CoordinatedCheckpointHost` or 60-second periodic autosave.

Instead, the actual Stage24g owned Paper, original A/B native children,
`PhysicalIssueAdmission`, and `ResidentCognitiveWorkOwner` remain
unchanged. New `capture_retired_resident_typed_world` runs **only after**
both original `bridge.logout()` calls have:
- fenced their physical ActionPort admission, reconciled original canonical
  WALs and drained `ActionSupervisor`;
- terminated their exact owned Mineflayer native child processes;
- fenced CPU writers, real GPU inference lane (if one was used), and the
  original unsent peer work scope;
- persisted and independently read back the original retained cognition.

A fresh bridge `world_only_quiescence()` receipt is used **only as
retirement evidence**, **not as a World-only checkpoint**. Each
existing owner writes a fresh generation-bound typed `SelfOwnerCut`
(including Intent/Skill history, accepted Schema, peer receipt and
pending-question refs). The already-persisted canonical Self retained
cognition and PhysicalActionJournal files are reused without swapping
owners or clearing WAL history.

The source is rechecked synchronously before `paper.stop_and_save()`.
The *same* real stopped-Paper tick, World UUID, branch, Paper session,
Paper save/stop process receipt and complete dimension files are then
captured via the existing `capture_typed_generation(..., paper_layout=True)`
with the exact A/B owner sources. The original `verify_generation` and
`verify_typed_generation` independently verify the entire committed
generation. If one Self tick is later than the stopped World tick, HOLD
and no typed commit. A partial failed capture is **never** treated as a
checkpoint.

This mode deliberately stops Paper and **does not restart or issue
another native Action**. A fresh branch restoration is separate Stage28c,
using the existing `restore_generation` and Stage28a inert recovery
gate. No automatic L1 output reuse, Goal completion or Skill reissue is
authorized. Stop/save ordering tolerates a bounded stopped-World clock
skew but is NOT proof of distributed atomicity.

## Pinned operator entrypoint

The exact source branch's `experiments.stage28b_pinned_typed_cut_launch_dev`
reuses the independently fixed Stage24g Paper 1.21.8 build-60 and *new*
resident witness Jar. The historical Stage24f Jar must not be loaded.
No new source hash can be supplied by the operator to bypass pins.

First use `--inspect-only` (without physical DEV flags), then with
new isolated scratch and exact Java21/Node22 binaries:

```bash
PYTHONPATH=src:. python3 -m experiments.stage28b_pinned_typed_cut_launch_dev \
  --paper-jar "$PAPER_JAR" \
  --plugin-jar "$STAGE24G_RESIDENT_WITNESS_PLUGIN_JAR" \
  --scratch-parent "$NEW_EMPTY_STAGE28B_SCRATCH_PARENT" \
  --eula-accepted --execute-once --real-world-dev-grant \
  --java "$JAVA21_BIN" --node "$NODE22_BIN" --timeout-s 120
```

The user previously gave ongoing Minecraft EULA and isolated real DEV World
approval; it still must be explicitly represented by launcher flags.
No local World/GPU process is available from GitHub CI or this ChatGPT tool.
LocalCodex should find and validate the real original artifacts, not
substitute paths. This mode does not load or POST to Gemma and does not
operator-force MOVE.

## Required classification

If local original Paper/native observation, retired owner A/B, typed
COMMITTED generation and all archived bytes validate:
`REAL_PAPER_TWO_SELF_TYPED_STOPPED_WORLD_CUT_DEV`.

It proves that **two original Self persistent cognition snapshots and
stopped physical World files were captured in one typed generation**, not
that the cognitive process has resumed, that an Action had been autonomously
selected on the second World, or that an on-line 60-second autosave exists.

Until a separately classified local actual World trial:
`STAGE28B_OFFLINE_TYPED_CAPTURE_PATH_PASS / REAL_PAPER_TYPED_WORLD_SELF_NOT_RUN /
60S_AUTOSAVE_NOT_ATTESTED / FRESH_L1_NOT_RUN / QUAL_NO_GO / SCIENCE_NOT_RUN`.

## Next

To complete the *online* portion of Stage28b, add a **single-owner
resident-compatible checkpoint adapter**, preferably a two-phase full-roster
resident gate, to `CoordinatedCheckpointHost` rather than attaching a second
`CognitionOwnerCohort`. Require actual neutral STOP, same physical
admission owner, complete A/B native and CPU/GPU/peer fencing,
synchronous snapshot quiescence, 60-second timer and original
source-qualified native A/B rebind. No paper-only / single-self shortcut.

Stage24g 305-file source manifest digest
`b79646397ecf67f3b0c840964dfc7ee4fe669f2347cab264c9c303131c6716f1`
and Stage24f HOLD remain immutable. Stage27 PLACE is parallel and untouched.
