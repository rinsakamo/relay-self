"""Adversarial PRE_WORLD-only controls for the future I1+C+I4a runner."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from adapters.mineflayer.process_session import MineflayerProcessSession
from experiments.i_lane_i1_c_i4a_real_runner_dev import (
    I1CI4APreWorldHold,
    inspect_i1_c_i4a_preworld,
    main,
)
from relay_self.i_lane_i4a_s2_first_physical_reservation_dev import (
    I4AS2FirstReservationHold,
    require_i4a_offline_scripted_native,
)


def _root():
    return Path(__file__).resolve().parents[1]


def _exact_head():
    return subprocess.check_output(
        ["git", "-C", str(_root()), "rev-parse", "HEAD"],
        text=True,
    ).strip()


def test_preworld_inventory_is_never_world_or_model_admission():
    report = inspect_i1_c_i4a_preworld(
        repo_root=_root(), expected_head=_exact_head(),
    )
    assert report.classification == "I1_C_I4A_PRE_WORLD_HOLD"
    assert len(report.source_sha256) == 16
    assert {
        "src/relay_self/i_lane_i4a_s2_first_physical_reservation_dev.py",
        "src/relay_self/i_lane_i4a_s2_run_boundary_dev.py",
        "src/relay_self/i_lane_i4a_live_wal_anchor_dev.py",
        "src/relay_self/paper_tick_witness_dev.py",
        "adapters/mineflayer/process_session.py",
        "adapters/llama_cpp/relay_engine.py",
    }.issubset(report.source_sha256)
    assert report.blockers
    assert "live_original_s2_issuer_not_integrated" in report.blockers
    assert report.world_started is False
    assert report.model_posts == 0
    assert report.physical_actions == 0
    assert report.live_admission is False


@pytest.mark.parametrize("head", ["", "0" * 40, "a" * 39, "not-a-head"])
def test_preworld_rejects_foreign_or_malformed_integration_head(head):
    with pytest.raises(I1CI4APreWorldHold):
        inspect_i1_c_i4a_preworld(repo_root=_root(), expected_head=head)


def test_preworld_cli_grants_do_not_create_world_or_issue_actions(tmp_path, capsys):
    world = tmp_path / "world-must-not-start"
    code = main([
        "--repo-root", str(_root()),
        "--expected-head", _exact_head(),
        "--world-dir", str(world),
        "--real-world-dev-grant", "--accepted-eula",
    ])
    assert code == 2
    report = json.loads(capsys.readouterr().out)
    assert report["classification"] == "I1_C_I4A_PRE_WORLD_HOLD"
    assert report["live_admission"] is False
    assert not world.exists()
    assert not list(tmp_path.iterdir())


def test_preworld_cli_wrong_head_never_touches_world_dir(tmp_path, capsys):
    world = tmp_path / "no-world"
    code = main([
        "--repo-root", str(_root()),
        "--expected-head", "0" * 40,
        "--world-dir", str(world),
        "--real-world-dev-grant", "--accepted-eula",
    ])
    assert code == 2
    assert "HEAD" in capsys.readouterr().err
    assert not world.exists()


def test_preworld_does_not_repurpose_s2_synthetic_issuer_for_real_process():
    with pytest.raises(I4AS2FirstReservationHold, match="process-backed"):
        require_i4a_offline_scripted_native(
            object.__new__(MineflayerProcessSession),
        )

    class ProcessBackedNative(MineflayerProcessSession):
        pass

    disguised = object.__new__(ProcessBackedNative)
    disguised._process = object()
    with pytest.raises(I4AS2FirstReservationHold, match="process-backed"):
        require_i4a_offline_scripted_native(disguised)


def test_preworld_rejects_dirty_source_even_when_commit_head_matches(tmp_path):
    original = inspect_i1_c_i4a_preworld(
        repo_root=_root(), expected_head=_exact_head(),
    )
    for rel in original.source_sha256:
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_root() / rel, path)
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "-c", "user.name=CI",
         "-c", "user.email=ci@example.invalid", "commit", "-qm", "fixture"],
        check=True,
    )
    initial_head = subprocess.check_output(
        ["git", "-C", str(tmp_path), "rev-parse", "HEAD"], text=True,
    ).strip()
    assert inspect_i1_c_i4a_preworld(
        repo_root=tmp_path, expected_head=initial_head,
    ).live_admission is False
    changed = tmp_path / "src/relay_self/i_lane_i4a_s2_first_native_move_dev.py"
    changed.write_bytes(changed.read_bytes() + b"\n# tampered after HEAD\n")
    with pytest.raises(I1CI4APreWorldHold, match="tracked and clean"):
        inspect_i1_c_i4a_preworld(
            repo_root=tmp_path, expected_head=initial_head,
        )

@pytest.mark.parametrize("index_flag", ["--assume-unchanged", "--skip-worktree"])
def test_preworld_rejects_mutation_hidden_by_git_index_flags(tmp_path, index_flag):
    original = inspect_i1_c_i4a_preworld(
        repo_root=_root(), expected_head=_exact_head(),
    )
    for rel in original.source_sha256:
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_root() / rel, path)
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "-c", "user.name=CI",
         "-c", "user.email=ci@example.invalid", "commit", "-qm", "fixture"],
        check=True,
    )
    head = subprocess.check_output(
        ["git", "-C", str(tmp_path), "rev-parse", "HEAD"], text=True,
    ).strip()
    rel = "src/relay_self/i_lane_i4a_s2_first_native_move_dev.py"
    source = tmp_path / rel
    subprocess.run(
        ["git", "-C", str(tmp_path), "update-index", index_flag, "--", rel],
        check=True,
    )
    source.write_bytes(source.read_bytes() + b"\n# masked dirty source\n")
    # This demonstrates why the earlier git diff-only check was inadequate.
    assert subprocess.run(
        ["git", "-C", str(tmp_path), "diff", "--quiet", "HEAD", "--", rel],
        check=False,
    ).returncode == 0
    with pytest.raises(I1CI4APreWorldHold, match="committed source blob differs"):
        inspect_i1_c_i4a_preworld(repo_root=tmp_path, expected_head=head)


@pytest.mark.parametrize("rel", [
    "src/relay_self/i_lane_i4a_s2_first_physical_reservation_dev.py",
    "src/relay_self/paper_tick_witness_dev.py",
    "adapters/llama_cpp/relay_engine.py",
])
def test_preworld_rejects_dirty_newly_covered_boundary_sources(tmp_path, rel):
    report = inspect_i1_c_i4a_preworld(
        repo_root=_root(), expected_head=_exact_head(),
    )
    for source in report.source_sha256:
        target = tmp_path / source
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_root() / source, target)
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "-c", "user.name=CI",
         "-c", "user.email=ci@example.invalid", "commit", "-qm", "fixture"],
        check=True,
    )
    head = subprocess.check_output(
        ["git", "-C", str(tmp_path), "rev-parse", "HEAD"], text=True,
    ).strip()
    target = tmp_path / rel
    target.write_bytes(target.read_bytes() + b"\n# unexpected local source mutation\n")
    with pytest.raises(I1CI4APreWorldHold, match="tracked and clean"):
        inspect_i1_c_i4a_preworld(repo_root=tmp_path, expected_head=head)
