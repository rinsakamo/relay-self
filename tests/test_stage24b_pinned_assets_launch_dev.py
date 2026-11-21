"""Stage24b pinned-jar run guard: SYNTHETIC offline tests, no actual World."""
from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from types import SimpleNamespace

import pytest

from experiments import p0d_real_two_native_smoke_dev as original_runtime
from experiments import stage24b_pinned_assets_launch_dev as launch
from experiments.p0d_real_paper_smoke_dev import file_sha256
from relay_self.mineflayer_oxygen_patch_dev import SELF_OWNED


def _assets(tmp_path, monkeypatch):
    paper = tmp_path / "paper.jar"
    plugin = tmp_path / "P0BRecorder.jar"
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    with zipfile.ZipFile(paper, "w") as z:
        z.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\n")
    with zipfile.ZipFile(plugin, "w") as z:
        z.writestr("plugin.yml", "name: P0BRecorder\nversion: 1.0\n")
        z.writestr("io/github/rinsakamo/p0b/TickWitness.class", b"fixture")
        z.writestr("io/github/rinsakamo/p0b/Recorder.class", b"fixture")
        z.writestr("io/github/rinsakamo/p0b/ResidentPresenceWitness.class", b"fixture")
    # Fixture-specific pinned values: production constants stay pinned to the
    # independently archived actual Paper/build60 and P0BRecorder binaries.
    monkeypatch.setattr(launch, "PAPER_1218_60_SHA256", file_sha256(paper))
    monkeypatch.setattr(launch, "PINNED_STAGE24B_PLUGIN_SHA256", file_sha256(plugin))
    # Synthetic jars do not require actual host Java/Node/npm provisioning;
    # explicit CLI tests below replace this guard to verify original behavior.
    monkeypatch.setattr(launch, "_verify_local_runtime", lambda java, node: None)
    return paper, plugin, scratch


def test_production_plugin_pin_is_archived_confirmed_sha256():
    assert (
        launch.PINNED_STAGE24B_PLUGIN_SHA256
        == "cabf144a275c1582ecbbdcb6fb394b311f0705f5ca7d330bb80659437abe324e"
    )
    assert len(launch.PINNED_STAGE24B_PLUGIN_SHA256) == 64


def test_verified_bytes_pass_existing_preflight_without_world(tmp_path, monkeypatch):
    paper, plugin, scratch = _assets(tmp_path, monkeypatch)
    result = launch.check_stage24b_pinned_assets(
        paper_jar=paper, plugin_jar=plugin,
        scratch_parent=scratch, accepted_eula=True,
    )
    assert result.paper_sha256 == file_sha256(paper)
    assert result.plugin_sha256 == file_sha256(plugin)
    assert result.world_created is False
    assert result.gpu_used is False
    assert result.physical_action_issued is False
    assert list(scratch.iterdir()) == []


def test_typo_or_modified_plugin_hold_before_world(tmp_path, monkeypatch):
    paper, plugin, scratch = _assets(tmp_path, monkeypatch)
    with plugin.open("ab") as output:
        output.write(b"unexpected-mutation")
    with pytest.raises(launch.Stage24bPinnedPreflightRefusal, match="do not match"):
        launch.check_stage24b_pinned_assets(
            paper_jar=paper, plugin_jar=plugin,
            scratch_parent=scratch, accepted_eula=True,
        )
    assert not any(scratch.iterdir())


def test_wrong_archived_pin_hold_before_world(tmp_path, monkeypatch):
    paper, plugin, scratch = _assets(tmp_path, monkeypatch)
    monkeypatch.setattr(
        launch, "PINNED_STAGE24B_PLUGIN_SHA256",
        "cabf144a275c1582ecbbdcb6fb394b311f0705f5ca7f5ca7d330bb80659437abe324e",
    )
    with pytest.raises(launch.Stage24bPinnedPreflightRefusal, match="invalid pinned"):
        launch.check_stage24b_pinned_assets(
            paper_jar=paper, plugin_jar=plugin,
            scratch_parent=scratch, accepted_eula=True,
        )


