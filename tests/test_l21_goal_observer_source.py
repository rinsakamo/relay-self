"""L21 separate-client source only; byte/Action join, no real Minecraft."""
from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import replace

import pytest

import test_l13_independent_goal_receipt as l13
import test_l20_external_goal_commitment as l20
from adapters.mineflayer.l21_goal_observer_source import (
    L21ObserverRejected,
    review_l21_observer_original,
)


def fixture(*, status="REACHED"):
    args, criterion_original, goal_sha = l20.src()
    session, action = args["session_id"], args["action_id"]
    first = f"l16:{session}:{action}:goal-1"
    second = f"l16:{session}:{action}:goal-2"
    plan = args["plan"]
    if status == "REACHED":
        a = (plan.target_x, plan.target_z)
        b = (plan.target_x + 0.01, plan.target_z)
    elif status == "NOT_REACHED":
        a = (plan.target_x + 10, plan.target_z)
        b = (plan.target_x + 10.01, plan.target_z)
    elif status == "UNDETERMINED":
        a = (plan.target_x, plan.target_z)
        b = (plan.target_x + 1, plan.target_z)
    else:
        raise AssertionError(status)

    def position(x, z):
        return {"entity_id": 77, "x": x, "y": 64, "z": z}

    raw_rows = [
        {
            "kind": "start", "criterion_sha256": goal_sha,
            "observer_username": "RelayGoalObservr",
            "target_username": "RelaySelf",
            "observer_capabilities": "READ_ONLY_MINEFLAYER_SECOND_TCP_CLIENT",
            "goal_observation_authority": False,
        },
        {"kind": "ready", "observer_entity_id": 3},
        {"kind": "sample", "request_id": first, "position": position(*a)},
        {"kind": "sample", "request_id": second, "position": position(*b)},
        {
            "kind": "goal_result", "first_request_id": first,
            "second_request_id": second, "goal_status": status,
        },
        {"kind": "closed", "samples": 2},
    ]
    for i, row in enumerate(raw_rows):
        row.update({
            "schema": "L21_SEPARATE_CLIENT_GOAL_OBSERVER_V1",
            "observer_session": "observer-test-123", "index": i,
        })
    raw = b"".join(l13.raw(x) for x in raw_rows)
    kwargs = {
        "raw": raw, "criterion_original": criterion_original,
        "criterion_sha256": goal_sha, "plan": plan,
        "session_id": session, "action_id": action,
        "native_goal_status": status,
    }
    return kwargs, raw_rows


@pytest.mark.parametrize("status", ["REACHED", "NOT_REACHED", "UNDETERMINED"])
def test_separate_client_can_report_source_shaped_goal_without_learning(status):
    kwargs, _ = fixture(status=status)
    review = review_l21_observer_original(**kwargs)
    assert review.goal_status == status
    assert review.original_sha256 == hashlib.sha256(kwargs["raw"]).hexdigest()
    assert review.diagnostic_agreement is (None if status == "UNDETERMINED" else True)
    assert review.physical_second_tcp_client_source_claim
    assert not review.tcp_authenticated_independently
    assert not review.separate_external_goal_owner_authenticated
    assert not review.independently_attested_nonintervention
    assert review.qualified_real_learning_pairs == 0
    assert review.s10_updates == review.s11_grants == 0


def test_other_client_goal_disagreement_stays_visible_but_unqualified():
    kwargs, _ = fixture()
    kwargs["native_goal_status"] = "NOT_REACHED"
    review = review_l21_observer_original(**kwargs)
    assert review.goal_status == "REACHED"
    assert review.diagnostic_agreement is False
    assert review.qualified_real_learning_pairs == 0


@pytest.mark.parametrize("fault", [
    "sha", "criterion_geometry", "session", "action", "remove_line",
    "duplicate_line", "shuffle_samples", "duplicate_seq", "other_observer",
    "target_changed", "owner_authority", "observer_swapped",
    "unknown_position", "wrong_entity_id", "unstable_wrong_label",
    "same_self_entity", "other_request", "wrong_result_request",
    "not_closed", "not_ready", "fake_physically_qualified",
    "extra_goal_result", "wrong_sample_count", "negative_entity_id",
    "duplicate_json_key", "oversized", "malformed_json",
])
def test_unsafe_observer_original_is_not_promoted(fault):
    kwargs, data = fixture()
    if fault == "sha":
        kwargs["criterion_sha256"] = "f" * 64
    elif fault == "criterion_geometry":
        kwargs["plan"] = replace(kwargs["plan"], target_z=12345)
    elif fault == "session":
        kwargs["session_id"] = "other-session"
    elif fault == "action":
        kwargs["action_id"] = "foreign-action"
    elif fault == "remove_line":
        data.pop(3)
    elif fault == "duplicate_line":
        data.append(data[3].copy())
    elif fault == "shuffle_samples":
        data[2], data[3] = data[3], data[2]
    elif fault == "duplicate_seq":
        data[3]["index"] = 2
    elif fault == "other_observer":
        data[0]["observer_username"] = "RelaySelf"
    elif fault == "target_changed":
        data[0]["target_username"] = "Another"
    elif fault == "owner_authority":
        data[0]["goal_observation_authority"] = True
    elif fault == "observer_swapped":
        data[2]["observer_session"] = "foreign"
    elif fault == "unknown_position":
        data[3]["position"]["x"] = None
    elif fault == "wrong_entity_id":
        data[3]["position"]["entity_id"] = "foreign"
    elif fault == "unstable_wrong_label":
        data[3]["position"]["x"] += 10
    elif fault == "same_self_entity":
        data[3]["position"]["entity_id"] = 3
    elif fault == "other_request":
        data[3]["request_id"] = "foreign-goal-request"
    elif fault == "wrong_result_request":
        data[4]["second_request_id"] = "wrong"
    elif fault == "not_closed":
        data[-1]["kind"] = "fault"
    elif fault == "not_ready":
        data[1]["kind"] = "start"
    elif fault == "fake_physically_qualified":
        data[4]["physical_learning_attested"] = True
    elif fault == "extra_goal_result":
        data.append(data[4].copy())
    elif fault == "wrong_sample_count":
        data[-1]["samples"] = 3
    elif fault == "negative_entity_id":
        data[3]["position"]["entity_id"] = -1
    else:
        pass
    if fault not in ("sha", "criterion_geometry", "session", "action"):
        kwargs["raw"] = b"".join(l13.raw(x) for x in data)
    if fault == "oversized":
        kwargs["raw"] += b" " * 80000
    elif fault == "malformed_json":
        kwargs["raw"] = b"garbage\n"
    elif fault == "duplicate_json_key":
        kwargs["raw"] = kwargs["raw"].replace(
            b'"kind":"sample"', b'"kind":"start","kind":"sample"', 1
        )
    with pytest.raises((L21ObserverRejected, ValueError, TypeError)):
        review_l21_observer_original(**kwargs)


