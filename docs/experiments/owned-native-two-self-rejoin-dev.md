# P0-D #860 Stage 14 — owned native A/B process rejoin seam

Stacked on #874 via Draft PR #876. Python's `MineflayerProcessSession.launch` is
the default factory for `OwnedNativeRejoinCohort`; no new Mineflayer transport,
ActionPort issuer or memory owner is introduced.

**Prerequisites:** full A/B `MineflayerProcessSession` handles already
launched under one disposable localhost Paper server, explicit version 1.21.8,
distinct offline-mode usernames and shared `PhysicalIssueAdmission`. The
manager validates the complete roster, existing process startup receipts, and
installs the real final-stdin effect admission gate once per process.

During async rejoin, the existing World+Self host has already closed physical
and cognition admission, committed a complete generation, and restarted Paper.
The manager terminates **only its previously owned native child**, launches a
fresh bridge with the exact same configured Self username, waits for real
`spawn/respawn` plus correlated `probe` readback, and returns a new
process-session ID. Timeout/connection failure holds the entire physical gate;
there is no old command replay. It makes the new session available to the
existing STOP cohort provider for subsequent checkpoints.

The returned `NativePreparedRejoin` is deliberately **not** an
`ExternalRejoin`: it sets `gpu_tasks_fenced=False`,
`stale_transport_fenced=False`, and `physical_issue_authorized=False`.
The *existing* CognitionOwnerCohort external callback must independently
verify/terminate obsolete GPU and transport tasks and then rotate the shared
physical admission for each Self; the async host checks that the actual owner
rebind ID matches the prepared native process. Do not fabricate TRUE booleans
from the native process receipt.

## Limitations

The tests use process-shaped fake sessions with source-qualified protocol
objects, not a real Minecraft server. Existing isolated Paper-only smoke
uses max-players 1 and online-mode true and cannot accept two offline-auth
Mineflayer bots; a **new**, explicitly authorized, locally isolated two-Self
Paper harness is required (localhost bind, no public exposure, max-players >=2,
offline-mode for the test only). No real two-bot SAVE/CRASH/RESTORE or
cognitive-owner end-to-end qualification exists yet. Never attach this code
to an existing public server. QUAL/SCIENCE are NO GO.
