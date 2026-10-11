# E12 — original-wire native transport and actual S15/S16 Action3 closure

Authority: Issue #568. Exact frozen E11 parent
`95f041647ad5bebf5baa949e1ce676184f6b4f19`.

This is a one-purpose **operator library**, not a Java server launcher or
self-authorizing Minecraft scientific experiment.

`experiments.epistemic_e12_native_owner` adds:

- `OriginalWireSession.launch_original`: single actual loopback-only
  Node/Mineflayer original `bridge.mjs` process (when explicitly called by
  the future approved host operator), with original stdout written to an
  exclusive new JSONL file **before** typed source decoding; streaming
  frame/byte ceilings, original-start identity, one decoder/session/seq.
  Startup failure terminates the owned client without deleting raw evidence.
- `OriginalWireSession.close_original`: exactly one original shutdown command;
  capture the original `shutdown_ack`, optional immediate `connection_end`,
  EOF and exit0. Refuse missing/duplicate ACK, foreign session, extra data,
  nonzero exit or indefinite close. The `SourceShutdown` return is the exact
  existing E11 callback contract. Native raw evidence is never filtered.
- `OneAvatarOriginalOwner`: old client must be fully closed before the one
  optional new Action4 client can start; same declared Minecraft
  host/port/username/version from a single caller-owned config, distinct
  raw files and source IDs. Both launches are **consumed once**, including
  startup failure. E11 still independently checks original new seq1 spawn,
  position and typed continuity before use.
- `run_issued_parent_action3`: receives the original **already S14-approved
  and ActionSupervisor ISSUED** Action3 and its actual bound action. It
  invokes existing production S15 native `build_mineflayer_command` /
  `execute_mineflayer_command`, the S16 World interpreter, and the original
  ActionSupervisor terminal transition. Only real `EXECUTED` + terminal
  `OUTCOME` gives a positive Action3 parent; known rejection, UNKNOWN and
  UNAVAILABLE are never relabelled a positive. Caller still owns actual S23
  recovery preconditions, LearningPreference rev1, S29 grants/latency clocks.

## Relationship to E11 and live boundary

The host operator provides to E11's `SequentialActionHandoff` the two
callbacks `OneAvatarOriginalOwner.close_parent` and
`OneAvatarOriginalOwner.launch_action4`, only once a frozen E10/E11
`run_episode` has selected MOVE_AWAY and obtained independently AUTHORIZED
Action4. On WAIT/DENIED, no second client is launched. The original transport
still requires a real retained S23 Action3 authority/provenance and independent
Java server/World startup; it does **not** authenticate physical identity,
prepare World, or give E5 permission. A typed `SourceShutdown` on its own is
not proof of a real JVM/Node process: exact PID/exe/cwd/login/logout, original
config and playerdata/NBT and native event times require independent real
World inspection.

E9's previous World is Creative/NoAI with a near zombie and cannot be reused
as a Survival/damage comparison baseline. Before the single proposed
Survival/mob-AI golden episode, the user must explicitly authorize a **new
separately disposable World**, chosen baseline, exactly one episode and
bounded evidence collection. It is not an E5 arm and may not be inserted
into the frozen 36 trial denominator.

The CI runs fake-pipe transports with injected child spawn function and
existing S23 deterministic owner fixtures. No genuine Node, Java, server,
Minecraft, GPU or LLM process runs. Claim ceiling:
`E12_OPERATOR_TRANSPORT_OFFLINE_QUALIFIED`,
`E12_PHYSICAL_AVATAR_ACTION_LINEAGE_NOT_RUN`, E5 physical 36 NOT_RUN.
