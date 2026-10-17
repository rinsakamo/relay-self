"""R reader: first FLAT BLOCKED originals cannot be promoted to PASS/WAIT."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from experiments.standard_env import s50_p1_flat_blocked_original_audit as r


def fixture(tmp_path: Path):
    root = tmp_path / "originals"
    root.mkdir()
    session = r.SOURCE_SESSION
    native = [{"type": "observation", "seq": i, "session_id": session}
              for i in range(28)]
    native[0]["type"] = "adapter_started"
    native[26]["type"] = "shutdown_ack"
    native[27]["type"] = "connection_end"
    action_id = "m02-paper-walk-1"
    for i, effect, suffix in (
        (7, "look", "-look"),
        (8, "set_control", ""),
        (17, "clear_controls", "-clear"),
    ):
        native[i].update({"type": "effect_result", "effect": effect,
                          "action_id": action_id + suffix, "result": "applied"})
    action = [
        {"state": "issued", "action_id": "m02-paper-walk-1", "session_id": session},
        {"state": "outcome", "action_id": "m02-paper-walk-1",
         "session_id": session, "consequence": {
             "action_id": "m02-paper-walk-1", "session_id": session,
             "kind": "BLOCKED", "progress_m": -0.3363737550662047}},
    ]
    def controls_row(kind, ordinal, tick, *, seq=None, forward=False):
        state = {name: False for name in r.CONTROLS}
        state["forward"] = forward
        data = {"source": "S50_DEV_NATIVE_READBACK_V1", "kind": kind,
                "session_id": session, "ordinal": ordinal,
                "client_physics_tick": tick}
        if kind != "SESSION_START":
            data["controls"] = state
        if seq is not None:
            data["native_seq"] = seq
        return data

    rows = [controls_row("SESSION_START", 1, 0, seq=0),
            controls_row("EFFECT_ACK", 2, 0, seq=7),
            controls_row("EFFECT_ACK", 3, 0, seq=8, forward=True)]
    rows[1]["native_action_id"] = action_id + "-look"
    rows[2]["native_action_id"] = action_id
    for tick in range(1, 8):
        rows.append(controls_row("PHYSICS_TICK", len(rows)+1, tick, forward=True))
    rows.append(controls_row("EFFECT_ACK", len(rows)+1, 7, seq=17))
    rows[-1]["native_action_id"] = action_id + "-clear"
    for tick in range(8, 31):
        rows.append(controls_row("PHYSICS_TICK", len(rows)+1, tick))
    rows.append(controls_row("SHUTDOWN_ACK", len(rows)+1, 30, seq=26))
    pose = "x=0.5 y=-60.0 z=1.707742656099451"
    prior = "from_x=0.5 from_y=-60.0 from_z=1.707742656099451"
    counters = ("combat_events=0 swing_events=0 tick_meter_blocks=0 "
                "sprint=false sneak=false swimming=false")
    paper = ["Paper S50_DEV_WAIT_BEGIN marker_id=m world=w tick=43 "
             + pose + " packets=0 blocks=0 basal_ticks=28 " + counters]
    for idx, tick in enumerate(range(44, 52), 1):
        paper.append("Paper S50_DEV_WAIT_TICK "
                     f"marker_id=m world=w tick={tick} index={idx} "
                     + pose + " " + prior + " motion_packets=0 "
                     "motion_blocks=0 basal_ticks=" + str(28 + idx)
                     + " " + counters)

    files = {
        "original_native.jsonl": "\n".join(map(json.dumps, native))+"\n",
        "owner_commands.jsonl": "\n".join(map(json.dumps, [
            {"type": "effect", "action_id": action_id + "-look",
             "effect": "look"},
            {"type": "effect", "action_id": action_id,
             "effect": "set_control", "control": "forward", "state": True},
            {"type": "effect", "action_id": action_id + "-clear",
             "effect": "clear_controls"},
            {"type": "shutdown"},
        ]))+"\n",
        "paper_server.log": "\n".join(paper)+"\n",
        "s50_action_original.jsonl": "\n".join(map(json.dumps, action))+"\n",
        "s50_p1_native_controls_original.jsonl": "\n".join(map(json.dumps, rows))+"\n",
    }
    for name, data in files.items():
        (root / name).write_text(data)
    hashes = {name: hashlib.sha256(data.encode()).hexdigest()
              for name, data in files.items()}
    return root, hashes, native, action, rows, paper


def check(root, hashes):
    return r._review_sources(root, expected_sha=hashes, expected_session=r.SOURCE_SESSION)


def write_jsonl(root, name, rows):
    (root / name).write_text("\n".join(map(json.dumps, rows))+"\n")


def updated_hashes(root):
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in r.SOURCE_SHA256}


def test_exact_blocked_original_profile_is_only_dev_source(tmp_path):
    root, hashes, *_ = fixture(tmp_path)
    result = check(root, hashes)
    assert result["classification"] == r.CLASS
    assert result["native_frames_checked"] == 28
    assert result["client_physics_ticks"] == 30
    assert result["post_clear_client_callbacks"] >= 23
    assert result["s50_consequence"] == "BLOCKED_RETAINED_NO_PASS_PROMOTION"
    assert result["wait_ticks_admitted"] == 0
    assert not result["independent_R_qualification"]
    assert result["server_effective_input_release_tick"] == "NOT_ATTESTED"
    # Public function must not admit arbitrary test bytes.
    with pytest.raises(ValueError, match="SHA256"):
        r.review(root)


@pytest.mark.parametrize("damage", [
    "report_pass", "missing_outcome", "reverse_move", "forward_not_on",
    "clear_reactivated", "post_clear_reactivated", "skipped_physics_tick",
    "foreign_session", "missing_stop", "missing_wait_sample",
])
def test_forged_promoted_or_incomplete_original_rejected(tmp_path, damage):
    root, hashes, native, action, rows, paper = fixture(tmp_path)
    if damage == "report_pass":
        action[1]["consequence"]["kind"] = "ARRIVED"
        write_jsonl(root, "s50_action_original.jsonl", action)
    elif damage == "missing_outcome":
        write_jsonl(root, "s50_action_original.jsonl", action[:1])
    elif damage == "reverse_move":
        action[1]["consequence"]["progress_m"] = 0.5
        write_jsonl(root, "s50_action_original.jsonl", action)
    elif damage == "forward_not_on":
        rows[2]["controls"]["forward"] = False
        write_jsonl(root, "s50_p1_native_controls_original.jsonl", rows)
    elif damage == "clear_reactivated":
        next(x for x in rows if x.get("native_seq") == 17)["controls"]["forward"] = True
        write_jsonl(root, "s50_p1_native_controls_original.jsonl", rows)
    elif damage == "post_clear_reactivated":
        rows[-2]["controls"]["sprint"] = True
        write_jsonl(root, "s50_p1_native_controls_original.jsonl", rows)
    elif damage == "skipped_physics_tick":
        rows[-2]["client_physics_tick"] = 40
        write_jsonl(root, "s50_p1_native_controls_original.jsonl", rows)
    elif damage == "foreign_session":
        native[3]["session_id"] = "foreign"
        write_jsonl(root, "original_native.jsonl", native)
    elif damage == "missing_stop":
        native[26]["type"] = "observation"
        write_jsonl(root, "original_native.jsonl", native)
    elif damage == "missing_wait_sample":
        (root / "paper_server.log").write_text("\n".join(paper[:-1])+"\n")
    with pytest.raises(ValueError):
        check(root, updated_hashes(root))


def test_changed_original_bytes_are_never_hidden_by_a_stale_digest(tmp_path):
    root, hashes, *_ = fixture(tmp_path)
    with (root / "paper_server.log").open("a") as out:
        out.write("retroactive correction\n")
    with pytest.raises(ValueError, match="SHA256"):
        check(root, hashes)


def test_symlinked_original_is_rejected(tmp_path):
    root, hashes, *_ = fixture(tmp_path)
    file = root / "original_native.jsonl"
    data = tmp_path / "external-original"
    data.write_bytes(file.read_bytes())
    file.unlink()
    file.symlink_to(data)
    with pytest.raises(ValueError, match="missing/unbounded"):
        check(root, hashes)

@pytest.mark.parametrize("damage", [
    "ack_action_id", "extra_effect_command", "missing_look_sidecar",
    "sidecar_clear_ack_id", "postclear_stop_reactivation",
    "fabricated_physics_seq", "duplicate_native_readback_seq",
])
def test_native_ack_sidecar_bijection_rejects_forgery(tmp_path, damage):
    root, _, native, action, rows, _ = fixture(tmp_path)
    if damage == "ack_action_id":
        native[8]["action_id"] = "unrelated"
        write_jsonl(root, "original_native.jsonl", native)
    elif damage == "extra_effect_command":
        cmd = [json.loads(line) for line in (
            root / "owner_commands.jsonl").read_text().splitlines()]
        cmd.insert(2, {"type": "effect", "effect": "look",
                       "action_id": "foreign"})
        write_jsonl(root, "owner_commands.jsonl", cmd)
    elif damage == "missing_look_sidecar":
        rows.pop(1)
        for idx, row in enumerate(rows, 1):
            row["ordinal"] = idx
        write_jsonl(root, "s50_p1_native_controls_original.jsonl", rows)
    elif damage == "sidecar_clear_ack_id":
        clear = next(x for x in rows if x.get("native_seq") == 17)
        clear["native_action_id"] = "unrelated-clear"
        write_jsonl(root, "s50_p1_native_controls_original.jsonl", rows)
    elif damage == "postclear_stop_reactivation":
        rows[-1]["controls"]["sprint"] = True
        write_jsonl(root, "s50_p1_native_controls_original.jsonl", rows)
    elif damage == "fabricated_physics_seq":
        tick = next(x for x in rows if x["kind"] == "PHYSICS_TICK")
        tick["native_seq"] = 8
        write_jsonl(root, "s50_p1_native_controls_original.jsonl", rows)
    elif damage == "duplicate_native_readback_seq":
        clear = next(x for x in rows if x.get("native_seq") == 17)
        clear["native_seq"] = 8
        write_jsonl(root, "s50_p1_native_controls_original.jsonl", rows)
    with pytest.raises(ValueError):
        check(root, updated_hashes(root))
