# E11 — sequential native avatar handoff after E10 authorization

Parent: [#559](https://github.com/rinsakamo/relay-self/issues/559), exact offline E10 HEAD
`42bf12e238692d35b156a4d7c30f176942914b53`.
Owner: [#566](https://github.com/rinsakamo/relay-self/issues/566).

## Why this successor is needed

E10's fake-world apparatus accepts both an Action3/S29 observation transport
and a distinct Action4 transport *before* its coroutine begins. Minecraft does
not furnish proof that two concurrent connections with the same username share
an avatar, and a replacement login may disconnect the old one. Offline identity
equality on `host/port/username/version` cannot prove avatar continuity.

## Narrow new mechanism

`SequentialActionHandoff` is an **inert, injected transport**. The successor
`experiments.epistemic_e11_sequential_action_world.run_episode` retains E10's
typed E3/S24/E10 Action3→S29→S24 logic, but performs the handoff only if:
1. Exactly the original source-owned MOVE_AWAY decision follows two granted
   correlated reads; WAIT does not disconnect or spawn another client.
2. Separate Action4 authority returns the original typed AUTHORIZED successor.
   DENIED does not acquire another transport.
3. The parent Source/Action3 native client returns a source-native ACK, optional
   subsequent connection_end, and owned exit code0, checked **before** the new
   native launcher callback is invoked. The callback must preserve the raw
   original frames and actual owned processes; this helper cannot authenticate
   a fabricated callback result.
4. The new client must have identical declared Minecraft host/port/username/
   version and Mineflayer build, a genuinely distinct source session and
   original typed seq1 `spawn`. Its position must match the final policy
   observation within 0.01 m. The read-ahead seq1 original spawn is **buffered**
   and delivered exactly once to E10's S15 executor, preserving native seq.
5. The caller retains a typed `HandoffReceipt` (source/child IDs, ACK, deltas,
   health), never `physically_authenticated=true`. Handoff callbacks are
   single-use even on failure; no retry/replay. The original E10 function,
   tests, E5–E9 sources and all prior recorded outcomes remain unchanged.

## Physical evidence still needed

The handoff only proves offline that callback and typed stream ordering obey a
bounded contract. It does **not** prove actual same-avatar continuity or World
integrity. A future explicitly authorized single physical episode must acquire
a genuine **terminal S23 Action3 WorldConsequence** and E10 owner inputs *before*
running the successor. It must have a user-owned separately disposable Survival
World with AI/damage enabled; the old E9 Creative/NoAI geometry World containing
a saved near zombie cannot serve as the damage experiment baseline.

Before that live episode: pin process/session/username identity, PRE+POST
byte-original server config and playerdata, source JSONL including ACK/close,
login/logout timestamps, stable World identity, spawn position and later health,
the actual S15/S16 Action4 issue/outcome and separate post-decision evaluator.
E11 does **not** launch a server or bridge or provide a CLI `--run` path: the
host-owned source/launch callbacks and Action3 production owner still require
physical qualification. A future physical caller must not silently treat fake
transport evidence as physical evidence. E5's 36 arms and physical effect stay
NOT_RUN/UNDETERMINED; new explicit execution authorization is required.

Acceptance today: offline deterministic handoff and fail-closed cases, exact
stacked Draft PR CI. No actual Minecraft/Node/LLM/GPU and no physical E5 trials.
