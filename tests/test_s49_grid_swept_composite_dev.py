"""Swept footprint negatives and reproducible layouts; no physical claims."""
import random
from dataclasses import replace

import pytest

from relay_self.goal_grid_search_dev import choose_grid_route_dev, swept_body_safe_dev
from relay_self.provenance import Provenance
from test_s49_l1_grid_search_dev import _goal
from test_s49_l1_local_voxel_dev import grid


@pytest.mark.parametrize("field,value", [("feet","UNKNOWN"),("head","UNKNOWN"),
                                          ("floor","UNKNOWN"),("floor","CLEAR"),
                                          ("feet","BLOCKED"),("head","BLOCKED")])
def test_sweep_rejects_unverified_body_or_support(field,value):
    raw=grid(left_block=False)
    cells=tuple(replace(c,**{field:value}) if (c.dx,c.dz)==(1,1) else c for c in raw.cells)
    live=replace(raw,cells=cells)
    # Both centers are CLEAR; off-center continuous sweep overlaps column 1.
    assert not swept_body_safe_dev(live,(0.3,1.0),(0.3,0.0))


def test_contact_with_wall_and_outside_coverage():
    raw=grid(left_block=False)
    assert swept_body_safe_dev(raw,(0.0,1.2),(0.0,1.0))
    assert not swept_body_safe_dev(raw,(0.0,1.21),(0.0,1.0))
    assert not swept_body_safe_dev(raw,(-3.4,0.0),(-3.0,0.0))


@pytest.mark.parametrize("seed",[20261028,20261029,20261030])
def test_seeded_many_obstacles_and_closed_unknown_support(seed):
    rng=random.Random(seed)
    raw=grid(left_block=False)
    corridor={(0,1),(0,0),(1,0),(2,0),(2,1),(2,2),(2,3),(2,4),(1,4),(0,4)}
    cells=tuple(replace(c,feet="CLEAR" if (c.dx,c.dz) in corridor or rng.random()>.5 else "BLOCKED") for c in raw.cells)
    def choose(cs):
        return choose_grid_route_dev(replace(raw,cells=cs),_goal(),blocked_after_seq=33,
            blocked_action_id="original-unknown",provenance=Provenance("test","seed"))
    assert choose(cells).status=="SELECTED"
    for field,value in (("feet","BLOCKED"),("feet","UNKNOWN"),("floor","CLEAR")):
        closed=tuple(replace(c,**{field:value}) if c.dz==2 else c for c in cells)
        choice=choose(closed)
        assert choice.status=="DEFER" and choice.plan is None


@pytest.mark.parametrize("corrupt",["ack","layout","sweep","goal"])
def test_original_byte_auditor_rejects_report_mutations(tmp_path,corrupt):
    import json
    import shutil
    from pathlib import Path

    from adapters.mineflayer.s49_grid_composite_review_dev import audit
    original=Path(__file__).resolve().parents[1]/"docs/evidence/l1-l0-composite-20261028/attempt03"
    shutil.copytree(original,tmp_path/"run")
    root=tmp_path/"run"
    path=root/"HAZARD/goal_report.json"
    report=json.loads(path.read_text())
    if corrupt=="ack":
        report["detour"]["l0_inflight_interrupt"]["clear_ack"]["seq"]+=1
    elif corrupt=="layout":
        report["seeded_layouts_dev"][0]["native"]["cells"][0]["feet"]="UNKNOWN"
    elif corrupt=="sweep":
        report["detour"]["stages"][0]["swept_checks"][0]["safe"]=False
    else:
        report["goal_l2"]["target_z"]+=1.0
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError):
        audit(root)
