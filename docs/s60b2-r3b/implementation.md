# R3-B0 diagnostic Arm A admission

Authority: [Issue #563](https://github.com/rinsakamo/relay-self/issues/563).
The [manifest](manifest.md) remains frozen at commit
`a00b3bcb271d9671164d7175337d774534b1e462`, blob
`fcef08402a618bc32cd2d3317dd5c6f63d9cad22`, SHA256
`7fb4fbb5e4b91e4c561fbd462b522dc4ec89513fdb1d35b409ca5f9b88276330`.

## Admission and runner

The existing B2 `authorize()` remains byte-for-byte unchanged. Ordinary
`--plan` and `--run` retain their existing behavior. Diagnostic selection requires
`--run --diagnostic-arm-a --diagnostic-grant <private-file>` in addition to
B2's config, approval and evidence arguments. No environment switch selects it.
Direct `run()` uses keyword-only `diagnostic_arm_a=True` and
`diagnostic_grant_bytes`; it enforces the same admission before reservation.
A grant supplied without explicit diagnostic mode is rejected.

Both private approvals must be independently reviewed for the future live run.
The additional strict JSON object has exactly these fields:

| Field | Required binding |
| --- | --- |
| runner_head | Current clean R3-B checkout HEAD |
| manifest_sha256 | Frozen R3-B manifest SHA256 above |
| base_manifest_sha256 | Existing B2 `MANIFEST` SHA256 |
| config_sha256 | Original private config file bytes, including whitespace |
| approval_sha256 | Original B2 approval file bytes, including whitespace |
| arm | `A` |
| diagnostic_arm_a | JSON `true` |
| operator_token | The same uniquely selected 64 lowercase hex operator token as B2 approval |
| allow_model_gpu_launch | JSON `true` |
| source_binary_mapping_reviewed | JSON `true` |
| runtime_shared_libraries_reviewed | JSON `true` |
| prior_cleanup_confirmed | JSON `true` |
| evidence_root | Same resolved, new external private root as B2 approval |

No filled live credential is generated. Reviews are operator attestations, not
an automated proof of complete runtime library closure. Existing B2 source,
binary and GGUF pins, preflight, listener and process ownership remain active.
CI admission is refused for any nonempty CI indicator. Consumed roots are
rejected; the existing exclusive fsynced directory reservation remains the
once-only invocation boundary even if preflight or fsync fails. A diagnostic
grant cannot repair a rejected B2 approval or bypass its HEAD binding.

After both approvals pass, the owned runner injects the exact R3-A
`R3DiagnosticTransport` into the existing `measure()` seam. Parser, Future,
lease, fencing, L0, slot accounting and cleanup code are unchanged. The
observer, its 64-record bound, failure stages, durable off-loop writes and
interrupted-fsync behavior remain unchanged. Only stage, generation and time
enter diagnostic receipts. Failure does not trigger a second POST. Normal
Arm A completion requires two accepted complete responses and distinct
observed task starts, with no fabricated diagnostic failure. The diagnostic
success terminal is `R3B_RECEIPTS_REVIEW_REQUIRED`; cleanup uncertainty remains
`CLEANUP_UNCONFIRMED`. Every summary still denies physical qualification,
backend stop, GPU quiescence, VRAM release and production GO.

## Offline evidence and remaining live gates

`tests/test_feature_s60b2_r3b.py` exercises admission through CLI and direct API,
then actual runner/measure with synthetic subprocess, GGUF, `/proc`, and a real
localhost stock-shaped HTTP fixture. Tests cover successful fixed/chunked
responses, JSON/schema/model/fingerprint/usage/framing failures, disconnect,
timeout cancellation, L0, owned cleanup, replay refusal and redaction. Existing
R3 tests retain adapter failure, overflow and interrupted diagnostic fsync
coverage. No real model, GPU or Minecraft is launched by these tests.

B0 evidence is bounded to offline qualification. R3-B1 still requires separate
explicit new physical user authorization, a clean final exact HEAD, both newly
reviewed private grants, the frozen manifests and exact original file bytes,
reviewed pinned stock source/binary/GGUF/runtime/shared libraries, independently
confirmed previous cleanup, a new free exclusive loopback port and never-used
external private evidence root. One Arm A only; no retry, replay, Arm B/C,
llama.cpp modification or merge is authorized.

Historical Arm A cause remains `UNDETERMINED`. A coarse
`HTTP_READ_OR_FRAMING_UNCONFIRMED` does not identify connection/write cause;
slot idle does not establish complete HTTP or B1 lease release. Missing
classification remains `TRANSPORT_STAGE_UNKNOWN`, where appropriate. Offline
results establish no STOP ACK or physical same-process reentry proof.
