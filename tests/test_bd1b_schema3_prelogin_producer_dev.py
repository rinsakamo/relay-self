"""Original fresh Resident Schema3 prelogin source and opt-in real launcher.

This is CPU synthetic: neither the Paper process nor the actual Native
Minecraft connection or Gemma is started in these tests.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments import p0d_real_resident_presence_dev as resident_runner
from experiments import stage28b_pinned_typed_cut_launch_dev as launcher
from relay_self.bd1b_schema3_prelogin_source_dev import (
    BD1bSchema3ProducerHold,
    prepare_original_schema3_prelogin,
)
from relay_self.cognitive_minimal_dev import initial_patterns_with_relative_move
from relay_self.innate_schema import SchemaMode
from relay_self.persistent_cognition import load_persistent_cognition
from relay_self.schema_bootstrap_dev import SchemaBootstrapConfig, bootstrap_fresh_schemas
from test_b_np1a_schema_bootstrap_dev import make_resident


def _source(tmp_path):
    root = tmp_path / "self-roots"
    root.mkdir()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    resident = make_resident(root, initial_patterns_with_relative_move())
    bootstrap_fresh_schemas(resident, SchemaBootstrapConfig(True))
    return resident, evidence


def test_original_schema3_prelogin_persists_exact_registered_cognition_and_wal(
    tmp_path,
):
    resident, evidence = _source(tmp_path)
    previous = {
        sid: (resident.owners[sid].retained, resident.owners[sid].pattern_registry)
        for sid in ("A", "B")
    }
    receipt = prepare_original_schema3_prelogin(resident, evidence_dir=evidence)
    raw = (evidence / "stage28b-schema3-prelogin.json").read_bytes()
    manifest = json.loads(raw)
    assert receipt.self_ids == ("A", "B")
    assert receipt.schema_modes == ("FULL", "FULL")
    assert manifest["classification"] == "BD1B_ORIGINAL_PRELOGIN_SCHEMA3_UNAUDITED_DEV"
    assert manifest["real_model_post_attempted"] is False
    assert manifest["real_paper_independently_audited"] is False
    assert [row["self_id"] for row in manifest["registrations"]] == ["A", "B"]
    for sid, digest in receipt.cognition_sha256:
        owner = resident.owners[sid]
        raw_copy = (evidence / f"stage28b-schema3-{sid}-prelogin-cognition.json").read_bytes()
        assert raw_copy == owner.files.cognition_file.read_bytes()
        assert hashlib.sha256(raw_copy).hexdigest() == digest
        assert load_persistent_cognition(owner.files.cognition_file) == owner.retained
        assert owner.retained.pattern_registry is previous[sid][1]
        assert owner.retained.identity == previous[sid][0].identity
        assert owner.intent.events == ()
        assert resident._state(sid).mode == "OFFLINE"
        assert resident._state(sid).epoch == 0
    for sid, digest in receipt.wal_sha256:
        raw_copy = (evidence / f"stage28b-schema3-{sid}-prelogin-wal.json").read_bytes()
        assert raw_copy == resident.owners[sid].files.physical_wal_file.read_bytes()
        assert hashlib.sha256(raw_copy).hexdigest() == digest
    before = {p.name: p.read_bytes() for p in evidence.iterdir() if p.is_file()}
    with pytest.raises(BD1bSchema3ProducerHold):
        prepare_original_schema3_prelogin(resident, evidence_dir=evidence)
    assert {p.name: p.read_bytes() for p in evidence.iterdir() if p.is_file()} == before


@pytest.mark.parametrize("failure", [
    "partial-registration", "missing-registration", "off-mode", "registry-drift",
    "already-logged-in", "foreign-Self", "old-cognition-file",
    "stale-persistent-registry", "unsafe-wal",
])
def test_original_prelogin_adversarial_refuses_before_publishing_cognition(
    tmp_path, failure,
):
    resident, evidence = _source(tmp_path)
    if failure == "partial-registration":
        resident._present_schemas.pop("B")
    elif failure == "missing-registration":
        resident._present_schemas.clear()
    elif failure == "off-mode":
        snapshot, registry = resident._present_schemas["B"]
        activation = replace(snapshot.modules[0], mode=SchemaMode.OFF)
        resident._present_schemas["B"] = (
            replace(snapshot, modules=(activation,)), registry,
        )
    elif failure == "registry-drift":
        owner = resident.owners["B"]
        owner.pattern_registry = replace(owner.pattern_registry, revision=2)
    elif failure == "already-logged-in":
        resident.bind_login(
            self_id="A", native_session_id="native-A", world_epoch=0, world_tick=1,
        )
    elif failure == "foreign-Self":
        snapshot, registry = resident._present_schemas["A"]
        resident._present_schemas["A"] = (replace(snapshot, self_id="B"), registry)
    elif failure == "old-cognition-file":
        resident.owners["A"].files.cognition_file.write_bytes(b"existing")
    elif failure == "stale-persistent-registry":
        owner = resident.owners["B"]
        owner.retained = replace(owner.retained, pattern_registry=owner.pattern_registry)
    else:
        resident.owners["B"].files.physical_wal_file.write_bytes(b"invalid")
    with pytest.raises((BD1bSchema3ProducerHold, ValueError, RuntimeError)):
        prepare_original_schema3_prelogin(resident, evidence_dir=evidence)
    assert not list(evidence.iterdir())
    if failure not in {"old-cognition-file"}:
        assert not resident.owners["A"].files.cognition_file.exists()


def test_original_registered_schema3_cut_optin_launcher_passes_both_flags(
    tmp_path, monkeypatch,
):
    captured = {}
    monkeypatch.setattr(launcher, "check_stage24g_pinned_assets",
                        lambda **kwargs: SimpleNamespace(
                            paper_jar=Path("/local/paper.jar"),
                            paper_sha256="a" * 64,
                            plugin_jar=Path("/local/plugin.jar"),
                            plugin_sha256="b" * 64,
                            scratch_parent=tmp_path,
                        ))
    monkeypatch.setattr(launcher, "_verify_local_runtime",
                        lambda java, node: None)

    async def fake_runner(**kwargs):
        captured.update(kwargs)
        return tmp_path / "fake-report.json"

    monkeypatch.setattr(launcher, "run_real_resident_presence", fake_runner)
    monkeypatch.setattr(sys, "argv", [
        "stage28b", "--paper-jar", "/local/paper.jar",
        "--plugin-jar", "/local/plugin.jar", "--scratch-parent", str(tmp_path),
        "--eula-accepted", "--execute-once", "--real-world-dev-grant",
        "--record-exploration-schema3",
    ])
    assert launcher.main() == 0
    assert captured["typed_owner_cut_dev"] is True
    assert captured["exploration_schema_dev"] is True
    assert captured["initial_source_dev"] is True
    assert captured["real_llm_grant"] is False
    assert captured["b_autonomous_l1_dev"] is False
    assert captured["b_selected_move_dev"] is False


def test_old_launcher_explicit_default_remains_unchanged(tmp_path, monkeypatch):
    seen = {}
    monkeypatch.setattr(launcher, "check_stage24g_pinned_assets",
                        lambda **kwargs: SimpleNamespace(
                            paper_jar=Path("/local/paper.jar"),
                            paper_sha256="a" * 64,
                            plugin_jar=Path("/local/plugin.jar"),
                            plugin_sha256="b" * 64,
                            scratch_parent=tmp_path,
                        ))
    monkeypatch.setattr(launcher, "_verify_local_runtime",
                        lambda java, node: None)

    async def fake_runner(**kwargs):
        seen.update(kwargs)
        return tmp_path / "result.json"

    monkeypatch.setattr(launcher, "run_real_resident_presence", fake_runner)
    monkeypatch.setattr(sys, "argv", [
        "stage28b", "--paper-jar", "/local/paper.jar",
        "--plugin-jar", "/local/plugin.jar", "--scratch-parent", str(tmp_path),
        "--eula-accepted", "--execute-once", "--real-world-dev-grant",
    ])
    assert launcher.main() == 0
    assert seen["exploration_schema_dev"] is False
    assert seen["initial_source_dev"] is False
    assert seen["typed_owner_cut_dev"] is True


def test_source_option_rejects_missing_initial_native_before_world_io(
    tmp_path, monkeypatch,
):
    monkeypatch.setattr(resident_runner, "preflight_two_native",
                        lambda **kwargs: pytest.fail("unqualified Paper preflight"))
    args = dict(
        paper_jar=tmp_path / "paper.jar", paper_sha256="a" * 64,
        plugin_jar=tmp_path / "plugin.jar", plugin_sha256="b" * 64,
        scratch_parent=tmp_path, accepted_eula=True, real_world_dev_grant=True,
        typed_owner_cut_dev=True, exploration_schema_dev=True,
        initial_source_dev=False,
    )
    with pytest.raises(resident_runner.RealResidentPresenceRefusal,
                       match="initial-source"):
        asyncio.run(resident_runner.run_real_resident_presence(**args))
    assert not list(tmp_path.iterdir())
