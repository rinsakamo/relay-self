"""E9 prospective successor tests: fake source pipes ONLY; no physical run."""
from __future__ import annotations

import asyncio
import copy
import io
import json

import pytest

import test_epistemic_e8_operator_calibration as e8_fixture
from adapters.mineflayer.python_protocol import encode_observe, encode_shutdown
from experiments import epistemic_e7_native_trace_gate as e7
from experiments import epistemic_e8_operator_calibration as e8
from experiments import epistemic_e9_native_hurt_gate as gate
from experiments import epistemic_e9_hurt_aware_operator as e9


def frames_with_hurt(*, suffix: bool = False) -> list[dict]:
    frames = e8_fixture.native_frames(suffix=suffix)
    old_id = frames[2]["snapshot"]["nearby_entities"][0]["id"]
    frames.insert(4, {
        "type": "entity_hurt", "session_id": frames[0]["session_id"],
        "seq": 4, "entity_id": old_id,
        "source_entity_id": None, "actor_entity_id": 1,
    })
    renumber(frames)
    return frames


def renumber(frames: list[dict]) -> None:
    for i, frame in enumerate(frames):
        frame["seq"] = i


def attempt(frames: list[dict]):
    process = e8_fixture.FakeProcess(e8_fixture.line_bytes(frames))
    out = io.BytesIO()
    prompts: list[str] = []
    receipt = asyncio.run(e9.capture_one(
        process, out, message_timeout_s=3, prompts=prompts,
    ))
    return process, out.getvalue(), prompts, receipt


def rejected(change, *, start=None):
    frames = copy.deepcopy(start if start is not None else frames_with_hurt())
    change(frames)
    process = e8_fixture.FakeProcess(e8_fixture.line_bytes(frames))
    out = io.BytesIO()
    with pytest.raises((e9.E9Blocked, e7.E7Rejected, ValueError)):
        asyncio.run(e9.capture_one(
            process, out, message_timeout_s=3, prompts=[],
        ))
    assert all(
        b'"type":"observe"' in w or b'"type":"shutdown"' in w
        for w in process.stdin.writes
    )
    assert len(process.stdin.writes) <= 3


@pytest.mark.parametrize("suffix", [False, True])
def test_one_old_hurt_is_kept_byte_for_byte_and_is_not_gone(suffix):
    frames = frames_with_hurt(suffix=suffix)
    proc, raw, prompts, result = attempt(frames)
    assert raw == e8_fixture.line_bytes(frames)
    assert proc.stdin.writes == [
        encode_observe("e7:far:one").encode(),
        encode_observe("e7:near:two").encode(),
        encode_shutdown().encode(),
    ]
    assert prompts == [e9.PROMPT_FAR, e9.PROMPT_GONE, e9.PROMPT_NEAR]
    assert result.hurt_event_count == 1
    assert result.first_probe_seq == 3 and result.second_probe_seq == 7
    assert result.far_entity_id == 42 and result.near_entity_id == 43
    assert result.frames == len(frames)
    assert result.audited_prefix_bytes == len(
        e8_fixture.line_bytes(frames[:9])
    )
    assert result.classification == "LOCAL_E9_OPERATOR_TRACE_CANDIDATE_UNATTESTED"
    assert not result.physically_authenticated
    assert not result.e5_physical_study_authorized
    assert not result.action_issued
    assert not result.world_server_started_by_e8
    assert not result.minecraft_world_mutation_sent_by_e8
    assert result.bridge_exit_code == 0
    assert proc.wait_count == 1
    assert result.observed_close_suffix == ("connection_end" if suffix else "NONE")
    audit = gate.audit_jsonl(e8_fixture.line_bytes(frames[:9]))
    assert audit.hurt_event_count == 1
    assert audit.total_frames == 9
    assert audit.first_probe_seq == 3 and audit.second_probe_seq == 7
    with pytest.raises(e7.E7Rejected):
        e7.audit_jsonl(e8_fixture.line_bytes(frames[:9]))
    with pytest.raises(e8.E8Blocked):
        oldproc = e8_fixture.FakeProcess(e8_fixture.line_bytes(frames))
        asyncio.run(e8.capture_one(oldproc, io.BytesIO(), message_timeout_s=3))


def test_baseline_without_hurt_remains_eligible_but_not_authenticated():
    frames = e8_fixture.native_frames()
    _proc, raw, _prompts, receipt = attempt(frames)
    assert raw == e8_fixture.line_bytes(frames)
    assert receipt.hurt_event_count == 0
    assert gate.audit_jsonl(raw).hurt_event_count == 0
    assert receipt.physically_authenticated is False


