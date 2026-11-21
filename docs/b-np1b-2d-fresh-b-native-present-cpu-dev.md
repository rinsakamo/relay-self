# B-NP1b-2d — original B's later Native observations after A reJOIN (CPU DEV)

This stage extends the existing #1091 explicitly polled original Bridge
A/B Present/Inquiry path. It does **not** create a new Owner, session,
ActionPort, autonomous scheduler or model inference path.

## Original source and update sequence

1. Use the original Bridge A/B initial native login `InitialSourceReceipt`
   pair, original A fresh Composite, original A logout/retirement and genuine
   A reJOIN; original B stays continuously ONLINE on its initial native session.
2. The original owned Paper process must still prove A QUIT, B PRESENT in
   the gap, A reJOIN + PRESENT, then **B PRESENT after A reJOIN** with a
   current owned main-thread Paper tick ACK (as in #1091).
3. Bind original source history once with
   `bridge.bind_normal_rejoin_present_cpu(initial_receipts=...,
   historical_composite=...)`; the history itself is never a current source.
4. **On B's actual original Mineflayer ProcessSession**, asynchronously call
   `update_fresh_native(bridge=bridge, self_id="B",
   initial_receipt=initial_receipts[1])`. This is the existing receiver- and
   Owner-bound same-session Native observation update: correlated request ID,
   increasing sequence, Native time readback and owner adoption under original
   Resident lock, with a single claimed receiver and fail-closed fence.
5. Poll `bridge.poll_normal_present_cpu()` again. It obtains B's current
   source through `read_continuing_b_native_revision`, never a caller-provided
   current receipt. This helper rechecks original B owner, original login,
   still-running original session, decoder sequence, current adopted probe
   identity, original bridge's update record, bound initial history and
   recomputed Native revision. If B was not updated, it admits only the
   unchanged original login probe.
6. The original A Paper reJOIN verifier independently reads current B Native
   revision **before and after** Paper I/O; its evidence now binds that
   B revision. The A RejoinedComposite embeds an updated B continuity
   revision; B ContinuingComposite binds its own current Native revision
   plus an owned B post-reJOIN Paper PRESENT, and the exact A Composite.
   Both Present/Inquiry projections are re-read from original Schema and
   original Owner under the original Resident lock.

## Admission boundaries and rejected changes

- The unchanged original B Native session and Owner identity are mandatory;
  old B initial request/probe/session stay historical even after updating.
- Any unrecorded current observation, copied observation, modified revision,
  mismatched initial receipt, changed Native decoder sequence, outstanding
  receiver claim, changed resident/world epoch, logout, Paper log/process
  tampering, reJOIN source drift, or updated B Native during Paper
  verification yields HOLD.
- Each genuine adopted new B Native probe produces a distinct Native B
  revision and a new A B-continuity/B Composite/A Composite/pair revision
  without promoting the old Receipt. Repeating the same current sources
  returns a deterministic readout.
- Paper and Native clocks remain **independent**. This stage does not prove
  B Native and Paper observations happened in one physical instant; the
  Paper cut itself is independently verified and a fresh Native adoption
  is separately tied to the original Owner/decoder.
- The source helper does not itself receive a Native observation:
  **only** `update_fresh_native` may claim the original Native receiver,
  and a caller that already owns it cannot run another update concurrently.

## Verification and outstanding work

The synthetic CPU/offline test suite reuses the actual original
logout/reJOIN Bridge, process-session Native decoder, original Owner,
persistent cognition and owned synthetic Paper stream. It tests repeated
B Native updates, revision changes and adversarial mutations, including
a B update racing the independent Paper source verification.

**HOLD:** autonomous scheduler wiring, user hardware real Native/Paper,
multi-reJOIN cycles, restored Schema authentication, E2c SenseFrame
composition, L1/L2, Question ADOPT, Physical Action, QUAL/SCIENCE.
No real Gemma POST or Minecraft physical movement is claimed.

Parent Issue #1047, stacked predecessor Draft PR #1091.
