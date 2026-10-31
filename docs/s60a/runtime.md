# S60-A local runtime coordination

`BestEffortDisplacement` adds a small single-slot wrapper. It imports the actual
S48 `CognitionContext`, `L2InterruptionFence`, `L2WorkTicket` and result rejection,
and the S53 `UrgentL0Receipt`. Existing S53 uses a blocking-provider thread and
requires STOP ACK to retire an interrupted ticket; changing that implementation
would weaken its frozen proof contract. This wrapper therefore owns a separate
provider lease. It never calls S48 `retire_interrupted` or writes a stop ACK.
S47 allocation/RelayEngine and all predecessors stay byte-identical.

## Host integration contract

Construct inside the foreground asyncio loop with current context, trusted
admission source, monotonic clock, and nonblocking `start(request)` /
`cancel(request)` callbacks. Model coordination is confined to that exact loop;
callback reentry is denied. The host retains all World IO/Action ownership.

1. Explicitly call `observe(context)` for every session/World/intent/retained change.
   Changes revoke active, pending and unused admissions; causal regression fails.
2. Call `admit` with exact current context, L1/L2, priority, finite future deadline,
   positive wait budget and configured source provenance. It issues a unique
   work/generation object. Only the latest issued object is consumable once.
   This is advisory compute permission issued by a trusted caller, not external
   authentication or Action/Intent/Skill/Learning authority.
3. `submit` starts at most one actual callback attempt or retains one pending
   candidate. Same/higher priority replaces pending; lower cannot evict it.
   It revokes the old S48 result before invoking cancellation, once per lease.
4. The start adapter must return its exact attempt's asyncio completion Future
   on this loop. Future success must denote a naturally observed provider terminal
   response. Do not resolve success merely on local cancel, disconnect, HTTP
   error, socket close or an unassociated idle assertion. Reused/foreign Futures
   are rejected. This is an adapter admission contract, not independently attested
   backend-idle evidence. There is no trusted idle reader in S60-A.
5. Service `tick()` at a bounded cadence from the existing event loop. It never
   waits, spins, spawns a thread/task, polls a server or retries. Active deadline
   revokes output and requests cancellation. Pending expires at the earlier of
   its deadline and submit-time wait budget; if still physically occupied, it
   emits PENDING_EXPIRED, CANCEL_UNCONFIRMED_BACKEND_BUSY and MODEL_SKIPPED.
   Receipt storage is capped at 64 events; obsolete pending work has no worker.
6. A naturally completed old Future emits BACKEND_COMPLETION_OBSERVED, releases
   only this wrapper's provider lease and permits one next admission attempt.
   Stale output is rejected first. NEW_REQUEST_STARTED means the callback was
   invoked, including an invocation that raises; it never means successful
   inference, independently proven idle, backend stop, GPU stop or VRAM release.
   Cancelled/error/malformed attempts remain occupied fail closed. They require
   a separately authorized integration/reconciliation, not forced retirement.
7. `tick` returns a transient `CognitiveResult` only if its exact S48 ticket and
   context are still admissible and deadline is unexpired. Displaced text is
   never returned or inspected, and never schedules another generation. There
   are no Action, Learning, Memory or Belief sinks in this component.
8. `run_l0` invokes an independently authorized callback with no model dependency.
   It propagates exceptions and returns status values unchanged, including UNKNOWN.
   `urgent_l0` additionally revokes the old result and reuses the S53 callback
   receipt with backend_stopped/gpu_released false. A status return cannot be
   converted to that successful callback receipt. Callback completion is not
   World Action OUTCOME. No automatic retry or undo of already-issued Action.

Receipts contain event and generation only, never prompt/result/exception text,
provenance reference, secrets or filesystem paths. Complete historical evidence
requires a separate host receipt consumer; the bounded window is transient.

## Offline qualification ceiling

The fake adapter in tests holds manually controlled Futures and an injected clock;
it performs zero model/GPU/Minecraft calls. Tests cover accepted cancellation
failure, latest priority coalescing, natural-completion races, stale/replayed/foreign
admissions, all context revisions, deadline/wait expiry, ambiguous terminal errors,
L0 failure/UNKNOWN and bounded queue/receipt/task counts.

No production adapter is installed or auto-promoted. Live adapter association,
real slot availability, actual cancellation behavior, response latency, stop ACK,
GPU compute cessation and VRAM release remain unqualified. L0 independence relies
on the declared nonblocking adapter callbacks and the caller servicing the event
loop; the offline tests do not measure physical latency. Future S60-B needs separate
opt-in authority and review. Terminal: S60_BEST_EFFORT_LOGICAL_DISPLACEMENT_OFFLINE_QUALIFIED,
BACKEND_STOP_UNCONFIRMED, NO_PHYSICAL_RESOURCE_RELEASE_CLAIM, NO_PRODUCTION_GO.
