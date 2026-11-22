# Stage27e — original PREPARED bytes + independent Paper position DEV

Parent #951. Based on Stage27d Draft PR #961 and real HEAD
`6f2532a2d131321a4f2bf9a6666ed49500345a9c`, which achieved
`REAL_STAGE27_A_PLACE_MOVE_NATIVE_OBSERVED_DEV` (single original World
attempt, native displacement 0.6418188768690332 m). **Do not relabel or
retroactively alter that completed Stage27d evidence.**

## Discovery before changing the Paper plugin

The current `ResidentPresenceWitness` already samples Bukkit player
location on the **Paper main thread every 5 ticks**; it emits
`P0D_RESIDENT event=MOVE` after at least 0.2 m Euclidean motion and
periodic `PRESENT` otherwise. The owned Paper log is separate from
Mineflayer native stdout. Therefore Stage27e does **not** add a new
Paper plugin, new Action issuer, new movement operator, or path heuristics.

Existing Stage27d Paper logs may already contain a readable A MOVE event.
Offline examination of those old raw bytes can establish an independent
Paper position report, but **cannot** recreate PREPARED raw bytes or a
previously unsaved preissue log boundary. Never backfill these as observed.

## New explicit source tap

`--stage27e-independent-evidence` enables an opt-in hook inside the same
Stage27 real-world runner. Default Stage27d and Stage26 execution paths
remain unchanged.

1. Preserve the owned Paper Popen stdout **before** original A issuance,
   under `stage27e-paper-pre-native.log`. Never accept a global latest.log,
   another server PID or another World.
2. The original `PhysicalIssueAdmission.issue_place_move` acquires the
   existing single-parent physical lease, verifies the original
   Invocation/Target/owner/source, and calls the original issuer.
3. The issuer fsyncs the **original** A schema-v2 canonical
   `PREPARED_UNRESOLVED` WAL before any native effect. The new
   `pre_native_evidence` callback copies exactly those existing bytes to
   `stage27e-A-original-PREPARED.json`, fsyncs the evidence file and
   directory, then independently re-reads the original and snapshot
   through `PhysicalActionJournal.restore`. A failed copy never grants
   physical permission or retries; original PREPARED remains unresolved.
4. **Only then** the original LOOK → forward ON → STOP native child
   pipeline is allowed; the same 8+8 tick settling, original Action
   OUTCOME, L0 `YIELD_EVALUATION` and terminal WAL remain authoritative.
5. Retain `stage27e-paper-post-native.log`, require exact append-only
   prefix, unchanged Paper boot/World/A-B UUID identities and read-only
   Paper `MOVE` samples. Compare A's before/after Paper coordinates
   against the separate native before/settled coordinates within a
   DEV-only 0.3 m observation-window tolerance; retain raw SHA256,
   positions, movement count, and both source gaps.
6. Record `PAPER_A_POSITION_CORRELATED_DEV` **only** for an original A
   MOVE sample plus compatible positions. Otherwise return
   `PAPER_A_POSITION_UNATTESTED_DEV`: not zero displacement, not
   necessarily a failed native Action. Nonappend logs, mixed boot/World,
   swapped actor, A logout/rejoin during the Action are refused.
7. Preserve both original Self WALs, B Intent/Skill isolation, original
   source readback, evidence manifest, and a clean owner-controlled stop.

## Boundaries and explicit nonclaims

- Paper main-thread player movement is **independent position evidence**,
  not a Paper Action-ID causal join. The Paper witness does **not** know
  the original parent Action or its three native child IDs.
- Paper Bukkit tick and native Minecraft day clock are not compared
  numerically; only each source's internally ordered events are used.
- No independent native stdin wire capture, persistent ActionLifecycle
  transcript, or atomic World+2 Self checkpoint is added here.
- An individual MOVE pulse may overshoot a distance budget; detect and
  report violation, do not claim preemptive distance safety.
- Neither `PAPER_A_POSITION_CORRELATED_DEV` nor PREPARED capture makes
  Goal/Skill success, self-generated navigation, QUAL or SCIENCE true.
- If the Paper source lacks a new A MOVE event, retain native classification
  with an explicit independent-position **UNATTESTED** field.
- If STOP, WAL or source is ambiguous, HOLD and no physical retry.

## Test and real-World status

Contract tests are offline synthetic fixtures with a scripted native effect
stream, and should test the PREPARED-before-first-LOOK boundary, raw snapshot
vs terminal WAL difference, Paper actor/World/boot integrity, absence of
movement and opt-in default fences.

**Real Stage27e World trial is NOT RUN by this GitHub change.** One new
isolated World/real Gemma run is permitted by the user's standing EULA and
real-World DEV approvals when the exact HEAD's CI and host assets are checked.
Do not substitute synthetic tests for actual real Paper/Gemma observation.

Use the Stage27d documented CLI arguments, adding:

```sh
--stage27e-independent-evidence
```

Retain original evidence, manifest SHA, independently reread all outputs and
post exact classification and **limitations** to PR #961 / parent #951.
