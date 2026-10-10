"""E8 operator-owned runner: entirely fake pipes; NEVER start Minecraft.

The production `--run` path is not called here. No test installs Java, starts
a Minecraft server, invokes Node, accepts an EULA or sends World commands.
"""
from __future__ import annotations

import asyncio
import copy
import io
import json
from dataclasses import FrozenInstanceError

import pytest

import test_postmain_source_native_world as s27
from adapters.mineflayer.python_protocol import encode_observe, encode_shutdown
from experiments import epistemic_e8_operator_calibration as e8


def native_frames(*, suffix: bool = False) -> list[dict]:
    _data, _failed, _inputs, args = s27._fixture(distance_m=1.8)
    o = args["observation"]
    snap = s27._snapshot_wire(o.snapshot)
    sid = o.session_id
    none = copy.deepcopy(snap)
    none["nearby_entities"] = []
    none["nearby_entities_coverage"]["candidate_count"] = 0
    near = copy.deepcopy(snap)
    near["nearby_entities"][0]["id"] = 43
    near["nearby_entities"][0]["distance"] = 0.2
    near["nearby_entities"][0]["position"]["x"] = near["position"]["x"] + 0.2

    def observed(seq, kind, ss, *, request=None):
        v = {
            "type": "observation", "session_id": sid, "seq": seq,
            "kind": kind, "snapshot": copy.deepcopy(ss),
        }
        if request:
            v["request_id"] = request
        return v

    frames = [
        {"type": "adapter_started", "session_id": sid, "seq": 0,
         "mineflayer_version": s27.MINEFLAYER_VERSION,
         "config": {"host": "127.0.0.1", "port": 25565, "username": "RelaySelf",
                    "version": "1.21.8"}},
        observed(1, "spawn", none),
        observed(2, "entities", snap),
        observed(3, "probe", snap, request="e7:far:one"),
        observed(4, "entities", none),
        observed(5, "entities", near),
        observed(6, "probe", near, request="e7:near:two"),
        {"type": "shutdown_ack", "session_id": sid, "seq": 7},
    ]
    if suffix:
        frames.append({
            "type": "connection_end", "session_id": sid, "seq": 8,
            "reason": "RelaySelf adapter shutdown",
        })
    return frames


def line_bytes(frames: list[dict]) -> bytes:
    return b"".join((json.dumps(v, separators=(",", ":")) + "\n").encode()
                    for v in frames)


class FakeStdout:
    def __init__(self, raw: bytes):
        self.lines = iter(raw.splitlines(keepends=True))

    async def readline(self):
        return next(self.lines, b"")


class FakeStdin:
    def __init__(self):
        self.writes: list[bytes] = []

    def write(self, payload):
        self.writes.append(payload)

    async def drain(self):
        return None


class FakeProcess:
    def __init__(self, raw: bytes):
        self.stdin = FakeStdin()
        self.stdout = FakeStdout(raw)
        self.returncode = None
        self.wait_count = 0

    async def wait(self):
        self.wait_count += 1
        self.returncode = 0
        return 0


def invoke(frames: list[dict]):
    proc = FakeProcess(line_bytes(frames))
    stream = io.BytesIO()
    prompts = []
    receipt = asyncio.run(e8.capture_one(
        proc, stream, message_timeout_s=3, prompts=prompts,
    ))
    return proc, stream.getvalue(), prompts, receipt


def reject(mutator, *, suffix=False):
    frames = native_frames(suffix=suffix)
    mutator(frames)
    proc = FakeProcess(line_bytes(frames))
    stream = io.BytesIO()
    with pytest.raises((e8.E8Blocked, ValueError)):
        asyncio.run(e8.capture_one(
            proc, stream, message_timeout_s=3, prompts=[],
        ))
    assert all(
        b'"type":"effect"' not in command
        for command in proc.stdin.writes
    )
    assert len(proc.stdin.writes) <= 3
    assert all(
        b'"type":"observe"' in command or b'"type":"shutdown"' in command
        for command in proc.stdin.writes
    )


def test_frozen_manifest_and_external_E7_exact_authority():
    assert e8.digest() == e8.MANIFEST_SHA256
    assert e8.MANIFEST["exact_e7_base"] == (
        "83c5768cf17e3f9adb5a9125fe77db1f418124fb"
    )
    assert e8.MANIFEST["bot_motion_limit_m"] == 0.01
    assert "not authorized" in e8.MANIFEST["physical_execution_here"]
    altered = dict(e8.MANIFEST)
    altered["bot_motion_limit_m"] = 0.2
    assert e8.digest(altered) != e8.MANIFEST_SHA256


