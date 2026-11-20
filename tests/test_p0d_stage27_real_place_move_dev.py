"""Stage27d: real-runner one-shot API and original native wire replay gates.

HTTP/Gemma/Paper are never launched in these offline tests.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from experiments.p0d_real_preset_checkpoint_dev import (
    RealPresetCheckpointRefusal,
    run_real_two_self_preset_checkpoint,
)
from experiments.p0d_stage27_real_place_move_dev import (
    Stage27RealWorldRefusal,
    _native_place_wire_readback,
    _peer_snapshot,
    run_stage27_real_world,
    stage27_real_a_motor_hook,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from test_p0d_resident_llama_slot_owner_dev import ResidentFixture


def _write_wire(root: Path, *, wrong: str | None = None) -> Path:
    rows = [
        {"type": "observation", "kind": "probe",
         "session_id": "native-A", "seq": 6, "request_id": "current"},
        {"type": "effect_result", "session_id": "native-A",
         "seq": 7, "action_id": "stage27c-A-6-look",
         "effect": "look", "result": "applied"},
        {"type": "effect_result", "session_id": "native-A",
         "seq": 8, "action_id": "stage27c-A-6-start",
         "effect": "set_control", "result": "applied"},
        {"type": "effect_result", "session_id": "native-A",
         "seq": 9, "action_id": "stage27c-A-6-stop",
         "effect": "clear_controls", "result": "applied"},
        *(
            {"type": "observation", "kind": "probe",
             "session_id": "native-A", "seq": seq,
             "request_id": f"stop-{seq}"}
            for seq in (10, 11, 12)
        ),
    ]
    if wrong == "look-foreign":
        rows[1]["action_id"] = "stage27c-B-6-look"
    if wrong == "stop-rejected":
        rows[3]["result"] = "rejected"
    if wrong == "duplicate-child":
        rows.append(dict(rows[2]))
    if wrong == "foreign-session":
        rows[4]["session_id"] = "native-B"
    if wrong == "missing-probe":
        rows.pop()
    if wrong == "future-ack":
        rows[1]["seq"] = 19
    path = root / "original-A-native.jsonl"
    path.write_bytes(b"".join(
        (json.dumps(x, separators=(",", ":")) + "\n").encode()
        for x in rows
    ))
    return path


def _audit(path):
    return _native_place_wire_readback(
        path, session_id="native-A", parent="stage27c-A-6",
        new_probe_seq=6, ack_seqs=(7, 8, 9),
        stop_probe_seqs=(10, 11, 12),
    )


def test_original_wire_replay_look_start_stop_exactly_once(tmp_path):
    path = _write_wire(tmp_path)
    witness = _audit(path)
    assert witness["original_native_look_start_stop_sequence_verified"]
    assert witness["no_independent_paper_position_claim"]
    assert len(witness["exact_native_action_child_effect_results"]) == 3
    assert len(witness["sha256"]) == 64
    assert witness["length"] == path.stat().st_size


@pytest.mark.parametrize("fault", [
    "look-foreign", "stop-rejected", "duplicate-child",
    "foreign-session", "missing-probe", "future-ack",
])
def test_original_wire_bad_ack_or_foreign_native_never_qualifies(tmp_path, fault):
    path = _write_wire(tmp_path, wrong=fault)
    with pytest.raises(Stage27RealWorldRefusal):
        _audit(path)


@pytest.mark.parametrize("bad", [
    "missing-eula", "missing-grant", "missing-endpoint", "missing-model",
])
def test_new_stage27_runner_refuses_before_any_world_or_model_io(tmp_path, bad):
    args = dict(
        paper_jar=tmp_path / "paper-not-present.jar",
        paper_sha256="0" * 64,
        plugin_jar=tmp_path / "plugin-not-present.jar",
        plugin_sha256="0" * 64,
        scratch_parent=tmp_path,
        accepted_eula=True, real_world_dev_grant=True,
        gemma_l1_endpoint="http://127.0.0.1:18081/v1/chat/completions",
        gemma_l1_model="stage27-gemma",
    )
    if bad == "missing-eula":
        args["accepted_eula"] = False
    elif bad == "missing-grant":
        args["real_world_dev_grant"] = False
    elif bad == "missing-endpoint":
        args["gemma_l1_endpoint"] = ""
    else:
        args["gemma_l1_model"] = ""
    with patch(
        "experiments.p0d_stage27_real_place_move_dev."
        "run_real_two_self_preset_checkpoint", new_callable=AsyncMock,
    ) as existing:
        with pytest.raises(Stage27RealWorldRefusal):
            asyncio.run(run_stage27_real_world(**args))
    existing.assert_not_awaited()


def test_stage27_real_runner_passes_private_real_motor_hook_to_existing_cut(tmp_path):
    args = dict(
        paper_jar=tmp_path / "paper.jar", paper_sha256="0" * 64,
        plugin_jar=tmp_path / "plugin.jar", plugin_sha256="0" * 64,
        scratch_parent=tmp_path, accepted_eula=True,
        real_world_dev_grant=True,
        gemma_l1_endpoint="http://127.0.0.1:18081/v1/chat/completions",
        gemma_l1_model="stage27-gemma",
    )
    with patch(
        "experiments.p0d_stage27_real_place_move_dev."
        "run_real_two_self_preset_checkpoint", new_callable=AsyncMock,
    ) as source:
        source.return_value = tmp_path / "report.json"
        output = asyncio.run(run_stage27_real_world(**args))
    assert output == tmp_path / "report.json"
    config = source.await_args.kwargs
    assert config["_stage27_motor_hook"] is stage27_real_a_motor_hook
    assert config["real_gemma_l1"] is True
    assert config["gemma_l1_jev"] is False
    assert config["real_world_dev_grant"]
    assert config["accepted_eula"]


def test_old_stage26_runner_private_motor_requires_real_bounded_model(tmp_path):
    kwargs = dict(
        paper_jar=tmp_path / "absent-paper.jar",
        paper_sha256="0" * 64,
        plugin_jar=tmp_path / "absent-plugin.jar",
        plugin_sha256="0" * 64,
        scratch_parent=tmp_path,
        accepted_eula=True, real_world_dev_grant=True,
        _stage27_motor_hook=stage27_real_a_motor_hook,
    )
    with pytest.raises(RealPresetCheckpointRefusal, match="Stage27"):
        asyncio.run(run_real_two_self_preset_checkpoint(**kwargs))
    assert not list(tmp_path.glob("p0d-real-preset-cut-*"))


def test_nonready_a_keeps_original_peer_wal_and_does_not_issue(tmp_path):
    f = ResidentFixture(tmp_path, 2, cognitive_work=True)
    # Fixture identities are S000/S001. The one-shot original production
    # orchestration deliberately insists on A/B, preventing foreign cohorts.
    lane = SimpleNamespace(require_world_idle=lambda: None)

    async def scenario():
        with pytest.raises(Stage27RealWorldRefusal, match="two original Self"):
            await stage27_real_a_motor_hook(
                paper=f.paper, bridge=f.bridge, physical=f.physical,
                lane=lane, owners=f.owners, world_epoch=0,
                prepared={}, tickets={}, witnesses={}, refreshed={},
                evidence=tmp_path, world_uuid="world-live",
                native_audit=tmp_path / "not-created.jsonl",
            )
        journal = PhysicalActionJournal.restore(
            f.owners[f.names[1]].files.physical_wal_file,
            self_id=f.names[1],
        )
        journal.require_clear()

    try:
        asyncio.run(scenario())
    finally:
        f.stop_paper()


def test_original_peer_snapshot_is_nonmutating(tmp_path):
    f = ResidentFixture(tmp_path, 2, cognitive_work=True)
    try:
        before = _peer_snapshot(f.owners[f.names[1]])
        after = _peer_snapshot(f.owners[f.names[1]])
        assert before == after
        assert before["physical_wal_action_rows"] == 0
        assert before["skill_execution_count"] == 0
        assert before["open_action_count"] == 0
    finally:
        f.stop_paper()


@pytest.mark.parametrize(("number", "status"), [
    ("2", "ESCALATE_L2"), ("3", "DEFER"), (None, "RECONSIDER"),
])
def test_stage27_real_a_nonready_choice_never_grants_motor(tmp_path, number, status):
    """A real runner cannot force MOVE when A's source-selected number differs."""
    f = ResidentFixture(tmp_path, 2, cognitive_work=True)
    a, b = f.names

    async def scenario():
        keys = {"A": object(), "B": object()}
        witness = {
            "A": SimpleNamespace(selected_number=number, l1_status=status),
            "B": SimpleNamespace(selected_number="1", l1_status="READY"),
        }
        called = []
        lane = SimpleNamespace(require_world_idle=lambda: called.append("idle"))
        result = await stage27_real_a_motor_hook(
            paper=f.paper,
            bridge=SimpleNamespace(sessions={"A": object(), "B": object()}),
            physical=f.physical,
            lane=lane,
            owners={"A": f.owners[a], "B": f.owners[b]},
            world_epoch=0,
            prepared=keys,
            tickets=keys,
            witnesses=witness,
            refreshed=keys,
            evidence=tmp_path,
            world_uuid="synthetic-world",
            native_audit=tmp_path / "never-read-native-source.jsonl",
        )
        assert result["classification"] == (
            "REAL_STAGE27_A_MOVE_NOT_SELECTED_NO_PHYSICAL_DEV"
        )
        assert result["self_a_selected_number"] == number
        assert result["self_b_selected_number"] == "1"
        assert not result["physical_effect_observed"]
        assert not result["stage27_a_intent_started"]
        assert result["stage27_native_action_count"] == 0
        assert result["original_peer_b_before"] == result["original_peer_b_after"]
        assert called == ["idle"]
        assert not f.physical.active_action_ids
        for sid in f.names:
            journal = PhysicalActionJournal.restore(
                f.owners[sid].files.physical_wal_file, self_id=sid,
            )
            journal.require_clear()
            assert not journal.records
            assert f.owners[sid].intent.current_intent is None

    try:
        asyncio.run(scenario())
    finally:
        f.stop_paper()


