"""Offline-only RSEE Golden Run authority/qualified World identity tests."""
from __future__ import annotations

import hashlib
import json

import pytest

from adapters.mineflayer import self_demo, self_owned_llama
from experiments.standard_env import golden_admission as golden
from experiments.standard_env.world_binding import WorldBindingRejected
from test_rsee_world_binding import _fixture


def test_operator_receipts_are_fixed_to_one_independent_native_bootstrap():
    assert golden.QUALIFIED_BOOTSTRAP_HEAD == (
        "ca4afee5c78102ed3f917ea6011b6bef124d98e3"
    )
    assert golden.QUALIFIED_MANIFEST_SHA256 == (
        "5b1876db6a97fc8b9c4331938ca47727037c5626a241213d871b2073665996f8"
    )
    assert golden.QUALIFIED_INITIAL_EVIDENCE_SHA256 == (
        "7c974390d1879967ef5b5ce3b37d59a9628974c5f3e2a2dfefcf5e1e7701648b"
    )


def test_new_self_consistent_world_cannot_replace_physically_qualified_one(tmp_path):
    jar, snapshot, manifest, initial, jar_sha = _fixture(tmp_path)
    with pytest.raises(WorldBindingRejected, match="jar SHA256 mismatch"):
        golden.verify_qualified_world(jar, snapshot, manifest, initial)
    # Even after source jar qualifies as the selected asset, a new synthetic
    # self-consistent manifest + observation cannot replace the native run.
    from experiments.standard_env import golden_admission as module

    original = module.JAR_SHA256
    try:
        module.JAR_SHA256 = jar_sha
        with pytest.raises(WorldBindingRejected, match="not the independently qualified"):
            golden.verify_qualified_world(jar, snapshot, manifest, initial)
    finally:
        module.JAR_SHA256 = original


def test_exact_fixture_hash_pair_required_in_addition_to_internal_manifest(tmp_path, monkeypatch):
    jar, snapshot, manifest, initial, jar_sha = _fixture(tmp_path)
    monkeypatch.setattr(golden, "JAR_SHA256", jar_sha)
    monkeypatch.setattr(golden, "QUALIFIED_MANIFEST_SHA256",
                        hashlib.sha256(manifest.read_bytes()).hexdigest())
    monkeypatch.setattr(golden, "QUALIFIED_INITIAL_EVIDENCE_SHA256",
                        hashlib.sha256(initial.read_bytes()).hexdigest())
    binding = golden.verify_qualified_world(jar, snapshot, manifest, initial)
    assert binding.manifest_sha256 == golden.QUALIFIED_MANIFEST_SHA256

    # A forged replacement with new self-consistent manifest bytes must fail.
    new_data = json.loads(initial.read_text())
    new_data["extra"] = "self-consistent substitute"
    initial.write_text(json.dumps(new_data))
    contents = json.loads(manifest.read_text())
    contents["initial_evidence_sha256"] = hashlib.sha256(initial.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(contents, sort_keys=True))
    with pytest.raises(WorldBindingRejected, match="not the independently qualified"):
        golden.verify_qualified_world(jar, snapshot, manifest, initial)


def test_direct_rsee_demo_denies_world_without_fresh_golden_grant(
    tmp_path, monkeypatch, capsys,
):
    jar, snapshot, manifest, initial, _ = _fixture(tmp_path)
    out = tmp_path / "evidence"
    out.mkdir()

    def forbidden(*_args, **_kwargs):
        pytest.fail("no Java, Node, port probing, or model without new grant")

    monkeypatch.setattr(self_demo.shutil, "which", forbidden)
    args = [
        "--run-disposable", "--confirm", self_demo.CONFIRM,
        "--output-dir", str(out), "--live-think", "--rsee-standard",
        "--model-alias", "rsee-gemma4", "--model-port", "1234",
        "--rsee-eula-accepted",
        "--rsee-world-jar", str(jar),
        "--rsee-world-snapshot", str(snapshot),
        "--rsee-world-manifest", str(manifest),
        "--rsee-initial-evidence", str(initial),
    ]
    assert self_demo.main(args) == 2
    assert json.loads(capsys.readouterr().out)["reason"] == "GOLDEN_RUN_NOT_AUTHORIZED"
    assert list(out.iterdir()) == []


def test_owned_llama_denies_previous_bootstrap_grant_before_model_hash(
    tmp_path, monkeypatch, capsys,
):
    import experiments.standard_env.product_gate as gate

    monkeypatch.setattr(
        gate, "audit_product",
        lambda **_kwargs: {
            "classification": "RSEE_PRODUCT_STATIC_COMPATIBLE_NOT_PHYSICALLY_QUALIFIED"
        },
    )

    def forbidden(*_a, **_kw):
        pytest.fail("GGUF/Jar hash or model process must not start")

    monkeypatch.setattr(self_owned_llama, "_sha256", forbidden)
    monkeypatch.setattr(self_owned_llama.subprocess, "Popen", forbidden)
    jar, snapshot, manifest, initial, _ = _fixture(tmp_path)
    out = tmp_path / "evidence"
    out.mkdir()
    args = [
        "--run-disposable", "--confirm", self_demo.CONFIRM,
        "--output-dir", str(out),
        "--llama-server", str(tmp_path / "not-a-real-binary"),
        "--gguf", str(tmp_path / "not-a-real.gguf"),
        "--gguf-sha256",
        "c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed",
        "--model-alias", "rsee-gemma4", "--model-port", "1234",
        "--ctx-size", "8192", "--gpu-layers", "999",
        "--rsee-required",
        "--rsee-eula-accepted",
        "--rsee-world-jar", str(jar),
        "--rsee-world-snapshot", str(snapshot),
        "--rsee-world-manifest", str(manifest),
        "--rsee-initial-evidence", str(initial),
    ]
    assert self_owned_llama.main(args) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "BLOCKED"
    assert result["model_process_launched"] is False
    assert result["minecraft_launched"] is False
    assert list(out.iterdir()) == []


def test_golden_flags_do_not_change_non_rsee_legacy_flow(tmp_path, capsys):
    out = tmp_path / "evidence"
    out.mkdir()
    assert self_demo.main([
        "--run-disposable", "--confirm", self_demo.CONFIRM,
        "--output-dir", str(out),
        "--rsee-golden-run-once",
    ]) == 2
    assert json.loads(capsys.readouterr().out)["reason"] == (
        "RSEE_WORLD_FLAGS_REQUIRE_STANDARD"
    )
    assert list(out.iterdir()) == []
