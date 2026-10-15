"""Adversarial synthetic V7 physical byte packets; never real World evidence."""
from __future__ import annotations

import gzip
import json

import pytest

from experiments.standard_env import v7_m02_paper_dev_audit as v


def specimen(tmp_path, arm="BASE_ON"):
    root = tmp_path / "synthetic-originals"
    root.mkdir()
    config = v.ARMS[arm][2]
    session = "test-v7-session"
    native = [
        {"type": "adapter_started", "session_id": session, "seq": 0},
        {"type": "observation", "session_id": session, "seq": 1},
        {"type": "effect_result", "session_id": session, "seq": 2, "effect": "look"},
        {"type": "effect_result", "session_id": session, "seq": 3, "effect": "set_control"},
        {"type": "effect_result", "session_id": session, "seq": 4, "effect": "clear_controls"},
        {"type": "observation", "session_id": session, "seq": 5},
        {"type": "shutdown_ack", "session_id": session, "seq": 6},
        {"type": "connection_end", "session_id": session, "seq": 7},
    ]
    commands = [
        {"type": "observe", "seq": 0}, {"type": "shutdown", "seq": 1},
    ]
    plugin_log = (
        "[INFO] M02_DEV_ONLY: candidate physics, not qualified by R/V\n"
        "[INFO] M02_DEV_BODY sampled_tick=1 player=RelaySelf exhaustion=0.001"
        " motion_blocks=0.0\n"
        "[INFO] M02_DEV_EVENT reason=WALK original=0.0 replaced=0.0\n"
        f"[INFO] M02_DEV_MOTION id=1 reason=WALK blocks=1.1"
        f" billed={1.1 * 0.01 * v.ARMS[arm][1]}"
        f" cumulative_blocks=1.1 cumulative_billed={1.1 * 0.01 * v.ARMS[arm][1]}\n"
        "[INFO] M02_DEV_BODY sampled_tick=200 player=RelaySelf exhaustion=0.2"
        " motion_blocks=1.1\n"
    )
    raw_world = gzip.compress(b"\x0a\x00\x00\x00", mtime=0)
    originals = {
        "paper_server.log": plugin_log.encode("utf-8"),
        "original_native.jsonl": "".join(json.dumps(row)+"\n" for row in native).encode(),
        "owner_commands.jsonl": "".join(json.dumps(row)+"\n" for row in commands).encode(),
        "initial_world_level.dat": raw_world,
    }
    report = {
        "classification": "M02_PAPER_DEV_ONLY_PHYSICS_OBSERVED",
        "scenario": f"V7_{arm}_PHYSICS_DEV",
        "status": "PASS", "owner_status": "PASS",
        "v7_arm": arm, "v7_seed": 61021,
        "v7_real_science_trials": 0, "v7_food_introduced_by_runner": False,
        "qualified": False, "science_go": False, "production_go": False,
        "m0_virtual_ledger_used": False, "java_exit": 0, "node_exit": 0,
        "port_released_after_shutdown": True,
        "paper_sha256": v.PAPER_SHA, "plugin_sha256": v.PLUGIN_SHA,
        "plugin_config_sha256": config,
        "source_session_id": session,
        "initial_world_receipt": {
            "sha256": v.sha(raw_world), "size_bytes": len(raw_world),
            "snapshot_phase": "AFTER_SERVER_READY_SAVE_FLUSH_BEFORE_ACTION",
        },
        "movement": {
            "source_session": session, "action_state": "outcome",
            "requested_max_step_blocks": 1.0,
            "observed_progress_blocks": 1.042,
            "look_seq": 2, "forward_seq": 3, "clear_seq": 4,
        },
        "v7_source": {
            "classification": "S_V7_PAPER_DEV_OBSERVED_SOURCE_SHAPE_ONLY",
            "arm": arm,
            "observed_motion_path_blocks": 1.1,
            "observed_motion_debit": 1.1 * 0.01 * v.ARMS[arm][1],
            "basal_source_charge_inferred_not_independently_attested": True,
            "science_go": False,
        },
        "evidence_hashes": {
            n: v.sha(x) for n, x in originals.items()
            if n in ("original_native.jsonl", "owner_commands.jsonl", "paper_server.log")
        },
    }
    for name, data in originals.items():
        (root / name).write_bytes(data)
    write_report(root, report)
    return root, report


def write_report(root, report):
    (root / "m02_report.json").write_text(json.dumps(report, sort_keys=True))


@pytest.mark.parametrize("arm", list(v.ARMS))
def test_synthetic_source_shapes_without_science(arm, tmp_path):
    root, _ = specimen(tmp_path, arm)
    result = v.review(root, arm)
    assert result["classification"] == v.CLASSIFICATION
    assert result["real_s50_move_attested"] is True
    assert result["min_player_ticks_reached"] == 200
    assert result["real_motion_path_blocks"] == pytest.approx(1.1)
    assert result["observed_walk_debit"] == pytest.approx(v.ARMS[arm][1] * .011)
    assert result["basal_debit_independently_attested"] is False
    assert result["source_basal_physical_debit_independently_attested"] is False
    assert not result["r_changed_config_physical_qualified"]
    assert not result["v_science_go"]


@pytest.mark.parametrize(("field", "value"), [
    ("classification", "RSEE_V7_SCIENCE_PASS"),
    ("status", "FAILED"), ("qualified", True),
    ("science_go", True), ("v7_real_science_trials", 20),
    ("v7_food_introduced_by_runner", True),
    ("v7_seed", 61022), ("paper_sha256", "0" * 64),
    ("plugin_config_sha256", "0" * 64),
    ("java_exit", 1), ("port_released_after_shutdown", False),
    ("source_session_id", "FOREIGN"),
])
def test_source_promotion_or_wrong_config_fails(field, value, tmp_path):
    root, report = specimen(tmp_path)
    report[field] = value
    write_report(root, report)
    with pytest.raises(v.Rejected):
        v.review(root, "BASE_ON")


@pytest.mark.parametrize(("original", "replacement"), [
    ("original_native.jsonl", b""),
    ("owner_commands.jsonl", b""),
    ("paper_server.log", b"UNVERIFIED"),
    ("initial_world_level.dat", b"bad"),
])
def test_missing_corrupt_original_fails(original, replacement, tmp_path):
    root, _ = specimen(tmp_path)
    (root / original).write_bytes(replacement)
    with pytest.raises(v.Rejected):
        v.review(root, "BASE_ON")


def test_missing_true_world_tick_or_wrong_walk_physics_blocked(tmp_path):
    root, report = specimen(tmp_path)
    path = root / "paper_server.log"
    path.write_text(path.read_text().replace("sampled_tick=200", "sampled_tick=199"))
    report["evidence_hashes"]["paper_server.log"] = v.sha(path.read_bytes())
    write_report(root, report)
    with pytest.raises(v.Rejected, match="200"):
        v.review(root, "BASE_ON")


def test_attempt_to_use_qualified_base_profile_for_zero_walk_refused(tmp_path):
    root, _ = specimen(tmp_path, "BASE_ON")
    with pytest.raises(v.Rejected):
        v.review(root, "WALK_ZERO")


def test_independently_read_original_twice_without_mutation(tmp_path):
    root, _ = specimen(tmp_path)
    before = {p.name: v.sha(p.read_bytes()) for p in root.iterdir()}
    v.review(root, "BASE_ON")
    assert {p.name: v.sha(p.read_bytes()) for p in root.iterdir()} == before
