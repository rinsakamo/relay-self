# R2-3e — Original first-reJOIN Question one-shot issuer and per-Self failure fence

**Stacked parent:** R2-3d Draft #1140 exact HEAD
`13dbf4a1253a3dc3eb2fac873a84f8ed3dcd6f54`.
Only R-lane opt-in DEV code is added. I/B/C/E, Stage28 first-login
issuer, Original Physical/WAL/Memory persistence and product L1 caller
remain unchanged.

## Goal and scope

R2-3c freezes and registers a genuine Original first A-reJOIN / continuing
B `BoundedChoiceRequest` for **Question ADOPT/HOLD/DECLINE**.
R2-3d can verify that registered Request/Source before submission and read
an already-completed original lane job without authorizing admission.
R2-3e implements the minimal **one-shot actual
`ResidentLlamaInferenceLane.submit` and `await_result`** via the
**existing Original `ResidentCognitiveWorkOwner`**, with failed-submission
and post-submission fences. This is not physical Skill+Target selection.

### Ownership and ordering

1. `ResidentCognitiveWorkOwner.issue_rejoined_original_question_once_dev`
   is the opt-in original Owner entrypoint. It verifies bridge and lane
   ownership; `issue_r23e_original_rejoin_question_once_dev` does not create
   another owner or lane.
2. **Before attempting submission**, hold the same original Resident Owner
   RLock, run R2-3d `preflight_r23d_original_rejoin_cpu`, verify Owner
   identity, Source, current Native/World epoch, frozen Request and backend,
   and synchronously call the original lane's `submit`. No gap in the
   Original Owner's lock between preflight and ticket registration.
   Paper and actual Native events remain external; this is not a perpetual
   source seal, authenticated backend proof or global exclusive process lock.
3. `submit` is attempted **once**, never replayed by this API. An
   exception inside or after attempted submission is ambiguous even if
   it occurred before a ticket was returned.
4. Release the original lock **before** waiting for the model worker.
   Reuse `ResidentLlamaInferenceLane.await_result` with a bounded deadline;
   its `asyncio.shield` does not imply cancellation of the actual
   llama-server call.
5. After actual completed worker and terminal idle witness, under the same
   Original Owner RLock, reuse R2-3d's result readback:
   actual ticket identity, submitted request SHA, candidate IDs,
   Original Owner, both A/B Source and current Schema/Need/Inquiry,
   unchanged Paper/Native/Composite, scope and original slot state.
   Confirm pre-submit vs readback Source and ticket equality.
6. Return a frozen `R23EOriginalRejoinQuestionOutcome`, containing
   **only** the previously submitted, source-qualified Question choice.
   Even an `ADOPT` result is **not committed**: no Question store,
   Memory, Intent, Skill, action port, physical lease or WAL mutation.
7. On **any** error/cancel/timeout after attempting submission, fence
   the original Self's GPU lane and resident cognition under the Original
   RLock (`lane.fence_self` and `resident.fence_self`). The other Self
   remains independently Online. This is a per-Self cognitive admission
   fence, **not** a claim that the backend has stopped generating or
   that the World has been quarantined. Before attempting submit, an
   invalid source/preflight simply HOLDS without poisoning an already
   active caller's job.

### CPU negative controls

Synthetic tests use the real Original Bridge/Owner/lane classes and
first-A-reJOIN/B-continuing Native/Paper fixtures, constructed in
observation-only mode before login. They substitute only the provider
`__call__` and backend idle witness. No real model endpoint, Minecraft
World, Mineflayer or full Paper JVM is launched.

Cases: A/B ADOPT/HOLD/DECLINE, unresolved/foreign choice; same-work
duplicate and simultaneous caller; two different Self work refs on
one serialized lane; foreign Owner/lane/turn, invalid deadline, stale
Paper and Physical mode pre-submit; post-submit Paper/Native/epoch/peer
drift, forged submitted Request, invalid provider type/error, lost
original lane, exception after enqueuing but before returning ticket,
uncertain backend timeout, canceled coroutine during active generation,
tampered terminal readback. Assert no memory/Intent/Question/Physical/WAL
writes, exact single job after each submitted attempt and per-Self
fencing without implicit peer quarantine.

## Deliberate HOLD and next step

This adds a **callable live-capable original lane issuer API**, but it is
not wired into the product L1 selector and was only tested with synthetic
provider and Source. R2-3e does not attest actual Gemma POST,
`/slots` on a real running server, 3Self product input migration,
Question ADOPT persistence, physical Skill+Target decisions, actual
World/Paper/Node or full model-lifetime retirement after timeout.
No new issuer capability for I/B/Physical is assumed.

**CI target:** full pytest, Ruff, repository contracts, Mineflayer adapter,
Paper witness on exact R2-3e HEAD.
Allowed on success only:
`R2_3E_ORIGINAL_REJOIN_QUESTION_ONE_SHOT_SYNTHETIC_CPU_DEV_PASS`.
Remain:
`R2_3E_REAL_WORLD_GEMMA_NOT_RUN`,
`R2_3_PRODUCT_L1_SWITCH_HOLD`,
`QUAL_NO_GO`, `SCIENCE_NOT_RUN`.
