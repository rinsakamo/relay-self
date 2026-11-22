# Stage24d — Mineflayer-owned oxygen, freshness receipt, head-space epistemic contract

Parent [Stage24 #911](https://github.com/rinsakamo/relay-self/issues/911), child [#938](https://github.com/rinsakamo/relay-self/issues/938). Draft Stage24d is stacked on Stage24c [#934](https://github.com/rinsakamo/relay-self/pull/934).

## Observed constraints

The previous actual Stage24b World run yielded native `oxygen_level=null`, no CPU Explore Goal and no MOVE candidate, followed by genuine Gemma Jev reserved UNRESOLVED; the original canonical WAL was empty. Stage24c separately obtained A `UNRESOLVED` vs B synthetic oxygen 300 `MOVE forward` (two real model responses, **zero World actions**). The causal reason for actual World's null remains **INDETERMINATE**.

[PrismarineJS/mineflayer upstream #3985](https://github.com/PrismarineJS/mineflayer/issues/3985) confirms self-breath was updated by foreign Entity metadata. [Upstream PR #4052](https://github.com/PrismarineJS/mineflayer/pull/4052) merged 2026-10-03 and guards `if (metas.air_supply != null && entity.id === bot.entity?.id)`. The published **4.39.0** tag still lacks the owner guard. This is a verified defect, but it is **NOT proven to explain** the actual null.

## Worktree-local dev backport (explicit)

The package lock retains exactly Mineflayer `4.39.0`. The local installed JavaScript code is **not stock 4.39.0 after the hotfix**: identify it in evidence as `mineflayer-4.39.0+upstream-4052-self-owner-guard`, not as a new npm version or as pristine installed bits.

In a **new isolated worktree** only:

```bash
npm ci --prefix adapters/mineflayer
node adapters/mineflayer/oxygen_owner_patch.mjs --apply
node adapters/mineflayer/oxygen_owner_patch.mjs --inspect-only
npm test --prefix adapters/mineflayer
```

The script searches the **exact original breathing code block** in the locked package, rejects altered/multiple/already-patched blocks, applies the single upstream predicate change, prints before/after SHA256, then reopens the modified source to verify it. It neither changes `package-lock.json` nor touches other worktrees/Node installs. **Never** use symlinks or `NODE_PATH` to bypass this checked worktree. `npm ci` must be followed by the reviewed patch again; otherwise the real Paper runner intentionally HOLDS.

The original `_verify_local_runtime` also refuses before World creation if the modified pinned package is missing the exact owner guard. `bridge.mjs` verifies the installed source again **before creating a bot**. Both checks ensure an unpatched 4.39.0 cannot enter this Stage24d native path.

These checks guard a narrow source snippet, not the entire installed package's immutable bytes. Archive the complete installed source SHA and npm lock integrity before and after the backport, and require exact-source audit in a later QUAL run.

## Live native read-only oxygen witness

`OwnedOxygenWitness` (`adapters/mineflayer/oxygen_owner_witness.mjs`) records the patched Mineflayer **self-only** `breath` event, self Entity ID, native session ID, native generation, source event sequence, age and value.

The real `bridge.mjs` no longer publishes arbitrary `bot.oxygenLevel` as its official `oxygen_level` snapshot. Instead, it passes a receipt into the existing protocol serializer. Only `FRESH_OWNED` (same native self Entity + same spawn/respawn generation + finite oxygen sample + age ≤5000ms) publishes a numeric oxygen value. Foreign, absent, stale, death, self turnover, wrong Entity or reset gives `null`. `oxygen=null` is still UNKNOWN; no forced value, no bounded MOVE permission.

For further source correlation, set a fresh private file via `RELAY_P0B_OXYGEN_WITNESS_PATH` in a separately approved native DEV experiment. A passive JSONL receipt is emitted for each requested probe, matching `native_session_id`, `native_seq`, `native_request_id` and recording `generation`, `self_entity_id`, source event sequence and age. The receipt does **not** archive the original raw `entity_metadata` packet and cannot independently prove that Mineflayer interpreted the packet correctly; do not elevate it to raw-Paper provenance.

The existing unqualified snapshotFromBot API default remains compatible for synthetic/offline legacy callers. The **actual bridge** always supplies the owned witness; tests lock that down.

**Freshness limitation:** metadata/breath event cadence in 1.21.8 remains to be measured. A 5s timeout is intentionally conservative; it may yield long UNKNOWN episodes on land. Do not extend TTL or synthesize positive oxygen solely to force Goal/MOVE. First collect real source evidence under a separately qualified World DEV grant.

## Separate head-space medium contract (offline only)

`src/relay_self/head_breathing_context_dev.py` defines a typed, source-qualified two-cell (eye + upper head), loaded/fresh/position-qualified observation and returns:

- `UNKNOWN`: missing/unloaded/ambiguous/stale eye or head evidence
- `HEAD_FLUID_PRESENT`: fluid intersects the observed breathing volume
- `HEAD_OBSTRUCTED`: solid head-volume medium
- `HEAD_AIRLIKE_OBSERVED`: two loaded, fresh airlike cells — **NOT** proof of positive oxygen or safe MOVE

`isInWater=false` alone never authorizes any of these positive conclusions. All assessments return `proven_breathable=False`, `grants_move=False`. No direct `bot.blockAt` or raw World call is wired yet; this is an interface and synthetic test contract, **not an implemented breathing environment sensor**. Head position and fluid sampling in loaded chunks require separately source-attested real measurements before modifying Schema gate semantics.

## Offline validation and required future evidence

```bash
PYTHONPATH=src:. python3 -m pytest -q tests/test_stage24d_oxygen_head_contract_dev.py tests/test_stage24b_pinned_assets_launch_dev.py
npm test --prefix adapters/mineflayer
```

The Node regression executes the old versus patched self-breath condition against foreign/self metadata and proves that only the patched source rejects foreign updates; it also tests empty/foreign/stale/respawn oxygen receipts and that actual snapshot serialization consumes a receipt rather than unqualified `bot.oxygenLevel`. Python tests the exact patched source gate, no symlink, distinct eye/head media, missing/unloaded inputs and no physical permission.

This patch is **offline DEV**. No newly run real World/Gemma is claimed. Before a future World attempt, validate exact install SHA, own Entity metadata update, foreign Entity injection, respawn, stale intervals, actual under/overwater and head block evidence. Keep original `PhysicalIssueAdmission`, native WAL, Stage24b candidate restrictions and conservative Stage24c exploration gate. Stage25 still NO_GO until an actual model-choice-to-World Action original causal trail exists.
