"""End-to-end DEV-only source projection: no World or Action dispatch."""
from __future__ import annotations

import asyncio
import json
from copy import deepcopy
from types import SimpleNamespace

import pytest

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_wait_fenced_executor_dev import S49WaitFencedExecutorDev
from adapters.mineflayer.s49_wait_typed_capture_dev import (
    S49TypedClosureCaptureDev,
)
from adapters.mineflayer.s49_wait_offline_dev import (
    _digest,
    _paper_rows,
    run_s49_s50_offline_dev,
)
from relay_self.action import ActionState
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from test_s50_p1_control_action import ACTION, MARKER, SESSION, WORLD
from test_s50_p1_wait_joint_dev import originals
from test_s49_wait_typed_capture_dev import fixture as typed_source_fixture


def owner(*, prior=True):
    intent = IntentCommitment()
    intent.commit(
        "escape-threat", objective="offline action", at_ns=1,
        provenance=Provenance("offline-fixture", "intent"),
    )
    ex = S49WaitFencedExecutorDev(
        SESSION, intent, marker_id=MARKER, world=WORLD, dev_only=True,
    )
    if prior:
        # Explicitly synthetic: no genuine native Action or qualification.
        ex._dispatched.add(ACTION)
        ex.supervisor._lifecycles[ACTION] = SimpleNamespace(
            state=ActionState.OUTCOME,
        )
    return ex


def run(ex, path, data=None):
    return asyncio.run(run_s49_s50_offline_dev(
        ex, originals() if data is None else data,
        prior_action_id=ACTION, output_path=path,
    ))


def test_same_owner_cross_source_projection_and_atomic_private_report(tmp_path):
    ex = owner()
    target = tmp_path / "run.json"
    result = run(ex, target)
    saved = json.loads(target.read_text())
    # The report is JSON; tuples from the Python screening result become lists.
    assert json.loads(json.dumps(result)) == saved
    assert saved["status"] == "OFFLINE_PROJECTION_ONLY"
    assert ex.wait_phase == "SEALED"
    assert len(saved["owner_rows"]) == 10
    paper = originals()[0]
    expected = _paper_rows(paper, marker=MARKER, world=WORLD, first=61)
    assert [
        r["source_ref"] for r in saved["owner_rows"][1:9]
    ] == [row[1] for row in expected]
    assert saved["input_hashes"]["paper"] == _digest(paper)
    assert saved["source_authentication"] == "UNATTESTED_CALLER_INPUT"
    assert saved["physical_clock_alignment"] == "NOT_ATTESTED"
    assert saved["joint_screen"]["all_action_issuers_proven_idle"] is False
    assert saved["wait_interval_ref"] is None
    assert saved["source_bound_tick"] is None
    assert saved["wait_ticks_admitted"] == 0
    assert saved["p1_fatigue_recovered"] == 0.0
    assert target.stat().st_mode & 0o777 == 0o600


def test_report_is_one_shot_and_same_owner_cannot_repeat(tmp_path):
    target = tmp_path / "run.json"
    ex = owner()
    run(ex, target)
    original = target.read_bytes()
    with pytest.raises(BoundaryRejected):
        run(ex, tmp_path / "another.json")
    with pytest.raises(BoundaryRejected):
        run(owner(), target)
    assert target.read_bytes() == original
    assert not (tmp_path / "another.json").exists()


@pytest.mark.parametrize("tamper", [
    "no_prior", "wrong_session", "wrong_action",
    "rejected_native_clear", "second_action",
    "missing_paper_tick", "double_paper_tick", "swap_ticks",
])
def test_source_damage_is_rejected_and_fault_written(tmp_path, tamper):
    ex = owner(prior=tamper != "no_prior")
    data = list(deepcopy(originals()))
    if tamper == "wrong_session":
        ex.session_id = "foreign-owner"
    elif tamper == "wrong_action":
        data[4]["action_id"] = "foreign-action"
    elif tamper == "rejected_native_clear":
        data[1][4]["result"] = "rejected"
    elif tamper == "second_action":
        data[3].append(deepcopy(data[3][-1]))
    elif tamper == "missing_paper_tick":
        data[0] = "\n".join(
            line for line in data[0].splitlines()
            if "tick=65 index=5" not in line
        )
    elif tamper == "double_paper_tick":
        line = next(
            line for line in data[0].splitlines()
            if line.startswith("S50_DEV_WAIT_TICK ")
        )
        data[0] += "\n" + line
    elif tamper == "swap_ticks":
        lines = data[0].splitlines()
        ix = [i for i, line in enumerate(lines)
              if line.startswith("S50_DEV_WAIT_TICK ")]
        lines[ix[3]], lines[ix[4]] = lines[ix[4]], lines[ix[3]]
        data[0] = "\n".join(lines)
    target = tmp_path / "fail.json"
    with pytest.raises(BoundaryRejected):
        run(ex, target, tuple(data))
    r = json.loads(target.read_text())
    assert r["status"] == "REJECTED_NOT_QUALIFIED"
    assert r["qualification_go"] is False
    assert r["source_bound_tick"] is None
    assert r["p1_fatigue_recovered"] == 0.0


