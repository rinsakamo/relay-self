# S #537 — S2-C source-bound S60-A/B1 async Gemma read-only shadow (DEV)

Parent [Draft #696](https://github.com/rinsakamo/relay-self/pull/696) real-World DEV PASS, exact HEAD `8949e64717b938418c9ecf624615fb87347810da`.
Stacked on preserved S2-B original owner readback and original S49 S16/WB/M source.
This PR prepares an independent **S2-C** entry point. **No Minecraft or
real Gemma can run in GitHub CI.** Offline tests use original implementation
classes with synthetic owner data and a fake local HTTP peer.

## Nonblocking physical design

`S2CAsyncObserver` subclasses the already physical-tested S2-B observer.
Its `observe()` callback runs only original S2-A WB L1/previous-S16 and
original L0/Intent owner identity checks. At the first qualified previous
S16, `S2BGatedL2Shadow.observe` calls the **existing S60-A
BestEffortDisplacement and S60-B1 LoopbackDisplacementAdapter** exactly once.
It schedules a separate `asyncio.Task` for polling; S49 `live_probe`
does **not await model completion**. The WB observation is a source-owned
original probe, not a new Action or native read.

The prompt includes:
- current same-source WB L1 and SelfWorld/SelfBody references;
- only the PREVIOUS completed S16 Action ID / source probe / after seq;
- original owner Intent ID, event-count causal generation and exact retained revision.
  The Intent generation is **not an explicit Intent revision field**.
- read-only instruction: no Action grant, learning, goal, reward or energy.

On an already closed **original S16** at the model's source probe,
`S2BOriginalOwnerEpochBinder.context_at_original_s16` reads actual
Intent and retained owners and the original S16 after-probe's native seq.
The S2-B wrapper tells **original S60-A** `observe(new_context)` to fence
and displace the older model lease. This is a valid native World advance
**without any new native read**. Transport cancellation, socket closure,
or S60 events do **not** independently prove the model/backend stopped or
GPU memory was released. Result text is advisory only and is not connected
to L0 decisions.

`S2CAsyncObserver.close_shadow` stops only its local poll task and original
S60-B1 client; it cannot claim backend STOP/slot idle. Reports distinguish
`s60_submissions` (one attempted call), `http_post_sent_observed`,
`http_completion_observed`, `ADVISORY_CURRENT_READ_ONLY` vs
`EXPIRED_ORIGINAL_S16_WORLD_ADVANCED` and backend unconfirmed close.

**Important:** Existing S60-B1 transport enforces exactly the five canonical
chat request fields and returns bounded nonempty assistant text. This PR
does **not** silently claim strict JSON Schema/Reasoning OFF request-level
controls that that adapter does not currently support. For local Gemma
experiments, the operator must confirm the backend's actual reasoning
configuration and the intended structured-response contract separately.
If strict JSON schema is a hard prerequisite, mark the live test
`DEFERRED_PROTOCOL_CONTRACT` until an explicit S60-compatible extension
is implemented/tested. The S2-C status itself is only read-only shadow
transport/source control, not a cognitive schema or prediction result.

## Real model / World preflight (separate DEV grant, not in this PR)

1. Check no overlapping DEV/QUAL/SCIENCE real-World or model consumers.
   Verify the S2-C branch exact HEAD, pinned M/WB owners, Python/Node/Java.
   Verify the single user-owned **llama-server process** on loopback:
   GGUF SHA256, binary SHA256/build, actual process PID, command line,
   loaded model mapping, alias, 8192 ctx, one slot, Reasoning OFF.
   This runner does NOT start the model nor independently attest that
   `--model-alias` corresponds to the file it is serving. Capture
   external source evidence before using the runner.
2. Require a fresh applicable S-lane World/model grant:
   one disposable World, original S49 at most two Action, one model
   submission, 1 slot, <=256 tokens, timeout <=60 seconds, retry=0.
   No fallback backend, no unknown-status request retry, no new executor.
3. After exact full preflight, in fresh evidence directory:

```bash
export PYTHONPATH=src:.:tests
export S49_REAL_SERVER_CI=1
export S49_COMPLETED_L0_DEV_ONLY=1
export S537_S2C_LIVE_L2_DEV_ONLY=1
python -m tools.s537_s2c_live_s60_shadow_dev \
  --m-owner-dir "$M_OWNER_DIR" --wb-owner-dir "$WB_OWNER_DIR" \
  --report "$EVIDENCE_DIR/s49.json" \
  --server-log "$EVIDENCE_DIR/server.log" \
  --s2c-report "$EVIDENCE_DIR/s2c.json" \
  --model-alias "$MODEL_ALIAS" --model-port "$MODEL_PORT" \
  --max-tokens 256 --timeout-s 45 --live-world-dev
```

The default-OFF gates prohibit this invocation absent explicit flags.
Use the original S49 S16 validator as the owner physical verifier.
The previous S2-B auditor still defaults to **zero** model calls;
for this S2-C model-enabled report use the new independent audit
with explicit one-sidecar request accounting:

```bash
python -m tools.s537_s2c_async_source_audit \
  --s49 "$EVIDENCE_DIR/s49.json" \
  --s2c "$EVIDENCE_DIR/s2c.json" \
  --output "$EVIDENCE_DIR/s2c-source-audit.json"
```

The audit compares original S49 native Action / S16 outcomes,
S2-A WB source and previous S16, exact original L0/Intent revision rows,
one S60 POST and original S16 expiry. Synthetic model receipts in CI are
test fixtures only. The audit does not independently attest the backend
PID, HTTP wire or Paper/W3 timestamp.

4. Record each source native sequence, Action S16 after sequence,
   exact L0/Intent revision, S60 request/cancellation/response stages
   and original S49 L0 timings. A model request sent then invalidated
   at next S16 may **never** yield a current advisory; that is expected
   correct handling, not evidence of actual Gemma reasoning.
5. All cleanup (Java/Node/processes/ports/World) and raw SHA verification
   is required. Do not claim provider stop/GPU idle without independent
   attestation. No learner, L0 promotion, energy debit or new Action.
   Source-attested stays FALSE; Paper/W3 independent attestation NOT_RUN.

## Status boundaries

Until one genuinely owner-verified model + new World:
`DEV_ONLY / S2C_ASYNC_S60_OFFLINE_ONLY /
S2C_REAL_WORLD_NOT_RUN / S2C_REAL_GEMMA_NOT_RUN /
SOURCE_UNATTESTED / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN`.

The maximal first physical test may establish an admitted original
same-source S60 model HTTP *attempt* with correct S16 displacement.
It must not claim current L2 insight if `HTTP_COMPLETION_OBSERVED` and
advisory acceptance at a current unchanged owner epoch were not both seen.