def test_c_lane_l0_diagnostic_preserves_uncertain_state(tmp_path):
    from experiments.p0d_stage27_real_place_move_dev import (
        _freeze_stage27h_l0_diagnostic,
    )

    wal = tmp_path / "wal"
    wal.write_bytes(b"unresolved WAL bytes")
    loop = SimpleNamespace(
        invocation=SimpleNamespace(budget=SimpleNamespace(
            max_duration_ms=15000, max_actions=4,
            max_observations=256, max_distance_m=2.0,
        )),
        owner=SimpleNamespace(self_id="A", files=SimpleNamespace(physical_wal_file=wal)),
        prepared=SimpleNamespace(native_session="native-A"),
        start_ns=0, terminal_status=None, action_count=0, last_action_id=None,
        last_native_seq=-1, _source_seq=7, last_wal_digest="", observation_count=61,
        _settlement_reserved=60, _reserved_source_seq=7, cumulative_distance_m=0.0,
    )
    _freeze_stage27h_l0_diagnostic(
        tmp_path, loop, None, world_uuid="world", error=RuntimeError("uncertain"),
    )
    data = json.loads((tmp_path / "c-stage27h-l0-diagnostic.json").read_text())
    assert data["settling_observations_reserved"] == 60
    assert data["remaining_observations"] == 195
    assert data["last_step"] is None
    assert data["last_validated_wal_sha256"] is None
    assert data["raw_wal_sha256"] is not None
    assert data["physical_state_certified"] is False
    assert data["error"] == "uncertain"
    with pytest.raises(FileExistsError):
        _freeze_stage27h_l0_diagnostic(
            tmp_path, loop, None, world_uuid="world", error=None,
        )
