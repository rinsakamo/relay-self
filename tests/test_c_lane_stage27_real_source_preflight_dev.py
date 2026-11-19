"""Read-only real-source preflight tests on original Stage27/28 Python fixtures.

All source evidence here is explicitly SYNTHETIC. Passing does NOT assert
that actual Paper, native controls, Gemma or autonomous C2 ran.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from relay_self.c_lane_stage27_real_source_preflight_dev import (
    C1RealSourcePreflightHold,
    inspect_stage27_to_stage28_original_sources,
    main,
)
from relay_self.stage28b_retired_resident_typed_cut_dev import (
    capture_retired_resident_typed_world,
)
from test_c_lane_stage27_stage28_same_cut_dev import _source_with_original_v2_wal
from test_c_lane_stage28_typed_continuity_dev import _case
from test_stage28b_retired_typed_cut_dev import _setup


def _dimensions(root):
    for name in ("world_nether", "world_the_end"):
        dim = root / name
        dim.mkdir()
        (dim / "region").mkdir()
        (dim / "region" / "r.0.0.mca").write_bytes(
            ("synthetic-" + name).encode(),
        )


def _synthetic_sources(tmp_path: Path, monkeypatch):
    """Two independent original typed saves; NEVER a real-stage evidence test."""
    prior_root = tmp_path / "stage27-before"
    prior_root.mkdir()
    bridge, paper, store, evidence = _setup(prior_root, monkeypatch)
    _dimensions(prior_root)
    before = capture_retired_resident_typed_world(
        bridge=bridge, paper=paper, store=store, evidence_dir=evidence,
    ).generation

    import test_c_lane_stage28_typed_continuity_dev as longitudinal

    post_root = tmp_path / "stage27-after"
    post_root.mkdir()
    source_setup = longitudinal._setup
    original_wal = tmp_path / "original-stage27-physical-wal.json"
    captured = {}

    def original_v2_setup(path, monkey):
        original = source_setup(path, monkey)
        owner = original[0].owners["A"]
        exp, digest, _inv, _start, _end = _source_with_original_v2_wal(owner)
        captured.update(exp=exp, digest=digest)
        original_wal.write_bytes(owner.files.physical_wal_file.read_bytes())
        return original

    monkeypatch.setattr(longitudinal, "_setup", original_v2_setup)
    monkeypatch.setattr(
        longitudinal, "_historical_synthetic_c1", lambda: captured["exp"],
    )
    args, _exp, _rejoined, _peer = _case(post_root, monkeypatch)
    after = args["source_generation"]

    hook = {
        "classification": "REAL_STAGE27H_L0_TARGET_REACHED_NATIVE_OBSERVED_DEV",
        "physical_effect_observed": True,
        "stage27h_skill_success": False,
        "stage27h_goal_success": False,
        "stage27h_self_a_skill_state": "started",
        "stage27h_original_skill": captured["exp"].skill_execution_id,
        "stage27h_original_intent": captured["exp"].intent_id,
        "stage27h_l0_action_count": 1,
        "stage27_native_action_count": 1,
        "stage27h_original_action_witnesses": [
            {"action": captured["exp"].action_ids[0]},
        ],
        "original_world_uuid": "world-1",
        "self_a_selected_number": "1",
    }
    frozen = tmp_path / "stage27-original-hook.json"
    frozen.write_text(json.dumps(hook, sort_keys=True))
    snapshot = {
        "original_hook_return_path": str(frozen),
        "original_hook_return_sha256": hashlib.sha256(frozen.read_bytes()).hexdigest(),
        "original_hook_contract_valid": True,
        "original_hook_frozen_before_parent_aggregation": True,
    }
    result = {
        "classification": hook["classification"],
        "world_uuid": "world-1",
        "committed_generation": str(before),
        "stage27": hook,
        "stage27h_hook_snapshot": snapshot,
        "real_native_physical_action_issued": True,
        "physical_action_issue_authorized": True,
    }
    report = tmp_path / "preset-two-self-result.json"
    report.write_text(json.dumps(result, sort_keys=True))
    return {
        "stage27_report": report, "stage27_wal": original_wal,
        "preaction_generation": before, "postaction_generation": after,
        "c1_memory_id": captured["exp"].memory_id,
    }, frozen


def test_original_source_preflight_returns_only_noncausal_dev_evidence(
    tmp_path, monkeypatch,
):
    args, _hook = _synthetic_sources(tmp_path, monkeypatch)
    a_root = args["postaction_generation"] / "selves" / "A"
    old_files = tuple(sorted(p.name for p in a_root.iterdir()))
    witness = inspect_stage27_to_stage28_original_sources(**args)
    assert witness.classification == "DEV_SOURCE_LINEAGE_COMPATIBLE_NOT_PHYSICAL_CAUSALITY"
    assert witness.source_world_uuid == "world-1"
    assert witness.source_branch_id == "source"
    assert len(witness.action_ids) == 1
    assert witness.original_wal_sha256
    assert witness.archived_c1_retained
    assert not witness.physical_causality_attested
    assert not witness.new_epoch_l1_attested
    assert not witness.c2_understanding_attested
    assert tuple(sorted(p.name for p in a_root.iterdir())) == old_files
    assert main([
        "--stage27-report", str(args["stage27_report"]),
        "--stage27-wal", str(args["stage27_wal"]),
        "--preaction-generation", str(args["preaction_generation"]),
        "--postaction-generation", str(args["postaction_generation"]),
        "--c1-memory-id", args["c1_memory_id"],
    ]) == 0


@pytest.mark.parametrize("fault", [
    "different-world", "same-preaction-cut", "wrong-frozen-hook",
    "forged-run-report", "foreign-stage27-wal", "empty-c1",
    "wrong-child-roster", "wrong-retained-skill",
    "wrong-source-branch", "source-sha-change",
])
def test_original_source_preflight_holds_mismatched_real_claims(
    tmp_path, monkeypatch, fault,
):
    args, frozen = _synthetic_sources(tmp_path, monkeypatch)
    report_path = args["stage27_report"]
    report = json.loads(report_path.read_text())
    if fault == "different-world":
        report["world_uuid"] = "real-foreign-world"
    elif fault == "same-preaction-cut":
        args["postaction_generation"] = args["preaction_generation"]
    elif fault == "wrong-frozen-hook":
        frozen.write_bytes(b"tampered frozen hook")
    elif fault == "forged-run-report":
        report["stage27"]["stage27h_original_skill"] = "counterfeit-skill"
    elif fault == "foreign-stage27-wal":
        args["stage27_wal"] = (
            args["postaction_generation"] / "selves" / "B" / "physical-wal.json"
        )
    elif fault == "empty-c1":
        args["c1_memory_id"] = "c1-skillrun:" + "f" * 64
    elif fault == "wrong-child-roster":
        report["stage27"]["stage27h_original_action_witnesses"] = [
            {"action": "counterfeit-child"},
        ]
    elif fault == "wrong-retained-skill":
        # Change both the frozen hook and the report, so the mismatch gets
        # as far as the typed Skill owner rather than merely frozen-source.
        report["stage27"]["stage27h_original_skill"] = "foreign-skill"
        frozen.write_text(json.dumps(report["stage27"], sort_keys=True))
        report["stage27h_hook_snapshot"]["original_hook_return_sha256"] = (
            hashlib.sha256(frozen.read_bytes()).hexdigest()
        )
    elif fault == "wrong-source-branch":
        # A different branch with the same World UUID does not establish
        # the same physical history, despite identical Self IDs.
        marker = args["postaction_generation"] / "COMMITTED.json"
        marker.write_bytes(b'{"branch_id":"foreign"}')
    elif fault == "source-sha-change":
        args["stage27_wal"].write_bytes(b"tampered wal")
    if fault in {
        "different-world", "forged-run-report",
        "wrong-child-roster", "wrong-retained-skill",
    }:
        report_path.write_text(json.dumps(report, sort_keys=True))
    with pytest.raises(C1RealSourcePreflightHold):
        inspect_stage27_to_stage28_original_sources(**args)


def test_cli_returns_pre_world_hold_without_starting_a_world(
    tmp_path, monkeypatch, capsys,
):
    args, _ = _synthetic_sources(tmp_path, monkeypatch)
    args["c1_memory_id"] = "c1-skillrun:" + "0" * 64
    rc = main([
        "--stage27-report", str(args["stage27_report"]),
        "--stage27-wal", str(args["stage27_wal"]),
        "--preaction-generation", str(args["preaction_generation"]),
        "--postaction-generation", str(args["postaction_generation"]),
        "--c1-memory-id", args["c1_memory_id"],
    ])
    assert rc == 2
    printed = json.loads(capsys.readouterr().out)
    assert printed["classification"] == "PRE_WORLD_HOLD"
    assert printed["real_world_trials"] == 0
