"""RSEE-to-product owner integration: strictly offline tests; no model/World."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from adapters.mineflayer import self_owned_llama as owned
from experiments.standard_env import product_gate


def test_exact_product_source_reports_real_standardization_gaps() -> None:
    result = product_gate.audit_product()
    assert result["classification"] == "RSEE_PRODUCT_STATIC_GAPS"
    assert result["runtime_observation"] is False
    assert result["physical_execution_authorized"] is False
    assert "L2_REQUEST_REASONING_OFF_NOT_EXPLICIT" in result["gaps"]
    assert "L2_REQUEST_CACHE_DISABLED_NOT_EXPLICIT" in result["gaps"]
    assert "OWNED_LLAMA_CONTEXT_SHIFT_NOT_DISABLED" in result["gaps"]
    assert "OWNED_LLAMA_GPU_LAYER_CAP_BELOW_STANDARD" in result["gaps"]
    assert "response_format" not in result["observed_l2_wire_fields"]


def test_explicit_current_runtime_mismatch_is_distinguished() -> None:
    result = product_gate.audit_product(
        ctx=4352, gpu_layers=60, model_port=12345, gguf_sha256="0" * 64,
    )
    assert {
        "CONTEXT_DIFFERS_FROM_STANDARD",
        "GPU_OFFLOAD_DIFFERS_FROM_STANDARD",
        "LOOPBACK_PORT_DIFFERS_FROM_STANDARD",
        "GGUF_IDENTITY_DIFFERS_FROM_STANDARD",
    }.issubset(result["gaps"])


def _args(tmp_path: Path) -> list[str]:
    root = tmp_path / "not-prepared"
    return [
        "--run-disposable", "--output-dir", str(root),
        "--llama-server", str(tmp_path / "missing-llama"),
        "--gguf", str(tmp_path / "missing-gguf"),
        "--gguf-sha256", "0" * 64,
        "--model-alias", "test",
        "--model-port", "12345",
    ]


@pytest.mark.parametrize("flag", ["--rsee-audit", "--rsee-required"])
def test_product_rsee_modes_block_without_launch_or_creating_artifacts(
    tmp_path, monkeypatch, capsys, flag,
) -> None:
    def forbidden(*_args, **_kwargs):
        pytest.fail("RSEE audit must not enter toolchain, model or World")

    monkeypatch.setattr(owned, "_preflight_mineflayer_dependencies", forbidden)
    monkeypatch.setattr(owned, "_preflight_python_world_imports", forbidden)
    monkeypatch.setattr(owned, "_sha256", forbidden)
    monkeypatch.setattr(owned.subprocess, "Popen", forbidden)
    assert owned.main([*_args(tmp_path), flag]) == 2
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["classification"] == "RSEE_PRODUCT_STATIC_GAPS"
    assert receipt["physical_execution_authorized"] is False
    assert not (tmp_path / "not-prepared").exists()


def test_real_s49_python_import_closure_is_qualified_before_process() -> None:
    result = owned._preflight_python_world_imports()
    assert result["s49_import_closure"] == "PASS"


def test_missing_python_dependency_blocks_before_binary_hash_or_launch(
    tmp_path, monkeypatch, capsys,
) -> None:
    out = tmp_path / "evidence"
    out.mkdir()
    args = _args(tmp_path)
    args[args.index("--output-dir") + 1] = str(out)
    args += ["--confirm", owned.CONFIRM]

    def missing(*_args, **_kwargs):
        raise owned.OwnedModelRejected("actual S49 Python closure unavailable")

    def forbidden(*_args, **_kwargs):
        pytest.fail("no GGUF hashing, model or World after missing Python import")

    monkeypatch.setattr(owned, "_preflight_mineflayer_dependencies",
                        lambda: {"mineflayer": "4.39.0"})
    monkeypatch.setattr(owned, "_preflight_python_world_imports", missing)
    monkeypatch.setattr(owned, "_sha256", forbidden)
    monkeypatch.setattr(owned.subprocess, "Popen", forbidden)
    import shutil
    original = shutil.which
    monkeypatch.setattr(
        shutil, "which",
        lambda name: "/ci/mock/" + name if name in ("java", "node") else original(name),
    )
    assert owned.main(args) == 2
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["status"] == "BLOCKED"
    assert receipt["model_process_launched"] is False
    assert receipt["minecraft_launched"] is False
    assert list(out.iterdir()) == []


def test_product_source_audit_fails_closed_when_l2_unknown(tmp_path) -> None:
    broken = tmp_path / "l2.py"
    broken.write_text("request = {'model': 'x', 'messages': []}\n", encoding="utf-8")
    with pytest.raises(product_gate.PreflightError):
        product_gate.audit_product(l2=broken)


def test_product_source_audit_rejects_source_symlink(tmp_path) -> None:
    link = tmp_path / "symlink.py"
    link.symlink_to(product_gate.L2)
    with pytest.raises(product_gate.PreflightError):
        product_gate.audit_product(l2=link)
