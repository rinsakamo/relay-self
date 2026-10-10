# S60-B2 R2 offline diagnostics

Authority #551, R1 comment 6097707476; pre-implementation manifest receipt
https://github.com/rinsakamo/relay-self/issues/551#issuecomment-6097968902
Manifest-only commit 23668247f80a7df058b577b41d23de90367dafa0;
SHA256 7ab0726b44586d82b25ef9d013d8152d68b024410486d32380d99a54e81765a6;
blob 954ae3fcfff720bf14f8685b8461380e3bec7177. Published/read back before code/tests.

Only new files. Physical B2 runner has no import/construction of the observer.
Subclass delegates every response to frozen MeasuredTransport and B1 parser;
no modified acceptance, transport task, Future, cancellation, owner, slot or
release contract. Receipt creation requires the adapter's exact attempt and
transport task; client cancellation uses the exact attempt callback. No new
scheduler. Observer does not publish results or consume/release leases.

## Interpretation

- HTTP_READ_OR_FRAMING_UNCONFIRMED: frozen _response failed; covers status,
  header, length/chunks, cut connection and read timeout without claiming which.
- JSON_DECODE_FAILURE: exact B2 parse_json failed (including duplicates/constants).
- MODEL_OR_FINGERPRINT_MISMATCH: dictionary decoded but exact B2 identity gate fails.
- USAGE_ENVELOPE_UNCONFIRMED: only B2's usage-dictionary gate; other usage validation
  failures remain SCHEMA_UNCONFIRMED.
- SCHEMA_UNCONFIRMED: residual frozen envelope/parser rejection, including empty,
  nontext/tool message or usage inconsistency; not proof of a particular subgate.
- CLIENT_CANCEL_OR_UNKNOWN: local cancel observation, not backend STOP.
- TRANSPORT_PRE_RESPONSE_UNKNOWN: frozen transport failed before _response;
  connection/write/drain/whole timeout cannot be separated.
- TRANSPORT_STAGE_UNKNOWN: unrecognized or otherwise unobserved failure.

Stage/generation/bounded monotonic elapsed milliseconds only, deque maxlen 64;
no exception inspection/text, raw bytes, model/header/path/prompt/token logging.
The observer temporarily decodes a body in memory for classification, retains
no body/object after return, and rethrows frozen errors to the original transport.
Normal transient model return remains governed by the inherited Future contract.
No drain or disk sink is added for diagnostics. Caller-provided frozen B2 journal
retains its existing content-free behavior. This class is prospective offline
fixture instrumentation only, not automatic live adoption or an R3 grant.

## Verification

20 new tests; focused A/B1/B2/R2: 246 passed. Each synthetic complete/partial HTTP
case runs both observer and frozen B2; inherited event receipts are equal.
Fixtures cover length/chunked success, JSON syntax/duplicate/constant negatives,
nonobject JSON, model/fingerprint, usage, empty/nontext/tools, usage consistency,
status/partial header/body, timeout, refused connection and both Future/adapter
cancel. Failure keeps lease occupied; no completion laundering. Foreign attempt
cannot emit a receipt; manual parser validation outside transport emits none.
Unknown code is sanitized and 100 observations leave exactly 64 receipts.
Full Ruff and repository contracts passed. Locked Node 22.22.2 protocol: 33 passed;
external dependency installation uses identical package-lock SHA256
545e32a148b1f3649ba199dac9383fca72d0aaae17afbe740dc26163491ae568.
Full regression and exact-head CI results are recorded on #551 / Draft PR after
completion. Initial local command used unavailable `python`/`ruff` names and
ran no tests; corrected to existing external Python 3.12 environment, no code fix.

## Evidence ceiling

S60_B2_R2_OFFLINE_DIAGNOSTIC_QUALIFIED requires full regression/exact-head CI PASS.
ARM_A_FAILURE_CAUSE_NOT_YET_OBSERVED. Historical sanitized receipt cannot recover
its missing stage or bytes. Stock normal timings are allowed by B1; source shapes
are possibilities only. Time ordering and independently idle slot do not establish
HTTP completion, STOP ACK, GPU cessation, slot reentry or L1 start.
NO_NEW_PHYSICAL_RUN; NO_STOP_ACK; NO_REENTRY_PROOF; NO_PRODUCTION_GO.
No LLM/GPU/Minecraft or old Arm A replay; separate R3 freeze/local approval/source
review remains necessary. No merge, auto-merge or Issue closure.
