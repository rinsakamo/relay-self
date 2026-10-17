"""Independent reader rejects provenance, profile and raw session substitutions."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.standard_env import s50_flat_four_original_audit as r
from experiments.standard_env.s50_flat_base_original_audit import FlatBaseAuditRejected


def config() -> bytes:
    root = Path(__file__).resolve().parents[1]
    source = root / "tests/fixtures/rsee_m02_v7_tick_base_qualified_config.yml"
    return source.read_bytes().replace(b"s50-tick-meter-dev: true\n", b"")


def test_independent_arm_config_factorial_and_sham():
    assert r.ARMS == ("SHAM_ON", "BASAL_ZERO", "WALK_ZERO", "BOTH_ZERO")
    base = config()
    assert r.validate_config(base, "SHAM_ON") == r.BASE_CONFIG_SHA
    for arm, pair in r.PROFILES.items():
        text = base.decode()
        for kind, mult in zip(("BASAL", "WALK"), pair, strict=True):
            lines = text.splitlines(keepends=True)
            text = "".join(line.replace("multiplier: 1.0", f"multiplier: {mult:.1f}")
                           if line.startswith(f"  {kind}:") else line for line in lines)
        assert len(r.validate_config(text.encode(), arm)) == 64


def test_other_cost_change_and_profile_spoof_rejected():
    with pytest.raises(FlatBaseAuditRejected, match="multiplier"):
        r.validate_config(config(), "BOTH_ZERO")
    with pytest.raises(FlatBaseAuditRejected, match="foreign M0.2"):
        r.validate_config(config().replace(b"standard: 0.001", b"standard: 0.002"), "SHAM_ON")


@pytest.mark.parametrize("seqs,sessions", [([0, 2], ["a", "a"]), ([0, 1], ["a", "b"])])
def test_foreign_or_discontinuous_native_rejected(tmp_path, seqs, sessions):
    file = tmp_path / "native.jsonl"
    file.write_text("\n".join(json.dumps({"seq": i, "session_id": s})
                              for i, s in zip(seqs, sessions, strict=True)))
    with pytest.raises(FlatBaseAuditRejected):
        r.frames(file)


def test_archive_symlink_and_alias_rejected(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "alias"
    link.symlink_to(real)
    with pytest.raises(FlatBaseAuditRejected):
        r.safe_root(link)
    with pytest.raises(FlatBaseAuditRejected):
        r.safe_root(real / ".." / "real")
    (real / "hidden").symlink_to(tmp_path / "outside")
    with pytest.raises(FlatBaseAuditRejected):
        r.safe_root(real)


def test_reader_cannot_start_java_node_or_import_s_producer():
    text = Path(r.__file__).read_text()
    assert "import subprocess" not in text
    assert "asyncio" not in text
    assert "from adapters" not in text
    assert "Popen(" not in text


def test_transport_checks_actual_zip_digest_before_unpack(tmp_path, monkeypatch):
    from experiments.standard_env import s50_flat_four_archive_fetch as transport

    def metadata(args):
        if args[-1].endswith("actions/runs/1"):
            return json.dumps({"head_sha": "head", "run_attempt": 1}).encode()
        return json.dumps({"workflow_run": {"id": 1}, "expired": False,
                           "digest": "sha256:" + "0" * 64}).encode()

    def download(args, stdout, check):
        stdout.write(b"corrupt ZIP bytes")

    monkeypatch.setattr(transport.subprocess, "check_output", metadata)
    monkeypatch.setattr(transport.subprocess, "run", download)
    with pytest.raises(ValueError, match="ZIP bytes"):
        transport.fetch("o/r", 1, "head", 2, "0" * 64, tmp_path / "transport")
    assert not (tmp_path / "transport/extracted").exists()


def test_transport_rejects_wrong_head_before_download(tmp_path, monkeypatch):
    from experiments.standard_env import s50_flat_four_archive_fetch as transport

    def metadata(args):
        if args[-1].endswith("actions/runs/1"):
            return json.dumps({"head_sha": "foreign", "run_attempt": 1}).encode()
        return json.dumps({"workflow_run": {"id": 1}, "expired": False,
                           "digest": "sha256:" + "0" * 64}).encode()

    monkeypatch.setattr(transport.subprocess, "check_output", metadata)
    with pytest.raises(ValueError, match="identity"):
        transport.fetch("o/r", 1, "head", 2, "0" * 64, tmp_path / "transport")
    assert not (tmp_path / "transport").exists()
