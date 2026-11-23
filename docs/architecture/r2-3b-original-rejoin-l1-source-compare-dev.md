# R2-3b — first reJOIN Original Owner Inquiry ↔ 3Self CURRENT (CPU DEV)

**Disposition:** Original post-reJOIN L1 BoundedChoiceRequest **not implemented/registered**
in this source family. This stage implements **only read-only Source/Need/Inquiry
compatibility**, not the requested full candidate/Skill/Target/request comparison.
Do **not** label it `R2_3B_ORIGINAL_REJOIN_L1_CONTEXT_COMPARE_CPU_DEV_PASS`.

## Pinned source audit

- Parent R2-3a Draft #1137 exact HEAD `062324d4f24b662458b280b64ecd431d0e254ff9`.
- Prior Original I U31 Draft #1124 `d3034026a8eea3d2d4927527f5bc0d6ad0455457`,
  Q-audited separately; this R stage does not re-audit archived World bytes.
- `ResidentCognitiveWorkOwner.read_present_cpu` dispatches first-reJOIN to
  `build_rejoined_owner_present`; `read_coverage_inquiry_cpu` uses
  `_build_inquiry` on that same source; `poll_normal_present_cpu` reads
  both A and B from one pre-bound original `_RejoinSourceCut` and rechecks
  Native/Paper/Composite and Source revision.
- The first-reJOIN normal scheduler and normal World runner in
  `b_np1b_normal_present_scheduler_dev.py` and
  `b_np1b_normal_cpu_world_runner_dev.py` only sample original Present;
  neither registers nor sends L1 work.
- The existing request issuer `prepare_coverage_adoption_turn`, invoked by
  `prepare_i_unified_exploration_turn`, takes Stage28 `boot/world/links`,
  creates a `BoundedChoiceRequest` with `CHOICES` and registers it in
  `_coverage_adoption_turns`. Its `_freeze_hash` and validators use
  Stage28 source inputs. **It is not the reJOIN inquiry issuer**.
- `stage28c2c_fresh_recovered_l1_dev.py` and
  `resident_l1_move_options_dev.py` are separate Stage28/Stage24 request
  paths, **not** evidence for registered first-reJOIN L1 candidate/Skill/Target
  bindings. U31 B S1→S2 is a different Original B physical/LLM sequence, not
  the A reJOIN / B continuing paired CPU path.

## Minimum Original Owner seam

`ResidentCognitiveWorkOwner.read_rejoined_l1_source_compatibility_cpu`
is opt-in, add-only and uses the same original resident lock. It requires
the **pre-existing** first-reJOIN `_normal_rejoin_source_cut`, calls the
**existing** original paired `poll_normal_present_cpu` (A+B), and reads
the existing R2-3a tri-source Context for the selected Self. It compares:

- Original A or B Owner object, resident/native/world epochs and A/B shared
  Composite/Paper cut; A's new Native and B's uninterrupted Native.
- The original Schema snapshot/revision, CURRENT qualified signals, Need
  reference, Attention references and Source triplet.
- The original bounded coverage Inquiry's Question ref/provenance, Need,
  world/branch/epoch and Source revisions.
- The unchanged original Owner Intent event history and retained reference,
  followed by independent Original paired CPU source re-poll and original
  tri-source liveness check.

The immutable `R23BOriginalL1SourceComparison` explicitly has **no**
`original_l1_request_id` or `original_choice_ids`, and has
`l1_request_registered=False`. Those are deliberately **absence markers**,
not a newly generated empty candidate set. The report cannot be used as an
L1 admission, candidate set, GPU ticket, Question/Intent adoption, Memory
grant or physical authorization. Unknown/missing Inquiry, old/foreign/changed
Source or second reJOIN => HOLD. Cached comparisons must be re-read through
`r23b_original_rejoin_inquiry_is_live`.

This code does **not** register a new L1 request, build a prompt, modify
the Stage28 `CHOICES`, access GPU, start Native/Paper/World, change
`Schema CURRENT` epistemic status, write Memory, or issue actions/WAL.

## Unclosed boundaries

To earn the exact `R2_3B_ORIGINAL_REJOIN_L1_CONTEXT_COMPARE_CPU_DEV_PASS`
criterion, a future **Original Owner-owned first-reJOIN** CPU L1 request must
actually exist, be frozen/registered with candidate IDs and prebound
Skill/Target, Need, Question, Schema and Source triplet, and be revalidated
before and after its existing inference fence. This stage does **not**
manufacture that request or grant runtime L1 input migration. The second
A reJOIN is a separate verifier/epoch family and is intentionally HOLD.

**Status:** `R2_3B_ORIGINAL_REJOIN_SOURCE_INQUIRY_CPU_COMPATIBILITY_DEV_PENDING`
(subject to exact-head focused/all pytest, Ruff, contracts and witness CI).
`R2_3B_ORIGINAL_REJOIN_L1_CONTEXT_COMPARE_HOLD` /
`R2_3_PRODUCT_L1_SWITCH_HOLD` / `QUAL_NO_GO` / `SCIENCE_NOT_RUN`.
