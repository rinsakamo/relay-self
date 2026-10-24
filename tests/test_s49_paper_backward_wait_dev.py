"""Offline same-S49-Action backward S16 → Paper callback source screen.

All Paper lines are invented *test inputs*. No Minecraft, Java or Node runs.
"""
from __future__ import annotations

import asyncio
import json

import pytest

import adapters.mineflayer.normal_action as original
from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_paper_backward_wait_dev import (
    BEGIN,
    TICK,
    project_s49_backward_paper_dev,
)
from adapters.mineflayer.s49_wait_typed_capture_dev import S49TypedClosureCaptureDev
from test_s49_wait_typed_capture_dev import fixture


def raw_paper(capture, *, initial_tick=70, newline="\n"):
    ex = capture._executor
    action = capture.projection.action_id
    session = ex.session_id
    marker = ex._wait_fence._marker
    world = ex._wait_fence._world
    common = (
        f"marker_id={marker} action_id={action} session_id={session}"
        f" world={world}"
    )
    lines = [f"{BEGIN} {common} tick={initial_tick} index=0"]
    for i in range(1, 9):
        lines.append(f"{TICK} {common} tick={initial_tick+i} index={i}")
    return newline.join(lines) + newline


def typed_owner(monkeypatch):
    ex, probe, receipt, readback = fixture()
    ex._wait_fence._marker = receipt.terminal.action_id + "-" + ex.session_id
    ex._wait_fence._world = "paper-dev-world-s49"

    async def no_native_execute(_session, _step, _bound, _probe, _p, _i):
        original._READ_ONLY_CLOSURE.get()(readback)
        return receipt

    monkeypatch.setattr(ex, "execute", no_native_execute)
    capture = S49TypedClosureCaptureDev(ex)
    asyncio.run(capture.execute_owned(None, None, None, probe, None, None))
    return capture


def run(capture, paper, path):
    return asyncio.run(project_s49_backward_paper_dev(
        capture, paper, output_path=path,
    ))


def test_same_s49_action_s16_clear_and_paper_source_shape(
    monkeypatch, tmp_path,
):
    capture = typed_owner(monkeypatch)
    ex = capture._executor
    path = tmp_path / "s49-paper.json"
    paper = raw_paper(capture)
    outcome = run(capture, paper, path)
    saved = json.loads(path.read_text())
    assert json.loads(json.dumps(outcome)) == saved
    assert outcome["status"] == "SAME_ACTION_PAPER_SHAPE_ONLY"
    assert outcome["session_id"] == ex.session_id
    assert outcome["action_id"] == capture.projection.action_id
    assert outcome["typed_s16_sha256"] == capture.projection.evidence_sha256
    assert outcome["source_authentication"] == "UNATTESTED_CALLER_PAPER_INPUT"
    assert outcome["server_effective_control_release"] == "NOT_ATTESTED"
    assert outcome["whole_tick_self_inactivity"] == "NOT_ATTESTED"
    assert outcome["all_action_issuers_idle"] == "NOT_ATTESTED"
    assert outcome["owner_review"]["owner_original_rows"] == 10
    assert [row["world_tick"] for row in outcome["owner_rows"][1:9]] == (
        list(range(71, 79))
    )
    assert ex.wait_phase == "SEALED"
    assert capture.state == "ARMED"
    assert outcome["source_bound_tick"] is None
    assert outcome["wait_interval_ref"] is None
    assert outcome["wait_ticks_admitted"] == 0
    assert outcome["p1_fatigue_recovered"] == 0.0
    assert path.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("mutation", [
    "wrong_action", "wrong_session", "wrong_world", "wrong_marker",
    "duplicate_tick", "missing_tick", "gapped_tick", "reordered",
    "missing_begin", "begin_late", "bad_index", "unknown_field",
    "duplicated_field", "extra_kind", "ambiguous_number",
])
def test_invalid_paper_or_cross_action_source_never_admits(
    monkeypatch, tmp_path, mutation,
):
    capture = typed_owner(monkeypatch)
    value = raw_paper(capture)
    if mutation == "wrong_action":
        value = value.replace(
            "action_id=" + capture.projection.action_id,
            "action_id=foreign-action", 1,
        )
    elif mutation == "wrong_session":
        value = value.replace(
            "session_id=" + capture.projection.session_id,
            "session_id=foreign-session", 1,
        )
    elif mutation == "wrong_world":
        value = value.replace("world=paper-dev-world-s49", "world=foreign", 1)
    elif mutation == "wrong_marker":
        value = value.replace("marker_id=", "marker_id=foreign-", 1)
    elif mutation == "duplicate_tick":
        line = [r for r in value.splitlines() if r.startswith(TICK)][0]
        value += line + "\n"
    elif mutation == "missing_tick":
        value = "\n".join(
            line for line in value.splitlines() if "index=5" not in line
        )
    elif mutation == "gapped_tick":
        value = value.replace("tick=74 index=4", "tick=75 index=4", 1)
    elif mutation == "reordered":
        rows = value.splitlines()
        rows[2], rows[3] = rows[3], rows[2]
        value = "\n".join(rows) + "\n"
    elif mutation == "missing_begin":
        value = "\n".join(value.splitlines()[1:])
    elif mutation == "begin_late":
        value = value.replace("tick=70 index=0", "tick=72 index=0", 1)
    elif mutation == "bad_index":
        value = value.replace("index=3", "index=2", 1)
    elif mutation == "unknown_field":
        value = value.replace(" index=4", " new_field=x index=4", 1)
    elif mutation == "duplicated_field":
        value = value.replace(" index=4", " index=4 index=4", 1)
    elif mutation == "extra_kind":
        value += "S49_DEV_BACK_WAIT_UNKNOWN marker=x\n"
    else:
        value = value.replace("tick=72 index=2", "tick=072 index=2", 1)
    target = tmp_path / "rejected.json"
    with pytest.raises(BoundaryRejected):
        run(capture, value, target)
    report = json.loads(target.read_text())
    assert report["status"] == "REJECTED_NOT_QUALIFIED"
    assert report["source_bound_tick"] is None
    assert report["wait_ticks_admitted"] == 0
    assert report["p1_fatigue_recovered"] == 0.0


