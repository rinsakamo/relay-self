"""Source-shaped synthetic fixture: independent S1 Native stdout vs WAL."""
import hashlib
import json
import math

import pytest

from relay_self.i_lane_i4a_live_wal_anchor_dev import capture_live_wal_history_anchor
from relay_self.i_lane_i4a_s1_native_source_audit_dev import (
    I4AS1NativeSourceHold,
    audit_i4a_original_s1_native_stdout,
)
from relay_self.i_lane_i4a_s1_source_capture_dev import freeze_original_s1_wal
from relay_self.physical_action_journal import PhysicalActionJournal
from test_c_lane_stage27hi_multi_action_review_dev import _fixture, _run_multi
from test_i4a_live_wal_anchor_dev import _close_original_s1


def _stream(rows):
    """Only a synthetic protocol fixture; never a genuine native witness."""
    session = rows[0]["session_id"]
    started = {
        "type": "adapter_started", "session_id": session, "seq": 0,
        "mineflayer_version": "4.39.0",
        "config": {"host": "127.0.0.1", "port": 25565,
                   "username": "RelayA", "version": "1.21.8"},
    }
    template = {
        "health": 20.0, "food": 20.0, "food_saturation": 5.0,
        "oxygen_level": 20.0,
        "position": dict(rows[0]["started_position"]),
        "time": {"time_of_day": 0, "day": 0, "is_day": True},
        "inventory": [], "nearby_entities": [],
        "nearby_entities_coverage": {
            "source_scope": "mineflayer_entity_registry",
            "max_distance": 16.0, "max_entities": 16,
            "candidate_count": 0, "truncated": False,
        },
    }
    events = {0: started}
    def probe(seq, request, pos=None, tick=None):
        snapshot = json.loads(json.dumps(template))
        if pos is not None:
            snapshot["position"] = dict(pos)
        if tick is not None:
            snapshot["time"] = {
                "time_of_day": tick % 24000, "day": tick // 24000,
                "is_day": tick % 24000 < 12000,
            }
        return {
            "type": "observation", "session_id": session, "seq": seq,
            "kind": "probe", "request_id": request,
            "snapshot": snapshot,
        }
    for row in rows:
        parent = row["action_id"]
        events[row["probe_seq"]] = probe(
            row["probe_seq"], row["probe_request_id"],
            row["started_position"],
        )
        for seq, suffix, effect in (
            (row["effect_seqs"][0], "-look", "look"),
            (row["effect_seqs"][1], "-start", "set_control"),
            (row["effect_seqs"][2], "-stop", "clear_controls"),
        ):
            events[seq] = {
                "type": "effect_result", "session_id": session, "seq": seq,
                "action_id": parent + suffix, "effect": effect,
                "result": "applied", "error": None,
            }
        if row.get("gait_ack_seq") is not None:
            seq = row["gait_ack_seq"]
            events[seq] = {
                "type": "effect_result", "session_id": session, "seq": seq,
                "action_id": parent + "-sneak", "effect": "set_control",
                "result": "applied", "error": None,
            }
        for seq, tick, pos, label in (
            (row["initial_stop_seq"], row["initial_stop_tick"],
             None, "first-stop"),
            (row["first_stable_seq"], row["first_stable_tick"],
             row["settled_position"], "first-stable"),
            (row["after_seq"], row["settled_tick"],
             row["settled_position"], "settled"),
        ):
            events[seq] = probe(seq, f"synthetic-{parent}-{label}", pos, tick)
    end = max(events)
    for seq in range(1, end + 1):
        if seq not in events:
            event = probe(seq, f"synthetic-passive-{seq}")
            event["kind"] = "time"
            del event["request_id"]
            events[seq] = event
    return [events[i] for i in range(end + 1)]


