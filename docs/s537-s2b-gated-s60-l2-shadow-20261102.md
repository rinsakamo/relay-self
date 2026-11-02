# S #537 S2-B — original S2-A source → gated S60-A/B1 L2 shadow (offline DEV)

## Scope and source

Parent: S2-A physical DEV PASS [Draft #691](https://github.com/rinsakamo/relay-self/pull/691),
exact HEAD `8cb90b0910084ee5fe889b5a5e3c1e29a61ac988`. The preserved
S49 original Action issuer/STOP/S15/S16, S1 WB/M and S2-A source callbacks
remain unchanged. The separate S branch adds only:

- `adapters/mineflayer/s537_s2b_gated_l2_shadow.py`
- `tests/test_s537_s2b_gated_l2_shadow.py`
- focused GitHub Actions and this document.

**Do not assume the S49 original runner already exposes intent and retained
revisions. It does not.** The existing
`self_live_think.LiveL2Observer.observe` demo hardcodes
`CognitionContext(..., 1, 1)`; this is NOT acceptable as proof of actual S49
original owner revisions for S2-B.

The new `S2BOwnerContextRead` requires explicitly supplied
`CognitionContext` from the original S49 L0/Intent owner and the **same
Python `S2AReadOnlyInput` object**. Its construction checks typed
session/native source, but does NOT itself attest the owner provenance:
a copied/fabricated context cannot become trustworthy by dataclass
construction. Actual live runner integration **must capture exact original
L0 retained and current Intent owner revision and establish their identity
before** invoking S2-B; until then the model must DEFER.

## Implemented bridge

`S2BGatedL2Shadow` is opt-in; accepts a single previous-S16-qualified
S2-A input, same-session owner context and an explicit loopback B1
config (one slot, max 256 output tokens, timeout <=60 seconds).

- No previous Action/S16, missing owner revision or invalid source =>
  no model submission; missing owner => `DEFERRED_ORIGINAL_OWNER_REVISION_UNAVAILABLE`.
- With supplied exact typed context, original **S60-A BestEffortDisplacement**
  owns admission/deadline/currentness and original **S60-B1
  LoopbackDisplacementAdapter** owns the one outbound HTTP request,
  response envelope, no retry and transport uncertainty.
- A new native probe invalidates the S2-B result for current cognition.
  If exact current owner context is also supplied, S60-A receives it for
  its own stale fence; if owner context is missing, the wrapper rejects
  any returned output as current but **cannot claim S60-A native context
  update or backend STOP**.
- L2 result stays bounded untrusted **read-only advisory text**;
  never Action, World, L1/L0 learning, goal attainment, reward or energy.
  Host close is NOT a backend STOP ACK or physical GPU release.

## Offline tests

The tests include a local **synthetic HTTP** completion fixture to exercise
the actual S60-A/B1 classes. It is NOT Gemma, Minecraft, real original
intent/retained revision, physical provider attestation, or cognitive gain.
Fail-closed cases: absent owner source, mismatched source, future S16,
replay, foreign session, invalid output bounds, default-OFF, stale result
and one-shot submission cap.

## Next boundary (not yet physically complete)

A minimal **original-source revision witness** is needed before the
S2-A `live_probe` can submit model inference:

1. Expose only a read-only snapshot of the exact original S49
   `NormalWorldL0.retained` and `NormalSessionActionExecutor.intent`
   (including authoritative generation/revisions) with same source/session.
   Do not infer missing owner revision as literal `1` or from saved JSON.
2. Verify native probe identity, previous S16 host order, exact
   L0/Intent source, and backend-owned Gemma process/model sha/alias.
   Do not substitute current `LiveL2Observer`'s synthetic revisions.
3. **Only after the explicit fresh DEV model/World budget is granted**:
   run disposable single World, original Action <=2, one S60 L2 request
   <=256 output tokens, timeout <=60 sec, retry 0. This is a proposal,
   **not** permission consumed by this offline PR.
4. Preserve exact original World/owner evidence, canonical B1 payload/
   completion, S60 currentness and stale/failure, shutdown and port release.
   Neither source shape nor a passed CI validates Paper/W3 source custody.

Status before physical integration:
`DEV_ONLY / S2B_OFFLINE_GATE_ONLY / S2B_REAL_WORLD_NOT_RUN /
S2B_REAL_GEMMA_NOT_RUN / SOURCE_UNATTESTED /
QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.
