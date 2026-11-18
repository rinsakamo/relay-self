"""Stage27e source-shaped tests: no real Paper, Mineflayer or Gemma."""
from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from experiments.p0d_stage27_real_place_move_dev import (
    run_stage27_real_world,
    stage27e_real_a_motor_hook,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.stage27e_independent_evidence_dev import (
    Stage27IndependentEvidenceError,
    capture_original_prepared_wal,
    correlate_owned_paper_position,
)
from test_p0d_resident_llama_slot_owner_dev import (
    ResidentFixture,
    _SyntheticLlamaServer,
)
from test_p0d_resident_paper_presence_join_dev import (
    BOOT,
    PAPER,
    WORLD,
    A,
    B,
    _line,
)
from test_p0d_stage26_gemma_l1_dev import _attach_and_audit
from test_p0d_stage27c_place_move_wal_issuer_dev import (
    ScriptedPlaceNative,
    _args,
    selected_original,
)


def _paper_window(*, moved=True, wrong_actor=False, b_move=False):
    pre = ("\n".join([
        f"[Server thread/INFO]: P0D_RESIDENT_READY boot={BOOT} "
        "source=PAPER_MAIN_THREAD version=1",
        _line("JOIN", 10, A, "RelayA", 9.5, y=75, z=0.5),
        _line("JOIN", 11, B, "RelayB", 15, y=75, z=0.5),
        _line("PRESENT", 50, A, "RelayA", 9.5, y=75, z=0.5),
    ]) + "\n").encode()
    post = pre
    if moved:
        post += (_line(
            "MOVE", 60, B if wrong_actor else A, "RelayA",
            10.14, y=75, z=0.5,
        ) + "\n").encode()
    if b_move:
        post += (_line("MOVE", 65, B, "RelayB", 15.5, y=75, z=0.5) + "\n").encode()
    return pre, post


def _correlate(pre, post, *, native_end=(10.1418, 75, 0.5)):
    return correlate_owned_paper_position(
        before=pre, after=post, paper_session_id=PAPER,
        world_uuid=WORLD, native_start_xyz=(9.5, 75, 0.5),
        native_settled_xyz=native_end,
    )


def test_independent_paper_movement_is_position_correlation_not_causation():
    pre, post = _paper_window(moved=True, b_move=True)
    result = _correlate(pre, post)
    assert result["status"] == "PAPER_A_POSITION_CORRELATED_DEV"
    assert result["paper_position_independently_correlated"]
    assert result["paper_a_displacement_m"] == pytest.approx(0.64)
    assert result["paper_b_move_events_after_preissue"] == 1
    assert not result["paper_action_causality_attested"]
    assert not result["goal_or_skill_success_attested"]
    assert result["paper_pre_log_bytes"] == len(pre)


def test_missing_paper_movement_is_unknown_not_zero_displacement():
    pre, post = _paper_window(moved=False)
    result = _correlate(pre, post)
    assert result["status"] == "PAPER_A_POSITION_UNATTESTED_DEV"
    assert not result["paper_position_independently_correlated"]
    assert result["paper_a_move_events_after_preissue"] == 0


@pytest.mark.parametrize("native_end", [
    (12, 75, 0.5), (-2, 75, 0.5),
])
def test_mismatched_independent_position_never_qualifies(native_end):
    pre, post = _paper_window()
    assert not _correlate(pre, post, native_end=native_end)[
        "paper_position_independently_correlated"
    ]


def test_foreign_actor_or_nonappend_paper_never_qualifies():
    pre, wrong_actor = _paper_window(wrong_actor=True)
    with pytest.raises(Stage27IndependentEvidenceError, match="actor"):
        _correlate(pre, wrong_actor)
    pre, post = _paper_window()
    with pytest.raises(Stage27IndependentEvidenceError, match="window"):
        _correlate(post, pre)


def test_prepared_raw_bytes_preserved_before_first_native_look(tmp_path):
    http = _SyntheticLlamaServer()
    http.choice_id = "1"
    endpoint = http.start()
    f = ResidentFixture(
        tmp_path, 2, cognitive_work=True, allow_resident_move=True,
    )
    lane = _attach_and_audit(f, endpoint, tmp_path)

    async def scenario():
        pre, handoff, plan, l0, former, current = await selected_original(f, lane)
        script = ScriptedPlaceNative(l0.native_session_id)
        script.seq = current.seq
        script.tick = 1213
        script.gate = lambda native, effect, action: f.physical.require_native_effect(
            self_id=f.names[0], native_session_id=native,
            effect=effect, action_id=action,
        )
        args = _args(f, pre, handoff, plan, l0, former, current)
        witness = {}

        def tap(journal, action_id):
            assert not script.sent_commands
            assert journal.unresolved
            witness.update(capture_original_prepared_wal(
                journal, tmp_path, action_id=action_id, self_id=f.names[0],
            ))

        receipt = await f.physical.issue_place_move(
            script, **args, pre_native_evidence=tap,
        )
        assert receipt.journal_status == "NATIVE_PLACE_MOVE_SETTLED"
        assert witness["captured_before_any_native_effect"]
        snapshot = PhysicalActionJournal.restore(
            Path(witness["snapshot_path"]), self_id=f.names[0],
        )
        assert snapshot.unresolved
        assert snapshot.records[-1]["status"] == "PREPARED_UNRESOLVED"
        terminal = PhysicalActionJournal.restore(
            f.owners[f.names[0]].files.physical_wal_file, self_id=f.names[0],
        )
        assert not terminal.unresolved
        assert terminal.digest != snapshot.digest
        assert witness["journal_digest"] == snapshot.digest

    try:
        asyncio.run(scenario())
    finally:
        f.stop_paper()
        http.stop()


def test_failed_prepared_evidence_capture_blocks_every_native_child(tmp_path):
    http = _SyntheticLlamaServer()
    http.choice_id = "1"
    endpoint = http.start()
    f = ResidentFixture(
        tmp_path, 2, cognitive_work=True, allow_resident_move=True,
    )
    lane = _attach_and_audit(f, endpoint, tmp_path)

    async def scenario():
        pre, handoff, plan, l0, former, current = await selected_original(f, lane)
        script = ScriptedPlaceNative(l0.native_session_id)
        script.seq = current.seq
        script.tick = 1213
        script.gate = lambda native, effect, action: f.physical.require_native_effect(
            self_id=f.names[0], native_session_id=native,
            effect=effect, action_id=action,
        )
        args = _args(f, pre, handoff, plan, l0, former, current)

        def fail_evidence(journal, action_id):
            assert journal.unresolved
            assert journal.records[-1]["action_id"] == action_id
            assert not script.sent_commands
            raise Stage27IndependentEvidenceError("evidence disk unavailable")

        with pytest.raises(Stage27IndependentEvidenceError, match="disk"):
            await f.physical.issue_place_move(
                script, **args, pre_native_evidence=fail_evidence,
            )
        assert script.sent_commands == []
        unresolved = PhysicalActionJournal.restore(
            f.owners[f.names[0]].files.physical_wal_file,
            self_id=f.names[0],
        )
        assert unresolved.unresolved
        assert unresolved.records[-1]["status"] == "PREPARED_UNRESOLVED"

    try:
        asyncio.run(scenario())
    finally:
        f.stop_paper()
        http.stop()


def test_stage27e_witness_only_explicit_runner_optin(tmp_path):
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
        result = asyncio.run(run_stage27_real_world(
            **args, stage27e_independent_evidence=True,
        ))
        assert result == tmp_path / "report.json"
        assert source.await_args.kwargs["_stage27_motor_hook"] is (
            stage27e_real_a_motor_hook
        )
        source.reset_mock()
        asyncio.run(run_stage27_real_world(**args))
        assert source.await_args.kwargs["_stage27_motor_hook"] is not (
            stage27e_real_a_motor_hook
        )
