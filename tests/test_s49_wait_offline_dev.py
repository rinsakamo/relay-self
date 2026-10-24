"""End-to-end DEV-only source projection: no World or Action dispatch."""
from __future__ import annotations

import asyncio
import json
from copy import deepcopy
from types import SimpleNamespace

import pytest

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_wait_fenced_executor_dev import S49WaitFencedExecutorDev
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
    assert result == saved
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
