# Cognitive Architecture v0.1 / 05 — CPU/GPU Runtime & Preemption Contract

> Frozen architecture parent [#828](https://github.com/rinsakamo/relay-self/issues/828), child [#837](https://github.com/rinsakamo/relay-self/issues/837). Stack: [Common I/O #830](https://github.com/rinsakamo/relay-self/pull/830) → [Innate Schema #832](https://github.com/rinsakamo/relay-self/pull/832) → [3Self / Present #834](https://github.com/rinsakamo/relay-self/pull/834) → [CPU Task/Profile #836](https://github.com/rinsakamo/relay-self/pull/836).
>
> **DRAFT / PURE OFFLINE OWNER RECEIPT VALIDATION / NOT AN ACTUAL STOP, GPU RESOURCE OWNER OR L1 EXECUTOR / DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN.**
>
> No real llama.cpp/Gemma request, Minecraft World/Action, real GPU synchronization, new source attestation or physics qualifications are claimed.

## 1. Reuse audit and non-negotiable authority

The **new implementation in `src/relay_self/preemption_contract.py` reuses** the original #830 `PreemptionTrace.append` five-state ordering, `result_is_current` L2 output gate, `CognitiveTask`, `ProfileDecision` and `Profile`. It consumes **#836 `ProfileRoute`** where a waiting finite-choice L1 was legitimately DEFERRED with `L2_PREEMPTION_REQUIRED`; this is a **preemption hint, not an L1 resource grant**.

`main:src/relay_self/runtime_coordination.py` already owns the minimal decision-epoch coordination around the **ActionSupervisor**; it is not a GPU scheduler. `main:adapters/llama_cpp/relay_engine.py` makes synchronous HTTP requests with a timeout, and at this audited HEAD provides **no trusted method to prove that an aborted HTTP call terminated backend generation, stopped its worker, evicted its KV/cache or freed enough VRAM**. The presence of a timeout/cancel/HTTP disconnect alone is not enough. Backend/request/slot ownership must be established at integration. The existing S49/Intent/Skill/Action physical issuer remains untouched.

#634 SelfBody/SelfWorld and #718 Unified v0.5 are separate unmerged Drafts. They are not evidence of deployed runtime integration. No new Goal, Question, Memory, Action, hardware scheduler or LLM inference owner is established here.

## 2. Exact five-stage state machine

```text
Existing resource owner: L2 lease(gpu, backend, task, generation)
      + L1 SELECT_FINITE CPU route = DEFER / L2_PREEMPTION_REQUIRED
      |
      v
(1) CANCEL_REQUESTED    <-- immediate old-generation result fence, even if
      |                      backend is still running / request still connected
      v
(2) OUTPUT_FENCED       <-- result-admission owner records exact L2 generation
      |                      rejected; no late output can be adopted or written
      v
(3) BACKEND_STOPPED     <-- actual backend owner observed generation stopped,
      |                      exact instance+lease, no active request of that target
      v
(4) RESOURCE_RELEASED   <-- GPU owner observed old lease inactive, slot FREE,
      |                      available VRAM >= fresh L1 requirement
      v
       Revalidate L1 Task/Profile route against current owner, source,
       generation, deadline, and owner resource revision.
      |
      v
(5) L1_ADMITTED         <-- **separate existing resource-owner-issued new lease**
                             bound to this L1 task/generation
```

Any missing, stale, foreign, out-of-order or negative witness leaves L1 **not admitted**. It must not be rescued by retries, a partial L2 output or a guessed availability. L0 native CPU `FastCue` remains separately qualified and does **not** depend on GPU cancellation, LLM, Present/Memory or log flushing; physical Action must still go through existing S49 authorization.

#830 `PreemptionTrace.output_fenced` becomes true on the first `CANCEL_REQUESTED` event to **deny output immediately**, even before the explicit separate acknowledgement in phase 2. Thus phase 2 cannot re-enable previously barred model text. A cancelled L2 task's Question/Goal/Intent references are held by their prior semantic owners and do **not** disappear when the compute generation is cancelled.

## 3. Type and source/authority matrix

| Type/value | Required | Owner and trust boundary | Failure case |
| --- | --- | --- | --- |
| `L2ComputeLease` | Self/world scope, L2 task and exact generation, lease ID, backend instance, GPU ID, resource owner ID, owner revision, issue timestamp, `Provenance` | Existing GPU resource owner must supply and authenticate actual L2 lease; pure value is not a permission token | Other World/Self, old generation, new backend instance, stale lease |
| `L2PreemptionReview` | Original #830 trace + exact L2 lease + waiting L1 #836 DEFER route + L1 VRAM requirement + owner epoch/ref | Immutable review record, **not a second scheduler** | Wrong task/source/resource version or L1 deadline → refuse request |
| `OutputFenceReceipt` | target lease, task/generation, result-admission owner, rejected_generation, host monotonic time, verification ref, provenance | Trusted result owner confirms its admission gate rejects cancelled output; **request already fences old generation** | False/foreign/stale receipt; no reuse of partial model output |
| `BackendStopReceipt` | exact lease/task/generation/backend instance, stopped_confirmed, active_request_count=0, time, source and verification ref | Backend adapter **must independently demonstrate real generation stop**. Transport cancelled is additional observation, never sufficient | HTTP disconnect only; ACK without stopped worker; foreign process or prior generation |
| `ResourceReleaseReceipt` | same GPU/lease/resource owner and scope, revision strictly newer than preemption lease, gpu_state=FREE, old lease inactive, available VRAM, monotonic time/expiry | Existing **resource owner** must independently measure/request-serialize GPU slot+memory; the CPU helper can only cross-check record fields | GPU state UNKNOWN/BUSY, lease still active, insufficient VRAM, old/expired/foreign reading |
| `L1ComputeGrantReceipt` | new distinct L1 lease, exact L1 task/generation/scope, same owner, *release revision*, time, grant_confirmed, provenance | **Only the existing resource owner can atomically grant** a GPU lease; this module verifies a supplied receipt, it cannot perform admission | No owner-granted lease, replay, mismatched generation, stale source/epoch/deadline, reused L2 lease |
| `PreemptionPending` | reason STOP_TIMEOUT / RELEASE_UNVERIFIED / OWNER_UNAVAILABLE / L1_DEADLINE_EXPIRED; time, provenance | Can be appended by caller to existing Log/audit; no implicit retries or releases | Recording a timeout never proves a stop or frees VRAM |

Implemented stages use pure functions `request_l2_preemption`, `confirm_output_fence`, `confirm_backend_stopped`, `confirm_resource_released`, `confirm_l1_compute_grant`; each returns a **new immutable review** (no hardware effects), invoking `PreemptionTrace.append` for ordering and clock monotonicity. `l2_result_is_admissible` calls **existing** #830 `result_is_current`. `note_preemption_pending` leaves the L2 output permanently barred for that attempt.

The source references and owner identity strings in these types are **not cryptographic attestations**. A dishonest caller can forge all fields; actual integration must bind receipts to authenticated transport/process handles and an authoritative resource-owner lease ledger. A `GPUState.FREE` value cannot be trusted simply because it is type-correct. The protocol validates *consistency conditional on truthful authority input*, not authenticity or physics. Replayed receipts across different reconstructed sessions must be prevented by owner-ledger uniqueness/CAS and persisted event IDs, **not by this pure dataclass alone**.

## 4. Operational integration requirements (not implemented here)

### Backend owner: stop identity and lifecycle
- Allocate an opaque backend process-instance ID and unique active request/generation handle. Record the exact binding of L2 task+generation to backend request and GPU lease on **actual compute admission**.
- On `CANCEL_REQUESTED`, immediately advance the **result owner** fence so late replies are forever rejected. Deliver cancellation to the backend using a supported verified mechanism. Closing the HTTP connection only does not prove the generation stopped.
- Observe the backend request/worker status with a documented protocol (stop ACK, process/slot state, cancellation applied to active request). Confirm **exact matching request** inactive; a later new L2 request or a stale stop ACK does not qualify.
- If the provider has no trustworthy per-request cancellation and stop observation, terminate/restart the owned backend only if explicitly authorized by its owner and then *independently verify* process death, remaining sessions/slots, and resource state. The pure contract cannot force kill or infer exit.
- L2 task generation becomes unusable after a cancellation; retry creates a **new CognitiveTask generation** only when the existing Self owner decides; never restore partial text as accepted understanding or Memory.

### GPU resource owner: release and fresh L1 admission
- The canonical owner tracks GPU identity, active lease ID, backend process/slot, GPU free/occupied status, memory measurements and a **monotonic owner revision/epoch**. A restart invalidates old grants, even if the same string IDs are reused.
- After backend stop, separately confirm old lease no longer active, GPU slot can admit new work and enough *measured or conservatively reserved* VRAM exists for L1. A stopped request does **not** imply free VRAM if L2 weights/KV remain in memory; model residency and model-switch cost must be accounted for.
- Obtain **fresh** Present/Question/Goal/Intent owner readout, task generation, source and resource snapshot. Re-run #836 route under current deadline/Context/VRAM. Positive `ProfileRoute.resource_admission=PENDING` is still not an actual grant.
- Atomically grant L1 under the same resource owner revision (compare-and-swap), create a **different** L1 lease ID and bind it to the right Self/session/task/generation. The next decision step/executor may use that real grant; this module only checks receipt shape and lineage.
- Deduplicate grant IDs and revocations across crashes and concurrent clients. Owner must not race with other GPU users between release observation and granting. A synthetic free readout is not admission.

### CPU L0 and Action
- L0 FastCue/installed CPU rule can proceed while GPU is blocked, because it does not consult the slow branch. S49 physical Action issuance remains separate and may still deny the action.
- L1 and L2 are **compute profiles**, not motor/action profiles; no compute grant confers permission to EAT/ATTACK/MOVE.
- Append trace to existing audit/log without requiring L0 to await durable flush. Failure to commit durable log may constrain later scientific claims, but never fabricate a successful preemption.

## 5. Deterministic offline test/negative control matrix

| Scenario | Expected |
| --- | --- |
| PRE-01 Complete chain | Five stages in exact order, with separate fence, backend, GPU and grant receipts; only last stage reports L1 admitted |
| PRE-02 Immediate fence | Late L2 result rejected from CANCEL_REQUESTED, before backend stop, after final L1 grant and with wrong generation |
| PRE-03 Request binding | Reject non-L1, wrong DEFER reason, wrong backend target, wrong World/Self, stale L1/L2 generation or source, stale resource revision, expired L1 deadline |
| PRE-04 Fence identity | Reject foreign lease/task/result owner, wrong generation or non-rejecting output gate |
| PRE-05 Backend | Reject HTTP-only cancellation, negative stop ACK, active request count >0, foreign instance, out-of-order stop or timestamp regression |
| PRE-06 GPU release | Reject release before stop, GPU UNKNOWN/BUSY, old lease still active, old revision, wrong owner/GPU/session/Self, insufficient VRAM, expiry or clock regression |
| PRE-07 Grant | Reject no independent new L1 lease, stale L1 generation/source, unrefreshed/DEFER route, mismatched release revision/owner, expired deadline, grant after admission or duplicate |
| PRE-08 Pending | Stop timeout/release uncertainty remains pending and L2 output remains fenced; no forced stop/phantom memory update |
| PRE-09 L0 and Self | CPU L0 independent of preemption; original Self Intent and Question/Goal refs unchanged by compute cancellation |

All PRE cases use **synthetic owner statements** and deterministic CPU Python, not a real scheduler. Passing them does **not** prove actual stop/release, emergency latency, successful self-directed L1 or autonomous Learning.

## 6. Immediate next dependencies

- **#828/06 Learning/Crystallization:** retained Question after interruption, source-bound event logs and future hypothesis about better circumstances for L2; require qualified C1 outcome and owner-governed C2 before storing learned rules. A timed-out stop is not a learned relation.
- **#828/07 Reference Action/Embodiment:** resource-granted cognition still cannot bypass existing S49 Action/Skill/Intent path; body capability checks remain World/WorldBody owned.
- **#828/08 Integration:** audit real llama.cpp/Gemma backend generation handles, cancellation control and VRAM resident model behavior; select or implement actual owner-authorized stop/release attestation; test hardware contention separately under DEV grant. Until then, `BackendStopReceipt`/`ResourceReleaseReceipt`/grant are **untrusted fixtures**.
- **#828/04 and #828/03 Owner integration:** result source, Present validity and resource readouts need actual owner currentness. Do not construct source/owner values from end-user/LLM text.

**Final verdict for this child:** Typed preemption/stop/release/grant sequence + fail-closed offline tests only. Production owner service, real cancellation, physical World and SCIENCE remain OPEN.
