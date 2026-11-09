# RelaySelf D14 R7 — native evidence / unresolved MOVE LocalCodex handoff

Scope: **DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN**. R7 is
instrumentation and forensic readback, not a claim of Paper-effective STOP,
EAT authorization, or autonomous long-run survival.

## Lineage and historical result

- Parent Draft PR #811, original pinned head:
  `d84f56e82284a3850ce552443e3fb31451dcc9b3`.
- Exact original R6 World: `44a10cf4-73ff-40d8-809d-c69023c1677a`,
  tick 12–2002, terminal `SELF_DISCONNECTED`.
- Two original S49 MOVE S16 OUTCOME rows: 0.6269m and 0.3428m.
- Third original S49 MOVE: `PREPARED_UNRESOLVED`,
  `ORIGINAL_S49_MOVE_S16_NOT_OUTCOME`. Dispatch, result and physical STOP
  are **UNKNOWN**. No replay or promotion of that original fence is allowed.
- Original historical World evidence has neither W3 raw stdout nor S50
  client controls. They cannot be reconstructed retroactively.

R7 reuses the original `MineflayerProcessSession.launch` W3 capture and
same-bot S50 passive readback. W3 is **raw Node-to-Python stdout JSONL**,
not Minecraft TCP packets. S50 is client-local controls and physics ticks,
not Paper-effective motor state.

## Offline preflight

1. Read the repo, this document, parent PR #811, D7/S50 source, R6, and the
   latest exact R7 CI. Verify the selected **full 40-digit HEAD** is the same
   SHA tested by a successful offline workflow. Do not accept this document
   as an authoritative exact future SHA.
2. Check out that exact HEAD in a **new clean detached worktree**. Preserve
   existing worktrees, the R6 World original and all prior evidence.
3. Run the repository contracts, Python R7 + R6 tests, Ruff, and the Java 21
   respawn plugin build/tests; use the R7 offline GitHub Actions workflow as
   the checked-in command list.
4. Verify the existing exact Paper 1.21.8 SHA256/size and plugin SHA256. The
   runtime must already have Node 22/Mineflayer 4.39 and ports available.
5. Grant one fresh World **explicitly**. In addition to the R3/R4/R5/R6
   original grants, R7 adds:

```bash
export D14_R7_NATIVE_EVIDENCE_ONEWORLD_ONLY=1
export D7_PASSIVE_CONTROLS_WORLD_ONLY=1
```

Do not omit any of the R3/R4/R5/R6 grant requirements in the existing R6
handoff. Do not set `NODE_OPTIONS`. Both new grants are necessary and
R7 cannot be used without the R6 local MOVE grant.

## Read-only inspection of the existing #811 evidence (no World)

Running this CLI does **not** edit or recover the original fence.
Choose an output path that does not exist, **outside** the source evidence
directory and its signed manifest:

```bash
python -B -m tools.bug0_d14_r7_evidence_post \
  --evidence-dir /home/rinsa/work/relay-self-evidence/d14-r7-async-fix-natural-original-01 \
  --out /home/rinsa/work/relay-self-evidence/d14-r7-async-fix-audit-01/r7-source-only.json
```

Expected: the third Action remains `PREPARED_UNRESOLVED`, W3/S50
`NOT_CAPTURED`, S16 result `UNKNOWN`. If the evidence is elsewhere,
use the exact LocalCodex path instead. No silent correction of the old
World report, checksum or sensor provenance.

## Optional separate one-World test after offline CI

Only launch through LocalCodex/WSL2 on a clean pinned commit, **never**
through GitHub Actions. Choose a fresh evidence directory outside the repo.
Fill `$EXPECTED_HEAD` from the successful R7 offline CI; use the
validated existing Paper/plugin env and command (see R6 handoff):

```bash
python -B -m tools.bug0_d14_local_oneworld \
  --repo "$PWD" --expect-head "$EXPECTED_HEAD" \
  --evidence-dir "$EVIDENCE" \
  --paper-jar "$D14_R3_PAPER_JAR" \
  --plugin-jar "$D14_R3_RESPAWN_JAR" \
  --max-wall-seconds 3600
```

No automatic World retry, clone, respawn, re-ISSUE, alternate issuer,
NoAI, Health/Hunger staging or artificial drop is authorized. The managed
natural zombie respawn remains 600 Paper ticks after a real death.
The original S49 pre-ISSUE fence is untouched on uncertain outcomes.

## New evidence and interpretation

- `w3-node-stdout.raw.jsonl`, `w3-node-stdout-receipt.json`: bytes
  captured synchronously before Python decoding and sealed even on most
  unexpected endings. `INCOMPLETE_UNQUALIFIED` is **not** a pass.
- `r7-s50-client-readback.jsonl`: same Mineflayer client controls and
  `PHYSICS_TICK` readbacks, no independent Paper alignment.
- `LIFE_ACTION_UNRESOLVED` in `d14_natural_events.jsonl`, original
  S49 terminal/partial `WorldConsequence` in `report.json`: generated
  **only on a new failed MOVE**, no guessed native ACK.
- `r7_source_forensics.json` or `r7_source_forensics_error.json`: pure
  read-only source review, produced even after a failed run when sources exist.
- `SHA256SUMS.txt`: one immutable manifest covering all new files, under
  the existing LocalCodex rules.

`r7_source_forensics` may record Node stdout ACKs and eight quiet S50 client
ticks after a clear, but these are **not proof of the Paper-effective STOP
tick**. Continue to report physical STOP as `UNATTESTED` and keep MOVE→EAT
fenced. Also preserve the distinction between `SELF_DISCONNECTED` and
`SELF_DIED`.

## Next R7/R8 task — Paper-effective STOP

After reviewing the new true captured sources, connect an actual Paper
main-thread per-tick body observer to the existing D7/S50 evidence model.
Require same World UUID/player, source-linked S15 clear, contiguous Paper
post-clear ticks with true player position/velocity and controls, and
same-client S50 controls. Until this is implemented and exercised in a
separate permitted World, do not call physical STOP a success and do not
enable post-MOVE EAT.

Report exact preflight HEAD, CI URL, one-World count (or NOT_RUN), Action
IDs, native ACK presence, original S16 states, unresolved fence, terminal
reason, SHA manifest, and cleanup to PR #811, new R7 Draft PR, and
Issues #742/#717/#431.