@pytest.mark.parametrize("fault", [
    "no_l20", "no_l16", "same_directory",
    "nested_directory", "used_output", "symlink",
])
def test_s49_l21_preflight_blocks_without_java_or_mineflayer(tmp_path, monkeypatch, fault):
    from adapters.mineflayer import s49_normal_session_real_ci as s49

    args, original, sha = l20.src()
    external = tmp_path / "external.jsonl"
    external.write_bytes(original)
    capture = tmp_path / "capture"
    capture.mkdir()
    observer = tmp_path / "observer"
    observer.mkdir()
    if fault == "no_l20":
        external = None
        sha = None
    elif fault == "no_l16":
        capture = None
    elif fault == "same_directory":
        observer = capture
    elif fault == "nested_directory":
        observer = capture / "nested"
        observer.mkdir()
    elif fault == "used_output":
        (observer / "l21_separate_client_goal_original.jsonl").write_bytes(b"old\n")
    elif fault == "symlink":
        observer_link = tmp_path / "observer-link"
        observer_link.symlink_to(observer, target_is_directory=True)
        observer = observer_link

    def no_java(*_args, **_kwargs):
        pytest.fail("invalid second observer spec cannot start Java")

    monkeypatch.setattr(s49, "_fetch_official_server", no_java)
    monkeypatch.setenv("S49_REAL_SERVER_CI", "1")
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    report = tmp_path / "report.json"
    rc = asyncio.run(s49.qualify(
        report, tmp_path / "java.log",
        l16_capture_root=capture, l16_goal_plan=args["plan"],
        l20_external_goal_original=external,
        l20_admitted_sha256=sha,
        l21_observer_root=observer,
    ))
    assert rc == 2
    assert json.loads(report.read_bytes())["status"] == "BLOCKED"
    assert not (tmp_path / "java.log").exists()


def test_synthetic_node_lifecycle_closes_input_and_seals_original(tmp_path, monkeypatch):
    """Actual Node pipe lifecycle with a fake bot; no TCP/physical claim."""
    import shutil

    from adapters.mineflayer.l21_goal_observer_source import L21ObserverSession

    if shutil.which("node") is None:
        pytest.skip("Node needed for synthetic pipe lifecycle")
    runtime = tmp_path / "runtime"
    package = runtime / "node_modules" / "mineflayer"
    package.mkdir(parents=True)
    (runtime / "package.json").write_text('{"private":true}\n')
    (package / "package.json").write_text(
        '{"version":"4.39.0","main":"index.cjs"}\n')
    (package / "index.cjs").write_text("""
const { EventEmitter } = require('node:events')
exports.createBot = options => {
  const bot = new EventEmitter()
  bot.username = options.username
  bot.entity = { id: 99 }
  bot.players = { RelaySelf: { entity: {
    id: 44, position: { x: 10, y: 64, z: -4 }
  } } }
  bot.quit = () => setImmediate(() => bot.emit('end', 'synthetic quit'))
  setImmediate(() => bot.emit('spawn'))
  return bot
}
""")
    monkeypatch.setenv("RELAYSELF_RSEE_NODE_RUNTIME_ROOT", str(runtime))
    _, raw, sha = l20.src()
    criterion = tmp_path / "criterion.jsonl"
    criterion.write_bytes(raw)
    output = tmp_path / "observer.jsonl"

    async def exercise():
        session = await L21ObserverSession.launch(
            source_path=output, criterion_path=criterion, criterion_sha256=sha)
        try:
            await session.sample("l16:synthetic:action:goal-1")
            await session.sample("l16:synthetic:action:goal-2")
            return await session.close()
        finally:
            await session.terminate()

    result = asyncio.run(exercise())
    rows = [json.loads(line) for line in result.splitlines()]
    assert [r["kind"] for r in rows] == [
        "start", "ready", "sample", "sample", "goal_result", "closed"]
    assert rows[-1]["samples"] == 2
    timings = [json.loads(line) for line in
               output.with_name(output.name + ".timing.jsonl").read_text().splitlines()]
    assert [r["index"] for r in timings] == list(range(6))
    assert all(int(a["monotonic_ns"]) <= int(b["monotonic_ns"])
               for a, b in zip(timings, timings[1:]))
