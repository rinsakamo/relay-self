"""S50 FLAT four-arm replay: offline-only negative and summary controls."""
from __future__ import annotations

import argparse
import asyncio

import pytest

from adapters.mineflayer.m02_paper_dev import s50_flat_four_foraging_dev as subject


def example_reports():
    return [
        {
            "arm": arm,
            "status": "PASS",
            "cleanup_complete": True,
            "basal_multiplier": subject.ARMS[arm][0],
            "walk_multiplier": subject.ARMS[arm][1],
            "config_sha256": "a" * 64,
            "java_launch_attempts": 1,
            "node_launch_attempts": 1,
            "initial_server_marker": {
                "seed": "63101", "full_time": str(20 + i),
                "x": "0.5", "y": "-60.0", "z": "0.5",
                "yaw": "0.0", "pitch": "0.0",
            },
            "foraging": {
                "status": "PICKUP_SOURCE_CONSISTENT",
                "movement_outcomes": [{"kind": "PROGRESSED"}, {"kind": "ARRIVED"}],
                "pickup": {"cooked_beef_inventory_delta": 1},
            },
            "eating": {"status": "EAT_RECORDED"},
        }
        for i, arm in enumerate(subject.ARMS_TO_RUN)
    ]


def test_only_four_unattempted_arms_not_baseline():
    assert subject.ARMS_TO_RUN == ("SHAM_ON", "BASAL_ZERO", "WALK_ZERO", "BOTH_ZERO")
    assert len(set(subject.ARMS_TO_RUN)) == 4
    assert "BASE_ON" not in subject.ARMS_TO_RUN
    assert set(subject.ARMS_TO_RUN) == set(subject.ARMS) - {"BASE_ON"}
    assert subject.BASE_ON_HISTORICAL_RUN == 38990613628


@pytest.mark.parametrize("wrong", ["", "SCIENCE", "QUALIFICATION", "V8-FIVE-WORLD-DEV-ONLY"])
def test_preflight_refuses_foreign_modes(wrong, monkeypatch, tmp_path):
    def unreachable(*_args, **_kwargs):
        raise AssertionError("must not access assets or start World")
    monkeypatch.setattr(subject.base, "preflight", unreachable)
    args = argparse.Namespace(confirm=wrong, archive=tmp_path,
                              paper_jar=tmp_path / "paper.jar",
                              plugin_jar=tmp_path / "plugin.jar",
                              plugin_sha256="0" * 64,
                              output=tmp_path / "new")
    with pytest.raises(ValueError, match="consent"):
        subject.preflight(args)
    assert not args.output.exists()


def test_four_positive_dev_behaviors_not_science(monkeypatch, tmp_path):
    expected = [{"relative_path": "level.dat", "size": 1, "sha256": "a" * 64}]
    monkeypatch.setattr(subject, "world_index", lambda _path: expected)
    summary = subject.summarize(example_reports(), tmp_path, expected)
    assert summary["all_four_executed"]
    assert summary["all_four_behavioral_pass"]
    assert summary["same_initial_native_pose"]
    assert not summary["same_initial_native_full_time"]
    assert not summary["not_run"]
    assert summary["historical_base_on_run_not_reexecuted"] == 38990613628
    assert not summary["science_go"]
    assert not summary["engineering_qualified"]
    assert summary["science_trials"] == summary["retries"] == 0


def test_failure_is_not_promoted_or_hidden(monkeypatch, tmp_path):
    expected = []
    monkeypatch.setattr(subject, "world_index", lambda _: expected)
    reports = example_reports()
    reports[2]["status"] = "FAIL"
    reports[2]["eating"] = None
    reports[2]["foraging"]["status"] = "INCOMPLETE_NOT_PICKUP"
    summary = subject.summarize(reports, tmp_path, expected)
    assert summary["all_four_executed"]
    assert not summary["all_four_behavioral_pass"]
    assert summary["arms"]["WALK_ZERO"]["behavioral_status"] == "FAIL"
    assert not summary["arms"]["WALK_ZERO"]["S51_eat_recorded"]


def test_partial_stopped_execution_leaves_future_arms_not_run(monkeypatch, tmp_path):
    monkeypatch.setattr(subject, "world_index", lambda _: [])
    reports = example_reports()[:2]
    reports[1]["cleanup_complete"] = False
    summary = subject.summarize(reports, tmp_path, [])
    assert not summary["all_four_executed"]
    assert summary["not_run"] == ["WALK_ZERO", "BOTH_ZERO"]
    assert not summary["all_four_behavioral_pass"]


def test_rejects_source_world_drift(monkeypatch, tmp_path):
    monkeypatch.setattr(subject, "world_index", lambda _: [{"mutated": True}])
    with pytest.raises(ValueError, match="mutated"):
        subject.summarize(example_reports(), tmp_path, [])


def test_rejects_arm_reordering_or_profile_tampering(monkeypatch, tmp_path):
    monkeypatch.setattr(subject, "world_index", lambda _: [])
    reports = example_reports()
    reports[0], reports[1] = reports[1], reports[0]
    with pytest.raises(ValueError, match="order"):
        subject.summarize(reports, tmp_path, [])
    reports = example_reports()
    reports[1]["basal_multiplier"] = 1
    with pytest.raises(ValueError, match="configuration"):
        subject.summarize(reports, tmp_path, [])


