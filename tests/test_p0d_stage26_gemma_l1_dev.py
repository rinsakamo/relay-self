"""Stage26 source-shaped native + bounded HTTP model original owner integration.

The locally hosted HTTP stub is NOT a real GPU/Gemma model; real Paper and
real weights require the separate operator-approved local one-shot run.
"""
from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from experiments.p0d_real_preset_checkpoint_dev import (
    RealPresetCheckpointRefusal,
    run_real_two_self_preset_checkpoint,
)
from relay_self.p0d_stage26_gemma_l1_dev import (
    Stage26L1Refusal,
    finish_restored_preset_l1,
    prepare_restored_preset_l1,
    submit_restored_preset_l1,
)
from relay_self.resident_llama_inference_lane_dev import ResidentGpuLaneError
from test_p0d_real_preset_checkpoint_dev import native_probe, source_recovered
from test_p0d_resident_llama_slot_owner_dev import (
    ResidentFixture,
    _attach,
    _SyntheticLlamaServer,
)


def _attach_and_audit(f, endpoint, tmp_path):
    lane = _attach(f, endpoint)
    folder = tmp_path / "source-http"
    folder.mkdir(mode=0o700)
    lane.provider.enable_stage26_raw_audit(folder)
    return lane


def _online_two_actor(f, lane):
    async def join():
        preserved = {}
        for sid in f.names:
            restored = source_recovered(sid)
            owner = f.owners[sid]
            owner.retained = restored.retained
            owner.pattern_registry = restored.semantic.pattern_registry
            preserved[sid] = restored
        for sid in f.names:
            await f.bridge.login(sid)
        return preserved

    return join()


@pytest.mark.parametrize(("choice_id", "expected_status"), [
    ("1", "READY"), ("2", "ESCALATE_L2"), ("3", "DEFER"),
])
def test_actual_bounded_http_response_is_rechecked_after_second_native_probe(
    tmp_path, choice_id, expected_status,
):
    http = _SyntheticLlamaServer()
    http.choice_id = choice_id
    endpoint = http.start()
    f = ResidentFixture(tmp_path, 2, cognitive_work=True)
    lane = _attach_and_audit(f, endpoint, tmp_path)

    async def scenario():
        restored = await _online_two_actor(f, lane)
        prepared = {}
        tickets = {}
        for sid in f.names:
            new_native = f.bridge.sessions[sid].started.session_id
            first = native_probe(sid, 10, session=new_native)
            plan = prepare_restored_preset_l1(
                self_id=sid, restored=restored[sid], first=first,
                owner=f.owners[sid], lane=lane,
            )
            assert len(plan.round.request.choices) == 3
            assert tuple(x.description for x in plan.round.request.choices)[1:] == (
                "ESCALATE_L2", "DEFER",
            )
            assert plan.round.request.request_id.endswith(f"{new_native}-10")
            prepared[sid] = plan
            tickets[sid] = submit_restored_preset_l1(plan, lane=lane)
        for sid in f.names:
            plan = prepared[sid]
            new_native = f.bridge.sessions[sid].started.session_id
            observed = []

            async def recheck():
                # The original model result must have completed BEFORE probe.
                assert http.calls
                observed.append("post-model-native")
                return native_probe(sid, 11, session=new_native)

            result, second = await finish_restored_preset_l1(
                plan, ticket=tickets[sid], lane=lane,
                fresh_probe=recheck,
            )
            assert observed == ["post-model-native"]
            assert second.seq > plan.first_probe.seq
            assert result.l1_status == expected_status
            assert result.selected_number == choice_id
            assert result.preset_ref.startswith("skill-preset:v1@")
            assert result.candidate_invocation_ref.startswith("skill-invocation:v1@")
            assert result.provider_kind == "REAL_LLAMA_CPP_BOUNDED_PROVIDER_NOT_SCRIPTED"
            assert result.available_numbered_choices == ("1", "2", "3")
            assert result.backend_slot_idle_after_call
            assert not result.selection_is_action_permission
            assert not result.issued_native_effect
            assert not result.old_gpu_result_reused
            assert result.inference_request_id == tickets[sid].request_id
            assert result.original_http_response_bytes > 0
            assert result.original_http_response_sha256
            assert result.original_http_request_sha256
            assert result.provider_call_facts["finish_reason"] == "stop"
        for sid in f.names:
            await f.bridge.logout(sid)
        assert all(lane.retired_clean(sid) for sid in f.names)
        assert lane.require_world_idle().n_slots == 1

    try:
        asyncio.run(scenario())
        assert http.maximum_active == 1
        assert len(http.calls) == 2
    finally:
        f.stop_paper()
        http.stop()


