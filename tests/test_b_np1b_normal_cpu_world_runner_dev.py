"""Normal original CPU Present within real-World runner wiring (offline fixtures).

The integration calls original owner/Bridge, actual Mineflayer process-session
decoder and owned synthetic Paper process; it DOES NOT execute real Paper World.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from experiments.p0d_real_resident_presence_dev import (
    RealResidentPresenceRefusal,
    _freeze_original_normal_cpu_world_readback,
    _verify_original_normal_cpu_world_report,
    run_real_resident_presence,
)
from relay_self.b_np1b_current_composite_source_dev import build_current_composite_source
from relay_self.b_np1b_normal_cpu_world_runner_dev import (
    NormalCpuOriginalHistory,
    OriginalNormalCpuWorldHold,
    capture_original_historical_cpu_source,
    capture_original_initial_cpu_sources,
    exercise_original_normal_cpu_runtime,
    read_original_normal_cpu_pair,
    start_original_normal_cpu_runtime,
    update_original_b_after_a_logout,
)
from relay_self.owned_paper_world_dev import PaperTickReceipt
from test_b_np1b_current_composite_source_dev import current as current
from test_b_np1b_normal_present_poll_dev import current_fixture as current_fixture
from test_b_np1b_normal_present_poll_dev import pair as pair
from test_b_np1b_normal_present_poll_dev import rejoined as rejoined
from test_b_np1b_normal_present_poll_dev import rejoined_present as rejoined_present
from test_b_np1b_fresh_native_update_dev import files


def _history(pair):
    f, initial, native, composite, *_ = pair
    return NormalCpuOriginalHistory(initial, native, composite)


def _owner_state(f):
    return {
        sid: (
            owner.retained, owner.intent, owner.pattern_registry,
            dict(owner.skills), set(owner.pending_questions),
        )
        for sid, owner in f.owners.items()
    }


def test_runner_original_world_cpu_pair_periodic_real_owner_and_b_refresh(pair):
    f = pair[0]
    before_files, before_owner = files(f), _owner_state(f)

    async def scenario():
        readback = await exercise_original_normal_cpu_runtime(
            bridge=f.bridge, history=_history(pair), interval_s=0.02, timeout_s=2.0,
        )
        assert readback.first_a.poll == readback.first_b.poll
        assert readback.later_a.poll == readback.later_b.poll
        assert readback.later_a.source_pair_revision == readback.later_b.source_pair_revision
        assert readback.first_a.source_pair_revision != readback.later_a.source_pair_revision
        assert readback.later_b.poll.b_present.source.composite_receipt.native_revision == (
            readback.updated_b_native.native_revision
        )
        assert readback.first_b.poll.b_present.source.composite_receipt.native_revision != (
            readback.updated_b_native.native_revision
        )
        assert readback.first_a.iteration < readback.later_a.iteration
        assert readback.first_b.iteration < readback.later_b.iteration
        assert f.cognitive._normal_present_scheduler.status("A")[0] == "STOPPED"
        assert f.cognitive._normal_present_scheduler.status("B")[0] == "STOPPED"
        assert all(task.done() for task in f.cognitive._normal_present_scheduler._tasks.values())
        return readback

    readback = asyncio.run(scenario())
    assert readback.first_a.token.native_session_id == f.bridge.sessions["A"].started.session_id
    assert readback.first_b.token.native_session_id == f.bridge.sessions["B"].started.session_id
    assert files(f) == before_files
    assert _owner_state(f) == before_owner
    assert not f.bridge.physical.active_action_ids


def test_runner_witness_frozen_and_independently_read_back(pair, tmp_path):
    f = pair[0]

    async def run():
        return await exercise_original_normal_cpu_runtime(
            bridge=f.bridge, history=_history(pair), interval_s=0.02, timeout_s=2.0,
        )

    readback = asyncio.run(run())
    path = tmp_path / "normal-cpu-world-source-readback.json"
    digest = _freeze_original_normal_cpu_world_readback(
        evidence_dir=tmp_path, readback=readback,
        world_uuid=f.bridge.lifecycle.world.world_id,
        paper_session=f.paper.owned_session_id,
        old_a=pair[4], original_b_native=pair[1][1].native_session_id,
    )
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    trial = dict(
        normal_cpu_present_opt_in=True,
        b_actual_physical_action=False,
        real_l1_l2_gpu_executed=False,
        normal_cpu_present_source_file=str(path),
        normal_cpu_present_source_sha256=digest,
        world_uuid=f.bridge.lifecycle.world.world_id,
        paper_session_id=f.paper.owned_session_id,
        a_original_native_session=pair[4],
        b_original_native_session=pair[1][1].native_session_id,
    )
    _verify_original_normal_cpu_world_report(trial)
    return trial, path


@pytest.mark.parametrize("fault", [
    "sha", "path", "classification", "world", "paper_session",
    "old_a_session", "initial_b_session", "new_b_native", "new_b_request",
    "pair_revision", "b_composite_revision", "paper_cut", "a_continuity",
    "epoch", "a_task_ref", "iteration", "source_no_action",
    "same_revision", "b_seq", "b_identity", "b_actor",
])
def test_tampered_frozen_world_runtime_report_is_hold(pair, tmp_path, fault):
    f = pair[0]

    async def run():
        return await exercise_original_normal_cpu_runtime(
            bridge=f.bridge, history=_history(pair), interval_s=0.02, timeout_s=2.0,
        )

    readback = asyncio.run(run())
    path = tmp_path / "normal-cpu-world-source-readback.json"
    digest = _freeze_original_normal_cpu_world_readback(
        evidence_dir=tmp_path, readback=readback,
        world_uuid=f.bridge.lifecycle.world.world_id,
        paper_session=f.paper.owned_session_id,
        old_a=pair[4], original_b_native=pair[1][1].native_session_id,
    )
    trial = dict(
        normal_cpu_present_opt_in=True, b_actual_physical_action=False,
        real_l1_l2_gpu_executed=False,
        normal_cpu_present_source_file=str(path), normal_cpu_present_source_sha256=digest,
        world_uuid=f.bridge.lifecycle.world.world_id,
        paper_session_id=f.paper.owned_session_id,
        a_original_native_session=pair[4],
        b_original_native_session=pair[1][1].native_session_id,
    )
    data = json.loads(path.read_text())
    if fault == "sha":
        trial["normal_cpu_present_source_sha256"] = "0" * 64
    elif fault == "path":
        trial["normal_cpu_present_source_file"] = str(tmp_path / "foreign.json")
    elif fault == "classification":
        data["classification"] = "REAL_WORLD_PASS"
    elif fault == "world":
        data["world_id"] = "foreign"
    elif fault == "paper_session":
        data["paper_session_id"] = "foreign"
    elif fault == "old_a_session":
        data["original_a_native_session"] = "foreign"
    elif fault == "initial_b_session":
        data["original_b_native_session"] = "foreign"
    elif fault == "new_b_native":
        data["adopted_b_native"]["native_revision"] = "fake"
    elif fault == "new_b_request":
        data["adopted_b_native"]["native_request_id"] = "fake"
    elif fault == "pair_revision":
        data["later_pair_revision"] = "sha256:" + "a" * 64
    elif fault == "b_composite_revision":
        data["later_b"]["composite_revision"] = "sha256:" + "b" * 64
    elif fault == "paper_cut":
        data["later_b"]["paper_log_sha256"] = "a" * 64
    elif fault == "a_continuity":
        data["later_a"]["b_continuity_revision"] = "sha256:" + "c" * 64
    elif fault == "epoch":
        data["a_cpu_epoch"] += 1
    elif fault == "a_task_ref":
        data["a_cpu_task_ref"] = "foreign"
    elif fault == "iteration":
        data["later_b_iteration"] = data["first_b_iteration"]
    elif fault == "source_no_action":
        data["no_gpu_or_physical_action"] = False
    elif fault == "same_revision":
        data["later_pair_revision"] = data["first_pair_revision"]
    elif fault == "b_seq":
        data["later_b"]["native_sequence"] += 1
    elif fault == "b_identity":
        data["later_b"]["self_id"] = "A"
    else:
        data["later_b"]["paper_actor_uuid"] = data["later_a"]["paper_actor_uuid"]
    if fault not in ("sha", "path"):
        path.write_text(json.dumps(data, sort_keys=True) + "\n")
        trial["normal_cpu_present_source_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(RealResidentPresenceRefusal):
        _verify_original_normal_cpu_world_report(trial)


def test_real_runner_rejects_early_initial_source_when_a_already_updated(current):
    f, initial, _, _ = current
    with pytest.raises(OriginalNormalCpuWorldHold):
        capture_original_initial_cpu_sources(bridge=f.bridge)
    assert initial[0].self_id == "A" and initial[1].self_id == "B"


def test_real_runner_builds_actual_historical_a_composite(current):
    f, initial, first_native, _ = current

    async def run():
        return await capture_original_historical_cpu_source(
            bridge=f.bridge, initial_receipts=initial,
        )

    old_history = asyncio.run(run())
    assert old_history.a_native_after_initial.native_revision != first_native.native_revision
    assert old_history.a_historical_composite.native_revision == (
        old_history.a_native_after_initial.native_revision
    )
    assert old_history.a_historical_composite.paper_tick > initial[0].paper_tick
    assert old_history.a_historical_composite.native_session_id == initial[0].native_session_id


def test_b_after_logout_requires_original_a_retired_offline(current):
    f, initial, native, _ = current
    old = build_current_composite_source(
        bridge=f.bridge, self_id="A", native_revision=native, initial_receipts=initial,
    )
    history = NormalCpuOriginalHistory(initial, native, old)

    async def run():
        with pytest.raises(OriginalNormalCpuWorldHold):
            await update_original_b_after_a_logout(bridge=f.bridge, history=history)
        logout = await f.bridge.logout("A")
        assert logout.physical_issuer_revoked
        b = await update_original_b_after_a_logout(bridge=f.bridge, history=history)
        assert b.native_session_id == initial[1].native_session_id
        assert b.native_sequence > initial[1].native_sequence
        assert f.owners["B"].current_worldbody_observation.request_id == b.native_request_id
        await f.bridge.login("A")
        with pytest.raises(OriginalNormalCpuWorldHold):
            await update_original_b_after_a_logout(bridge=f.bridge, history=history)

    asyncio.run(run())


def test_no_unverified_rejoin_world_start_and_no_owned_tasks(current):
    f, initial, native, _ = current
    old = build_current_composite_source(
        bridge=f.bridge, self_id="A", native_revision=native, initial_receipts=initial,
    )

    async def run():
        with pytest.raises(OriginalNormalCpuWorldHold):
            start_original_normal_cpu_runtime(
                bridge=f.bridge,
                history=NormalCpuOriginalHistory(initial, native, old),
            )
        assert not hasattr(f.cognitive, "_normal_present_scheduler")
        assert all(not s.tasks for s in f.cognitive._states.values())

    asyncio.run(run())


@pytest.mark.parametrize("interval", [0, -2, 30.01, "0.2", None, True])
def test_invalid_world_cpu_interval_never_binds_unowned_runtime(pair, interval):
    f = pair[0]

    async def run():
        with pytest.raises(OriginalNormalCpuWorldHold):
            start_original_normal_cpu_runtime(
                bridge=f.bridge, history=_history(pair), interval_s=interval,
            )
        assert not hasattr(f.cognitive, "_normal_rejoin_source_cut")
        assert all(not s.tasks for s in f.cognitive._states.values())

    asyncio.run(run())


@pytest.mark.parametrize("deadline", [0, -1, 31, "1", None, True])
def test_invalid_world_cpu_read_deadline_is_hold(pair, deadline):
    f = pair[0]

    async def run():
        with pytest.raises(OriginalNormalCpuWorldHold):
            await read_original_normal_cpu_pair(bridge=f.bridge, timeout_s=deadline)

    asyncio.run(run())


@pytest.mark.parametrize("fault", [
    "schema_disabled", "initial_source", "world_only", "typed_owner",
    "selected_move", "autonomous_l1", "real_llm", "model_receipt",
])
def test_real_world_cli_optin_preflight_blocks_conflicting_modes_before_io(tmp_path, fault):
    options = dict(
        paper_jar=tmp_path / "missing-paper.jar",
        paper_sha256="0" * 64, plugin_jar=tmp_path / "missing-plugin.jar",
        plugin_sha256="1" * 64, scratch_parent=tmp_path,
        accepted_eula=False, real_world_dev_grant=True,
        normal_cpu_present_dev=True, exploration_schema_dev=True,
    )
    if fault == "schema_disabled":
        options["exploration_schema_dev"] = False
    elif fault == "initial_source":
        options["initial_source_dev"] = True
    elif fault == "world_only":
        options["world_only"] = True
    elif fault == "typed_owner":
        options["typed_owner_cut_dev"] = True
    elif fault == "selected_move":
        options["b_selected_move_dev"] = True
    elif fault == "autonomous_l1":
        options["b_autonomous_l1_dev"] = True
    elif fault == "real_llm":
        options["real_llm_grant"] = True
    else:
        options["stage24g_model_receipt"] = object()
    async def run():
        with pytest.raises(RealResidentPresenceRefusal, match="normal CPU runner"):
            await run_real_resident_presence(**options)

    asyncio.run(run())
    assert not list(tmp_path.iterdir())


def test_real_world_cpu_mode_cannot_implicitly_grant_world(tmp_path):
    async def run():
        with pytest.raises(RealResidentPresenceRefusal, match="HOLD_REAL_WORLD_GRANT"):
            await run_real_resident_presence(
                paper_jar=tmp_path / "no-paper.jar", paper_sha256="0" * 64,
                plugin_jar=tmp_path / "no-plugin.jar", plugin_sha256="1" * 64,
                scratch_parent=tmp_path, accepted_eula=False,
                real_world_dev_grant=False,
                normal_cpu_present_dev=True, exploration_schema_dev=True,
            )

    asyncio.run(run())
    assert not list(tmp_path.iterdir())