@pytest.mark.parametrize("suffix", [False, True])
def test_full_native_raw_preserved_and_only_two_read_commands_one_shutdown(suffix):
    frames = native_frames(suffix=suffix)
    process, raw, prompts, result = invoke(frames)
    assert raw == line_bytes(frames)
    assert process.wait_count == 1 and process.returncode == 0
    assert process.stdin.writes == [
        encode_observe("e7:far:one").encode(),
        encode_observe("e7:near:two").encode(),
        encode_shutdown().encode(),
    ]
    assert prompts == [e8.PROMPT_FAR, e8.PROMPT_GONE, e8.PROMPT_NEAR]
    assert result.classification == "LOCAL_OPERATOR_TRACE_CANDIDATE_UNATTESTED"
    assert not result.physically_authenticated
    assert not result.e5_physical_study_authorized
    assert not result.action_issued
    assert not result.world_server_started_by_e8
    assert not result.minecraft_world_mutation_sent_by_e8
    assert result.bridge_exit_code == 0
    assert result.first_probe_seq == 3 and result.second_probe_seq == 6
    assert result.far_entity_id == 42 and result.near_entity_id == 43
    assert result.source_bytes == len(raw)
    assert result.frames == len(frames)
    assert result.observed_close_suffix == ("connection_end" if suffix else "NONE")
    assert result.audited_prefix_bytes == len(line_bytes(frames[:8]))
    with pytest.raises(FrozenInstanceError):
        result.physically_authenticated = True


@pytest.mark.parametrize("index,key,value", [
    (0, "seq", 1),
    (0, "type", "observation"),
    (0, "mineflayer_version", "unknown"),
    (0, "session_id", "alien"),
    (1, "kind", "death"),
    (2, "kind", "probe"),
    (3, "request_id", "e7:wrong:one"),
    (3, "seq", 2),
    (4, "kind", "probe"),
    (5, "kind", "respawn"),
    (6, "request_id", "e7:far:one"),
    (6, "seq", 5),
    (7, "type", "connection_end"),
])
def test_bad_native_session_events_fail_without_any_action(index, key, value):
    reject(lambda f: f[index].__setitem__(key, value))


@pytest.mark.parametrize("index,cm", [(2, 2.0), (3, 2.0), (5, 0.3), (6, 0.19)])
def test_actual_rounded_source_geometry_must_match_frozen_request(index, cm):
    def change(frames):
        target = frames[index]["snapshot"]["nearby_entities"][0]
        target["distance"] = cm
        target["position"]["x"] = frames[index]["snapshot"]["position"]["x"] + cm
    reject(change)


@pytest.mark.parametrize("index", [2, 3, 5, 6])
def test_source_target_mismatch_or_ambiguous_zombies_fail(index):
    def bad_id(frames):
        frames[index]["snapshot"]["nearby_entities"][0]["id"] = 991
    reject(bad_id)
    def two(frames):
        snap = frames[index]["snapshot"]
        snap["nearby_entities"].append(copy.deepcopy(snap["nearby_entities"][0]))
        snap["nearby_entities_coverage"]["candidate_count"] = 2
    reject(two)


@pytest.mark.parametrize("index", [2, 3, 4, 5, 6])
def test_uncommanded_bot_motion_makes_calibration_fail(index):
    def movement(frames):
        frames[index]["snapshot"]["position"]["z"] += 0.03
    reject(movement)


def test_native_absence_and_new_spawn_must_be_causally_separate():
    def deleted_gone(frames):
        frames[4]["snapshot"] = copy.deepcopy(frames[3]["snapshot"])
    reject(deleted_gone)
    def same_id(frames):
        frames[5]["snapshot"]["nearby_entities"][0]["id"] = 42
    reject(same_id)
    def stale_first(frames):
        frames[3]["snapshot"]["nearby_entities"][0]["id"] = 997
    reject(stale_first)


def test_only_close_suffix_after_ack_allowed():
    def other_close(frames):
        frames[-1]["type"] = "shutdown_ack"
    reject(other_close, suffix=True)
    def doubled(frames):
        frames.append({
            "type": "command_error", "session_id": frames[0]["session_id"],
            "seq": len(frames), "message": "unexpected trailing data",
        })
    reject(doubled, suffix=True)


