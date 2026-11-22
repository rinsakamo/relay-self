# B-NP1b-2g — second A logout/reJOIN source boundary and original CPU rearm (DEV)

This stage is **one additional (second) A logout/reJOIN inside the same
owned World**. It builds on original first A reJOIN source and periodic A/B
Present from stacked Draft PR #1105. It does **not** claim arbitrary
unbounded reJOIN loops, restored Schema attestation or real World execution.

## Why the old verifier cannot be reused

The original first reJOIN verifier deliberately binds A's original
first login to its first retirement. At the second logout the Bridge's
original `_b_np1b_retired_login["A"]` now references A's *second*
retirement (the first rejoined A Native session). Simply passing the
original first `InitialSourceReceipt` or an old `CompositeSourceReceipt`
would falsely attach it to the new Native/Owner epoch and must HOLD.

## Original Owner generation boundary

1. When A1 and continuous B are both ONLINE, the existing original
   `ResidentCognitiveWorkOwner` has two already-running periodic CPU tasks.
   Call `capture_first_rejoin_cpu_anchor(bridge=bridge)`. It reads
   **both live original scheduled task results**, revalidates the full
   original A/B Native, Paper and Schema source and pins an immutable
   `FirstRejoinAnchor` internally under the original resident lock.
   No externally passed current receipt is accepted.
2. Call the original `bridge.logout("A")` (issuer first, Owner fence,
   CPU cancellation/await, persisted Cognition and original Native
   retirement). The B task remains ONLINE but its paired Present is
   automatically HOLD because A is absent.
3. Call original `bridge.login("A")`; the Owner epoch and Native
   session change, with all retired A native sessions still forbidden.
   A later independent owned Paper main-thread tick ACK must contain
   the **second** A QUIT, B PRESENT while A is gone, A JOIN,
   post-reJOIN A PRESENT **and post-reJOIN B PRESENT**.
4. `build_second_rejoin_cpu_pair(bridge=bridge)` independently reads
   original A/B owners, current Native receivers, original retirement
   tuple, B original-session decoder/adoption, original owned Paper
   process/log, earlier first-pair full-Paper prefix SHA and ACK, and
   new Paper tick ACK; it enforces *exactly* three A JOIN and two A QUIT
   events across this two-generation qualified history, one B JOIN and
   no B QUIT. It rechecks Native and Paper again before returning.
   It produces current **typed** `RejoinedCompositeSourceReceipt` A and
   `ContinuingCompositeSourceReceipt` B, using the existing current
   Native/Paper fields; new A composite binds the immediately prior A1
   receipt, second logout, second Paper generation and B continuity.
5. `await rearm_second_rejoin_normal_cpu(bridge=bridge)` requires the
   old A task to have retired via original logout. It independently
   verifies the *new* source before stopping the old B CPU task, checks
   every old task's completed identity and A2/B Owner epochs, removes
   only the retired B task ref from the original Owner ledger, and
   binds a `SecondRejoinCut` on the same Resident. A new pair of
   CPU tasks is registered via the pre-existing original
   `start_cpu_task`; no standalone Owner or alternative timer is
   created. The first historical selector remains immutable.
6. The existing `read_present_cpu` and `read_coverage_inquiry_cpu`
   dispatch to the second verifier **only after** the new cut is
   fully bound, and still use the original ThreeSelf/Schema/Need
   projector. `bridge.poll_normal_present_cpu()` and
   `bridge.require_scheduled_present_cpu` retain their public APIs:
   source tuples are recomputed, never served from stale old task
   cache. New B Native updates can change both A/B current
   composite revisions while B's original session stays unchanged.
7. The old scheduler and any of its cached results remain permanently
   fenced. A second attempt to rearm this same generation is rejected.
   Original individual logout/cancellation remains the retirement
   authority for new tasks too.

## Evidence, limitations

CPU/offline tests exercise a genuine original synthetic Mineflayer decoder
and owned synthetic Paper process, first- and second-generation Paper
events and original `bridge.logout/login`; adversarial cases include
missing/duplicate QUIT/JOIN, no B continuation, wrong actors or boot,
Paper prefix/log/ACK spoofing, swapped owner and Native sessions,
foreign retirement and staged updates, invalid Schema, epoch and task
reuse. No mainline source or independent Stage28 verification is
relaxed.

**Scope of PASS, if CI succeeds:** `B-NP1b-2g SECOND_A_REJOIN_CPU_REARM_OFFLINE_PASS`
only: exactly **two A logout/reJOIN cycles**, one owned World epoch,
continuous original B native, with explicit source-qualified first
anchor and one-time second-generation task rearm.

**Remaining HOLD:** 3rd and later A reJOIN loops (need recursive source
proof and auditable chain), automatic unattended real World rearm,
independent physical Paper/Mineflayer original evidence, restored
Schema authentication, E2c SenseFrame, L1/L2/GPU, Question ADOPT,
Physical Action, QUAL/SCIENCE. No Native/Paper cross-clock
simultaneity, memory write or newly granted Action permission.

Parent Issue #1047; stacked predecessor PR #1105.
