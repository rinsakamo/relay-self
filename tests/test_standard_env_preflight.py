"""Deterministic contract tests; no Minecraft, Node, Java, LLM, GPU or HTTP starts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from experiments.standard_env import preflight


def test_candidate_profile_is_valid_and_explicitly_unqualified() -> None:
    profile, sha = preflight.read_profile()
    assert len(sha) == 64
    assert profile["llm"]["reasoning_effort"] == "none"
    assert profile["llm"]["structured_output"] == {"type": "json_schema", "strict": True}
    assert profile["llm"]["context"] == 8192
    assert profile["llm"]["slots"] == 1
    assert profile["llm"]["context_shift"] is False
    assert profile["minecraft"]["initial_world"] == "UNBOUND_PER_RUN"


def test_default_plan_is_pure_and_never_calls_probes(monkeypatch, capsys) -> None:
    def forbidden(*_args, **_kwargs):
        pytest.fail("plan mode must not probe tools, import closure, file hashes or network")

    monkeypatch.setattr(preflight, "_check_tools", forbidden)
    monkeypatch.setattr(preflight, "_sha256_file", forbidden)
    monkeypatch.setattr(preflight, "_version_output", forbidden)
    assert preflight.main([]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["classification"] == "RSEE_PLAN_ONLY"
    assert result["side_effects"] == "NONE"
    assert "execution authorization" in result["not_verified"]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p.update(qualification="PHYSICALLY_QUALIFIED"),
        lambda p: p["llm"].update(slots=2),
        lambda p: p["llm"].update(reasoning_effort="medium"),
        lambda p: p["llm"].update(structured_output={"type": "json_object"}),
        lambda p: p["minecraft"].update(host="0.0.0.0"),
        lambda p: p.update(new_unowned_field="unsafe"),
        lambda p: p.update(not_inferred=[]),
    ],
)
def test_profile_variations_fail_closed(tmp_path, mutate) -> None:
    profile, _ = preflight.read_profile()
    mutate(profile)
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(profile), encoding="utf-8")
    with pytest.raises(preflight.PreflightError):
        preflight.read_profile(path)


def test_no_implicit_artifact_check_without_explicit_flag(capsys) -> None:
    assert preflight.main(["--model", "some-file"]) == 2
    assert json.loads(capsys.readouterr().out)["classification"] == "RSEE_PROFILE_INVALID"


def test_missing_local_artifacts_are_not_admitted(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(preflight, "_check_tools", lambda _profile: [])
    result = preflight.verify_local(
        preflight.PROFILE,
        model=None,
        llama_server=None,
        llama_sha256=None,
        minecraft_jar=None,
        minecraft_sha256=None,
        mineflayer_root=tmp_path,
    )
    assert result["classification"] == "RSEE_LOCAL_PREFLIGHT_BLOCKED"
    assert result["physical_execution_authorized"] is False
    assert len(result["errors"]) >= 4


def test_model_hash_mismatch_is_blocking_even_with_other_local_files(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(preflight, "_check_tools", lambda _profile: [])
    model, llama, jar = (tmp_path / name for name in ("model.gguf", "llama-server", "server.jar"))
    model.write_bytes(b"wrong model")
    llama.write_bytes(b"fake executable")
    llama.chmod(0o755)
    jar.write_bytes(b"fake jar")
    root = _mineflayer_root(tmp_path)
    result = preflight.verify_local(
        preflight.PROFILE,
        model=str(model),
        llama_server=str(llama),
        llama_sha256=hashlib.sha256(llama.read_bytes()).hexdigest(),
        minecraft_jar=str(jar),
        minecraft_sha256=hashlib.sha256(jar.read_bytes()).hexdigest(),
        mineflayer_root=root,
    )
    assert result["classification"] == "RSEE_LOCAL_PREFLIGHT_BLOCKED"
    assert result["errors"] == ["GGUF: SHA256 mismatch"]


def _mineflayer_root(tmp_path: Path) -> Path:
    root = tmp_path / "mineflayer"
    installed = root / "node_modules" / "mineflayer"
    installed.mkdir(parents=True)
    (root / "package-lock.json").write_text(
        json.dumps({"packages": {"": {"dependencies": {"mineflayer": "4.39.0"}}}}),
        encoding="utf-8",
    )
    (installed / "package.json").write_text(
        json.dumps({"version": "4.39.0"}), encoding="utf-8"
    )
    return root


def test_all_file_checks_still_cannot_authorize_execution(monkeypatch, tmp_path) -> None:
    """Synthetic file checks are mocked; this is NOT a physical qualification."""
    monkeypatch.setattr(preflight, "_check_tools", lambda _profile: [])
    model, llama, jar = (tmp_path / name for name in ("model.gguf", "llama-server", "server.jar"))
    model.write_bytes(b"fake local model")
    llama.write_bytes(b"fake local binary")
    llama.chmod(0o755)
    jar.write_bytes(b"fake local jar")
    real_hash = preflight._sha256_file

    def fake_hash(path: Path) -> str:
        if path == model:
            return preflight.read_profile()[0]["llm"]["model_sha256"]
        return real_hash(path)

    monkeypatch.setattr(preflight, "_sha256_file", fake_hash)
    result = preflight.verify_local(
        preflight.PROFILE,
        model=str(model),
        llama_server=str(llama),
        llama_sha256=real_hash(llama),
        minecraft_jar=str(jar),
        minecraft_sha256=real_hash(jar),
        mineflayer_root=_mineflayer_root(tmp_path),
    )
    assert result["classification"] == "RSEE_LOCAL_FILES_VERIFIED_NOT_PHYSICALLY_QUALIFIED"
    assert result["errors"] == []
    assert result["physical_execution_authorized"] is False
    assert result["live_world_and_model_verified"] is False


def test_version_and_sha_input_denials(monkeypatch) -> None:
    assert not preflight._sha_arg(None)
    assert not preflight._sha_arg("0" * 63)
    assert not preflight._sha_arg("Z" * 64)
    assert preflight._sha_arg("0" * 64)
    assert preflight._check_file(None, "0" * 64, "sample")
    monkeypatch.setattr(preflight, "_version_output", lambda _name, _arg: "invalid-version")
    errors = preflight._check_tools(preflight.read_profile()[0])
    assert "Node >=22 required" in errors
    assert "Java 21 required" in errors


def test_product_probe_requires_local_opt_in(capsys) -> None:
    assert preflight.main(["--verify-product"]) == 2
    assert json.loads(capsys.readouterr().out)["classification"] == "RSEE_PROFILE_INVALID"


@pytest.mark.parametrize("failure", ["python", "node", None])
def test_actual_product_dependency_gate_never_launches(monkeypatch, failure) -> None:
    from adapters.mineflayer import self_owned_llama as owner

    def forbidden(*args, **kwargs):
        pytest.fail("product preflight must never launch or contact a server")

    monkeypatch.setattr(owner.subprocess, "Popen", forbidden)
    monkeypatch.setattr(owner, "_ready", forbidden)
    monkeypatch.setattr(owner, "_free_loopback", forbidden)
    monkeypatch.setattr(preflight, "_check_tools", lambda _: [])
    monkeypatch.setattr(preflight, "_check_mineflayer", lambda *_: [])
    monkeypatch.setattr(preflight, "_check_file", lambda *_, **__: [])
    calls = []

    def probe(name):
        calls.append(name)
        if failure == name:
            raise owner.OwnedModelRejected("missing actual dependency")
        return {"closure": "PASS"}

    monkeypatch.setattr(owner, "_preflight_python_world_imports", lambda: probe("python"))
    monkeypatch.setattr(owner, "_preflight_mineflayer_dependencies", lambda: probe("node"))
    result = preflight.verify_local(
        preflight.PROFILE, model=None, llama_server=None, llama_sha256=None,
        minecraft_jar=None, minecraft_sha256=None,
        mineflayer_root=preflight.REPO_ROOT / "adapters/mineflayer", verify_product=True,
    )
    assert calls == (["python"] if failure == "python" else ["python", "node"])
    assert bool(result["errors"]) == (failure is not None)
    assert result["golden_run_readiness"] == "BLOCKED"
    assert result["physical_execution_authorized"] is False


def test_foreign_dependency_folder_cannot_qualify_product(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(preflight, "_check_tools", lambda _: [])
    monkeypatch.setattr(preflight, "_check_mineflayer", lambda *_: [])
    monkeypatch.setattr(preflight, "_check_file", lambda *_, **__: [])
    result = preflight.verify_local(
        preflight.PROFILE, model=None, llama_server=None, llama_sha256=None,
        minecraft_jar=None, minecraft_sha256=None,
        mineflayer_root=tmp_path, verify_product=True,
    )
    assert result["classification"] == "RSEE_LOCAL_PREFLIGHT_BLOCKED"
    assert result["product_dependencies"] == {}


def test_product_source_drift_blocks_even_when_local_files_pass(monkeypatch):
    from adapters.mineflayer import self_owned_llama as owner
    from experiments.standard_env import product_gate

    monkeypatch.setattr(preflight, "_check_tools", lambda _: [])
    monkeypatch.setattr(preflight, "_check_mineflayer", lambda *_: [])
    monkeypatch.setattr(preflight, "_check_file", lambda *_, **__: [])
    monkeypatch.setattr(product_gate, "audit_product", lambda **_: {
        "gaps": ["OWNED_LLAMA_CONTEXT_SHIFT_NOT_DISABLED"],
    })
    monkeypatch.setattr(owner, "_preflight_python_world_imports", lambda: {"closure": "PASS"})
    monkeypatch.setattr(owner, "_preflight_mineflayer_dependencies", lambda: {"closure": "PASS"})
    result = preflight.verify_local(
        preflight.PROFILE, model=None, llama_server=None, llama_sha256=None,
        minecraft_jar=None, minecraft_sha256=None,
        mineflayer_root=preflight.REPO_ROOT / "adapters/mineflayer", verify_product=True,
    )
    assert result["classification"] == "RSEE_LOCAL_PREFLIGHT_BLOCKED"
    assert result["errors"] == ["OWNED_LLAMA_CONTEXT_SHIFT_NOT_DISABLED"]
