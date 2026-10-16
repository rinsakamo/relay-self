# L-CF1 / L-CF2 — Cognitive Fatigue offline candidate

**Status:** DEV_ONLY / engineering candidate. No Minecraft, inference backend, GPU, S49 Action, R qualification, or V scientific run performed. Parent is immutable L5 #613 at \`17c5357fd5625274ee567ad979b780e77bf7b1e7\`. This branch does not integrate sibling S #545, P1 #626, M #617, or V #625.

## Ownership and observed existing contracts

- L #426 owns cognition allocation/learning. Existing \`src/relay_self/cognitive_allocation.py\` has \`CognitionBudget\` (max_model_calls/THINK/OPEN) and L0-first \`allocate_cognition\`. **Call count is NOT a sufficient fatigue work unit.**
- Existing \`relay_engine.py\` has \`ProviderCallFacts.prompt_tokens/completion_tokens/total_tokens\` and \`elapsed_ns\` for *returned* attempts. Total tokens (input+output) are a suitable explicitly chosen **virtual work meter** for fully metered calls, not a physical joule or a time conversion. The selected coefficient is an *uncalibrated simulation parameter*.
- S-owned \`self_live_think.py\` / \`s60b1_loopback_adapter.py\` owns \`LoopbackTransportConfig.max_tokens\`, optional single outstanding provider attempt, timeouts and client-local cancellations. S \`BestEffortDisplacement\` / \`L2InterruptionFence\` distinguish logical interruption, backend ACK, GPU release and stale output. **The L model does not mint any of these receipts.**
- P1 #626 is a separate physical Body Fatigue, driven by World WAIT/MOVE/FIGHT; L does not read Body WAIT or regenerate Energy.

## Minimal physics / timebase

\`F_c \in [0,1]\`; OFF by default. With positive total-token deltas (same work ID, cumulative meter), \`F' = min(1, F + delta_tokens * charge_per_total_token)\`. On an independently source-attested non-L2 monotonic host interval \`[from_ns, to_ns]\`, with **no active in-flight backend**, \`F' = max(0, F - (to_ns-from_ns)/1e9 * recovery_per_idle_s)\`. **Time while L2 remains active is never also idle.** No World tick, Minecraft hunger/exhaustion or elapsed World/host rate conversion. Time between two receipts is not implicitly free recovery.

The default coefficients (0.002 per total token and 0.02 per attested idle second) are not calibrated constants. Replace under versioned, SHA-identified profile; do not interpret as biological equivalence. Mode options: OFF, FIXED, LINEAR, NONLINEAR. FIXED is an output-budget comparator while the meter remains distinct. For LINEAR the token-budget fraction scales with F; NONLINEAR is flat until a knee then falls exponentially; never increases the S-provided \`requested_max_tokens\`. Hard block at \`F>=block_at\`; stay blocked until \`F<resume_below\`. L0 and Action authorization are entirely outside this module, regardless of mode/block.

## Receipt and security boundary

- State: unique session, profile SHA, revision/last monotonic ns, chained event SHA, state SHA, used work IDs, cumulative metered token counter, active work. No built-in reset/retry path.
- \`L2Start\`: S-originated admission **claim** matching the calculated token cap; does not start the provider.
- \`L2Usage\`: cumulative **reported total token** meter for one L2 work. PROGRESS keeps the work active; COMPLETED must be a real natural backend terminal result; STOP_ACK must mean independent backend-stop acknowledgement **plus terminal usage attestation**. These names/hashes are structural pointers only: this offline model cannot independently authenticate a runtime/LLM receipt.
- On cancellation, timeout, failure, unknown usage, or mere client cancellation, do **not** issue a fabricated terminal receipt. Keep the model active, retain already metered work, refuse subsequent L2 starts and idle recovery until the owner supplies qualified terminal evidence. Existing S/R owner must provide provenance, final partial-use meter and stop ACK, or record unresolved cost as UNDETERMINED.
- \`NonL2Interval\`: explicit S/R clock/idle attestation only, independent of physical MOVE/WAIT. Reject replayed/out-of-order revisions, foreign sessions, non-finite data, timestamp overlap and mismatched profile/state hashes.
- A SHA makes tampering detectable relative to a trusted anchor; it is **not external authenticity**. The S/runtime integration must persist state atomically, pin the last digest outside Self control, and prevent fresh genesis on the same session as a free fatigue reset. A new session cannot inherit/reset historical F_c without an explicit trusted continuity rule. Without such a ledger, **live admission remains blocked**.

## Intended S integration contract — not implemented here

1. Before S's actual L2 transport request, call \`budget_for_l2(profile, state, S_base_max_tokens)\`. Apply \`L2Budget.max_output_tokens\` to the real transport payload and validate its echo; never issue a request if \`admitted=False\`. This function never changes L0/L1 or allows an Action.
2. Link \`L2Start\` to actual S60-B1 \`NEW_REQUEST_STARTED\` and request identity. Link returned provider usage facts to \`L2Usage\` (meter and runtime evidence independent). An L2 interrupted without a terminal usage meter remains unresolved.
3. Only after actual backend inactivity (not just local client cancellation), S/R may attest a non-L2 host interval; Body WAIT is neither necessary nor sufficient. S must provide a durable state checkpoint across process restarts.
4. The evaluator retains true F_c and compute costs separately. Optional \`sensory_projection(...,enabled=True)\` shares only a coarse category; no true F_c/World future leakage.

### Development comparison and status

OFF / FIXED / LINEAR / NONLINEAR deterministic pure comparisons and negative controls: \`tests/test_cognitive_fatigue.py\`. This is **not** a live behavioral comparison, scientific evidence, or confirmation of efficacy. Without qualified token usage from interrupted L2, neither partial-token accounting completeness nor live cancellation re-admission is demonstrated. S/R must wire the gate and measured source receipts; M/P1 must remain physically separate; V #619 must preregister cheap/constant budget controls and assess actual World outcomes.

**No hidden goals:** F_c does not select WAIT, induce a will to rest, create Energy, alter L0 safety or grant an Action.
