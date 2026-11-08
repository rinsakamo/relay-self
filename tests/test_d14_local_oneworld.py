"""D14 R5 local one-use preflight, exact source and interrupted evidence."""
from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path

import pytest

from tools import bug0_d14_local_oneworld as local


@pytest.mark.parametrize("value", [True, False, None, -1, 0, 599, 7201, 1.0, "3600"])
def test_watchdog_requires_bounded_integer(value):
    with pytest.raises(local.D14LocalRejected, match="WATCHDOG"):
        local.validate_watchdog(value)


@pytest.mark.parametrize("value", [600, 1200, 1800, 3600, 7200])
def test_local_watchdog_allows_bounded_range(value):
    assert local.validate_watchdog(value) == value


def _fixture_paths(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    external = tmp_path / "evidence"
    paper = tmp_path / "paper.jar"
    plugin = tmp_path / local.PLUGIN_NAME
    paper.write_bytes(b"official-pinned-paper")
    plugin.write_bytes(b"built-respawn-plugin")
    paper_hash = hashlib.sha256(paper.read_bytes()).hexdigest()
    plugin_hash = hashlib.sha256(plugin.read_bytes()).hexdigest()
    monkeypatch.setattr(local, "PAPER_1218_SIZE", paper.stat().st_size)
    monkeypatch.setattr(local, "PAPER_1218_SHA256", paper_hash)
    env = {
        **{k: "1" for k in (*local.R3_ENV, local.R4_GRANT, local.R5_GRANT)},
        "D14_R3_PAPER_JAR": str(paper),
        "D14_R3_RESPAWN_JAR": str(plugin),
        "D14_R3_RESPAWN_SHA256": plugin_hash,
    }
    return repo, external, paper, plugin, env


def _validate(paths, *, check_checkout=False):
    repo, external, paper, plugin, env = paths
    return local.validate_local_sources(
        repo=repo, output_dir=external, paper=paper, plugin=plugin,
        exact_head="a" * 40, watchdog=3600, environment=env,
        check_checkout=check_checkout, check_port=False,
    )


def test_preflight_is_source_bound_not_model_or_world_stage(tmp_path, monkeypatch):
    paths = _fixture_paths(tmp_path, monkeypatch)
    accepted = _validate(paths)
    assert accepted["source_head"] == "a" * 40
    assert accepted["physical_issuer"] == "ORIGINAL_S49_ONLY"
    assert not paths[1].exists()


def test_preflight_requires_independent_one_world_grant(tmp_path, monkeypatch):
    paths = _fixture_paths(tmp_path, monkeypatch)
    paths[4].pop(local.R5_GRANT)
    with pytest.raises(local.D14LocalRejected, match="GRANTS"):
        _validate(paths)
    assert not paths[1].exists()


def test_preflight_does_not_create_or_replace_world_evidence(tmp_path, monkeypatch):
    paths = _fixture_paths(tmp_path, monkeypatch)
    paths[1].mkdir()
    (paths[1] / "paper_original.log").write_text("original")
    with pytest.raises(local.D14LocalRejected, match="ALREADY_EXIST"):
        _validate(paths)
    assert (paths[1] / "paper_original.log").read_text() == "original"


def test_preflight_refuses_dirty_or_wrong_plugin(tmp_path, monkeypatch):
    paths = _fixture_paths(tmp_path, monkeypatch)
    paths[3].write_bytes(b"tampered-plugin")
    with pytest.raises(local.D14LocalRejected, match="PLUGIN_SOURCE"):
        _validate(paths)


def test_preflight_refuses_evidence_inside_checkout(tmp_path, monkeypatch):
    paths = _fixture_paths(tmp_path, monkeypatch)
    paths = (paths[0], paths[0] / "inside", *paths[2:])
    with pytest.raises(local.D14LocalRejected, match="OUTSIDE_REPOSITORY"):
        _validate(paths)


def test_preflight_refuses_node_options(tmp_path, monkeypatch):
    paths = _fixture_paths(tmp_path, monkeypatch)
    paths[4]["NODE_OPTIONS"] = "--no-warnings"
    with pytest.raises(local.D14LocalRejected, match="NODE_OPTIONS"):
        _validate(paths)


def test_exact_head_validation_never_uses_partial_ref(tmp_path):
    with pytest.raises(local.D14LocalRejected, match="40_HEX"):
        local.validate_local_checkout(tmp_path, "main")


def test_local_manifest_tracks_all_and_refuses_tampering(tmp_path):
    (tmp_path / "source.log").write_text("before")
    (tmp_path / "report.json").write_text("{}")
    local.write_manifest_once(tmp_path)
    assert local.validate_manifest(tmp_path) is True
    with pytest.raises(FileExistsError):
        local.write_manifest_once(tmp_path)
    (tmp_path / "source.log").write_text("after")
    assert local.validate_manifest(tmp_path) is False


def test_partial_source_does_not_fabricate_terminal_or_outcome(tmp_path):
    (tmp_path / "paper_original.log").write_text(
        "RSELF_ENDURANCE_START world=fake start_tick=1\n"
        "RSELF_ENDURANCE_SAMPLE world=fake tick=201 elapsed_ticks=200\n"
    )
    (tmp_path / "d14_natural_events.jsonl").write_text(
        '{"kind":"LIFE_DECISION"}\ninvalid-json\n'
    )
    result = local.source_only_partial(tmp_path)
    assert result["status"] == "PARTIAL_SOURCE_ONLY_NOT_QUALIFIED"
    assert result["paper_checkpoints"] == 1
    assert result["paper_limit_markers"] == 0
    assert result["paper_early_terminals"] == 0
    assert result["derivative_has_invalid_records"] is True
    assert result["long_run_survival_proven"] is False


def test_local_wrapper_saves_failure_once_without_retry(tmp_path, monkeypatch):
    paths = _fixture_paths(tmp_path, monkeypatch)
    repo, external, paper, plugin, env = paths
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setattr(local, "validate_local_checkout", lambda *_: None)
    seen = []

    async def fake_world(report_path, paper_log, journal_path, **kwargs):
        seen.append(kwargs)
        report_path.write_text(json.dumps({
            "status": "FAIL", "new_s49_actions": 0,
            "failure": "NATIVE_SOURCE_NOT_AVAILABLE",
        }))
        paper_log.write_text("RSELF_ENDURANCE_START world=source tick=1\n")
        journal_path.write_text("")
        return 2

    monkeypatch.setattr(local, "run", fake_world)
    assert asyncio.run(local.run_local(
        repo=repo, output_dir=external, paper=paper, plugin=plugin,
        exact_head="a" * 40, watchdog=3600,
    )) == 2
    assert len(seen) == 1
    assert seen[0]["max_wall_seconds"] == 3600
    assert local.validate_manifest(external)
    partial = json.loads((external / "local_partial_source_only.json").read_text())
    assert partial["original_report_status"] == "FAIL"
    assert not (external / "independent_audit.json").exists()


def test_audit_failure_preserves_original_and_does_not_claim_pass(tmp_path, monkeypatch):
    paths = _fixture_paths(tmp_path, monkeypatch)
    repo, external, paper, plugin, env = paths
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setattr(local, "validate_local_checkout", lambda *_: None)
    original = {"status": "PASS_DEV", "new_s49_actions": 0}

    async def incomplete_world(report_path, paper_log, journal_path, **kwargs):
        report_path.write_text(json.dumps(original))
        paper_log.write_text("")
        journal_path.write_text("")
        return 0

    monkeypatch.setattr(local, "run", incomplete_world)
    assert asyncio.run(local.run_local(
        repo=repo, output_dir=external, paper=paper, plugin=plugin,
        exact_head="a" * 40,
    )) == 2
    assert json.loads((external / "report.json").read_text()) == original
    assert (external / "independent_audit_error.json").exists()
    assert not (external / "independent_audit.json").exists()
    assert local.validate_manifest(external)
