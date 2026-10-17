"""R negative controls: S50 post-outcome WAIT originals, never grants recovery."""
import hashlib
import json

import pytest

from experiments.standard_env import s50_p1_wait_original_audit as audit

SESSION = "ad0a0000-0000-0000-0000-000000000000"
AID = "m02-paper-walk-1"
MARKER = AID + "-" + SESSION


def _line(prefix, **kv):
    return prefix + " " + " ".join(f"{k}={v}" for k, v in kv.items())


def fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "EXPECTED_JAR", hashlib.sha256(b"stub").hexdigest())
    events = [
        {"seq": i, "session_id": SESSION, **event}
        for i, event in enumerate((
            {"type": "adapter_started"},
            {"type": "effect_result", "action_id": AID+"-look",
             "effect": "look", "result": "applied"},
            {"type": "effect_result", "action_id": AID,
             "effect": "set_control", "result": "applied"},
            {"type": "effect_result", "action_id": AID+"-clear",
             "effect": "clear_controls", "result": "applied"},
            {"type": "shutdown_ack"}, {"type": "connection_end"},
        ))
    ]
    journal = [{"action_id": AID, "session_id": SESSION, "state": state}
               for state in ("issued", "outcome")]
    commands = [{"action_id": action_id, "effect": effect}
                for action_id, effect in ((AID+"-look", "look"),
                                          (AID, "set_control"),
                                          (AID+"-clear", "clear_controls"))]
    rows = [
        _line("M02_DEV_S50_PHASE", marker_id=MARKER, world="world",
              world_full_time=t, phase=p)
        for t, p in ((25, "PRE_FORWARD"), (28, "POST_FORWARD"),
                     (33, "PRE_CLEAR"), (35, "POST_CLEAR"))
    ]
    rows.append(_line(
        "S50_DEV_WAIT_BEGIN", marker_id=MARKER, world="world", tick=40,
        packets=10, blocks=1.9, tick_meter_blocks=1.92,
        combat_events=0, swing_events=0, basal_ticks=40, x=1.5, y=-60, z=0.5,
    ))
    for i in range(1, 9):
        rows.append(_line(
            "S50_DEV_WAIT_TICK", marker_id=MARKER, world="world",
            tick=40+i, index=i, from_x=1.5, from_y=-60, from_z=0.5,
            x=1.5, y=-60, z=0.5, motion_packets=10,
            motion_blocks=1.9, tick_meter_blocks=1.92,
            combat_events=0, swing_events=0, basal_ticks=40+i,
            sprint="false", sneak="false", swimming="false",
        ))
    rows.extend(_line("M02_DEV_BASAL_WRITE", id=i) for i in range(1, 49))
    raw = {
        "paper_server.log": "\n".join(rows),
        "original_native.jsonl": "\n".join(json.dumps(e) for e in events),
        "owner_commands.jsonl": "\n".join(json.dumps(e) for e in commands),
        "s50_action_original.jsonl": "\n".join(json.dumps(e) for e in journal),
    }
    for file, data in raw.items():
        (tmp_path / file).write_text(data)
    (tmp_path / "relay-metabolism-paper-dev.jar").write_bytes(b"stub")
    nbt = b"stub World NBT"
    (tmp_path / "initial_world_level.dat").write_bytes(nbt)
    report = {
        "status": "PASS", "owner_status": "PASS", "qualified": False,
        "science_go": False, "v7_arm": "BASE_ON", "v7_seed": 61021,
        "v7_tick_meter_dev": True, "v7_server_clock_calibration_dev": True,
        "plugin_sha256": audit.EXPECTED_JAR, "paper_sha256": audit.EXPECTED_PAPER,
        "java_exit": 0, "node_exit": 0, "port_released_after_shutdown": True,
        "source_session_id": SESSION,
        "evidence_hashes": {
            name: hashlib.sha256(data.encode()).hexdigest()
            for name, data in raw.items()
        },
        "initial_world_receipt": {
            "sha256": hashlib.sha256(nbt).hexdigest(), "size_bytes": len(nbt),
        },
        "movement": {
            "source_session": SESSION, "action_id": AID, "action_state": "outcome",
            "v7_p1_wait_evidence_dev": True, "v7_tick_meter_dev": True,
            "v7_phase_marker_id": MARKER,
            "p1_wait_candidate": {
                "first_world_tick": 41, "last_world_tick": 48,
                "wait_ticks_admitted": 0, "p1_fatigue_recovered": 0,
            },
        },
    }
    (tmp_path / "m02_report.json").write_text(json.dumps(report))


