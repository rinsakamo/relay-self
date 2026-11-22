"""I2g initial ORIGINAL born A/B v3 durable Registry→recorded empty Schema.

CPU/synthetic fixtures exercise the *same* original owner and stopped typed
cut, not Paper/Native real-world evidence.
"""
from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from experiments import i_lane_i2g_new_original_v3_world_dev as runner
from experiments.p0d_real_resident_presence_dev import (
    RealResidentPresenceRefusal,
    run_real_resident_presence,
)
from relay_self.cognitive_minimal_dev import initial_patterns, initial_patterns_with_relative_move
from relay_self.i_lane_i2g_real_origin_schema_dev import (
    I2gOriginSchemaHold,
    register_i2g_born_original_empty_schemas,
)
from relay_self.persistent_cognition import (
    IdentitySpecification,
    PersistentCognition,
    load_persistent_cognition,
    save_persistent_cognition,
)
from relay_self.provenance import Provenance
from relay_self.resident_cognitive_work_owner_dev import ResidentCognitiveWorkOwner
from relay_self.self_owner_checkpoint_dev import verify_typed_generation
from relay_self.stage28b_retired_resident_typed_cut_dev import (
    capture_retired_resident_typed_world,
)
from test_stage28b_retired_typed_cut_dev import _setup


def _born(tmp_path, monkeypatch, *, stale_b=False, motor=False, corrupt_a=False):
    bridge, paper, store, evidence = _setup(tmp_path, monkeypatch)
    for name in ("world_nether", "world_the_end"):
        dim = tmp_path / name
        dim.mkdir()
        (dim / "region").mkdir()
        (dim / "region" / "r.0.0.mca").write_bytes(b"new-v3-synthetic-world")
    for sid in ("A", "B"):
        owner = bridge.owners[sid]
        owner.native_session_id = "offline-born-" + sid
        owner.last_observed_tick = 0
        pattern = (
            initial_patterns_with_relative_move()
            if motor and sid == "A" else initial_patterns()
        )
        owner.pattern_registry = pattern
        owner.retained = PersistentCognition(
            IdentitySpecification(
                sid, ("World-independent retained identity",),
                Provenance("p0d-real-resident", sid),
            ),
            pattern_registry=pattern,
        )
        save_persistent_cognition(owner.files.cognition_file, owner.retained)
    if stale_b:
        bridge.owners["B"].native_session_id = "native-old-B"
    if corrupt_a:
        bridge.owners["A"].files.cognition_file.write_bytes(b"stale")
    resident = ResidentCognitiveWorkOwner(bridge.owners)
    bridge.cognitive_work = resident
    return bridge, paper, store, evidence, resident


def test_i2g_born_initial_exact_a_b_registry_and_future_v3_cut(
    tmp_path, monkeypatch,
):
    bridge, paper, store, evidence, resident = _born(tmp_path, monkeypatch)
    receipt = register_i2g_born_original_empty_schemas(resident)
    assert receipt.self_ids == ("A", "B")
    assert receipt.born_initial_only is True
    assert receipt.learning_claimed is False
    assert receipt.physical_action_authorized is False
    assert receipt.original_registry_revisions == (("A", 0), ("B", 0))
    assert receipt.schema_modes == (
        ("A", "NO_EXPLORATION_MODULE"), ("B", "NO_EXPLORATION_MODULE"),
    )
    for sid in ("A", "B"):
        owner = bridge.owners[sid]
        assert load_persistent_cognition(owner.files.cognition_file) == owner.retained
        assert owner.retained.pattern_registry == initial_patterns()
        assert resident._present_schemas[sid][0].modules == ()
        resident.bind_login(
            self_id=sid, native_session_id="new-live-" + sid,
            world_epoch=0, world_tick=105,
        )
    for sid in ("A", "B"):
        resident.fence_self(sid)
        receipt_stop = asyncio.run(resident.retire_self(sid))
        resident.mark_offline(receipt_stop)
    cut = capture_retired_resident_typed_world(
        bridge=bridge, paper=paper, store=store, evidence_dir=evidence,
    )
    for saved in verify_typed_generation(cut.generation):
        assert saved.recorded_schema is not None
        assert saved.recorded_schema.modules == ()
        assert saved.recorded_schema.revision == 0
        assert saved.pattern_registry == initial_patterns()
        assert saved.cognition_sha256 is not None
    assert paper.stop_count == 1
    assert not receipt.physical_action_authorized


