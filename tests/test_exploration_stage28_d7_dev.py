"""D7 candidate gate: real Stage28 Python source verification, no fake World launch."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

from experiments import stage28_d7_exploration_source_inspect_dev as cli
from relay_self.exploration_d7_real_world_preflight_dev import (
    D7RealWorldPreflightHold,
    inspect_d7_real_world_candidate,
)
from test_exploration_stage28_d6_dev import _actual_cut_and_restore


def _fixture(tmp_path: Path):
    (_, _, old_tasks, _, _, gen, restored, receipt, sha) = (
        _actual_cut_and_restore(tmp_path)
    )
    inputs = {
        "expected_world_id": "world-A",
        "expected_source_branch_id": "source",
        "expected_fork_branch_id": receipt["fork_branch_id"],
        "expected_committed_sha256": sha,
        "expected_generation_id": gen.name,
    }
    return gen, restored, old_tasks, inputs


def test_d7_full_a_b_owner_world_3d_and_question_attempts_only_inert(tmp_path):
    generation, restored, old_tasks, pins = _fixture(tmp_path)
    result = inspect_d7_real_world_candidate(generation, restored, **pins)
    assert result.source_kind == "STRUCTURAL_TYPED_CUT_ONLY"
    assert result.owner_roster == ("A", "B")
    assert result.generation_id == "g-000000000000"
    assert result.committed_sha256 == hashlib.sha256(
        (generation / "COMMITTED.json").read_bytes()
    ).hexdigest()
    assert result.fork_branch_id == pins["expected_fork_branch_id"]
    assert result.real_world_attested is False
    assert result.real_native_rejoin_attested is False
    assert result.real_gemma_l1_attested is False
    assert result.l2_dispatch_authorized is False
    assert result.physical_action_issue_authorized is False
    assert result.historical_action_or_l2_replay_authorized is False
    for sid, got in zip(("A", "B"), result.selves, strict=True):
        assert got.self_id == sid
        assert got.question_refs == (
            "question:ridge" if sid == "A" else "question:forest",
        )
        assert got.attempt_refs == (old_tasks[sid].attempt_ref,)
        assert got.attempts_reserved == 1
        assert got.prior_native_session_id == "native-old-" + sid
        assert got.no_old_l2_replay_authorized
        assert got.no_old_action_replay_authorized


@pytest.mark.parametrize("field,new", [
    ("expected_world_id", "foreign-world"),
    ("expected_source_branch_id", "foreign-source"),
    ("expected_fork_branch_id", "foreign-fork"),
    ("expected_generation_id", "g-000000000001"),
    ("expected_committed_sha256", "0" * 64),
])
def test_d7_wrong_source_pins_hold_without_world_start(tmp_path, field, new):
    gen, restored, _, pins = _fixture(tmp_path)
    pins[field] = new
    with pytest.raises(D7RealWorldPreflightHold):
        inspect_d7_real_world_candidate(gen, restored, **pins)
    assert not (restored / "paper.jar").exists()


@pytest.mark.parametrize("file", [
    "cognition.json", "owner-state.json", "physical-wal.json",
])
def test_d7_mutated_restored_a_owner_files_hold_before_world(
    tmp_path, file,
):
    gen, restored, _, pins = _fixture(tmp_path)
    changed = restored / "selves" / "A" / file
    changed.write_bytes(changed.read_bytes() + b"\nchanged-after-restore\n")
    with pytest.raises(D7RealWorldPreflightHold):
        inspect_d7_real_world_candidate(gen, restored, **pins)
    assert not (restored / "paper.jar").exists()


def test_d7_missing_real_paper_companion_holds_even_if_a_b_files_exist(tmp_path):
    gen, restored, _, pins = _fixture(tmp_path)
    # A/B Cognition/WAL still exist, but one original World dimension is lost.
    import shutil

    shutil.rmtree(gen / "paper-dimensions" / "world_nether")
    with pytest.raises(D7RealWorldPreflightHold):
        inspect_d7_real_world_candidate(gen, restored, **pins)


def test_d7_symlink_archive_and_equal_source_destination_hold(tmp_path):
    gen, restored, _, pins = _fixture(tmp_path)
    with pytest.raises(D7RealWorldPreflightHold, match="distinct immutable"):
        inspect_d7_real_world_candidate(gen, gen, **pins)
    alias = tmp_path / "alias-to-archive"
    alias.symlink_to(gen, target_is_directory=True)
    with pytest.raises(D7RealWorldPreflightHold, match="distinct immutable"):
        inspect_d7_real_world_candidate(alias, restored, **pins)


def test_d7_cli_inspection_is_readonly_and_refuses_any_execute(tmp_path, monkeypatch, capsys):
    gen, restored, _, pins = _fixture(tmp_path)
    def argv(mode):
        return [
            "d7", "--generation", str(gen), "--restored", str(restored),
            "--world-id", pins["expected_world_id"],
            "--source-branch", pins["expected_source_branch_id"],
            "--fork-branch", pins["expected_fork_branch_id"],
            "--committed-sha256", pins["expected_committed_sha256"],
            "--generation-id", pins["expected_generation_id"], mode,
        ]
    before = hashlib.sha256((gen / "COMMITTED.json").read_bytes()).hexdigest()
    monkeypatch.setattr(sys, "argv", argv("--inspect-only"))
    assert cli.main() == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["real_world_attested"] is False
    assert parsed["l2_dispatch_authorized"] is False
    assert parsed["owner_roster"] == ["A", "B"]
    assert hashlib.sha256((gen / "COMMITTED.json").read_bytes()).hexdigest() == before

    monkeypatch.setattr(sys, "argv", argv("--execute-once"))
    assert cli.main() == 2
    assert "PRE_WORLD_HOLD" in capsys.readouterr().err
    assert not (restored / "paper.jar").exists()


def test_d7_partial_source_before_commit_never_promotes_candidate(tmp_path):
    gen = tmp_path / "g-000000000000"
    gen.mkdir()
    restored = tmp_path / "fork"
    restored.mkdir()
    with pytest.raises(D7RealWorldPreflightHold):
        inspect_d7_real_world_candidate(
            gen, restored,
            expected_world_id="world-A",
            expected_source_branch_id="source",
            expected_fork_branch_id="fork",
            expected_committed_sha256="a" * 64,
            expected_generation_id=gen.name,
        )