def test_s50_forward_protocol_cannot_be_used_as_s49_backward(
    monkeypatch, tmp_path,
):
    from test_s50_p1_wait_joint_dev import originals

    capture = typed_owner(monkeypatch)
    paper = originals()[0]
    path = tmp_path / "legacy-rejected.json"
    with pytest.raises(BoundaryRejected):
        run(capture, paper, path)
    assert json.loads(path.read_text())["status"] == "REJECTED_NOT_QUALIFIED"


def test_no_replay_or_existing_report_overwrite(monkeypatch, tmp_path):
    capture = typed_owner(monkeypatch)
    path = tmp_path / "unique.json"
    run(capture, raw_paper(capture), path)
    first = path.read_bytes()
    with pytest.raises(BoundaryRejected):
        run(capture, raw_paper(capture), tmp_path / "second.json")
    with pytest.raises(BoundaryRejected):
        run(typed_owner(monkeypatch), raw_paper(capture), path)
    assert path.read_bytes() == first
    assert not (tmp_path / "second.json").exists()


def test_source_bytes_distinguish_lf_and_crlf(monkeypatch, tmp_path):
    a = typed_owner(monkeypatch)
    first = run(a, raw_paper(a), tmp_path / "lf.json")
    b = typed_owner(monkeypatch)
    second = run(b, raw_paper(b, newline="\r\n"), tmp_path / "crlf.json")
    assert first["paper_input_sha256"] != second["paper_input_sha256"]
    assert [r["source_ref"] for r in first["owner_rows"][1:9]] != [
        r["source_ref"] for r in second["owner_rows"][1:9]
    ]
    assert first["wait_ticks_admitted"] == second["wait_ticks_admitted"] == 0


def test_cancel_after_arm_records_abort_not_recovery(monkeypatch, tmp_path):
    capture = typed_owner(monkeypatch)
    owner = capture._executor
    target = tmp_path / "cancel.json"

    async def scenario():
        task = asyncio.create_task(project_s49_backward_paper_dev(
            capture, raw_paper(capture), output_path=target,
        ))
        for _ in range(80):
            if owner.wait_phase in {"ARMED", "SAMPLING"}:
                break
            await asyncio.sleep(0)
        assert owner.wait_phase in {"ARMED", "SAMPLING"}
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())
    result = json.loads(target.read_text())
    assert result["status"] == "CANCELLED_NOT_QUALIFIED"
    assert result["owner_rows"][-1]["kind"] == "ABORT"
    assert owner.wait_phase == "ABORTED"
    assert result["p1_fatigue_recovered"] == 0.0


def test_typed_s16_tamper_before_arm_rejects(monkeypatch, tmp_path):
    capture = typed_owner(monkeypatch)
    capture.projection.decoded_evidence["cleanup_receipt"]["result"] = "rejected"
    path = tmp_path / "tampered.json"
    with pytest.raises(BoundaryRejected):
        run(capture, raw_paper(capture), path)
    result = json.loads(path.read_text())
    assert result["status"] == "REJECTED_NOT_QUALIFIED"
    assert result["wait_interval_ref"] is None