def test_old_model_answer_rejected_after_self_logout_and_new_native_login(tmp_path):
    http = _SyntheticLlamaServer()
    http.choice_id = "1"
    endpoint = http.start()
    f = ResidentFixture(tmp_path, 2, cognitive_work=True)
    lane = _attach_and_audit(f, endpoint, tmp_path)

    async def scenario():
        original = await _online_two_actor(f, lane)
        sid = f.names[0]
        native = f.bridge.sessions[sid].started.session_id
        plan = prepare_restored_preset_l1(
            self_id=sid, restored=original[sid],
            first=native_probe(sid, 10, session=native),
            owner=f.owners[sid], lane=lane,
        )
        ticket = submit_restored_preset_l1(plan, lane=lane)
        await lane.await_result(ticket)
        await f.bridge.logout(sid)
        assert lane.retired_clean(sid)
        with pytest.raises(ResidentGpuLaneError, match="late"):
            lane.result(ticket)
        await f.bridge.login(sid)
        assert f.bridge.sessions[sid].started.session_id != native
        with pytest.raises((ResidentGpuLaneError, Stage26L1Refusal)):
            await finish_restored_preset_l1(
                plan, ticket=ticket, lane=lane,
                fresh_probe=lambda: asyncio.sleep(0),
            )
        for name in f.names:
            await f.bridge.logout(name)

    try:
        asyncio.run(scenario())
    finally:
        f.stop_paper()
        http.stop()


@pytest.mark.parametrize("fault", [
    "wrong-self", "foreign-native", "old-native",
    "unregistered", "wrong-owner-registry", "wrong-owner-retained",
])
def test_source_and_owner_mismatch_refuses_before_model_submission(
    tmp_path, fault,
):
    http = _SyntheticLlamaServer()
    endpoint = http.start()
    f = ResidentFixture(tmp_path, 2, cognitive_work=True)
    lane = _attach_and_audit(f, endpoint, tmp_path)

    async def scenario():
        restored = await _online_two_actor(f, lane)
        sid = f.names[0]
        owner = f.owners[sid]
        active = f.bridge.sessions[sid].started.session_id
        first = native_probe(sid, 10, session=active)
        actor = restored[sid]
        if fault == "wrong-self":
            sid = f.names[1]
        elif fault == "foreign-native":
            first = native_probe(sid, 10, session="foreign-native")
        elif fault == "old-native":
            first = native_probe(sid, 10, session=actor.semantic.cut.former_native_session_id)
        elif fault == "unregistered":
            actor = source_recovered(sid, accepted=False)
        elif fault == "wrong-owner-registry":
            owner.pattern_registry = source_recovered(sid, accepted=False).semantic.pattern_registry
        else:
            owner.retained = replace(
                owner.retained, pattern_registry=source_recovered(
                    sid, accepted=False,
                ).semantic.pattern_registry,
            )
        with pytest.raises(Stage26L1Refusal):
            prepare_restored_preset_l1(
                self_id=sid, restored=actor,
                first=first, owner=owner, lane=lane,
            )
        assert not http.calls
        for name in f.names:
            await f.bridge.logout(name)

    try:
        asyncio.run(scenario())
    finally:
        f.stop_paper()
        http.stop()


@pytest.mark.parametrize("endpoint,model,enable", [
    ("http://127.0.0.1:9/v1/chat/completions", None, True),
    (None, "Gemma-4", True),
    (None, None, False),
])
def test_real_model_mode_is_explicit_and_never_launches_unqualified_paper(
    tmp_path, endpoint, model, enable,
):
    parent = tmp_path / "not-created"
    kwargs = dict(
        paper_jar=tmp_path / "missing-paper.jar", paper_sha256="0" * 64,
        plugin_jar=tmp_path / "missing-plugin.jar", plugin_sha256="1" * 64,
        scratch_parent=parent, accepted_eula=True, real_world_dev_grant=True,
        real_gemma_l1=enable, gemma_l1_endpoint=endpoint,
        gemma_l1_model=model,
    )
    with pytest.raises(Exception):
        asyncio.run(run_real_two_self_preset_checkpoint(**kwargs))
    assert not parent.exists()


def test_jev_requires_actual_bounded_provider_mode_before_any_world(tmp_path):
    with pytest.raises(RealPresetCheckpointRefusal, match="JEV"):
        asyncio.run(run_real_two_self_preset_checkpoint(
            paper_jar=tmp_path / "paper.jar", paper_sha256="0" * 64,
            plugin_jar=tmp_path / "plugin.jar", plugin_sha256="0" * 64,
            scratch_parent=tmp_path / "nonexistent",
            accepted_eula=True, real_world_dev_grant=True,
            gemma_l1_jev=True,
        ))
