# S60-A prospective implementation contract

Authority: Issue #500 and user-adopted #417 comment 6090041172.
Frozen base: Draft #413, branch self/postmain-feature-s57-owned-local-llama-backend-20261009,
HEAD 564b52cfead748258594be65927072489fee963d. Remote main refreshed:
4348a614900c1d0828581a8eec2c523ba5ae237f. Primary checkout remains untouched.
No conflicting S60 open PR at inspection. Main protection active.

Add one event-loop-local single-slot wrapper, typed transient requests and bounded
sanitized receipts. Reuse S48 context/fence and S53 L0 receipt; never mutate S18-S59
or retire an interrupted S48 ticket without STOP ACK. A completed old wrapper
lease may be released under the narrower provider admission contract below;
its S48 ticket remains logically rejected, not stop-acknowledged.

Admission: owner-issued object identity, monotonically unique work/generation,
exact current context and configured provenance source, L1/L2, integer priority,
finite future deadline and positive wait budget. No Action or Learning authority.
Only current issued request can be submitted once. Context changes explicitly
revoke active/pending/unused admissions; no foreign session admission.

Backend adapter contract: start/cancel are nonblocking event-loop-local callbacks.
Start invokes an actual provider attempt and returns an asyncio Future owned by
that adapter. Successful completion must mean naturally observed provider terminal
response for this exact attempt (not merely client close). Only that successful
completion allows another admission attempt; it is not independent idle, STOP ACK,
GPU cessation or VRAM evidence. Cancelled Future, exceptions, malformed start,
unknown/claimed idle all remain occupied fail closed. No production adapter/live
promotion here. No retry/kill. No polling loop, worker/thread creation by wrapper.

One physical active lease and at most one pending request. Same/higher priority
newest replaces pending; lower priority cannot displace it or active higher priority.
Revocation precedes cancellation callback. Repeated displacement does not repeat
cancel. Deadline or wait budget expiration drops model request with
CANCEL_UNCONFIRMED_BACKEND_BUSY, MODEL_SKIPPED. Externally driven tick handles
expiry/completion; caller must service tick at its own bounded event cadence.
Receipts retain only latest 64 events. No prompts/text/errors/paths in receipts.
L0 callback can run with no model lease; callback failures/UNKNOWN propagate and
never produce success or reissue.

Frozen tests: blocked L2 + urgent L1 + independent L0; ignored/raising/local cancel;
natural completion/cancel/replacement races; 3+ priority/deadline coalescing;
source/context/revision/identity replay/forgery; errors/unknown/false idle;
L0 failure/UNKNOWN; no stale Action/Learning output. Deterministic Future and
injected monotonic clock, no actual model/GPU/Minecraft. Full pytest, Ruff,
repository contracts and Node protocol checks on exact HEAD; dedicated exact-head
CI. Preserve first red-run/fix records. Do not alter acceptance after tests.

Terminal ceiling: S60_BEST_EFFORT_LOGICAL_DISPLACEMENT_OFFLINE_QUALIFIED;
BACKEND_STOP_UNCONFIRMED; NO_PHYSICAL_RESOURCE_RELEASE_CLAIM; NO_PRODUCTION_GO.
Draft stacked PR only. No merge. No physical execution or scientific #46/#415 work.