def test_foreign_symlink_and_absent_eula_refused(tmp_path, monkeypatch):
    paper, plugin, scratch = _assets(tmp_path, monkeypatch)
    link = tmp_path / "linked-plugin.jar"
    link.symlink_to(plugin)
    with pytest.raises(launch.Stage24bPinnedPreflightRefusal, match="symlink"):
        launch.check_stage24b_pinned_assets(
            paper_jar=paper, plugin_jar=link,
            scratch_parent=scratch, accepted_eula=True,
        )
    with pytest.raises(launch.Stage24bPinnedPreflightRefusal, match="EULA"):
        launch.check_stage24b_pinned_assets(
            paper_jar=paper, plugin_jar=plugin,
            scratch_parent=scratch, accepted_eula=False,
        )


def test_inspect_only_cli_never_executes_original_world_runner(
    tmp_path, monkeypatch, capsys,
):
    paper, plugin, scratch = _assets(tmp_path, monkeypatch)

    async def unexpected_world(**kwargs):
        raise AssertionError("inspect-only must not create World or call model")

    monkeypatch.setattr(launch, "run_real_resident_presence", unexpected_world)
    monkeypatch.setattr(sys, "argv", [
        "stage24b_pinned_assets_launch_dev",
        "--paper-jar", str(paper),
        "--plugin-jar", str(plugin),
        "--scratch-parent", str(scratch),
        "--eula-accepted",
        "--inspect-only",
    ])
    assert launch.main() == 0
    assert "STAGE24B_ASSET_CHECK_OK" in capsys.readouterr().out
    assert not any(scratch.iterdir())



def test_inspect_only_invokes_original_local_runtime_gate(
    tmp_path, monkeypatch, capsys,
):
    paper, plugin, scratch = _assets(tmp_path, monkeypatch)
    checked = []

    def verify(java, node):
        checked.append((java, node))

    async def unexpected_world(**kwargs):
        raise AssertionError("inspect-only must not create a World")

    monkeypatch.setattr(launch, "_verify_local_runtime", verify)
    monkeypatch.setattr(launch, "run_real_resident_presence", unexpected_world)
    monkeypatch.setattr(sys, "argv", [
        "stage24b_pinned_assets_launch_dev",
        "--paper-jar", str(paper), "--plugin-jar", str(plugin),
        "--scratch-parent", str(scratch), "--eula-accepted",
        "--inspect-only",
    ])
    assert launch.main() == 0
    assert checked == [("java", "node")]
    assert "STAGE24B_RUNTIME_CHECK_OK" in capsys.readouterr().out
    assert not any(scratch.iterdir())


def test_inspect_only_missing_local_lock_dependencies_is_hold(
    tmp_path, monkeypatch, capsys,
):
    paper, plugin, scratch = _assets(tmp_path, monkeypatch)

    def missing(java, node):
        raise original_runtime.TwoNativePaperRefusal(
            "locked mineflayer dependencies absent; npm ci --prefix adapters/mineflayer"
        )

    async def unexpected_world(**kwargs):
        raise AssertionError("missing worktree install must fail before World")

    monkeypatch.setattr(launch, "_verify_local_runtime", missing)
    monkeypatch.setattr(launch, "run_real_resident_presence", unexpected_world)
    monkeypatch.setattr(sys, "argv", [
        "stage24b_pinned_assets_launch_dev",
        "--paper-jar", str(paper), "--plugin-jar", str(plugin),
        "--scratch-parent", str(scratch), "--eula-accepted",
        "--inspect-only",
    ])
    assert launch.main() == 2
    result = capsys.readouterr()
    assert "STAGE24B_RUNTIME_CHECK_OK" not in result.out
    assert "locked mineflayer dependencies absent" in result.err
    assert not any(scratch.iterdir())


