"""RSEE-to-product owner integration: strictly offline tests; no model/World."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from adapters.mineflayer import self_owned_llama as owned
from experiments.standard_env import product_gate


def test_exact_product_source_has_optin_standard_controls_not_physical_proof() -> None:
    result = product_gate.audit_product()
    assert result["classification"] == (
        "RSEE_PRODUCT_STATIC_COMPATIBLE_NOT_PHYSICALLY_QUALIFIED"
    )
    assert result["runtime_observation"] is False
    assert result["physical_execution_authorized"] is False
    assert result["gaps"] == []
    assert "reasoning_effort" in result["observed_l2_wire_fields"]
    assert "cache_prompt" in result["observed_l2_wire_fields"]
    assert "--no-context-shift" in result["observed_launcher_flags"]
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


def test_standard_rsee_audit_reaches_static_compatibility_without_side_effects(
    tmp_path, monkeypatch, capsys,
) -> None:
    def forbidden(*_args, **_kwargs):
        pytest.fail("audit must never touch toolchain/model/World")
    monkeypatch.setattr(owned, "_preflight_python_world_imports", forbidden)
    monkeypatch.setattr(owned, "_preflight_mineflayer_dependencies", forbidden)
    monkeypatch.setattr(owned.subprocess, "Popen", forbidden)
    args = _args(tmp_path)
    args[args.index("--gguf-sha256") + 1] = product_gate.read_profile()[0][
        "llm"
    ]["model_sha256"]
    args[args.index("--model-port") + 1] = "1234"
    args.extend(["--ctx-size", "8192", "--gpu-layers", "999", "--rsee-audit"])
    assert owned.main(args) == 0
    outcome = json.loads(capsys.readouterr().out)
    assert outcome["classification"] == (
        "RSEE_PRODUCT_STATIC_COMPATIBLE_NOT_PHYSICALLY_QUALIFIED"
    )
    assert not (tmp_path / "not-prepared").exists()


def test_opted_standard_still_requires_operator_consent(tmp_path, capsys) -> None:
    args = _args(tmp_path)
    args[args.index("--gguf-sha256") + 1] = product_gate.read_profile()[0][
        "llm"
    ]["model_sha256"]
    args[args.index("--model-port") + 1] = "1234"
    args.extend(["--ctx-size", "8192", "--gpu-layers", "999", "--rsee-required"])
    assert owned.main(args) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "BLOCKED"


@pytest.mark.parametrize("change", [
    None,
    ("model_alias_missing", None),
    ("models_alias", "WRONG_ALIAS"),
    ("model_alias", "WRONG_ALIAS"),
    ("model_path", "/foreign/model.gguf"),
    ("total_slots", 2),
    ("build_info", ""),
    ("n_ctx", 4352),
    ("slot_ctx", 2048),
])
def test_rsee_live_props_slots_source_binding_fail_closed(
    tmp_path, monkeypatch, change,
) -> None:
    import adapters.mineflayer.self_owned_llama as model_owner

    gguf = tmp_path / "gemma-4-12B-it-Q4_K_M.gguf"
    gguf.write_bytes(b"synthetic-not-a-model")
    props = {
        "model_alias": "relay-self-local",
        "model_path": str(gguf),
        "default_generation_settings": {"n_ctx": 8192},
        "total_slots": 1,
        "build_info": "offline-fixture-build",
    }
    slots = [{"n_ctx": 8192}]
    models = {"data": [{"id": "relay-self-local"}]}
    if change is not None:
        key, val = change
        if key == "model_alias_missing":
            props.pop("model_alias")
        elif key == "models_alias":
            models["data"][0]["id"] = val
        elif key == "n_ctx":
            props["default_generation_settings"]["n_ctx"] = val
        elif key == "slot_ctx":
            slots[0]["n_ctx"] = val
        else:
            props[key] = val

    class Response:
        status = 200

        def __init__(self, value):
            self.data = json.dumps(value).encode()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _n):
            return self.data

    class Opener:
        def open(self, url, timeout):
            assert timeout == 2.0
            assert url in (
                "http://127.0.0.1:1234/props",
                "http://127.0.0.1:1234/slots",
                "http://127.0.0.1:1234/v1/models",
            )
            if url.endswith("/v1/models"):
                return Response(models)
            return Response(props if url.endswith("/props") else slots)

    monkeypatch.setattr(model_owner.urllib.request, "build_opener", lambda *_: Opener())
    evidence = tmp_path / "endpoint-evidence"
    evidence.mkdir()
    if change is None or change[0] == "model_alias_missing":
        receipt = model_owner._rsee_live_binding(
            1234, "relay-self-local", gguf, evidence_dir=evidence,
        )
        assert receipt["context"] == 8192
        assert receipt["slot_count"] == 1
        assert receipt["gpu_execution_attested"] is False
        assert receipt["thinking_disabled_physically_attested"] is False
        assert receipt["backend_stop_ack"] is False
    else:
        with pytest.raises(model_owner.OwnedModelRejected):
            model_owner._rsee_live_binding(
                1234, "relay-self-local", gguf, evidence_dir=evidence,
            )
    audit = json.loads((evidence / "rsee_live_binding_diagnostic.json").read_text())
    assert audit["model_post_count"] == 0
    assert audit["minecraft_launch_count"] == 0
    assert audit["status"] == (
        "HTTP_BINDING_QUALIFIED_NOT_PHYSICAL_PROOF"
        if change is None or change[0] == "model_alias_missing" else "BLOCKED"
    )
    assert len(audit["endpoint_receipts"]) == 3
    assert {
        "rsee_http_models.json", "rsee_http_props.json", "rsee_http_slots.json",
        "rsee_live_binding_diagnostic.json",
    } == {p.name for p in evidence.iterdir()}
    for key, filename in [
        ("models", "rsee_http_models.json"),
        ("props", "rsee_http_props.json"),
        ("slots", "rsee_http_slots.json"),
    ]:
        assert len((evidence / filename).read_bytes()) == audit[
            "endpoint_receipts"
        ][key]["bytes_read"]
    if change is not None and change[0] == "models_alias":
        assert "models.alias.exactly_once" in audit["failed_checks"]
    if change is not None and change[0] == "model_alias":
        assert "props.optional_alias.consistent" in audit["failed_checks"]


def test_rsee_live_binding_refuses_truncated_or_duplicate_json(
    tmp_path, monkeypatch,
) -> None:
    import adapters.mineflayer.self_owned_llama as model_owner

    gguf = tmp_path / "model.gguf"
    gguf.write_bytes(b"synthetic")
    class Response:
        status = 200
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return False
        def read(self, _):
            return b'{"model_alias":"a","model_alias":"b"}'
    class Opener:
        def open(self, *_args, **_kwargs):
            return Response()
    monkeypatch.setattr(model_owner.urllib.request, "build_opener", lambda *_: Opener())
    with pytest.raises(model_owner.OwnedModelRejected):
        model_owner._rsee_live_binding(1234, "a", gguf)


@pytest.mark.parametrize(
    ("failure", "expected", "last_endpoint"),
    [
        ("duplicate", "RSEE_BINDING_PROPS_JSON_INVALID", "props"),
        ("oversize", "RSEE_BINDING_PROPS_BODY_TOO_LARGE", "props"),
        ("http_status", "RSEE_BINDING_PROPS_HTTP_NOT_200", "props"),
    ],
)
def test_rsee_http_first_failure_seals_bounded_raw_response_and_diagnostic(
    tmp_path, monkeypatch, failure, expected, last_endpoint,
) -> None:
    gguf = tmp_path / "model.gguf"
    gguf.write_bytes(b"fake model")
    evidence = tmp_path / "source-evidence"
    evidence.mkdir()
    requested = []

    class Response:
        def __init__(self, url):
            self.status = 500 if failure == "http_status" and url.endswith("/props") else 200
            if url.endswith("/v1/models"):
                self.data = b'{"data":[{"id":"rsee-gemma4"}]}'
            elif failure == "duplicate":
                self.data = b'{"model_path":"a","model_path":"b"}'
            elif failure == "oversize":
                self.data = b" " * 16385
            else:
                self.data = b'{"error":"offline fixture"}'
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return False
        def read(self, length):
            return self.data[:length]

    class Opener:
        def open(self, url, timeout):
            assert timeout == 2.0
            requested.append(url.rsplit("/", 1)[-1])
            return Response(url)

    monkeypatch.setattr(owned.urllib.request, "build_opener", lambda *_: Opener())
    with pytest.raises(owned.OwnedModelRejected, match=expected):
        owned._rsee_live_binding(
            1234, "rsee-gemma4", gguf, evidence_dir=evidence,
        )
    assert requested == ["models", last_endpoint]
    diagnostic = json.loads(
        (evidence / "rsee_live_binding_diagnostic.json").read_text()
    )
    assert diagnostic["failed_checks"] == [expected]
    assert diagnostic["status"] == "BLOCKED"
    assert "slots" not in diagnostic["endpoint_receipts"]
    assert (evidence / "rsee_http_models.json").is_file()
    raw = (evidence / "rsee_http_props.json").read_bytes()
    assert len(raw) == (16385 if failure == "oversize" else len(Response(
        "http://127.0.0.1:1234/props",
    ).data))
    assert diagnostic["endpoint_receipts"]["props"]["bytes_read"] == len(raw)
    assert diagnostic["endpoint_receipts"]["props"]["response_truncated"] == (
        failure == "oversize"
    )
    assert diagnostic["model_post_count"] == 0


def test_rsee_existing_evidence_prevents_any_http_requests(
    tmp_path, monkeypatch,
) -> None:
    gguf = tmp_path / "model.gguf"
    gguf.write_bytes(b"fake")
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "rsee_http_models.json").write_bytes(b"immutable")
    count = []

    class Opener:
        def open(self, *_args, **_kwargs):
            count.append("GET")
            return None

    monkeypatch.setattr(owned.urllib.request, "build_opener", lambda *_: Opener())
    with pytest.raises((owned.OwnedModelRejected, OSError)):
        owned._rsee_live_binding(1234, "rsee-gemma4", gguf, evidence_dir=evidence)
    assert (evidence / "rsee_http_models.json").read_bytes() == b"immutable"
    assert count == ["GET"]
