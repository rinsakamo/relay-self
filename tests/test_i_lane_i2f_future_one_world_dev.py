"""I2f new source pin and one-World boundary without real Paper/GPU."""
from __future__ import annotations

import asyncio
import json
from dataclasses import asdict

import pytest

from experiments import i_lane_i2f_future_one_world_dev as real
from experiments import stage28c2b_real_recovered_rejoin_dev as legacy
from relay_self.i_lane_i2f_future_source_pins_dev import (
    I2fFuturePinsHold,
    I2fFutureSourcePins,
    inspect_i2f_future_original_sources,
    read_i2f_future_source_pins,
    verify_i2f_original_source_unchanged,
)
from test_i_lane_i2e_future_original_preflight_dev import _future


def _pins(args, *, manifest="a" * 64):
    return I2fFutureSourcePins(
        source_world_id=args["expected_world_id"],
        source_branch_id=args["expected_source_branch_id"],
        source_committed_sha256=args["expected_committed_sha256"],
        fork_branch_id=args["expected_fork_branch_id"],
        original_manifest_sha256=manifest,
        original_manifest_files=285,
    )


def test_i2f_read_explicit_new_v3_pins_no_world(tmp_path, monkeypatch):
    args = _future(tmp_path, monkeypatch)
    pins = _pins(args)
    file = tmp_path / "source-pins.json"
    file.write_text(json.dumps(asdict(pins)))
    assert read_i2f_future_source_pins(file) == pins
    assert not pins.source_committed_sha256 == legacy._SOURCE_COMMITTED_SHA
    assert not pins.source_world_id == legacy._SOURCE_WORLD
    assert file.read_text().startswith("{")
    assert not (tmp_path / "i2f-execution").exists()


@pytest.mark.parametrize("fault", [
    "missing", "extra", "corrupt", "bad-commit", "bad-evidence",
    "bad-count", "foreign-fork", "bool-count", "symlink",
])
def test_i2f_pins_fail_closed_without_old_default(tmp_path, monkeypatch, fault):
    args = _future(tmp_path, monkeypatch)
    valid = asdict(_pins(args))
    if fault == "missing":
        del valid["source_world_id"]
    elif fault == "extra":
        valid["legacy_source_default"] = True
    elif fault == "bad-commit":
        valid["source_committed_sha256"] = "x" * 64
    elif fault == "bad-evidence":
        valid["original_manifest_sha256"] = "0" * 63
    elif fault == "bad-count":
        valid["original_manifest_files"] = 0
    elif fault == "bool-count":
        valid["original_manifest_files"] = True
    elif fault == "foreign-fork":
        valid["fork_branch_id"] = ""
    file = tmp_path / "source-pins.json"
    file.write_text("{broken" if fault == "corrupt" else json.dumps(valid))
    if fault == "symlink":
        other = tmp_path / "real.json"
        file.rename(other)
        file.symlink_to(other)
    with pytest.raises(I2fFuturePinsHold):
        read_i2f_future_source_pins(file)


@pytest.mark.parametrize("fault", [
    "missing-evidence", "unqualified-manifest", "foreign-commit",
    "foreign-fork", "malformed-pins",
])
def test_i2f_future_source_inspection_requires_actual_original_native(
    tmp_path, monkeypatch, fault,
):
    args = _future(tmp_path, monkeypatch)
    evidence = tmp_path / "future-origin-evidence"
    if fault != "missing-evidence":
        evidence.mkdir()
    pins = _pins(args)
    if fault == "foreign-commit":
        pins = I2fFutureSourcePins(
            pins.source_world_id, pins.source_branch_id, "0" * 64,
            pins.fork_branch_id, pins.original_manifest_sha256, 285,
        )
    elif fault == "foreign-fork":
        pins = I2fFutureSourcePins(
            pins.source_world_id, pins.source_branch_id,
            pins.source_committed_sha256, "foreign-fork",
            pins.original_manifest_sha256, 285,
        )
    elif fault == "malformed-pins":
        pins = object()
    # Neither a valid future v3 cut alone nor guessed source strings
    # authenticate historic raw Mineflayer/Paper evidence.
    with pytest.raises(I2fFuturePinsHold):
        inspect_i2f_future_original_sources(
            generation=args["generation"], restored=args["restored"],
            original_evidence=evidence, pins=pins,
        )
    assert not (tmp_path / "one-world-exec").exists()