def test_original_runtime_rejects_external_node_path_instead_of_local_lock(
    tmp_path, monkeypatch,
):
    # A real PATH/NODE_PATH lookup is NOT the source used by original runner.
    # Simulate Java 21 + Node 22 as already installed, without touching real
    # npm cache or executing untrusted packages.
    source = tmp_path / "experiments" / "p0d_real_two_native_smoke_dev.py"
    monkeypatch.setattr(original_runtime, "__file__", str(source))

    def fake_runtime(args, **kwargs):
        if args[-1] == "-version":
            return SimpleNamespace(stdout="", stderr='openjdk version "21.0.12"')
        assert args[-1] == "--version"
        return SimpleNamespace(stdout="v22.22.2", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_runtime)
    external = tmp_path / "outside" / "node_modules"
    external.mkdir(parents=True)
    monkeypatch.setenv("NODE_PATH", str(external))
    (external / "mineflayer").mkdir()
    (external / "mineflayer" / "package.json").write_text(
        json.dumps({"version": "4.39.0"}),
    )
    with pytest.raises(
        original_runtime.TwoNativePaperRefusal,
        match="locked mineflayer dependencies absent",
    ):
        original_runtime._verify_local_runtime("java", "node")

    local = tmp_path / "adapters" / "mineflayer" / "node_modules" / "mineflayer"
    local.mkdir(parents=True)
    package = local / "package.json"
    package.write_text(json.dumps({"version": "4.39.1"}))
    with pytest.raises(
        original_runtime.TwoNativePaperRefusal, match="only locked Mineflayer 4.39.0",
    ):
        original_runtime._verify_local_runtime("java", "node")
    package.write_text(json.dumps({"version": "4.39.0"}))
    entities = local / "lib" / "plugins" / "entities.js"
    entities.parent.mkdir(parents=True)
    entities.write_text(SELF_OWNED)
    original_runtime._verify_local_runtime("java", "node")


def test_execute_once_requires_grants_and_actual_model_endpoint(
    tmp_path, monkeypatch,
):
    paper, plugin, scratch = _assets(tmp_path, monkeypatch)
    monkeypatch.setattr(sys, "argv", [
        "stage24b_pinned_assets_launch_dev",
        "--paper-jar", str(paper),
        "--plugin-jar", str(plugin),
        "--scratch-parent", str(scratch),
        "--eula-accepted",
        "--execute-once",
    ])
    assert launch.main() == 2
    assert not any(scratch.iterdir())


def test_explicit_execute_once_passes_computed_pins_to_original_runner(
    tmp_path, monkeypatch, capsys,
):
    paper, plugin, scratch = _assets(tmp_path, monkeypatch)
    calls = []

    async def original_real_runner(**kwargs):
        calls.append(kwargs)
        return tmp_path / "result-placeholder.json"

    monkeypatch.setattr(launch, "run_real_resident_presence", original_real_runner)
    monkeypatch.setattr(sys, "argv", [
        "stage24b_pinned_assets_launch_dev",
        "--paper-jar", str(paper),
        "--plugin-jar", str(plugin),
        "--scratch-parent", str(scratch),
        "--eula-accepted",
        "--execute-once",
        "--real-world-dev-grant",
        "--grant-real-llm",
        "--llama-endpoint", "http://127.0.0.1:8080/v1/chat/completions",
        "--systemone-endpoint", "http://127.0.0.1:8080/v1/systemone",
        "--model", "stage24b-gemma",
    ])
    assert launch.main() == 0
    assert len(calls) == 1
    call = calls[0]
    assert call["paper_sha256"] == file_sha256(paper)
    assert call["plugin_sha256"] == file_sha256(plugin)
    assert call["b_autonomous_l1_dev"] is True
    assert call["b_selected_move_dev"] is False
    assert call["b_pulse_seconds"] == 0.35
    assert call["world_only"] is True
    assert call["real_world_dev_grant"] is True
    assert call["real_llm_grant"] is True
    assert "STAGE24B_ONESHOT_REAL_RESULT" in capsys.readouterr().out
    assert list(scratch.iterdir()) == []