def changed(tmp_path, file, before, after, update_hash=True):
    target = tmp_path / file
    raw = target.read_text()
    assert before in raw
    target.write_text(raw.replace(before, after, 1))
    if update_hash and file in audit.ORIGINALS:
        report = json.loads((tmp_path / "m02_report.json").read_text())
        report["evidence_hashes"][file] = hashlib.sha256(target.read_bytes()).hexdigest()
        (tmp_path / "m02_report.json").write_text(json.dumps(report))


def test_stationary_source_never_creates_physical_wait_or_fatigue(tmp_path, monkeypatch):
    fixture(tmp_path, monkeypatch)
    verdict = audit.review(tmp_path)
    assert verdict["sampled_stationary_count"] == 8
    assert verdict["observed_world_ticks"] == [41, 48]
    assert verdict["whole_tick_motor_combat_inactivity"] == "NOT_ATTESTED"
    assert verdict["global_solo_entity_census"] == "NOT_ATTESTED"
    assert verdict["p1_wait_ticks_admitted"] == 0
    assert verdict["p1_fatigue_recovered"] == 0


@pytest.mark.parametrize("file,before,after", [
    ("paper_server.log", "tick=43 index=3", "tick=42 index=3"),
    ("paper_server.log", "tick=43 index=3", "tick=43 index=2"),
    ("paper_server.log", "basal_ticks=44", "basal_ticks=43"),
    ("paper_server.log", "from_x=1.5", "from_x=1.4"),
    ("paper_server.log", "marker_id="+MARKER, "marker_id=foreign"),
    ("paper_server.log", "world=world", "world=foreign"),
    ("s50_action_original.jsonl", '"state": "outcome"', '"state": "unknown"'),
    ("original_native.jsonl", '"type": "shutdown_ack"', '"type": "none"'),
    ("paper_server.log", "M02_DEV_BASAL_WRITE id=48",
     "M02_DEV_BASAL_WRITE id=47"),
])
def test_recomputed_local_hash_cannot_hide_physical_source_discrepancy(
    tmp_path, monkeypatch, file, before, after,
):
    fixture(tmp_path, monkeypatch)
    changed(tmp_path, file, before, after)
    with pytest.raises(audit.WaitOriginalRejected):
        audit.review(tmp_path)


def test_changed_sha_or_jar_or_missing_source_fails(tmp_path, monkeypatch):
    fixture(tmp_path, monkeypatch)
    (tmp_path / "paper_server.log").write_text("tampered")
    with pytest.raises(audit.WaitOriginalRejected):
        audit.review(tmp_path)
    fixture(tmp_path, monkeypatch)
    (tmp_path / "relay-metabolism-paper-dev.jar").write_bytes(b"not pinned")
    with pytest.raises(audit.WaitOriginalRejected):
        audit.review(tmp_path)
    fixture(tmp_path, monkeypatch)
    (tmp_path / "owner_commands.jsonl").unlink()
    with pytest.raises(audit.WaitOriginalRejected):
        audit.review(tmp_path)


def test_motor_active_snapshot_is_reported_not_recovered(tmp_path, monkeypatch):
    fixture(tmp_path, monkeypatch)
    changed(tmp_path, "paper_server.log", "sprint=false", "sprint=true")
    verdict = audit.review(tmp_path)
    assert verdict["sampled_stationary_count"] == 7
    assert verdict["sampled_active_ticks"] == [41]
    assert verdict["p1_wait_ticks_admitted"] == 0


def test_producer_forge_fatigue_recovery_is_denied(tmp_path, monkeypatch):
    fixture(tmp_path, monkeypatch)
    changed(tmp_path, "m02_report.json",
            '"p1_fatigue_recovered": 0', '"p1_fatigue_recovered": 0.8',
            update_hash=False)
    with pytest.raises(audit.WaitOriginalRejected):
        audit.review(tmp_path)