def test_no_action_frame_ever_allowed():
    def effect(frames):
        frames[5] = {
            "type": "effect_result", "session_id": frames[0]["session_id"],
            "seq": 5, "action_id": "stale",
            "effect": "set_control", "result": "applied", "error": None,
        }
    reject(effect)


def test_missing_or_extra_frames_and_wrong_host_rejected():
    reject(lambda frames: frames.pop(4))
    reject(lambda frames: frames[0]["config"].__setitem__("host", "0.0.0.0"))
    reject(lambda frames: frames[0]["config"].__setitem__("version", "1.20.1"))
    reject(lambda frames: frames[0]["config"].__setitem__("username", "Imposter"))
    reject(lambda frames: frames.append(copy.deepcopy(frames[6])))


@pytest.mark.parametrize("confirmation", [None, "", "I AGREE", "S31-A"])
def test_local_run_gate_fails_without_explicit_fresh_operator_permission(
    tmp_path, confirmation,
):
    raw = tmp_path / "one.jsonl"
    report = tmp_path / "one.json"
    with pytest.raises(e8.E8Blocked):
        e8.validate_run_gate(True, confirmation, raw, report, environ={})
    with pytest.raises(e8.E8Blocked):
        e8.validate_run_gate(False, e8.CONFIRMATION, raw, report, environ={})


@pytest.mark.parametrize("env", [
    {"CI": "true"},
    {"GITHUB_ACTIONS": "true"},
    {"NODE_OPTIONS": "--require fake-mineflayer"},
])
def test_ci_and_test_preloads_cannot_launch_physical_bridge(tmp_path, env):
    with pytest.raises(e8.E8Blocked):
        e8.validate_run_gate(
            True, e8.CONFIRMATION,
            tmp_path / "native.jsonl", tmp_path / "native.json",
            environ=env,
        )


def test_gate_requires_two_fresh_distinct_outputs_and_existing_directories(tmp_path):
    r = tmp_path / "native.jsonl"
    p = tmp_path / "native.json"
    e8.validate_run_gate(True, e8.CONFIRMATION, r, p, environ={})
    r.write_text("existing", encoding="utf-8")
    with pytest.raises(e8.E8Blocked):
        e8.validate_run_gate(True, e8.CONFIRMATION, r, p, environ={})
    with pytest.raises(e8.E8Blocked):
        e8.validate_run_gate(
            True, e8.CONFIRMATION, tmp_path / "new.jsonl",
            tmp_path / "new.jsonl", environ={},
        )
    with pytest.raises(e8.E8Blocked):
        e8.validate_run_gate(
            True, e8.CONFIRMATION, tmp_path / "unmade" / "native.jsonl",
            p, environ={},
        )


def test_plan_and_denied_cli_do_not_call_live_run(tmp_path, capsys, monkeypatch):
    called = []

    async def forbidden(*_a, **_kw):
        called.append("LIVE")
        raise AssertionError("CI must never launch")

    monkeypatch.setattr(e8, "run_once", forbidden)
    assert e8.main(["--plan"]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["classification"] == "E8_PLAN_ONLY_NO_WORLD_ATTEMPT"
    assert plan["world_launched_by_e8"] is False
    assert plan["physical_execution_authorized"] is False
    assert e8.main(["--run"]) == 2
    denied = json.loads(capsys.readouterr().out)
    assert denied["classification"] == "E8_NOT_AUTHORIZED_TO_LAUNCH"
    assert denied["world_launched_by_e8"] is False
    assert called == []


def test_bounded_transport_timeout_and_unframed_stream_fail():
    f = native_frames()
    process = FakeProcess(line_bytes(f))
    with pytest.raises(e8.E8Blocked):
        asyncio.run(e8.capture_one(process, io.BytesIO(), message_timeout_s=0))
    with pytest.raises(e8.E8Blocked):
        asyncio.run(e8.capture_one(process, io.BytesIO(), message_timeout_s=121))


def test_no_bypass_via_source_label_or_pretend_real_outcome():
    _proc, _raw, _prompts, report = invoke(native_frames())
    assert report.classification == "LOCAL_OPERATOR_TRACE_CANDIDATE_UNATTESTED"
    assert report.physical_geometry != "PASS"
    assert "INDEPENDENT" in report.physical_geometry
    assert report.e5_physical_study_authorized is False