def test_no_overwrite_or_symlink_follow(tmp_path):
    saved = tmp_path / "protected.json"
    saved.write_text("historical")
    link = tmp_path / "link.json"
    link.symlink_to(saved)
    with pytest.raises(BoundaryRejected):
        run(owner(), link)
    assert saved.read_text() == "historical"


def test_cancelled_window_saves_abort_before_rethrow(tmp_path):
    ex = owner()
    target = tmp_path / "cancel.json"

    async def scenario():
        task = asyncio.create_task(run_s49_s50_offline_dev(
            ex, originals(), prior_action_id=ACTION, output_path=target,
        ))
        for _ in range(100):
            if ex.wait_phase in {"ARMED", "SAMPLING"}:
                break
            await asyncio.sleep(0)
        assert ex.wait_phase in {"ARMED", "SAMPLING"}
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())
    report = json.loads(target.read_text())
    assert report["status"] == "CANCELLED_NOT_QUALIFIED"
    assert report["owner_rows"][-1]["kind"] == "ABORT"
    assert ex.wait_phase == "ABORTED"


def test_paper_line_digest_distinguishes_lf_and_crlf():
    paper = originals()[0]
    first = _paper_rows(paper, marker=MARKER, world=WORLD, first=61)
    second = _paper_rows(
        paper.replace("\n", "\r\n"),
        marker=MARKER, world=WORLD, first=61,
    )
    assert [tick for tick, _ in first] == [tick for tick, _ in second]
    assert [ref for _, ref in first] != [ref for _, ref in second]


def test_typed_s16_cannot_be_aliased_to_unrelated_s50_paper_demo(
    tmp_path, monkeypatch,
):
    # Test observer registration using typed S17 fixture; no physical S49 run.
    ex, probe, receipt, readback = typed_source_fixture()
    import adapters.mineflayer.normal_action as original

    async def offline_return(_session, _step, _bound, _probe, _p, _i):
        original._READ_ONLY_CLOSURE.get()(readback)
        return receipt

    monkeypatch.setattr(ex, "execute", offline_return)
    capture = S49TypedClosureCaptureDev(ex)
    asyncio.run(capture.execute_owned(None, None, None, probe, None, None))
    # Set the caller-reported session to S50's marker to test that the typed
    # closure still cannot be claimed as S50's different physical action.
    ex.session_id = SESSION
    out = tmp_path / "typed-incompatible.json"
    with pytest.raises(BoundaryRejected, match="session or Action"):
        asyncio.run(run_s49_s50_offline_dev(
            ex, originals(), prior_action_id=ACTION,
            output_path=out, typed_capture=capture,
        ))
    report = json.loads(out.read_text())
    assert report["closure_mode"] == "TYPED_EXECUTOR_ORIGINAL_DEV"
    assert report["status"] == "REJECTED_NOT_QUALIFIED"
    assert report["typed_s16_evidence_sha256"] == (
        capture.projection.evidence_sha256
    )
    assert report["source_bound_tick"] is None
    assert report["p1_fatigue_recovered"] == 0
    assert ex.wait_phase == "NEW"


def test_typed_capture_must_match_exact_existing_executor(tmp_path):
    ex, _, _, _ = typed_source_fixture()
    capture = S49TypedClosureCaptureDev(ex)
    caller = owner()
    target = tmp_path / "foreign-capture.json"
    with pytest.raises(BoundaryRejected, match="typed S49 owner"):
        asyncio.run(run_s49_s50_offline_dev(
            caller, originals(), prior_action_id=ACTION,
            output_path=target, typed_capture=capture,
        ))
    assert json.loads(target.read_text())["status"] == "REJECTED_NOT_QUALIFIED"
