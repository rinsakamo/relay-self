"""Adversarial R Paper B1 historical-source admission checks, no World."""
from __future__ import annotations

import json

import pytest

from experiments.standard_env import m02_paper_b1_original_audit as r


def test_absent_archive_remains_not_run(capsys):
    assert r.main([]) == 0
    outcome = json.loads(capsys.readouterr().out)
    assert outcome["classification"] == "PAPER_B1_R_REVIEW_NOT_RUN_NO_ORIGINAL_ZIP"
    assert outcome["new_source_r_engineering_qualified"] is False
    assert outcome["physical_world_launches_by_reviewer"] == 0


def test_foreign_or_changed_archive_does_not_get_review(tmp_path, capsys):
    p = tmp_path / "m02-b1.zip"
    p.write_bytes(b"not a historical zip")
    assert r.main(["--original-zip", str(p)]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["classification"] == "PAPER_B1_R_HISTORICAL_ORIGINAL_REVIEW_BLOCKED"
    assert result["new_source_r_engineering_qualified"] is False
    assert "SHA" in result["reason"] or "historical" in result["reason"]
    assert r.main(["--original-zip", "relative.zip"]) == 2


def test_native_motion_source_and_zero_walk_event_are_legit():
    log = ("M02_DEV_ONLY: candidate physics, not qualified by R/V\n"
           "M02_DEV_BODY sampled_tick=1 player=RelaySelf exhaustion=0.001\n"
           "M02_DEV_BODY sampled_tick=20 player=RelaySelf exhaustion=0.020\n"
           "M02_DEV_MOTION id=1 reason=WALK blocks=0.7 billed=0.007 "
           "cumulative_blocks=0.7 cumulative_billed=0.007\n"
           "M02_DEV_MOTION id=2 reason=WALK blocks=0.8 billed=0.008 "
           "cumulative_blocks=1.5 cumulative_billed=0.015\n").encode()
    expected = {"count_walk_motion_packets": 2, "count_walk_native_events": 0,
                "world_measured_walk_blocks": 1.5,
                "world_billed_walk_exhaustion": 0.015}
    m = r.physics(log, expected)
    assert m["native_motion_packets"] == 2
    assert m["native_walk_event_count"] == 0
    assert m["native_walk_exhaustion"] == pytest.approx(0.015)
    assert m["native_path_blocks"] == pytest.approx(1.5)
    with pytest.raises(r.Rejected):
        r.physics(log.replace(b"billed=0.008", b"billed=0.001"), expected)
    with pytest.raises(r.Rejected):
        r.physics(log.replace(b"cumulative_blocks=1.5", b"cumulative_blocks=1.7"),
                  expected)
    with pytest.raises(r.Rejected):
        r.physics(log.replace(b"sampled_tick=1", b"sampled_tick=3"), expected)
    with pytest.raises(r.Rejected):
        r.physics(log + b"M02_DEV_EVENT id=1 reason=WALK original=0.0 replaced=0.1\n",
                  expected)
    with pytest.raises(r.Rejected):
        r.physics(log, {**expected, "count_walk_motion_packets": 3})


def test_wrong_source_effect_cannot_be_applied():
    cmd = [{"type": "effect", "effect": "set_control", "action_id": "s50-0"}]
    native = [{"type": "effect_result", "effect": "set_control", "action_id": "s50-0",
               "result": "applied"}]
    r._one_effect(native, cmd, 0, "set_control", "s50-0")
    with pytest.raises(r.Rejected):
        r._one_effect(native, cmd, 0, "set_control", "s50-1")
    with pytest.raises(r.Rejected):
        r._one_effect(native, cmd * 2, 0, "set_control", "s50-0")
    with pytest.raises(r.Rejected):
        r._one_effect([{**native[0], "result": "rejected"}], cmd, 0,
                      "set_control", "s50-0")


def test_external_pin_and_claim_ceiling_are_explicit():
    assert len(r.PAPER_ARTIFACT_ZIP_SHA256) == 64
    assert len(r.S_PRODUCER_HEAD) == 40
    assert r.original_prefix("on") != r.original_prefix("off")
    assert r.ORIGINAL_SHA["on"]["initial_world_level.dat"] != (
        r.ORIGINAL_SHA["off"]["initial_world_level.dat"])
    with pytest.raises(r.Rejected):
        r.point({"position": {"x": float("nan"), "z": 0}})
    with pytest.raises(r.Rejected):
        r.probe([{"type": "adapter_started"}], 0)