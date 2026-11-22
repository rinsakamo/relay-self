# Stage28c1 — exact Stage28b typed World+A/B inert branch restore (DEV)

Parent [Stage28 #966](https://github.com/rinsakamo/relay-self/issues/966),
based on Stage28b Draft [#969](https://github.com/rinsakamo/relay-self/pull/969)
and Stage28a Draft [#967](https://github.com/rinsakamo/relay-self/pull/967).

## Real source (LocalCodex, not available inside GitHub CI)

Stage28b independently attested exactly one real Paper A/B typed cohort:
- Original source branch HEAD `1dcd48ad8f725f00743e8ba56523bbe41bf8c18b`,
  CI 5/5 and pytest 1,839 PASS.
- Original source World UUID `f9221410-b99e-417d-98f4-e98938586472`,
  branch `p0d-real-resident-presence`, generation `g-000000000000`.
- World cut Paper tick 221. Self A cut 210 (11 ticks behind), Self B
  cut 39 (182 ticks behind). A/B cognition has fresh identities, zero
  Memories, zero Intent/Skill history, four innate Schema patterns each,
  no peer receipts/pending Questions, empty canonical WAL. This source
  does NOT attest the survival of learned experience, an active Intent,
  a physically issued Action or a distributed atomic transaction.
- Full Stage28b evidence root reported by LocalCodex:
  `/home/rinsa/evidence/stage28b-1dcd48-20261118/`.
  Original 285 file manifest `SHA256SUMS` has SHA256
  `7a202d68f6d275a0031f9c7091e0e1e7f33c4976c4565461d425e040f87209f4`.
  Do not infer the nested generation directory without enumerating the
  actual original files. Do not mutate, delete, rename or re-run this World.
- Stage24g original manifest
  `b79646397ecf67f3b0c840964dfc7ee4fe669f2347cab264c9c303131c6716f1`;
  Stage24f remains HOLD. Stage27 PLACE is parallel and untouched.

## 28c1 contract

`inspect_stage28c_source` is read-only and requires a **typed committed**
generation, the exact A/B original owner roster, source World ID, source
branch, and all three Paper dimensions (Overworld, Nether, End). It validates
original typed cross-Self receipts and WALs via the existing
`verify_typed_generation`; it refuses Self cut ticks later than saved World
tick. It returns SHA256 of the original `COMMITTED.json` as an independent
operator-pinned input for the one-shot file restoration.

`prepare_stage28c_inert_restore` refuses reused, symlinked, foreign
or source-overlapping destinations. It uses the **original**
`restore_generation`, then independently invokes
`verify_restored_world` on the main World and **each** Paper companion.
All three restore sidecars must point to one new fork branch, source World
and same generation/tick. Existing Stage28a
`stage28_inert_cognitive_recovery` checks exact restored World contents,
original A/B typed retained cognition and canonical WAL, and makes only
inert owner candidates.

The returned receipt explicitly denies:
- old native session reuse, old L1 decision reuse, old Skill or Action
  replay, peer message redelivery;
- L1 reevaluation eligibility or any physical Action issue;
- proof of a real new Paper session, native A/B rejoin, GPU source, or
  live WorldBody observation.

If a copy fails *after* creating the new destination, keep the partial
destination for HOLD evidence. Do not delete/reuse it or silently retry.

**Important:** A fresh World fork retains the saved physical World UUID
but gets a different **branch ID** in the sidecar; these are distinct
identities. Old Self B C39 is not current world perception W221. Fresh
native WorldBody reevaluation after new Paper session is indispensable.

## LocalCodex operator procedure

Read the repository and #966/#967/#969 before any operation, then inspect
the original Stage28b evidence `SHA256SUMS` and its files. Confirm the
original reported manifest hash **outside the code's generated receipts**.
Resolve the actual nested typed generation directory containing
`COMMITTED.json`, Overworld, `paper-dimensions` and `selves/A,B`.
Never use Stage24g's roster-free World-only generation as source.

Inspection does **not** create a destination:

```bash
PYTHONPATH=src:. python3 -m experiments.stage28c1_pinned_inert_restore_dev \
  --generation "$EXACT_STAGE28B_TYPED_GENERATION" \
  --expected-world-id f9221410-b99e-417d-98f4-e98938586472 \
  --expected-source-branch-id p0d-real-resident-presence \
  --inspect-only
```

Independently record the returned `source.committed_sha256` and compare
it with a fresh `sha256sum "$EXACT_STAGE28B_TYPED_GENERATION/COMMITTED.json"`.
Only after explicit source pin validation, create a **different fresh
directory**, outside prior evidence and worktree:

```bash
PYTHONPATH=src:. python3 -m experiments.stage28c1_pinned_inert_restore_dev \
  --generation "$EXACT_STAGE28B_TYPED_GENERATION" \
  --expected-world-id f9221410-b99e-417d-98f4-e98938586472 \
  --expected-source-branch-id p0d-real-resident-presence \
  --source-committed-sha256 "$INDEPENDENT_COMMITTED_SHA256" \
  --destination "$NEW_NEVER_EXISTED_STAGE28C1_BRANCH_DIR" \
  --restore-id stage28c1-inert-a-b-one-shot \
  --prepare-once
```

Capture stdout and stderr *outside the immutable archive*, hash them, then
read back the output sidecars, restored dimensions and typed Self files
with the original verifier from a **separate process**.

28c1 itself makes no network requests, never starts Paper/Node/Mineflayer,
never POSTs to Gemma and issues no physical Action. It requires no new
Minecraft World EULA grant because it copies local stopped World files.
This is a file-level source audit; running a new Paper world will be a
separately authorized Stage28c2 one-shot DEV.

## Adversarial test coverage

- Source is exact typed A/B from one real-schema stopped Paper generation;
  no roster-free World-only or legacy opaque owner snapshot.
- A+B original cognition/Skill and WAL bytes retained, while their old
  native sessions and pending Skills remain inert.
- Overworld, Nether, End are all copied, each with a validated source,
  fresh fork branch and independent restore sidecar.
- Wrong World, branch, generation/COMMITTED SHA, missing Paper companion,
  source tampering, reused/overlapping destination all reject before copy.
- Corrupted new companion receipt remains HOLD after a partial restore.
- CLI inspect-only never invokes restore; missing independent pin refuses
  mutation; prepare once returns an inert typed receipt.

## Next 28c2: real Paper + new A/B cognition

Use **one** fresh fork directory from this exact checked receipt.
A new Paper process, original `OwnedResidentPhysicalBridge`, fresh
per-Self native processes and actual `NativeLoginEvidence` must prove
new Paper session, WorldBody perception, old GPU/peer epochs fenced and
canonical WAL clear. **Rehydrate the saved owners, not new default A/B
identities**; do not recreate innate-only clean owners as a substitute
for restoration. Only then permit a new L1 numbered candidate selection
via the existing original L1 lane, not the prior Stage24g result. No
automatic physical Action lease from the restore receipt.

This remains `STAGE28C1_OFFLINE_INERT_RESTORE / REAL_RESTORED_PAPER_NOT_RUN /
NEW_L1_NOT_RUN / 60S_AUTOSAVE_NOT_ATTESTED / QUAL_NO_GO / SCIENCE_NOT_RUN`
until independently repeated on real original Stage28b source files.
