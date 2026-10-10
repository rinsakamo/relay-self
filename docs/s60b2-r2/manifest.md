# S60-B2 R2 prospective offline diagnostic freeze

Authority: #551 and R1 comment 6097707476. Base #542 exact
 a378d4db320cd77b4278517226373946a5a5c78c.

Only additive files: this manifest, docs/s60b2-r2/validation.md,
adapters/mineflayer/s60b2_offline_diagnostic.py,
tests/test_feature_s60b2_diagnostic.py,
.github/workflows/feature-s60b2-r2.yml.
All predecessor tracked files remain byte-identical. No scheduler, accepted
parser, Future publication, cancellation, lease, pending, L0, Action or Learning changes.

Offline-only subclass intercepts frozen _response and _validate_response and
_record. No monkeypatch. Exact current attempt/task provenance required.
HTTP_READ_OR_FRAMING_UNCONFIRMED is deliberately coarse: header/status/body/
read timeout cannot be reliably separated at the frozen seam.
JSON_DECODE_FAILURE, MODEL_OR_FINGERPRINT_MISMATCH,
USAGE_ENVELOPE_UNCONFIRMED (only B2 dictionary gate), SCHEMA_UNCONFIRMED
(remaining B1 failures), CLIENT_CANCEL_OR_UNKNOWN,
TRANSPORT_PRE_RESPONSE_UNKNOWN and TRANSPORT_STAGE_UNKNOWN are allowlisted.
Diagnostics contain stage, generation, bounded monotonic elapsed milliseconds
only; bounded 64 receipts, no raw exception/body/header/prompt/path/token storage.
No diagnostic success/release authority. Frozen parser alone accepts responses.
No production wiring, live flags or physical invocation.

Verify synthetic complete/partial HTTP, JSON, identity, schema, cancellation,
timeout, refusal, redaction, provenance, queue bounds and unchanged completion
and failed-lease semantics; full pytest, Ruff, repository contracts, locked Node
protocol, exact-head push and PR CI. Draft target self/s60b2-p0-20261010.
Ceiling: S60_B2_R2_OFFLINE_DIAGNOSTIC_QUALIFIED only.
ARM_A_FAILURE_CAUSE_NOT_YET_OBSERVED; NO_NEW_PHYSICAL_RUN; NO_STOP_ACK;
NO_REENTRY_PROOF; NO_PRODUCTION_GO. R3 requires new freeze/local approval/review.
