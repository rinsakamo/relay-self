# P0-D #860 — 60-second World + Multi-Self checkpoint DEV

Status: offline generation + 60-second pollable trigger policy. Stacked on PR #859. Not a live Paper scheduler, full owner serializer, independently attested quiescence, real two-Self recovery, QUAL, or SCIENCE.

## Accepted policy

- Nominal cadence is **60 seconds** of monotonic host uptime between successful checkpoints. No replay.
- One generation contains a stopped Minecraft World and *every* roster Self. Minor save-time skew is tolerated; do not claim identical tick or distributed World/WAL atomicity.
- Recovery selects the newest completely verified generation and discards **all** later World changes, cognition, learning, Actions, WAL reservations, conversations, pending messages and runtime context. UUIDs spawned after the checkpoint are not reconciled.
- A generation is committed only after the World archive and all Self artifacts are captured and checked. The commit marker is written last, and interrupted generations remain ineligible. Older generations remain untouched.
- Real full cognitive rollback requires Goal/Intent/Skill, Structured and Log Memory, Recent3Self, communication state and Self/Body owner revisions. This first slice captures existing PersistentCognition and physical WAL bytes, plus an optional **opaque** owner-state file. It does NOT prove owner restoration or that all necessary artifacts exist.
- Server stop and Self quiescence are external preconditions. The operator-supplied references are not authenticated; this module does not stop, pause, synchronize or issue Actions. Permitted small skew does NOT mean file copies may race active writers.
- All restores use NEW directories and a NEW World branch. Old sessions, GPU leases, messages and Action authority are invalid, and old WAL records must not be issued again.

## Reused components

Existing world_checkpoint_dev.capture_stopped_world / verify_world_checkpoint / restore_world_to_new_branch are reused. Existing persistent_cognition.load_persistent_cognition checks durable Self identity; PhysicalActionJournal.restore validates source WAL format before it is copied. The offline AutosaveGate polls for 60 seconds elapsed and checks the newly committed generation before advancing its clock. This gate does not create a background timer.

Example roster JSON file (outside the repo):

~~~json
{
  "self_ids": ["A", "B"],
  "sources": [
    {"self_id": "A", "cognition_file": "/ABS/A/cognition.json", "physical_wal_file": "/ABS/A/wal.json"},
    {"self_id": "B", "cognition_file": "/ABS/B/cognition.json", "physical_wal_file": "/ABS/B/wal.json"}
  ]
}
~~~

**Only after Paper is cleanly stopped and all Self writers are quiesced**, create a store directory and invoke the CLI:

~~~bash
python -m experiments.coordinated_checkpoint_dev capture \
  --source-world /ABS/stopped-world \
  --store /ABS/checkpoint-store \
  --sequence 1 --self-sources-json /ABS/self-roster.json \
  --world-id WORLD_ID --branch-id SOURCE_BRANCH \
  --logical-tick 100 --tick-source-ref operator:tick-readback \
  --stopped-server-ref operator:clean-stop \
  --quiesced-selves-ref operator:all-self-owners-fenced

python -m experiments.coordinated_checkpoint_dev latest \
  --store /ABS/checkpoint-store

python -m experiments.coordinated_checkpoint_dev verify \
  --generation /ABS/checkpoint-store/g-000000000001

python -m experiments.coordinated_checkpoint_dev restore \
  --generation /ABS/checkpoint-store/g-000000000001 \
  --new-destination /ABS/new-rollback \
  --restore-id rollback-1
~~~

Restore yields a fresh World directory and a fresh-world branch receipt, plus inert per-Self state files. RESTORE_PREPARED.json says physical_action_issue_authorized=false and full_self_owner_restored=false. It never resumes the old Self owner or reissues an Action.

## Offline fault / qualification matrix

| Case | Expected |
|---|---|
| Complete World + A and B cognition and journals | Generation committed and verified |
| Missing / duplicate / foreign Self | No commit |
| Interrupted generation | Prior verified generation survives |
| Tampered World/Self file/commit marker | REJECT, no restore |
| Failure after 60 seconds | Timer not advanced |
| Newer runtime history | Not part of restored generation |
| Save-time skew | Accepted as DEV uncertainty, never atomicity attestation |
| Real Paper and Self live autosave | NOT WIRED / NOT RUN |
| Full Self owner recovery | NOT IMPLEMENTED |
| QUAL / SCIENCE | NO GO / NOT RUN |

## Next real integration

1. Connect a single external coordinator to pause new physical admission and cognition writers, settle/fence in-flight Actions, flush all Self-owned persistent states, and cleanly save/stop Paper. Do not create a second issuer.
2. Persist Goal/Intent/Skill, Learning, Log and Structured Memory, Recent3Self, conversation and message delivery state, plus correct per-Self owner revision. At recovery, old grants, task generations, GPU leases and native sessions must be invalidated.
3. Wire AutosaveGate to the live runtime monotonic heartbeat, and collect measured saving duration and failures. Only then is it a *real* 60-second autosave.
4. In one Minecraft World with actual two-Self cognition streams: commit a generation, cause World/Memory/communication changes, crash between checkpoints, recover the committed generation, verify no post-generation experience remains and no old Action is reissued.
5. Report exact HEAD, evidence hashes and trial classification to #860 / #851. No replay qualification, no PR merge, and no QUAL/SCIENCE promotion.

Small clock skew is intentionally tolerated, but cross-component generation membership and no stale physical authorization remain required.
