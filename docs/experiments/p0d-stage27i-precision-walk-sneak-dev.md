# Stage27i — Precision WALK/SNEAK (OFFLINE DEV, isolated World NOT RUN)

Stacks on Stage27h #979, original two-Self Stage27 owner. One original
bounded Gemma/L1 choice binds Skill + Target + operator-authorized Preset;
CPU L0 reuses the same original Intent, Skill, Invocation, TargetContract,
PhysicalIssueAdmission, and fsynced canonical WAL for each finite child
Action. No L1 decision is requested between MOVE pulses.

## New explicit operator DEV preset

- Initial place target: 1.5m east of original first new-native probe.
- Target acceptance radius: 0.15m horizontal, 1m vertical; immutable and
  bound before L1 choice. This is a target requirement, not a globally
  hardcoded motor tolerance. The target remains an authored exploration DEV
  target, **not** terrain-qualified pathfinding.
- Original complete SkillBudget: at most 4 Actions, 15s, 2.0m cumulative,
  256 entire-Invocation native observations, as Stage27h.
- New accepted Preset ID: `OperatorPrecisionWalkSneakAt075`. The name is
  a concrete operator DEV profile, **not an autonomous Self-adopted preset**.
- Finite L0 choice: if horizontal center distance >0.75m use `WALK`;
  otherwise `SNEAK`. Pulses remain fixed at 0.15s each. No dynamic pulse
  tuning, implicit speed model, extra L1 call, or parameter adjustment.
  L2 needs to create/approve a *different preset* to change profile
  parameters in the future.

## Native physical eligibility

For WALK, original PLACE LOOK -> forward ON -> STOP, unchanged.
For SNEAK, the original ActionPort/PhysicalIssueAdmission permits one
additional **exactly identified, once-only** native
`set_control(control="sneak", state=True)` child after LOOK and before
forward ON. Its ID is `{original_action_id}-sneak`; it must appear in
the **fsynced original PREPARED WAL as `gait_mode=SNEAK` before any native
effect**. The same original Action's `-start` enables forward and
`-stop` calls `clear_controls`, clearing *both* forward and sneak.
The original terminal WAL retains look/start/stop effect chronology and
an additional gait ACK seq; old MOVE_PLACE schema-v2 records without
gait fields still restore identically.

At most 60 STOP/settling native probes must be reserved before each
physical Action (entire Invocation 256); every probe is counted, unused
reservation refunded only after canonical terminal WAL. New receipt
and original native stdout must attest an exact-once `-sneak` ACK
between LOOK and forward for a SNEAK row. Failure/unconfirmed STOP
retains unresolved WAL and prevents repeated physical actions.

## Mandatory original Self B retained Memory audit

The initial Stage27i exact-HEAD preflight at
`4d13c70bd660cbf84e760d0fcdffbf327f539006` correctly stopped
with `PRE_WORLD_HOLD`: `_peer_snapshot` tracked only Intent/Skill counts
and physical WAL, not `owner.retained.memories`. That was a missing
audit, **not** evidence that B Memory actually changed. No World was
started, no Gemma or Mineflayer process ran, and the old Stage27h World
was not replayed.

The updated source-qualified B snapshot is computed from the **live**
`owner.retained.memories` tuple. It records the ordered list of Memory
IDs and individual SHA256 digests covering **content and both provenance
fields**, and a SHA256 digest of the whole ordered tuple, along with
Intent event-history digest, Skill history digest, original WAL digest
and unresolved status. Memory text is not exposed in the motor summary;
the digest is an evidence fingerprint, not a complete independent
recovery of Memory content. Identity mismatch and foreign/invalid
retained cognition are rejected.

For Stage27i, write-once and fsync two independent JSON files:

- `evidence/stage27i-peer-b-before.json`: *before any A physical Action*
- `evidence/stage27i-peer-b-after.json`: *after final A L0 decision*,
  and **before** peer comparison, logout and final report aggregation

Read back both files and SHA256 digests in the original parent runner
as part of the typed Stage27i result contract. Missing Memory fields,
different content with an unchanged record count, stale/mismatched
evidence, mutated B Intent/Skill/WAL, or missing source -> explicit
HOLD. If a mutation is detected after irreversible A movement,
preserve the separate before/after snapshots in the HOLD audit; never
retry the original Action. The parent frozen hook return file remains
write-once and separate from these snapshots. Stage27h and all
earlier real runner flags still use the previous semantics.

Real Source/Gemma/Paper validation and precision arrival remain
**NOT RUN / NOT ATTESTED** pending another, separate one-shot trial.

## Mandatory source-derived L1 HTTP count audit

The original Stage27i hook result had
`stage27h_additional_model_requests: 0` as a literal, which cannot
prove there were no real model HTTP calls. New code reads the original
owned Stage26 provider `evidence/original-model-http` directory:

- The exactly two accepted **A and B** original request IDs must have
  their `.request.json`, `.response.json`, and
  `.source.sha256.json` raw sources, rechecked through the existing
  provider receipt.
- Take `stage27i-model-http-before.json` after initial A/B L1 results
  and **before the first A physical Action**.
- Recount and freeze `stage27i-model-http-after.json` after the L0
  loop, before parent aggregation; also do this on nonselected A.
- Both source-derived snapshots must be identical and contain exactly
  **2 requests, 2 responses, 2 manifests**. Any third `.request.json`
  counts as an attempted HTTP call, even without a corresponding
  response. Do not replace real counts with a hard-coded zero.
- Parent independently verifies the source files and SHA manifests,
  before/after frozen snapshots, receipt IDs, and final counted
  `stage27h_additional_model_requests == 0`. Preserve original raw
  files and independently frozen census in HOLD.
- This attests the **owned audited provider** only. The real llama.cpp
  server PID/load log should be compared as an independent witness
  in LocalCodex. Do not infer external global HTTP traffic absence.

## Real runner / experiment boundary

Do not run a real World until the exact-HEAD GitHub Actions suite, focused
L0+native+WAL+parent contract regression, and local asset/GPU preflight
all succeed. Separate future one-shot World is needed; **do not replay
the previous Stage27h World UUID bf008be2-7386-4929-a976-71bfbfb5c7fa**.
The earlier Stage27h trial consumed one shot and is a HOLD, not repaired by
offline Stage27i tests. Standing Minecraft EULA consent and isolated World
DEV authorization are on file; don't request the same approval repeatedly.

The new mutually exclusive CLI switch is:
`--stage27i-precision-gait`.

Use `experiments/p0d_stage27_real_place_move_dev.py` with verified Paper
1.21.8/plugin/model args and existing `--eula-accepted` plus
`--real-world-dev-grant` for any *separately planned* one-shot run.
Never combine with --stage27h-l0-move-loop, --stage27g-real-l1-evaluation,
--stage27f-cpu-evaluation, or --stage27e-independent-evidence.

Capture for every child: original PREPARED before LOOK, selected gait from
immutable original Preset, exact look/sneak?/forward/STOP ACKs, 8+8
settling and full source probe IDs, terminal WAL, actual xyz/displacement,
Paper independent correlated position (NOT Action-ID causal proof),
complete CPU result, A/B unchanged owner comparison, 0 extra Gemma calls,
write-once parent hook report, post-action checkpoint limitations, PID
cleanup, and manifest SHA256.

Target CONDITION_OBSERVED != Skill/Goal success. Real QUAL/SCIENCE
classifications remain NOT ATTESTED. The target may already be reached
after one or two MOVE Actions; never force extra Actions solely to
demonstrate SNEAK. A valid non-arrival/budget exit is a DEV observation,
not an excuse to auto-retry.
