# R2-3f — Original first-reJOIN Question ADOPT persistence (DEV)

**Parent:** R2-3e Draft #1141 exact base `53a4ffa9b5768ef158af9b4f228a876d4e82f7a6`.
This is an **opt-in original Owner** Question-adjudication path.
No new Owner, GPU lane, World/Physical executor, skill selector,
cognition file format or schema projection is created.

## Contract

The original R2-3c first-A-reJOIN/B-continuing `R23CFrozenOriginalRejoinL1`
is a **Question ADOPT/HOLD/DECLINE** choice, **not** a prebound physical
Skill + Target selection. R2-3e issues it exactly once using the
original Resident GPU lane, and R2-3d performs Source preflight/result
readback. R2-3f permits the original Owner to consume that result and
persist **only the OPEN Question**, not a memory episode, Intent, Skill or
physical Action.

### Existing Original Owner custody

The R2-3e issuer adds its exact immutable outcome to a **weak, in-process**
`ResidentCognitiveWorkOwner._rejoin_question_outcomes` registry, keyed by
the already-registered R2-3c work ref, while holding that **same** original
Resident lock. The original R2-3e result type can be weakly referenced.
This is **not a durable signature, second owner, database, replay record,
or authentication of an external provider**. A caller copying/replacing
an issuer outcome, changing a provider choice, or supplying a receipt
from a directly submitted lane job cannot pass the original weak
producer-identity check. The registry disappears with the original
resident lifetime; old scopes and source are rechecked on every commit.

The Original Owner exposes
`commit_rejoined_original_question_dev(bridge,lane,turn,outcome)` and
an opt-in one-call
`issue_and_commit_rejoined_original_question_dev(...)`.
Neither is wired into the product L1 loop.

### ADOPT: exactly one original persistence transaction

- Hold **existing** Original Resident and lane locks.
- Require exact Original Owner/Bridge/lane, registered frozen work ref
  **and** weakly registered producer outcome identity. Require the
  **same exact** issued ticket object in the actual lane job.
- Require `job.question_adoption_state == unused`, no previous
  Question consumption or memory adoption.
- Call the original R2-3d `read_r23d_original_rejoin_result_cpu` to
  requalify full Native/Paper/Composite/3Self/Schema/Need/Inquiry,
  owner/cohort scopes, prior ticket, actual submitted request SHA,
  terminal idle, model result and the full readback equality.
- Only a **resolved** `ADOPT` (choice `1`) enters the existing
  `bd1b_question_store_dev._store_current_inquiry` path. Reuse the
  **existing** Stage28 `question_adoption_binding` and
  `question_adoption_state` (mark committing, then committed/failed).
  Verify current source, result and that binding **before** storage and
  **after** the disk readback. Persist one `QuestionRecord` with
  traceable `Provenance`, then update Original retained cognition and
  pending Question set **only on successful disk revalidation**.
- Duplicate Question, repeated commit, changed Source, concurrent
  original Owner, altered request/provider result, missing disk,
  read/write failure and post-save Source drift **never become a
  second successful adoption**. An eligible but invalid genuine
  submitted result becomes `failed` and fences only its Self's
  resident cognition and GPU lane.
- `HOLD`, `DECLINE` or `UNRESOLVED`: no Question, disk, Memory,
  Intent, Skill, WAL or Physical change. Re-reading that terminal
  job can return the same non-adoption decision but cannot resubmit
  the same work ref.

**Crash limitation:** The Original Question store is still the
existing file-based, revalidation-after-write mechanism. If a
post-save check fails, the file may contain new bytes while
`owner.retained` retains the prior object. The API **does not**
claim rollback or full transactional crash durability; it quarantines
the affected Self and requires a separate recovery qualification.

### Original B checkpoint prerequisite

The imported A-first-reJOIN/B-continuing CPU fixture does not always
create a **canonical B `cognition.json`**. The existing original
`_store_current_inquiry` must **refuse** to create a missing file,
rather than silently fabricating a recovered checkpoint. A positive
synthetic B ADOPT test therefore creates a matching, canonical initial
B cognition checkpoint as part of test setup **before original GPU
submission**, and verifies its exact readback. A separate explicit
negative B case leaves that file absent: it must HOLD, fence B, keep
A online and **not** write a new cognition file. The production
Question writer is not changed.

### CPU synthetic tests

Original Owner/Bridge/Resident GPU lane classes, original A-first-reJOIN
and continuing B Native/Paper fixtures with the physical gate
observation-only **from construction**, synthetic provider responses.
No live World, Gemma, real `/slots`, physical issuing or prompt
migration.

Positive A/B ADOPT disk readback/one Question, one-call issuance &
commit, HOLD/DECLINE/UNRESOLVED no write, forged/replaced receipt or
foreign turn, directly submitted job without R2-3e issuer, duplicate
and racing commits, Paper/Native/other-Self epoch/source/schema/
Intent/registration drift, physical observation-only loss, provider
request changes, missing disk, simulated disk failure and post-save
Source change; assert original job consumption, no unauthorized
physical/memory writes and per-Self fencing.

## Status

On exact-HEAD full CI success only:
`R2_3F_ORIGINAL_REJOIN_QUESTION_ADOPTION_SYNTHETIC_CPU_DEV_PASS`.
Keep `R2_3F_REAL_WORLD_GEMMA_NOT_RUN`,
`R2_3_PRODUCT_L1_SWITCH_HOLD`, `QUAL_NO_GO`,
`SCIENCE_NOT_RUN`.
A following stage must independently qualify real model and World
authority; this stage does not imply product L1 routing.
