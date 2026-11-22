"""No-World I2e future committed A/B source preflight fixtures and hostile guards."""
from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from relay_self.cognitive_minimal_dev import initial_patterns_with_relative_move
from relay_self.innate_schema import (
    SchemaActivation, SchemaMode, SchemaModuleSpec, SchemaSnapshot,
)
from relay_self.i_lane_i2e_future_original_preflight_dev import (
    I2eFutureSourceHold,
    preflight_i2e_future_source,
)
from relay_self.persistent_cognition import save_persistent_cognition
from relay_self.provenance import Provenance
from relay_self.resident_cognitive_work_owner_dev import ResidentCognitiveWorkOwner
from relay_self.stage28b_retired_resident_typed_cut_dev import (
    capture_retired_resident_typed_world,
)
from test_stage28b_retired_typed_cut_dev import _setup
from test_stage28c1_inert_restore_dev import _prepare, _source


def _future(tmp_path, monkeypatch, *, registered=("A", "B"), explore=False):
    bridge, paper, store, evidence = _setup(tmp_path, monkeypatch)
    for name in ("world_nether", "world_the_end"):
        dim = tmp_path / name
        dim.mkdir()
        (dim / "region").mkdir()
        (dim / "region" / "r.0.0.mca").write_bytes(b"future-synthetic-world")
    for sid in ("A", "B"):
        owner = bridge.owners[sid]
        if explore:
            owner.pattern_registry = initial_patterns_with_relative_move()
        owner.retained = replace(owner.retained, pattern_registry=owner.pattern_registry)
        save_persistent_cognition(owner.files.cognition_file, owner.retained)
    resident = ResidentCognitiveWorkOwner(bridge.owners)
    bridge.cognitive_work = resident
    for sid in ("A", "B"):
        if sid in registered:
            if explore:
                spec = SchemaModuleSpec(
                    "exploratory", 1, frozenset({SchemaMode.FULL}),
                    ("QUESTION_CANDIDATE", "EXPLORATION_NEED"), (),
                    Provenance("test", "future-full"),
                )
                snapshot = SchemaSnapshot(
                    sid, 1, (SchemaActivation(spec, SchemaMode.FULL),),
                )
            else:
                snapshot = SchemaSnapshot(sid, 0, ())
            resident.register_present_schema(sid, snapshot)
        resident.bind_login(
            self_id=sid, native_session_id=bridge.owners[sid].native_session_id,
            world_epoch=0, world_tick=105,
        )
    for sid in ("A", "B"):
        resident.fence_self(sid)
        result = asyncio.run(resident.retire_self(sid))
        resident.mark_offline(result)
    generation = capture_retired_resident_typed_world(
        bridge=bridge, paper=paper, store=store, evidence_dir=evidence,
    ).generation
    dest = tmp_path / "i2e-future-restored"
    prepared = _prepare(generation, dest)
    args = {
        "generation": generation,
        "restored": dest,
        "expected_world_id": "world-1",
        "expected_source_branch_id": "source",
        "expected_committed_sha256": prepared.source_commit_sha256,
        "expected_fork_branch_id": prepared.restored_branch_id,
    }
    return args


def test_i2e_preflight_only_new_original_schema3_empty_registry(
    tmp_path, monkeypatch,
):
    args = _future(tmp_path, monkeypatch)
    receipt = preflight_i2e_future_source(**args)
    assert receipt.schema_recovered_a_b
    assert receipt.original_selves_offline
    assert receipt.committed_sha256 == args["expected_committed_sha256"]
    assert receipt.source_world_id == "world-1"
    assert not receipt.paper_started and not receipt.native_rejoined
    assert receipt.model_post_count == 0
    assert not receipt.physical_action_issue_authorized
    for sid in ("A", "B"):
        assert receipt.restored.cognitive_work._present_schemas[sid][0].modules == ()
        assert receipt.restored.owners[sid].pattern_registry.revision == 0
        assert receipt.restored.physical.resident_states[sid] == "OFFLINE"
    assert receipt.restored.physical.active_action_ids == ()


@pytest.mark.parametrize("registered", [(), ("A",), ("B",)])
def test_i2e_preflight_refuses_legacy_or_partially_recorded_source(
    tmp_path, monkeypatch, registered,
):
    args = _future(tmp_path, monkeypatch, registered=registered)
    with pytest.raises(I2eFutureSourceHold):
        preflight_i2e_future_source(**args)


def test_i2e_preflight_refuses_historical_unrecorded_generation(
    tmp_path, monkeypatch,
):
    generation = _source(tmp_path, monkeypatch)
    dest = tmp_path / "legacy-restored"
    prepared = _prepare(generation, dest)
    with pytest.raises(I2eFutureSourceHold):
        preflight_i2e_future_source(
            generation=generation, restored=dest,
            expected_world_id="world-1",
            expected_source_branch_id="source",
            expected_committed_sha256=prepared.source_commit_sha256,
            expected_fork_branch_id=prepared.restored_branch_id,
        )


@pytest.mark.parametrize("fault", [
    "nonempty-exploration", "foreign-world", "bad-commit",
    "bad-fork", "mutated-a-cognition", "mutated-b-owner",
    "mutated-b-wal",
])
def test_i2e_preflight_refuses_synthetic_source_upgrade_or_corruption(
    tmp_path, monkeypatch, fault,
):
    args = _future(
        tmp_path, monkeypatch, explore=(fault == "nonempty-exploration"),
    )
    if fault == "foreign-world":
        args["expected_world_id"] = "different-world"
    elif fault == "bad-commit":
        args["expected_committed_sha256"] = "0" * 64
    elif fault == "bad-fork":
        args["expected_fork_branch_id"] = "foreign-restoration"
    elif fault.startswith("mutated-"):
        _, sid, label = fault.split("-")
        filename = {
            "cognition": "cognition.json",
            "owner": "owner-state.json",
            "wal": "physical-wal.json",
        }[label]
        (args["restored"] / "selves" / sid.upper() / filename).write_bytes(b"tampered")
    with pytest.raises(I2eFutureSourceHold):
        preflight_i2e_future_source(**args)
