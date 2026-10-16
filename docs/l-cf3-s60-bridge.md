# L-CF3 — S60-B1 opt-in cognitive fatigue budget bridge

Status: DEV_ONLY. The L-owned adapter creates S60 budget-constrained requests without a second inference executor. No S-approved live integration, Minecraft execution or scientific trial.

## Source audit

Existing S60-B1 validates literal max_tokens <= LoopbackTransportConfig.max_tokens before sending HTTP. It parses provider usage into ProviderCallFacts, but successful futures expose text only. No provider original usage receipt is available to L after completion, and a local cancellation is not backend stop acknowledgement. S49 owns World/Action permissions.

## Connection

- src/relay_self/cognitive_fatigue_s60.py maps F_c to an actual S60 LoopbackTransportConfig max_tokens and strict payload wrapper. OFF preserves the original object exactly; ON uses a bounded copy.
- make_s60_adapter returns the preexisting LoopbackDisplacementAdapter, not a new execution system. The real S60 payload serializer independently enforces the same cap. No connection to S49 is claimed.
- reserve_s60_l2 accepts typed S ModelRequest with exact session, generation and work ID, and conservatively reserves cognition before S submission. S must atomically checkpoint that state before sending requests. Incomplete starts, retries and unknown cancellation remain active; neither a clock advance nor physical Body WAIT grants recovery.
- settle_s60_l2 accepts an explicit claimed S/R full cumulative usage envelope and checks its profile/work/session, requested cap, complete token equation and terminal status. The envelope type is NOT independently authenticating; caller-provided VERIFIED string cannot be taken as a receipt without S/R raw evidence audit. Stock S60-B1 does NOT expose a source-verifiable usage envelope yet. Therefore automatic live fatigue settlement is NOT IMPLEMENTED / NOT QUALIFIED. Synthetic terminal tests are interface-only, not empirical evidence.

## Tests and next gates

tests/test_cognitive_fatigue_s60.py checks OFF parity, fixed/linear/nonlinear caps, original S60 request serialization, foreign/non-L2/overbudget refusal, stale plan/replay, timeout and unmetered cancellation, source-shaped terminal acceptance, invalid usage and L0 boundary. CI runs L-CF and S60 regression, full inherited Python, lint, repository contracts; no backend or World execution.

S: instrument opt-in original completion-token and response-digest receipts with request identity, preserve default behavior, ensure separate stop acknowledgement for interrupted calls, then apply this gate in its own self_live_think integration. R: qualify raw source, trustworthy monotonic idle intervals and durable state checkpoint/chain. P1/M: retain independent physical WAIT fatigue and energy. V: predeclare OFF/FIXED/LINEAR/NONLINEAR World contrasts and cheap controls after qualified S/R gates.

Classification: offline S60 token budget connection implemented. Live S-owned response metering, provenance authentication, durable ledger, World testing and scientific outcome remain NOT_DONE.