def test_i2f_source_unchanged_refuses_unverified_original_evidence(
    tmp_path, monkeypatch,
):
    args = _future(tmp_path, monkeypatch)
    with pytest.raises(I2fFuturePinsHold):
        verify_i2f_original_source_unchanged(
            generation=args["generation"],
            original_evidence=tmp_path / "missing-evidence",
            pins=_pins(args),
        )


def test_i2f_original_runner_default_pinned_stage28b_is_not_rebound(
    tmp_path, monkeypatch,
):
    assert legacy._SOURCE_COMMITTED_SHA == (
        "d1425c49a5ef0ff03486931427907aeed6eccf568494efd8177ed96d3ce3f4ee"
    )
    assert legacy._SOURCE_WORLD == "f9221410-b99e-417d-98f4-e98938586472"
    assert legacy._FORK_BRANCH == "fork-3883122c-6edb-4017-bd82-00fc4324aded"
    old = legacy.inspect_real_recovered_sources
    # Caller omitted future_pins; the old historical hardpins remain the only
    # path and never silently accept the newer synthetic v3 original.
    args = _future(tmp_path, monkeypatch)
    assert old.__kwdefaults__["future_pins"] is None
    with pytest.raises(RuntimeError):
        old(args["generation"], args["restored"], tmp_path / "not-stage28b")


@pytest.mark.parametrize("fault", [
    "missing-explicit-grants", "inspect-with-execution", "both-modes",
])
def test_i2f_cli_refuses_world_before_inspection_or_model(
    tmp_path, monkeypatch, capsys, fault,
):
    args = _future(tmp_path, monkeypatch)
    pins_file = tmp_path / "pins.json"
    pins_file.write_text(json.dumps(asdict(_pins(args))))
    fixed = [
        "--generation", str(args["generation"]),
        "--restored", str(args["restored"]),
        "--original-evidence", str(tmp_path / "missing-evidence"),
        "--new-source-pins", str(pins_file),
        "--paper-jar", str(tmp_path / "missing-paper.jar"),
        "--plugin-jar", str(tmp_path / "missing-plugin.jar"),
        "--gguf-path", str(tmp_path / "missing-gguf.gguf"),
        "--llama-pid", "999999", "--model-alias", "synthetic",
        "--llama-endpoint", "http://127.0.0.1:18999/v1/chat/completions",
        "--eula-accepted",
    ]
    if fault == "missing-explicit-grants":
        options = ["--execute-once"]
    elif fault == "inspect-with-execution":
        options = ["--inspect-only", "--execution-dir", str(tmp_path / "x")]
    else:
        options = ["--inspect-only", "--execute-once"]
    monkeypatch.setattr("sys.argv", ["i2f", *fixed, *options])
    assert real.main() == 2
    assert "I2F_PRE_WORLD_OR_TRIAL_HOLD" in capsys.readouterr().err
    assert not (tmp_path / "x").exists()


def test_i2f_one_world_no_runner_model_or_paper_without_real_gate(
    tmp_path, monkeypatch,
):
    args = _future(tmp_path, monkeypatch)
    with pytest.raises(real.I2fOriginalWorldHold):
        asyncio.run(real.run_i2f_one_original_world(
            generation=args["generation"],
            restored=args["restored"],
            original_evidence=tmp_path / "missing-evidence",
            pins=_pins(args),
            paper_jar=tmp_path / "missing-paper.jar",
            plugin_jar=tmp_path / "missing-plugin.jar",
            execution_dir=tmp_path / "exec",
            evidence_dir=tmp_path / "evidence",
            java="java", node="node",
            llama_endpoint="http://127.0.0.1:18999/v1/chat/completions",
            model_alias="unknown", gate=object(),
        ))
    assert not (tmp_path / "exec").exists()
    assert not (tmp_path / "evidence").exists()
