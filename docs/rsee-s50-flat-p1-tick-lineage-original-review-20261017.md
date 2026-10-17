# RSEE R — FLAT P1 native MOVE tick-lineage candidate independent review (2026-10-17)

## Verdict

**`R_FLAT_P1_TICK_LINEAGE_ORIGINAL_REVIEW_DEV_ONLY` — source readback PASS.**

This audit verifies native Paper MOVE-event/tick lineage and consistency of the
offline, independent-branch P1 preview. It **does not** qualify full World
ticks as P1 physical activity, admit P1 `SourceBoundTick`, calculate genuine
Body WAIT recovery, establish evolutionary advantage, or issue SCIENCE/GO.

- Original **physical** FLAT four-arm DEV S [run #38994504183](https://github.com/rinsakamo/relay-self/actions/runs/38994504183),
  HEAD `9cb7a009b392ea8127528c310171d804251c90ec`.
  S artifact #12086324331, pinned original ZIP
  `6bd9d446eefb0a27a7599cdc4d1b79837bff3ef14d6c12ef6361435a9ea69ca6`.
- **Derived S/P1 offline preview** [run #39003515983](https://github.com/rinsakamo/relay-self/actions/runs/39003515983),
  S source HEAD `5ef136f5c91d4d0cc65b91ebf638e4b669c831be`,
  pinned **independent P1 owner** HEAD
  `0ab76b4e46efd914877e543a65de58b6cfc71326`
  (P1 Draft #626). S preview artifact #12089998075,
  full ZIP SHA256
  `b09f5f8c4392cd7b9073f21f51fde1819f8490e2135ec94a53052020de2db384`.
- **New independent R** [run #39003776317](https://github.com/rinsakamo/relay-self/actions/runs/39003776317),
  attempt1 **terminal SUCCESS**, separate R reader
  `experiments/standard_env/s50_flat_p1_tick_lineage_original_audit.py`.
  Receipt artifact [#12090505466](https://github.com/rinsakamo/relay-self/actions/runs/39003776317/artifacts/12090505466),
  GitHub ZIP digest `sha256:75b94bb91be04df105eb6ecaa0de88a61e089451d970ecffd63b03413f4a0d63`.
  R new Java/Node/World starts **0**.
- R uses **no S imports**; the S and P1 historical artifact ZIPs are separately
  downloaded and their **entire ZIP SHA256 independently recomputed** before
  expanding the source. R checks source original `report.json` /
  `paper_server.log` against original SHA manifest and S derived preview
  references.

## Observations and claim limits

| New DEV arm | Native MOVE rows | Source-positive World ticks | Continuous source-positive MOVE windows | UNKNOWN World ticks | Hypothetical P1 gain, not admitted |
| --- | ---: | ---: | ---: | ---: | ---: |
| SHAM_ON | 14 | 14 | 2 | 587 | 0.094474774934 |
| BASAL_ZERO | 14 | 14 | 2 | 586 | 0.094474774934 |
| WALK_ZERO | 14 | 14 | 2 | 586 | 0.094474774934 |
| BOTH_ZERO | 14 | 14 | 2 | 587 | 0.085851510982 |

R re-decoded all native event IDs, World UUID/full_time, actual `from_x/z`
and `to_x/z` distances, source cumulative counters, per-arm WALK metabolic
bills and terminal aggregate. For every Paper World tick in the original
range, R independently checked either a positive event with original
displacement or an **UNKNOWN_NOT_WAIT** row. It re-computed the preview
0.04/block P1 model's hypothetical per-window fatigue increments, strictly
resetting each preview at UNKNOWN gaps, with no stored/recovered P1 Body state.

The physical World tick is not attested merely by the presence of a native
PlayerMoveEvent callback. UNKNOWN means neither idle, WAIT, nor in-flight
MOVE was demonstrated. Original R prior FLAT source audit
[#38995296570](https://github.com/rinsakamo/relay-self/actions/runs/38995296570)
is historical; the new R readback audits **this** derived result specifically.

**Remaining blocker:** Paper full-tick S Body activity and its Action/motor
in-flight scope must be independently source-qualified before a real
`SourceBoundTick(WAIT)`, recovery, or state progression across gaps. A blocked
zero-distance MOVE does not become WAIT. M0.2 BASAL remains due during genuine
WAIT; no double-cost Ledger, free recovery, or unmetered physical activity.

New R audit is **DEV original rereview only**, not R engineering qualification
or V SCIENCE. V8 SCIENCE=0, G3/production NO_GO; original physical run,
all archived evidence, previously consumed grants and protected main unchanged.

The one-shot R workflow is preserved historically and removed from the current
branch after its single completed run. Tests:
`tests/test_rsee_s50_flat_p1_tick_lineage_original.py`.
