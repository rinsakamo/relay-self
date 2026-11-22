"""I1 normal CPU owner rebootstrap and repeated SENSE (offline; no Minecraft)."""
import asyncio
import time
from dataclasses import replace

import pytest

from relay_self.cognitive_minimal_dev import initial_patterns_with_relative_move
from relay_self.i_lane_i1_normal_runtime_dev import (
    I1NormalRuntimeHold,
    install_i1_original_schema_bootstrap,
    prepare_i1_original_schema_bootstrap,
    read_i1_original_cpu_epoch,
    sample_i1_original_cpu_epochs,
)
from relay_self.innate_schema import SchemaSnapshot
from relay_self.resident_cognitive_work_owner_dev import (
    ResidentCognitiveWorkError,
    ResidentCognitiveWorkOwner,
)
from test_bd1b_owner_present_dev import _configured
from test_bd1b_owner_source_dev import _files
from test_i_lane_e2c_original_present_dev import _inject
from test_stage28c2_recovered_resident_owner_dev import _context, _reattach
from test_stage28c2c_fresh_recovered_l1_dev import _ready


def test_restored_A_B_without_explore_bootstraps_only_existing_cpu_patterns(
    tmp_path, monkeypatch,
):
    generation, restored, prepared = _context(tmp_path, monkeypatch)
    recovered = _reattach(generation, restored, prepared)
    before = _files(type("Bridge", (), {"owners": recovered.owners})())
    saved = {sid: owner.pattern_registry for sid, owner in recovered.owners.items()}
    planned = prepare_i1_original_schema_bootstrap(recovered.cognitive_work)
    assert tuple(s.self_id for s in planned) == ("A", "B")
    assert all(s.modules == () and s.revision == 0 for s in planned)
    assert install_i1_original_schema_bootstrap(recovered.cognitive_work) == planned
    assert recovered.cognitive_work._present_schemas["A"][0] == planned[0]
    assert recovered.cognitive_work._present_schemas["B"][0] == planned[1]
    assert all(recovered.owners[s].pattern_registry is saved[s] for s in saved)
    assert _files(type("Bridge", (), {"owners": recovered.owners})()) == before
    with pytest.raises(I1NormalRuntimeHold):
        install_i1_original_schema_bootstrap(recovered.cognitive_work)


def test_existing_original_exploration_config_only_for_the_self_that_has_it(
    tmp_path, monkeypatch,
):
    generation, restored, prepared = _context(tmp_path, monkeypatch)
    recovered = _reattach(generation, restored, prepared)
    a = recovered.owners["A"]
    a.pattern_registry = initial_patterns_with_relative_move()  # test-only saved-registry stand-in
    snapshots = install_i1_original_schema_bootstrap(recovered.cognitive_work)
    assert snapshots[0].get("exploratory").spec.version == 1
    assert snapshots[1].get("exploratory") is None
    assert a.pattern_registry is recovered.cognitive_work._present_schemas["A"][1]
    assert recovered.owners["B"].pattern_registry.revision == 0


def test_invalid_second_original_registry_is_rejected_before_any_schema_install(
    tmp_path, monkeypatch,
):
    generation, restored, prepared = _context(tmp_path, monkeypatch)
    recovered = _reattach(generation, restored, prepared)
    registry = initial_patterns_with_relative_move()
    bad = replace(registry.patterns[-1], version=2)
    recovered.owners["B"].pattern_registry = replace(
        registry, patterns=(*registry.patterns[:-1], bad),
    )
    with pytest.raises(I1NormalRuntimeHold):
        install_i1_original_schema_bootstrap(recovered.cognitive_work)
    assert recovered.cognitive_work._present_schemas == {}