@pytest.mark.parametrize("field,value", [
    ("entity_id", 111), ("entity_id", 1),
    ("actor_entity_id", 42), ("source_entity_id", 999),
    ("session_id", "impostor"), ("seq", 99),
])
def test_wrong_old_zombie_hurt_is_not_suppressed(field, value):
    rejected(lambda f: f[4].__setitem__(field, value))


def test_duplicate_hurt_rejected_without_rewriting_original_seq():
    def duplicate(f):
        f.insert(5, copy.deepcopy(f[4]))
        renumber(f)
    rejected(duplicate)


def test_hurt_before_far_probe_and_after_native_gone_are_rejected():
    def early(f):
        f.insert(3, f.pop(4))
        renumber(f)
    rejected(early)
    def late(f):
        f.insert(6, f.pop(4))
        renumber(f)
    rejected(late)


def test_hurt_is_never_substitute_for_actual_old_absence():
    def absent_missing(f):
        f[5]["snapshot"] = copy.deepcopy(f[3]["snapshot"])
    rejected(absent_missing)
    def same_near_id(f):
        f[6]["snapshot"]["nearby_entities"][0]["id"] = 42
    rejected(same_near_id)


def test_other_native_event_effect_bot_death_and_geometry_fail_closed():
    def foreign_hurt(f):
        f[4]["type"] = "effect_result"
        f[4].pop("entity_id")
        f[4].pop("source_entity_id")
        f[4].pop("actor_entity_id")
        f[4].update(action_id="false", effect="set_control",
                    result="applied", error=None)
    rejected(foreign_hurt)
    def forced_move(f):
        f[5]["kind"] = "forcedMove"
    rejected(forced_move)
    def near_mismatch(f):
        zombie = f[6]["snapshot"]["nearby_entities"][0]
        zombie["distance"] = 0.35
        zombie["position"]["x"] = f[6]["snapshot"]["position"]["x"] + 0.35
    rejected(near_mismatch)
    def bot_shift(f):
        f[6]["snapshot"]["position"]["z"] += 0.02
    rejected(bot_shift)


def test_p3_five_line_physical_prefix_stays_partial_not_success():
    # The real P3 stopped at native seq4 hurt: no native gone or near probe.
    partial = frames_with_hurt()[:5]
    raw = e8_fixture.line_bytes(partial)
    with pytest.raises(gate.E9Rejected):
        gate.audit_jsonl(raw)
    with pytest.raises((e9.E9Blocked, ValueError)):
        proc = e8_fixture.FakeProcess(raw)
        asyncio.run(e9.capture_one(proc, io.BytesIO(), message_timeout_s=3))


def test_unsafe_traces_fail_full_strict_audit_even_if_live_would_stop_earlier():
    def bad_extra(f):
        f.insert(6, copy.deepcopy(f[4]))
        renumber(f)
    for mutate in [
        lambda f: f.__setitem__(5, copy.deepcopy(f[6])),
        bad_extra,
        lambda f: f.pop(5),
    ]:
        f = frames_with_hurt()
        mutate(f)
        with pytest.raises((gate.E9Rejected, ValueError)):
            gate.audit_jsonl(e8_fixture.line_bytes(f))


def test_new_opt_in_gate_and_ci_remain_fail_closed(tmp_path, capsys, monkeypatch):
    e9._frozen()
    assert e9.CONFIRMATION == "E9-I-OWN-LOCAL-TEST-WORLD"
    assert e9.CONFIRMATION != e8.CONFIRMATION
    assert e9.main(["--plan"]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["classification"] == "E9_PLAN_ONLY_NO_WORLD_ATTEMPT"
    assert plan["physical_execution_authorized"] is False
    assert e9.main(["--run"]) == 2
    denied = json.loads(capsys.readouterr().out)
    assert denied["classification"] == "E9_NOT_AUTHORIZED_TO_LAUNCH"
    for environment in [
        {"CI": "true"}, {"GITHUB_ACTIONS": "true"},
        {"NODE_OPTIONS": "--require mock.js"},
    ]:
        with pytest.raises(e9.E9Blocked):
            e9.validate_run_gate(
                True, e9.CONFIRMATION, tmp_path / "raw.jsonl",
                tmp_path / "report.json", environ=environment,
            )
    called = []
    async def forbidden(*args, **kwargs):
        called.append(True)
        raise AssertionError("physical launch forbidden in tests")
    monkeypatch.setattr(e9, "run_once", forbidden)
    assert e9.main(["--run"]) == 2
    assert called == []
