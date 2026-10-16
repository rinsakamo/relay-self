"""R V8 prospective stopped-World clone parity; synthetic bytes, never World starts."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from experiments.standard_env import v8_stopped_world_clone_preflight as r


def setup_stopped(tmp_path: Path):
    source = tmp_path / "stopped-original"
    (source / "region").mkdir(parents=True)
    (source / "entities").mkdir()
    (source / "data").mkdir()
    (source / "level.dat").write_bytes(b"synthetic_not_valid_NBT_seed-62101")
    (source / "region" / "r.0.0.mca").write_bytes(b"stopped-clone-region-synthetic")
    (source / "entities" / "r.0.0.mca").write_bytes(b"entities")
    (source / "data" / "scoreboard.dat").write_bytes(b"scoreboard")
    (source / "session.lock").write_bytes(b"same-copy-origin")
    candidates = {}
    for arm in sorted(r.ARMS):
        dest = tmp_path / ("arm-" + arm)
        shutil.copytree(source, dest)
        candidates[arm] = dest
    return source, candidates


def snapshot(tmp_path: Path):
    source, clones = setup_stopped(tmp_path)
    return r.review_stopped_clones(source, clones, seed=62101)


def test_five_stopped_clones_exact_bytes_pass_only_offline(tmp_path):
    verdict = snapshot(tmp_path)
    assert verdict["classification"] == r.CLASS
    assert verdict["prospective_seed"] == 62101
    assert verdict["hypothetical_arm_count"] == 5
    assert verdict["checked_stopped_world_files"] == 5
    assert verdict["original_region_file_count"] == 1
    assert verdict["source_and_five_stopped_clones_exact_bytes_equal"] is True
    assert len(verdict["original_world_tree_sha256"]) == 64
    assert verdict["worlds_physically_started"] == 0
    assert verdict["v8_trials_credited"] == 0
    for field in (
        "candidate_clone_inputs_independently_source_authenticated",
        "world_seed_from_native_nbt_attested",
        "physical_server_loaded_same_chunk_geometry",
        "native_agent_pose_and_server_start_tick_equal",
        "finite_food_and_resource_controls_equal",
        "native_actual_trajectory_equal_or_required",
        "source_plugin_and_all_five_profiles_newly_qualified_for_v8",
        "science_grant_issued", "science_go", "production_go",
    ):
        assert verdict[field] is False, field


@pytest.mark.parametrize("arm", sorted(r.ARMS))
def test_foreign_changed_region_or_mobs_per_arm_fail_closed(tmp_path, arm):
    source, clones = setup_stopped(tmp_path)
    (clones[arm] / "region" / "r.0.0.mca").write_bytes(b"hidden-different-collision")
    with pytest.raises(r.CloneRejected, match="differs"):
        r.review_stopped_clones(source, clones, seed=62101)


@pytest.mark.parametrize("part", [
    "level.dat", "region/r.0.0.mca", "entities/r.0.0.mca",
    "data/scoreboard.dat", "session.lock",
])
def test_seed_or_level_dat_comparison_alone_cannot_hide_any_changed_file(tmp_path, part):
    source, clones = setup_stopped(tmp_path)
    (clones["BASAL_ZERO"] / part).write_bytes(b"changed")
    with pytest.raises(r.CloneRejected, match="differs"):
        r.review_stopped_clones(source, clones, seed=62101)


def test_missing_or_extra_file_rejected_even_if_seed_is_same(tmp_path):
    source, clones = setup_stopped(tmp_path)
    (clones["SHAM_ON"] / "data" / "scoreboard.dat").unlink()
    with pytest.raises(r.CloneRejected, match="differs"):
        r.review_stopped_clones(source, clones, seed=62101)
    shutil.copyfile(source / "data" / "scoreboard.dat",
                    clones["SHAM_ON"] / "data" / "scoreboard.dat")
    (clones["SHAM_ON"] / "data" / "extra.dat").write_bytes(b"extra")
    with pytest.raises(r.CloneRejected, match="differs"):
        r.review_stopped_clones(source, clones, seed=62101)


def test_separate_roots_and_world_non_aliasing_required(tmp_path):
    source, clones = setup_stopped(tmp_path)
    clones["SHAM_ON"] = clones["BASE_ON"]
    with pytest.raises(r.CloneRejected, match="aliased"):
        r.review_stopped_clones(source, clones, seed=62101)
    clones["SHAM_ON"] = source
    with pytest.raises(r.CloneRejected, match="aliased"):
        r.review_stopped_clones(source, clones, seed=62101)


def test_symlinks_and_noncanonical_roots_denied(tmp_path):
    source, clones = setup_stopped(tmp_path)
    linked = tmp_path / "alias"
    linked.symlink_to(source, target_is_directory=True)
    with pytest.raises(r.CloneRejected, match="symlink"):
        r.review_stopped_clones(linked, clones, seed=62101)
    with pytest.raises(r.CloneRejected, match="relative"):
        r.review_stopped_clones(Path("relative"), clones, seed=62101)
    missing = clones["WALK_ZERO"] / "region" / "r.0.0.mca"
    missing.unlink()
    missing.symlink_to(source / "region" / "r.0.0.mca")
    with pytest.raises(r.CloneRejected, match="symlink"):
        r.review_stopped_clones(source, clones, seed=62101)


@pytest.mark.parametrize("seed", [61021, 62100, 62109, True, -1, 0])
def test_out_of_roster_seed_cannot_enter_v8(seed, tmp_path):
    source, clones = setup_stopped(tmp_path)
    with pytest.raises(r.CloneRejected, match="seed"):
        r.review_stopped_clones(source, clones, seed=seed)


def test_wrong_arm_set_fails_even_with_matching_clone_bytes(tmp_path):
    source, clones = setup_stopped(tmp_path)
    clones.pop("WALK_ZERO")
    with pytest.raises(r.CloneRejected, match="arm"):
        r.review_stopped_clones(source, clones, seed=62101)
    clones["INVALID"] = shutil.copytree(source, tmp_path / "foreign")
    with pytest.raises(r.CloneRejected, match="arm"):
        r.review_stopped_clones(source, clones, seed=62101)


def test_only_level_dat_and_no_real_chunk_files_rejected(tmp_path):
    source, clones = setup_stopped(tmp_path)
    for root in (source, *clones.values()):
        (root / "region" / "r.0.0.mca").unlink()
    with pytest.raises(r.CloneRejected, match="generated terrain"):
        r.review_stopped_clones(source, clones, seed=62101)


def test_empty_chunk_not_accepted_as_world_initial_state(tmp_path):
    source, clones = setup_stopped(tmp_path)
    for root in (source, *clones.values()):
        (root / "region" / "r.0.0.mca").write_bytes(b"")
    with pytest.raises(r.CloneRejected, match="empty terrain"):
        r.review_stopped_clones(source, clones, seed=62101)


def test_cli_is_read_only_and_never_issues_qual_or_science_grant(
    tmp_path, monkeypatch, capsys,
):
    import sys

    source, clones = setup_stopped(tmp_path)
    initial = {root.name: r.world_index(root)
               for root in (source, *clones.values())}
    args = ["r-v8", "--source", str(source), "--seed", "62101"]
    for arm, root in sorted(clones.items()):
        args += ["--arm-root", f"{arm}={root}"]
    monkeypatch.setattr(sys, "argv", args)
    assert r.main() == 0
    verdict = json.loads(capsys.readouterr().out)
    assert verdict["classification"] == r.CLASS
    assert verdict["science_go"] is False
    assert verdict["source_plugin_and_all_five_profiles_newly_qualified_for_v8"] is False
    assert initial == {root.name: r.world_index(root)
                       for root in (source, *clones.values())}
    args += ["--arm-root", f"SHAM_ON={clones['SHAM_ON']}"]
    monkeypatch.setattr(sys, "argv", args)
    assert r.main() == 2
    assert json.loads(capsys.readouterr().out)["science_go"] is False