def _write_raw(path, events):
    data = b"".join(
        (json.dumps(e, sort_keys=True, separators=(",", ":")) + "\n").encode()
        for e in events
    )
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def test_s1_raw_native_matches_all_original_wal_probes_and_child_acks(tmp_path):
    async def scenario(f, lane, server):
        loop, _, _, _, _ = await _run_multi(f, lane, server)
        _close_original_s1(loop)
        anchor = capture_live_wal_history_anchor(loop, lane=lane)
        directory = tmp_path / "s1-source"
        directory.mkdir()
        receipt = freeze_original_s1_wal(
            loop.owner, physical=f.physical, lane=lane,
            anchor=anchor, evidence_dir=directory,
        )
        rows = PhysicalActionJournal.restore(
            loop.owner.files.physical_wal_file, self_id=loop.owner.self_id,
        ).records
        original = tmp_path / "native-original.jsonl"
        events = _stream(rows)
        digest = _write_raw(original, events)
        verified = audit_i4a_original_s1_native_stdout(
            receipt, native_stdout=original,
            expected_native_stdout_sha256=digest,
        )
        assert verified.classification == (
            "I4A_S1_NATIVE_WAL_SOURCE_CORRELATION_CPU_OFFLINE_ONLY"
        )
        assert verified.parent_action_ids == anchor.action_ids
        assert verified.exact_child_acks >= len(rows) * 3
        assert verified.checked_native_probes == len(rows) * 4
        assert not verified.physical_authorized
        assert not verified.independent_paper_attested
        assert not verified.restart_authenticated
        assert original.read_bytes()

        broken = json.loads(json.dumps(events))
        child = next(e for e in broken if e["type"] == "effect_result")
        child["action_id"] = "foreign-look"
        bad_sha = _write_raw(original, broken)
        with pytest.raises(I4AS1NativeSourceHold, match="child effect ACK"):
            audit_i4a_original_s1_native_stdout(
                receipt, native_stdout=original,
                expected_native_stdout_sha256=bad_sha,
            )
        broken = json.loads(json.dumps(events))
        end = rows[-1]["after_seq"]
        broken[end]["snapshot"]["time"]["time_of_day"] += 1
        bad_sha = _write_raw(original, broken)
        with pytest.raises(I4AS1NativeSourceHold, match="probe/position/Native clock"):
            audit_i4a_original_s1_native_stdout(
                receipt, native_stdout=original,
                expected_native_stdout_sha256=bad_sha,
            )
        broken = json.loads(json.dumps(events))
        broken.pop(3)
        bad_sha = _write_raw(original, broken)
        with pytest.raises(I4AS1NativeSourceHold, match="stream invalid"):
            audit_i4a_original_s1_native_stdout(
                receipt, native_stdout=original,
                expected_native_stdout_sha256=bad_sha,
            )
        broken = json.loads(json.dumps(events))
        broken[-1]["session_id"] = "foreign-native"
        bad_sha = _write_raw(original, broken)
        with pytest.raises(I4AS1NativeSourceHold, match="stream invalid"):
            audit_i4a_original_s1_native_stdout(
                receipt, native_stdout=original,
                expected_native_stdout_sha256=bad_sha,
            )
    _fixture(tmp_path, scenario)


def test_s1_command_capture_rejects_missing_duplicate_and_replaced_effects(tmp_path):
    from relay_self.i_lane_i4a_s1_native_command_audit_dev import audit_i4a_s1_native_commands

    async def scenario(f, lane, server):
        loop, _, _, _, _ = await _run_multi(f, lane, server)
        _close_original_s1(loop)
        anchor = capture_live_wal_history_anchor(loop, lane=lane)
        directory = tmp_path / "capture"
        directory.mkdir()
        captured = freeze_original_s1_wal(
            loop.owner, physical=f.physical, lane=lane, anchor=anchor, evidence_dir=directory,
        )
        rows = PhysicalActionJournal.restore(
            loop.owner.files.physical_wal_file, self_id=loop.owner.self_id,
        ).records
        stdout = tmp_path / "stdout"
        stdout_sha = _write_raw(stdout, _stream(rows))
        commands = []
        for row in rows:
            start, target = row["started_position"], row["target_position"]
            yaw = math.atan2(start["x"] - target["x"], start["z"] - target["z"])
            assert yaw == pytest.approx(row["aim_yaw_rad"])
            parent = row["action_id"]
            commands.extend([
                (row["effect_seqs"][0], {"type": "effect", "action_id": parent + "-look",
                                          "effect": "look", "yaw": yaw, "pitch": 0}),
                (row["effect_seqs"][1], {"type": "effect", "action_id": parent + "-start",
                                          "effect": "set_control", "control": "forward", "state": True}),
                (row["effect_seqs"][2], {"type": "effect", "action_id": parent + "-stop",
                                          "effect": "clear_controls"}),
            ])
            if row.get("gait_ack_seq") is not None:
                commands.append((row["gait_ack_seq"], {"type": "effect", "action_id": parent + "-sneak",
                                  "effect": "set_control", "control": "sneak", "state": True}))
        commands = [command for _, command in sorted(commands)]
        stdin = tmp_path / "stdin"
        def audit(items):
            sha = _write_raw(stdin, items)
            return audit_i4a_s1_native_commands(
                captured, native_stdout=stdout, expected_native_stdout_sha256=stdout_sha,
                native_stdin=stdin, expected_native_stdin_sha256=sha,
            )
        assert audit(commands).child_commands == len(commands)
        for broken in (commands[1:], commands + commands[:1],
                       [dict(commands[0], action_id="foreign")] + commands[1:]):
            with pytest.raises(I4AS1NativeSourceHold, match="stdin correlation"):
                audit(broken)

        # A valid SHA over forged stdin is not proof of an authentic heading.
        for change in (
            {"yaw": commands[0]["yaw"] + 0.4},
            {"pitch": 0.3},
            {"yaw": math.nan},
            {"yaw": math.inf},
            {"unexpected": "ignored-before"},
        ):
            wrong = [dict(command) for command in commands]
            wrong[0].update(change)
            with pytest.raises(I4AS1NativeSourceHold, match="stdin correlation"):
                audit(wrong)

        # No custom observe/shutdown envelope can disguise a source mutation.
        for extra in (
            {"type": "observe", "request_id": "valid-id", "effect": "look"},
            {"type": "observe", "request_id": "not valid"},
            {"type": "shutdown", "effect": "look"},
            {"type": "shutdown"},
        ):
            with pytest.raises(I4AS1NativeSourceHold, match="stdin correlation"):
                audit([extra, *commands])

        # The valid original heading still holds with inert observation frames.
        assert audit([{"type": "observe", "request_id": "native-a-1"}, *commands]).child_commands == len(commands)
        assert audit([*commands, {"type": "shutdown"}]).child_commands == len(commands)
    _fixture(tmp_path, scenario)
