# Product/S model-only runtime

Refs #575 / #633. `adapters.llama_cpp.model_runtime.owned_model` is a
synchronous product/S-owned lifetime over the existing S57 process primitives.
It does not create a RelayEngine, accept shell commands, or import Minecraft.
S55 artifact hashing and S57 primitives now live under `adapters.llama_cpp`;
the original S55/S57 APIs re-export those same definitions. Existing World
launch and qualification remain in their original entry points.

Use RSEE's existing Python 3.12 venv, original binary and original GGUF. Supply
an `OwnedBackendSpec` with freshly verified binary/GGUF SHA256, a single alias,
IPv4 loopback port, context 8192, parallel 1, and explicit GPU layer count.
`owned_model(spec, evidence=absolute_new_path, confirm="PRODUCT_MODEL_DEV_ONLY")`
yields only after health, models, props, slots and runtime identity checks.
A/B and other callers keep their original provider/engine and requests. The
SelfWorld A/B CLI remains byte-identical and runs as a caller within this scope.

The scope adds `--no-context-shift --slots`, retains binary stdout/stderr bytes
in an exclusive-new file, records PID/group/starttime, and reuses S57's
TERM/KILL/wait cleanup. Caller failures and cancellation trigger cleanup;
secondary cleanup failures remain visible beside the primary exception.
Reap, `/proc` absence and a successful port bind are separate observations.
They do not establish backend STOP ACK or GPU VRAM release. The synchronous
scope must enclose the caller's whole execution; it is not an async task owner.
SIGTERM on the main thread raises through the cleanup path; SIGKILL cannot
provide Python cleanup guarantees.

Resource key remains `llama-cpp:local-gpu`. A nonblocking host flock at
`/tmp/relay-self-llama-cpp-local-gpu-<uid>.lock` prevents cooperating S scopes
from starting concurrently. There is no repository-wide external GPU lease
service in the audited S55/S57 path. The lock does not arbitrate noncooperating
or other-user GPU jobs. Check host process/GPU occupancy before execution and
never stop another process or reclaim its lease. Existing S60 request leases
and failure semantics remain unchanged; this scope does not release them.

RSEE R1 `shared_runtime.py` remains a separate read-only plan/preflight branch.
No R1 code or unmerged RSEE Draft is integrated. R owns no process or lease.
Existing Golden/World grants and historical evidence convey no new authority.

Focused tests cover exact hashes, API identity, occupied resources, import
closure, normal/error/cancel exits, primary plus secondary faults, group guards,
TERM/KILL and reap. Fake API tests are not live model evidence. Every live run
needs its own outside-repository evidence, source pin and host checks.

Claim ceiling: DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.
