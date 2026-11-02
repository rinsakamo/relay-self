# S #537 — S2-B original L0/Intent source epoch witness (DEV, no model)

Parent: S2-B offline S60 gate [Draft #695](https://github.com/rinsakamo/relay-self/pull/695), exact commit `5c227bad9072198d06ddefaa9ff9a7c19d2b829c`.
Grandparent S2-A real-World DEV PASS #691, exact `8cb90b0910084ee5fe889b5a5e3c1e29a61ac988`.

## Original owner witness, not a made-up revision

Original `S49 qualify` creates **one** genuine `NormalWorldL0`
and **one** genuine `IntentCommitment` before its first native event. The
existing `live_probe(reading)` had no access to either owner, so the earlier
S2-B branch correctly DEFERRED with no model call.

A new **optional, default-OFF, try/except isolated** `owner_epoch_readonly`
callback executes inside the original `reprobe` **after** a native
`_correlated_observe` returns and stage-R observation, but **before** the
existing `live_probe` and next L0 decision. It receives only references to
the exact original native `reading`, `host: NormalWorldL0`, and
`intent: IntentCommitment` objects. It cannot issue, cancel, clear,
STOP, mutate owner or grant learning. Any callback exception cannot veto
the original S49 Action.

The owner source has two different revision semantics:

- **Retained revision**: `host.retained.revision`, the existing explicit
  governed LearningPreferenceState revision. It is NOT inferred from
  the observed World and cannot be hard-coded to 1.
- **Intent causal generation**: `len(intent.events)`, directly measured
  from the original IntentCommitment's immutable event tuple, plus exact
  event-prefix / committed-current-ID checks. **IntentCommitment has
  no `revision` field.** The event-count generation is an explicitly
  declared mapping to S60 `CognitionContext.intent_revision`;
  do not present it as a separately attested native Intent revision.

`S2BOriginalOwnerEpochBinder` checks the exact native probe Python
object, persistent original L0 & Intent owner identities, same session
and request, current Intent ID, retained snapshot identity and revision,
monotonic native seq, retained revision and event generation, immutable
Intent event-history prefix and max-eight epochs. If owner changes after
the witness and before binding the S2-A input, reject the input rather than
back-fill a newer revision.

The no-model runner `tools/s537_s2b_original_owner_witness_dev.py`
reuses the existing S2-A original S49 single-run path, genuine S16 tap,
WB L1 projection, and M same-process original admission, adding the
owner tap only. This runner is **not S2-B real Gemma integration**.
Its S2-B report is a separate immutable DEV observation, not proof of
independent Paper/W3 source attestation.

## DEV-only usage, ONLY with a valid local grant

Exact pinned M and WB owner clean worktrees are required:
- M #676 `9afce6bde1079f8a42aaf3c4e515ef35fc6b0396`
- WB #669 `944db858186a4d9449946b6acdcb8c8e5998e071`

```bash
export PYTHONPATH=src:.:tests
export S49_REAL_SERVER_CI=1
export S49_COMPLETED_L0_DEV_ONLY=1
export S537_S2B_OWNER_WITNESS_DEV_ONLY=1
python -m tools.s537_s2b_original_owner_witness_dev \
  --m-owner-dir "$M_OWNER_DIR" --wb-owner-dir "$WB_OWNER_DIR" \
  --report "$EVIDENCE_DIR/s49.json" \
  --server-log "$EVIDENCE_DIR/server.log" \
  --s2b-report "$EVIDENCE_DIR/s2b.json" --live-world-dev
```

Preflight: independent S worktree, clean pinned sources, valid DEV
authorization/World budget, Python3.12/Java21/Node22, fresh evidence
paths, no NODE_OPTIONS shim, process/port ownership. First new World
once, no automatic retry. Preserve original report, observer errors,
host chronology, source refs, receipts and closure Action IDs, final
owner-view consistency and process/World/port cleanup; do not reuse
prior one-shot authorizations.

Use the independent post-run JSON report-row auditor **only if** the real-World\nS2-B report is RECORDED and the original S49 JSON file exists:\n\n\`\`\`bash\npython -m tools.s537_s2b_original_owner_audit \\\n  --s49 \"$EVIDENCE_DIR/s49.json\" \\\n  --s2b \"$EVIDENCE_DIR/s2b.json\" \\\n  --output \"$EVIDENCE_DIR/s2b-source-audit.json\"\n\`\`\`\n\nThe S2-B report embeds the S2-A host callback chronology and original\nWB/M source rows; the independent auditor matches both reports\nagainst S49 Action/S16 native after-seq and the three owner contexts,\nrejecting future S16, mismatched Action/owner, foreign session,\nmissing/duplicate callback, changed WB rows, or any model submission.\n**It is still not independent Paper/W3 process source attestation.**\n\n**Model calls = 0, S60 submissions = 0**, irrespective of owner witness
outcome. Separately obtaining a live S2B **real Gemma** grant/budget is
necessary. A passing synthetic fixture or a real owner witness alone
cannot attest backend identity, L2 quality, independent Paper/W3 tick
chronology, or learning/Action gain.

Classification until an actual new World:
`DEV_ONLY / S2B_OWNER_EPOCH_OFFLINE_ONLY /
S2B_NEW_WORLD_NOT_RUN / REAL_GEMMA_NOT_RUN / SOURCE_UNATTESTED /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
