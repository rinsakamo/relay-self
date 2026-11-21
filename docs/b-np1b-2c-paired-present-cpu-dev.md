# B-NP1b-2c original Bridge A/B current CPU Present poll (DEV)

This is a **CPU/offline, original-Bridge** caller and source admission, not an
autonomous scheduler. It does not admit GPU inference, Skill/Action issuance,
Question adoption or writes to persistent cognition/WAL.

## Required source chronology

1. Fresh original A/B Owner and registered exploration Schema, initial original
   native login on independent A/B Mineflayer ProcessSessions, original
   `InitialSourceReceipt` A/B.
2. Same-session fresh A Native update and `CompositeSourceReceipt` for A;
   preserve both original receipts as immutable history.
3. Original Bridge `logout("A")` completes retirement, revoked issuer and
   old Native fence; `login("A")` creates a new Native session/Resident epoch.
   Original B stays ONLINE on its unchanged Native session and adopted initial probe.
4. The **owned Paper process** provides A QUIT / B PRESENT in the gap /
   A JOIN + PRESENT / **new B PRESENT after A's reJOIN** and a newer main-thread
   ACK (tick/nonce). All lines belong to the one original Paper session/boot.
5. Invoke `bridge.bind_normal_rejoin_present_cpu(initial_receipts=...,
   historical_composite=...)` once. This requalifies **both** original
   Native/Paper/Owner sources under the original resident lock before storing
   only an immutable source-history selector on that same resident.
6. Invoke `bridge.poll_normal_present_cpu()` for synchronous, read-only A/B
   Present and optional coverage inquiry. Each invocation re-runs the original
   A reJOIN Composite verifier and separate B continuing Composite verifier,
   projects the same registered Schema with the original Present projector,
   rechecks both, compares the common current Paper digest/tick source and
   returns an immutable `NormalPresentCpuPoll`.

The caller does not accept a caller-provided *current* source receipt. The
original A verifier rebuilds the Native and Paper revisions, confirms prior
logout/retirement and rejects old Native sessions. The continuing-B verifier
binds its original still-adopted Native probe/Owner to a **post-A-reJOIN**
Paper PRESENT with the **latest** owned tick ACK. B's Native revision is
explicitly the original login observation; this stage does **not** claim a fresh
new Native B WorldBody observation, or that B's Native and Paper clocks are
numerically comparable.

Historical initial/composite inputs are never promoted directly into current
authority: they must be verified against the original owners and current
live stream on every poll. If the log grows after the selected Paper ACK,
if either Native session/Owner/epoch/Schema changes, if A/B Paper identity
changes or if a logout/fence/pending Native update occurs, the poll HOLDs.
A new owned tick and corroborating source can produce a new deterministic
Paper/Composite/pair revision without mutating the original history.

## Trust and qualification limits

The resident lock protects the original cognitive Owner; the external Paper
process is not locked, so verification is a **rechecked source cut**, not
physical simultaneity. SHA256 binds the bytes read from the original Paper
owner but does not authenticate a detached, externally supplied log.

The test exercises the original Bridge logout/login, Mineflayer decoder,
synthetic owned Paper process, new A/B Present/Inquiry, deterministic repeat,
new Paper tick refresh, stale source rejection and hostile changes. Existing
Stage28 and B-NP1b-1B2b-1/-2 regressions run in the full suite.

**HOLD:** real Paper/World, automatic periodic runtime scheduling, restored
Schema attestation, a B same-session *new* Native observation after A reJOIN,
multiple reJOIN cycles, E2c SenseFrame, L1/L2, Question ADOPT, Physical
Action, QUAL and SCIENCE. The existing Stage28 first-JOIN verifier is unchanged.

Primary issue: #1047. Parent source PRs: #1079 and #1086.
