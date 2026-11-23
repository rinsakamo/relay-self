# R2-3h — Q-audited R2-3g → real Original first-reJOIN Gemma seam (opt-in DEV)

**Pinned parent:** [R2-3g Draft #1145](https://github.com/rinsakamo/relay-self/pull/1145)
exact `2deb27e7bb92529c9efbe447d39523c47d965c30`.
Independent [Q audit #1146](https://github.com/rinsakamo/relay-self/pull/1146)
exact `f77284c3590101854ef6d2bbd8776f7be20835e1` verified
Question-only GPU ticket purpose prevents generic Memory adoption.
Both were synthetic CPU and remain **Draft/unmerged**.

## Scope and original ownership

This stage adds a **live-capable opt-in seam**,
`experiments/r2_3h_original_rejoin_real_question_dev.py`, for an
**already running original** `OwnedResidentPhysicalBridge` with genuine
**first A reJOIN / continuing B** native and Paper source cut.
It does **not** create or restore the World. It does **not** substitute
Stage28c2c's fresh A+B restored-login run for an A-logout/reJOIN.
The existing Original Owner and Resident GPU lane are reused.
No new Owner, scheduler, memory path, physical action or World authority.

- `inspect_r23h_original_live_source` independently rereads the
  already registered original paired CURRENT + inquiry twice under
  the original Resident lock. Requires both original A/B active,
  observation-only Physical mode, no issued Action, **no GPU lane**,
  same actual Original Owner/Native/World scopes, source pair revision,
  and no unqualified second reJOIN. No model/network endpoint used.
- `inspect_r23h_original_real_model` calls the **existing**
  `verify_stage24g_model_gate` for actual pinned GGUF SHA256,
  same operator-owned llama-server PID and mapped model, PID-owned
  loopback socket, GPU occupancy/model catalog and the single
  **idle** slot; must still have the original source after checks.
  It is a read-only preflight.
- The single-execution path requires
  `real_model_post_grant=True`, bounded wait <=75s, entirely
  new evidence root **outside original Paper/Owner folders**,
  and current original source. It freezes a real registered
  `R23CFrozenOriginalRejoinL1` BEFORE GPU lane attachment.
  It then attaches one real `ResidentLlamaInferenceLane` through
  the **unchanged** Original Bridge observation-only attachment gate.
- Reuses `OriginalRawBoundedLlamaProvider` from Stage28c2c,
  which captures the **exact HTTP entity-body bytes** for request
  and response (not wire headers) plus status/hash/size receipt.
  Original R2-3e issuer submits exactly one bounded Question request
  with R2-3g `purpose='original_rejoin_question'`,
  rechecks terminal idle and revalidates A/B original context.
  **No Question adoption** in R2-3h, even if Gemma chooses ADOPT.
- On source drift, HTTP failure, timeout, wrong result, or other
  submitted-work ambiguity: **HOLD**, per-Self original GPU/cognition
  fence, no automatic retry, no fake Paper/Native readback, no
  claimed backend cancellation, no physical/quarantine inference.
  The caller must use existing Bridge logout/retirement and
  separately audit raw evidence. A written local manifest is
  **not itself independent provenance authentication**.

**Important live limitation:** actual Paper/native source can
advance while model tokens are generated. R2-3e's strict frozen
source contract must reject a changed cut rather than silently
relabel it as the same observation; a real trial may therefore
legitimately HOLD and reveal a future Source freshness policy
requirement. We do **not** weaken the acceptance condition or
invent a stable live World clock.

## Access and execution boundary

This file intentionally does **not** expose a standalone
`--execute-once` CLI that invents its own World or a new Original
Owner. A separate owner-controlled runner must first produce and
hold an *actually qualified* first-A-reJOIN/B-continuing Original
Bridge, then call `inspect_r23h_original_real_model` and, only
when explicitly permitted, `run_r23h_original_real_question_once`.
The Stage28c2b/28c2c restored-A+B run is NOT that producer.
The returned receipt is **independent-source-audit pending**,
not a live-qualified passing result.

## CPU tests and qualifications

Tests in `tests/test_r2_3h_original_rejoin_real_question_dev.py`
reuse existing R2-3g Original Owner, Native/Paper and Bridge fixtures
with observation-only Physical mode. They fake only model gate,
idle socket and HTTP endpoint. They check:
A/B source read-only, gate rejection, missing grant, reused/overlapping
evidence, missing/changed reJOIN, Paper/Native/peer epoch drift,
physical mode loss, real-provider-style exact single raw POST,
ADOPT/HOLD/DECLINE without memory/Question/Physical writes,
source mutation during HTTP, bad HTTP status, bounded report and
original per-Self fences.

**Only after exact-head full CI:** 
`R2_3H_REAL_MODEL_SEAM_SYNTHETIC_CPU_DEV_PASS`.
Actual owned World process, actual PID/GPU checks, real Gemma HTTP,
independent raw evidence audit, product L1 input migration and
Skill+Target physical choice still **NOT RUN / HOLD**.
Keep `R2_3_PRODUCT_L1_SWITCH_HOLD / QUAL_NO_GO / SCIENCE_NOT_RUN`.
