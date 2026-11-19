# C Lane — Stage27 ↔ Stage28 same-World original source preflight (DEV)

This read-only CLI is a **preflight gate**, not a launcher or an independent
physical/native causal audit. It creates no World, does not request Gemma,
does not mutate the Self's Memory, and never replays an Action or Skill.

## Why the existing real runners cannot be spliced together

- Stage27h/i's original source result **deliberately records**
  `stage27h_self_a_skill_state="started"` and
  `stage27h_skill_success=false`. It issues bounded MOVE Actions but returns
  before a subsequent **Self-owned terminal Skill evaluation and C1 adoption**.
  An Action OUTCOME or geometrical Target observation does not suffice.
- The Stage27 parent result's `committed_generation` is the **pre-action**
  typed Stage25 preset cut. It cannot be relabeled as a post-action C1 cut.
- The Stage28c2b existing real runner
  `experiments/stage28c2b_real_recovered_rejoin_dev.py` pins its original
  source World UUID to `f9221410-b99e-417d-98f4-e98938586472` and fork to
  `fork-3883122c-6edb-4017-bd82-00fc4324aded`. A new Stage27 isolated
  World UUID must **never** be silently substituted into that runner.
  A proper future Stage28 source needs the exact **new Stage27 World**, a
  **new post-action** full original World+A/B typed COMMITTED generation,
  and its own separately validated native/Paper lineage.
- The Stage27/Stage28 branches have an actual shared WAL grammar difference:
  Stage27 adds `MOVE_PLACE` v2; Stage28 adds terminal
  `NATIVE_MOVE_NO_NET_DISPLACEMENT` for original relative MOVE.
  Reconciliation has been tested in integration-only Draft #1016, not yet
  incorporated into the two original production branches.

## Usage

Run from a local working tree containing integration-only Draft #1016 plus
this slice, **after** original source files exist:

```bash
PYTHONPATH=src:. python -m relay_self.c_lane_stage27_real_source_preflight_dev \
  --stage27-report /absolute/original-stage27-evidence/preset-two-self-result.json \
  --stage27-wal /absolute/original-self-A/physical-wal.json \
  --preaction-generation /absolute/original-stage27-preaction/g-000000000000 \
  --postaction-generation /absolute/new-stage28-postaction/g-000000000001 \
  --c1-memory-id 'c1-skillrun:<exact-sha256>'
```

The operator supplies **actual** paths and exact accepted C1 ID. The example
paths are placeholders, not verified files. No path is inferred from a report
title, and the CLI does not move/copy/repair evidence or launch Minecraft.

- Output `PRE_WORLD_HOLD`, process exit code **2**: missing/inconsistent
  original source or not-yet-terminal Skill; do not infer continuity, do not
  auto-retry a potentially issued physical Action.
- Output `DEV_SOURCE_LINEAGE_COMPATIBLE_NOT_PHYSICAL_CAUSALITY`, exit **0**:
  same source World UUID/branch A+B, distinct validated pre/post COMMITTED
  generations, original frozen Stage27 hook, Stage27 schema-v2 WAL matching
  the archived WAL checksum/rows, committed parent Intent, later
  Self-terminalized SkillRun, and previously adopted C1 Memory with exact
  original Action/Target/Preset/WAL SHA provenance. **This does not prove
  real native effect, independent Paper causality or learning benefit.**

The CLI validates SHA/checksum via the *original* Stage27 canonical `_read`
without invoking `PhysicalActionJournal.restore` on an immutable archive
(which would create a `.lock` sibling). It does not numerically compare
old/new Paper process ticks or claim their continuity.

## Evidence still required before real DEV attestation

1. A Stage27 *new isolated World* trial, with full original Paper stdout /
   native raw source / Gemma model identity/HTTP, and its canonical
   terminal WAL. Record unresolved PREPARED as HOLD (never retry).
2. A later explicit original Owner evaluation of the bounded child Skill
   and approved C1 `Memory` adoption, with the original parent Intent and
   child Action/WAL lineage intact. No synthetic Skill terminalization.
3. One **post-action** stopped World + both *original* A/B Self cognitive
   state COMMITTED cut, verified by Stage28's existing typed owner source
   capture. No World-only or mismatched pre-action generation.
4. Independently audited Stage28 new-world-source execution copy and
   new Paper process A/B native rejoin using that **same World**. Its current
   fixed-source real runner must be correctly parameterized/reworked under
   the existing source owners, not bypassed with hand-authored receipts.
5. A separately independently qualified C2 accepted-revision receipt and
   *real Gemma bounded L1* A(no retrieval)/B(with retained C1) comparison;
   the same immutable L1 choices and new-current context. Context presence
   alone is not a learning advantage.

**No real-world trial has been executed by this slice.** Existing synthetic
tests assert that the read-only source check can admit self-consistent typed
fixtures without making the claim of physical causality, and that tampered
sources and cross-World mixing fail closed.

Classification: `DEV_SOURCE_PREFLIGHT_OFFLINE_ONLY /
REAL_WORLD_LONGITUDINAL_NOT_ATTESTED / QUAL_NO_GO / SCIENCE_NOT_RUN`.