def test_current_original_E_snapshot_enters_normal_cpu_once(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    _, bridge, boot, world, links, _ = case
    before = _files(bridge)
    frame = _inject(bridge, world)
    row = read_i1_original_cpu_epoch(
        bridge=bridge, boot=boot, world=world, links=links, self_id="A",
    )
    assert row.sense_revision == frame.source_revision_ref
    assert row.native_seq == frame.observation.seq
    assert row.source_revision_refs[-1] == row.sense_revision
    assert row.inquiry_ref is not None
    assert "EXPLORE_WORLD" in row.goal_ids
    assert row.l1_descriptions == ("ESCALATE_L2", "DEFER")
    assert not row.model_invoked and not row.action_issue_authorized
    assert _files(bridge) == before


def test_two_qualified_native_versions_for_each_self_without_action_or_memory(
    tmp_path, monkeypatch,
):
    case = _configured(tmp_path, monkeypatch, need=True)
    _, bridge, boot, world, links, _ = case
    original = {sid: bridge.owners[sid].current_worldbody_observation for sid in ("A", "B")}
    before = _files(bridge)
    for sid in ("A", "B"):
        _inject(bridge, world, sid)
    rounds = 0
    bridge._i1_correlated_sense = {}
    bridge._i1_correlated_received_at = {}

    async def refresh_native():
        nonlocal rounds
        rounds += 1
        # Synthetic original single-session matched probes are separate from
        # passive SENSE. No new source Owner, launcher, or Action is installed.
        observed = {}
        for sid in ("A", "B"):
            frame = bridge._sense[sid]
            matched = replace(
                frame, observation=replace(
                    frame.observation, seq=3 + rounds, kind="probe",
                    request_id=f"i1-original-sense-{rounds:031x}{int(sid == 'B'):x}",
                    snapshot=replace(frame.observation.snapshot, food=float(8 + rounds)),
                ),
                source_revision_ref=f"mineflayer:{frame.observation.session_id}:{3 + rounds}",
            )
            bridge._sense[sid] = matched
            bridge._sense_received_at[sid] = time.monotonic()
            bridge._i1_correlated_sense[sid] = matched
            bridge._i1_correlated_received_at[sid] = time.monotonic()
            observed[sid] = matched
        return observed

    result = asyncio.run(sample_i1_original_cpu_epochs(
        bridge=bridge, boot=boot, world=world, links=links,
        refresh_native_source=refresh_native,
        refresh_paper_source=lambda: (world, links),
        timeout_s=1.0, poll_s=0.01,
    ))
    assert result.per_self_counts == (("A", 2), ("B", 2))
    assert result.continuous_native_updates_observed
    assert [x.native_seq for x in result.epochs if x.self_id == "A"] == [4, 5]
    assert [x.native_seq for x in result.epochs if x.self_id == "B"] == [4, 5]
    assert all(not x.action_issue_authorized and not x.model_invoked for x in result.epochs)
    assert all(bridge.owners[s].current_worldbody_observation is original[s] for s in original)
    assert _files(bridge) == before


def test_no_second_native_revision_cannot_claim_continuity(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    _, bridge, boot, world, links, _ = case
    for sid in ("A", "B"):
        _inject(bridge, world, sid)
    result = asyncio.run(sample_i1_original_cpu_epochs(
        bridge=bridge, boot=boot, world=world, links=links,
        refresh_paper_source=lambda: (world, links),
        timeout_s=0.1, poll_s=0.01,
    ))
    assert result.per_self_counts == (("A", 1), ("B", 1))
    assert not result.continuous_native_updates_observed


def test_fenced_owner_stops_current_normal_readout(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    _, bridge, boot, world, links, _ = case
    _inject(bridge, world)
    bridge.cognitive_work.fence_self("A")
    with pytest.raises((I1NormalRuntimeHold, ResidentCognitiveWorkError)):
        read_i1_original_cpu_epoch(
            bridge=bridge, boot=boot, world=world, links=links, self_id="A",
        )


def test_old_original_registry_without_explore_projects_live_body_and_sense(
    tmp_path, monkeypatch,
):
    original_bind = ResidentCognitiveWorkOwner.bind_login

    def bind_config_only(resident, *, self_id, **kwargs):
        owner = resident.owners[self_id]
        assert not any(p.schema_id == "exploration" for p in owner.pattern_registry.patterns)
        resident.register_present_schema(
            self_id, SchemaSnapshot(self_id, owner.pattern_registry.revision, ()),
        )
        return original_bind(resident, self_id=self_id, **kwargs)

    monkeypatch.setattr(ResidentCognitiveWorkOwner, "bind_login", bind_config_only)
    case = _ready(tmp_path, monkeypatch)
    _, bridge, boot, world, links, _ = case
    original_registries = {sid: bridge.owners[sid].pattern_registry for sid in ("A", "B")}
    before = _files(bridge)
    from relay_self.i_lane_cpu_readout_dev import read_i0_owner_cpu

    args = dict(bridge=bridge, boot=boot, world=world, links=links, self_id="A")
    baseline = read_i0_owner_cpu(**args)
    assert baseline.coverage_inquiry is None
    assert baseline.present.exploration_need is None
    assert baseline.present.schema.modules == ()
    frame = _inject(bridge, world)
    fresh = read_i1_original_cpu_epoch(**args)
    assert fresh.sense_revision == frame.source_revision_ref
    assert fresh.inquiry_ref is None
    assert "EXPLORE_WORLD" not in fresh.goal_ids
    assert fresh.l1_descriptions == ("ESCALATE_L2", "DEFER")
    assert all(bridge.owners[sid].pattern_registry is original_registries[sid]
               for sid in ("A", "B"))
    assert _files(bridge) == before