def test_rejects_natural_world_seed_inside_flat_arm(monkeypatch, tmp_path):
    monkeypatch.setattr(subject, "world_index", lambda _: [])
    reports = example_reports()
    reports[0]["initial_server_marker"]["seed"] = "62101"
    with pytest.raises(ValueError, match="seed"):
        subject.summarize(reports, tmp_path, [])


def test_host_cleanup_failure_prevents_next_world(monkeypatch, tmp_path):
    outputs = []
    monkeypatch.setattr(subject, "preflight", lambda args: [])
    monkeypatch.setattr(subject, "world_index", lambda path: [])
    monkeypatch.setattr(subject.base.owner, "_port_free", lambda: True)

    async def run_one(_archive, _out, arm, _paper, _plugin, _expected):
        outputs.append(arm)
        row = example_reports()[len(outputs) - 1]
        row["cleanup_complete"] = False
        return row

    monkeypatch.setattr(subject.base, "arm_run", run_one)
    args = argparse.Namespace(archive=tmp_path / "archive",
                              paper_jar=tmp_path / "paper",
                              plugin_jar=tmp_path / "plugin",
                              plugin_sha256="x" * 64,
                              output=tmp_path / "out", confirm=subject.CONFIRM)
    assert asyncio.run(subject.run(args)) == 2
    assert outputs == ["SHAM_ON"]
    assert (args.output / "summary.json").is_file()


def test_profiles_and_sham_bytes():
    from adapters.mineflayer.m02_paper_dev.v7_paired_config import TEMPLATE, render_arm
    assert [subject.ARMS[a] for a in subject.ARMS_TO_RUN] == [(1, 1), (0, 1), (1, 0), (0, 0)]
    assert render_arm(TEMPLATE.read_bytes(), "BASE_ON") == render_arm(TEMPLATE.read_bytes(), "SHAM_ON")


@pytest.mark.parametrize("field", ["archive", "paper_jar", "plugin_jar", "output"])
def test_symlink_ancestors_rejected_before_asset_checks(field, monkeypatch, tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(real, target_is_directory=True)
    args = argparse.Namespace(confirm=subject.CONFIRM, archive=tmp_path / "archive",
                              paper_jar=tmp_path / "paper.jar", plugin_jar=tmp_path / "plugin.jar",
                              plugin_sha256=subject.base.PLUGIN_SHA, output=tmp_path / "output")
    setattr(args, field, alias / "child")
    monkeypatch.setattr(subject.base, "preflight", lambda *a: pytest.fail("unsafe delegation"))
    with pytest.raises(ValueError, match="symlinks"):
        subject.preflight(args)


def test_lifecycle_exception_retained_and_later_arms_not_run(monkeypatch, tmp_path):
    monkeypatch.setattr(subject, "preflight", lambda _: [])
    monkeypatch.setattr(subject, "world_index", lambda _: [])
    monkeypatch.setattr(subject.base.owner, "_port_free", lambda: True)
    calls = []

    async def broken(*args):
        calls.append(args[2])
        raise OSError("stop could not be proved")

    monkeypatch.setattr(subject.base, "arm_run", broken)
    args = argparse.Namespace(archive=tmp_path / "archive", paper_jar=tmp_path / "paper",
                              plugin_jar=tmp_path / "plugin", output=tmp_path / "out")
    assert asyncio.run(subject.run(args)) == 2
    assert calls == ["SHAM_ON"]
    import json
    summary = json.loads((args.output / "summary.json").read_text())
    assert summary["not_run"] == ["BASAL_ZERO", "WALK_ZERO", "BOTH_ZERO"]
    assert summary["arms"]["SHAM_ON"]["behavioral_status"] == "FAIL"
    assert (args.output / "SHAM_ON-launcher-error.json").exists()


@pytest.mark.parametrize("mutation", ["seed", "source", "paper", "plugin", "overlap"])
def test_real_preflight_negative_controls(mutation, monkeypatch, tmp_path):
    from test_s50_flat_base_foraging_dev import fixture, inject_asset_probes
    archive, paper, plugin, output = fixture(tmp_path)
    inject_asset_probes(monkeypatch)
    if mutation == "seed":
        prop = archive / "flat-source/server/server.properties"
        prop.write_bytes(prop.read_bytes().replace(b"63101", b"63102"))
    elif mutation == "source":
        (archive / subject.base.FLAT_SOURCE / "region/r.0.0.mca").write_bytes(b"mutation")
    elif mutation in ("paper", "plugin"):
        def real_asset_check(path, digest):
            from adapters.mineflayer.m02_paper_dev.v8_stopped_world_clone_dev import sha
            if path == {"paper": paper, "plugin": plugin}[mutation] and sha(path) != digest:
                raise ValueError("asset SHA256 mismatch")
        monkeypatch.setattr(subject.base.owner, "_fresh_asset", real_asset_check)
    else:
        output = archive / "forbidden-new-world"
    args = argparse.Namespace(confirm=subject.CONFIRM, archive=archive,
                              paper_jar=paper, plugin_jar=plugin,
                              plugin_sha256=subject.base.PLUGIN_SHA, output=output)
    with pytest.raises(ValueError):
        subject.preflight(args)
    assert not output.exists()