@pytest.mark.parametrize("fault", [
    "stale-native-b", "learned-motor-a", "corrupt-cognition-a",
    "already-registered", "wrong-provenance", "unexpected-memory",
])
def test_i2g_origin_refuses_unborn_or_legacy_registry_and_no_partial_schema(
    tmp_path, monkeypatch, fault,
):
    bridge, paper, store, evidence, resident = _born(
        tmp_path, monkeypatch,
        stale_b=fault == "stale-native-b",
        motor=fault == "learned-motor-a",
        corrupt_a=fault == "corrupt-cognition-a",
    )
    if fault == "already-registered":
        register_i2g_born_original_empty_schemas(resident)
    if fault == "wrong-provenance":
        o = bridge.owners["B"]
        o.retained = replace(
            o.retained,
            identity=replace(o.retained.identity, provenance=Provenance("old", "B")),
        )
        save_persistent_cognition(o.files.cognition_file, o.retained)
    if fault == "unexpected-memory":
        resident.bind_login(
            self_id="B", native_session_id="native-B", world_epoch=0, world_tick=2,
        )
    with pytest.raises(I2gOriginSchemaHold):
        register_i2g_born_original_empty_schemas(resident)
    if fault != "already-registered":
        assert not resident._present_schemas
    assert paper.stop_count == 0
    assert not (store / "g-000000000001").exists()


def test_i2g_origin_cannot_register_late_after_original_native_login(
    tmp_path, monkeypatch,
):
    *_, resident = _born(tmp_path, monkeypatch)
    resident.bind_login(
        self_id="A", native_session_id="fresh-A", world_epoch=0, world_tick=10,
    )
    with pytest.raises(I2gOriginSchemaHold):
        register_i2g_born_original_empty_schemas(resident)


def test_i2g_original_world_flag_rejected_without_exact_typed_source(
    tmp_path, monkeypatch,
):
    async def refuse():
        await run_real_resident_presence(
            paper_jar=tmp_path / "missing-paper.jar",
            paper_sha256="a" * 64,
            plugin_jar=tmp_path / "missing-plugin.jar",
            plugin_sha256="b" * 64,
            scratch_parent=tmp_path, accepted_eula=True,
            real_world_dev_grant=True, i2g_original_v3_source=True,
            typed_owner_cut_dev=False,
        )
    with pytest.raises(RealResidentPresenceRefusal):
        asyncio.run(refuse())
    assert not list(tmp_path.glob("p0d-resident-presence-*"))


@pytest.mark.parametrize("options", [
    ["--inspect-only", "--real-world-dev-grant"],
    ["--execute-once"],
    ["--execute-once", "--real-world-dev-grant"],
])
def test_i2g_local_cli_refuses_before_world_when_source_unqualified(
    tmp_path, monkeypatch, capsys, options,
):
    args = [
        "i2g", "--paper-jar", str(tmp_path / "missing-paper"),
        "--plugin-jar", str(tmp_path / "missing-plugin"),
        "--scratch-parent", str(tmp_path),
        *options,
    ]
    monkeypatch.setattr("sys.argv", args)
    assert runner.main() == 2
    assert "I2G_REAL_ORIGINAL_PRE_WORLD_OR_TRIAL_HOLD" in capsys.readouterr().err
    assert not list(tmp_path.glob("p0d-resident-presence-*"))
