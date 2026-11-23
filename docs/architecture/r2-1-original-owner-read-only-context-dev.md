# R2-1 — One Original Resident Owner read-only Context entrypoint

**Scope:** opt-in CPU DEV only. `R2_2_HOLD / R2_3_HOLD / QUAL_NO_GO /
SCIENCE_NOT_RUN`. No real World, model call, physical issuer, or product
L1 input switch.

## Anchors

- I U31 `d3034026a8eea3d2d4927527f5bc0d6ad0455457` retains its bounded
  original S1→Owner redecision→S2 Native/Paper/WAL execution history.
- R1 `06349c7a216b042511a90e05ad0196f4a7164378` owns the **read-only**
  Stage28 initial login Shadow with original persisted Owner provenance.
- R2-0 `a8d1492a1e54f3f647109da183cf71179c7b5932` extracted the one
  pure nine-field legacy Present-versus-Schema CURRENT comparison.
- Independent Q R2-0 CPU+Git [Draft #1132](https://github.com/rinsakamo/relay-self/pull/1132):
  27/27 CPU and real pinned R1/R2-0 Git checks PASS. No Q approval is
  inherited automatically for newly changed R2-1 source.

## Owner API

`ResidentCognitiveWorkOwner.read_context_shadow_cpu(bridge, self_id,
boot, world, links, memory_ids=(), recent_limit=8)` is an **opt-in read
method on the existing resident gate for the same original
CheckpointedCognitiveOwner**. It creates no new Owner, state, Memory
writer, Schema registry, listener, L1 job, model result or physical token.

- Reuse the **existing resident RLock** and the bridge's exact original
  Owner pointer; reject absent, foreign, swapped or retired Self.
- Call the existing R1 `compare_original_owner_r1_shadow` with the
  unchanged first-login Stage28 source and existing canonical persisted
  cognition, already retained accepted subjective Questions, Schema CURRENT
  and old Memory digest pointers. Do not create a second Context store.
- Refuse `HOLD` and `MISMATCH`. Reuse `r1_shadow_is_live` under the same
  existing lock before returning even a `MATCH`, because Native/Paper
  observations and original Owner Question records may have changed.
- **Return the existing immutable R1ShadowComparison**, not a new
  admission ticket or a bare cached `CognitiveContext` stripped of
  original owner Question/Memory freshness semantics. A subsequent
  consumer must re-run the existing R1 freshness validator before
  relying on its ephemeral Context, because Paper advances outside
  the Python lock.
- Original `read_present_cpu`, `read_coverage_inquiry_cpu`, L1/GPUs,
  Intent/Skill issuer, Memory persistence, Native/Paper/STOP/WAL paths
  are byte-identical to R2-0 **except for adding this opt-in method to the
  existing resident Owner class**. No caller in the original product
  L1 path is switched to this method.

## Independent qualifications

R2-1 adds A/B read-only/no-write tests, exact original Owner pointer
identity, Memory REMEMBERED/UNKNOWN digest-only retrieval, corrupted
original cognition/missing memory/invalid selector refusal, foreign
Self/resident/Paper/boot/epoch refusal and a source-drift-mid-read race.
Full exact-head pytest, Ruff, repository contracts, Mineflayer and
Paper witness must pass.

This stage is a **read API attachment** to the one Original Owner; R2-2
will independently compare possible candidate L1 Context inputs before
any selection change. R2-3 production input routing requires a distinct
authorization and Q review; R2-1 itself is not an authorization.

`R2_1_OWNER_CONTEXT_READ_CPU_DEV_PENDING / Q_R2_1_INDEPENDENT_REVIEW_PENDING /
R2_2_HOLD / R2_3_HOLD / QUAL_NO_GO / SCIENCE_NOT_RUN`.
