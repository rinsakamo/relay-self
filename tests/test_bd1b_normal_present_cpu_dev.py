"""Offline original resident CPU entry and its existing inquiry consumer."""
import asyncio
from dataclasses import replace

import pytest

import relay_self.bd1b_owner_present_dev as projection
from relay_self.bd1b_coverage_inquiry_dev import build_coverage_inquiry
from relay_self.bd1b_owner_source_dev import BD1bSourceHold
from relay_self.resident_cognitive_work_owner_dev import ResidentCognitiveWorkOwner
from test_bd1b_owner_present_dev import _configured
from test_bd1b_owner_source_dev import _files


def test_resident_cpu_present_and_current_inquiry(tmp_path, monkeypatch):
    bind_login = ResidentCognitiveWorkOwner.bind_login
    case = _configured(tmp_path, monkeypatch, need=True)
    _, bridge, boot, world, links, _ = case
    resident = bridge.cognitive_work
    files = _files(bridge)
    state = {sid: (o.retained, o.intent, dict(o.skills), set(o.pending_questions),
                   o.pattern_registry) for sid, o in bridge.owners.items()}
    args = dict(bridge=bridge, boot=boot, world=world, links=links)
    frames = {}
    for sid in ("A", "B"):
        assert resident.current_scope(sid)[1] == bridge.last_login_observations[sid].session_id
        frame = resident.read_present_cpu(**args, self_id=sid)
        frames[sid] = frame
        assert frame.schema == resident.present_schema(sid)
        assert frame.source.native_probe_ref == bridge.last_login_observations[sid].request_id
        claim = frame.present.three_self.self_world.claims[0]
        assert claim.claim_key == frame.exploration_need.basis[0].present_ref
        inquiry = resident.read_coverage_inquiry_cpu(**args, self_id=sid)
        assert inquiry.coverage_claim_ref == claim.claim_key
        assert inquiry.source_revision_refs == frame.present.three_self.source_revision_refs
    assert frames["A"].source.native_session_id != frames["B"].source.native_session_id
    assert frames["A"].present.three_self.scope != frames["B"].present.three_self.scope

    # A changed observation cannot be consumed with the old source receipt.
    original = bridge.owners["A"].current_worldbody_observation
    bridge.owners["A"].current_worldbody_observation = replace(original, seq=original.seq + 1)
    with pytest.raises(BD1bSourceHold):
        build_coverage_inquiry(**args, self_id="A", readout=frames["A"])
    bridge.owners["A"].current_worldbody_observation = original
    with pytest.raises(BD1bSourceHold):
        build_coverage_inquiry(**{**args, "world": replace(world, epoch=world.epoch + 1)},
                               self_id="A", readout=frames["A"])

    # A source change during projection must be detected before returning.
    project = projection.project_present_frame
    def changed_during_projection(**kwargs):
        result = project(**kwargs)
        bridge.owners["A"].current_worldbody_observation = replace(original, seq=original.seq + 1)
        return result
    with monkeypatch.context() as m:
        m.setattr(projection, "project_present_frame", changed_during_projection)
        with pytest.raises(BD1bSourceHold):
            resident.read_present_cpu(**args, self_id="A")
    bridge.owners["A"].current_worldbody_observation = original
    resident.fence_self("A")
    with pytest.raises(BD1bSourceHold):
        build_coverage_inquiry(**args, self_id="A", readout=frames["A"])
    retirement = asyncio.run(resident.retire_self("A"))
    resident.mark_offline(retirement)
    with pytest.raises(BD1bSourceHold):
        build_coverage_inquiry(**args, self_id="A", readout=frames["A"])
    bind_login(resident, self_id="A", native_session_id="new-native-A",
               world_epoch=world.epoch, world_tick=0)
    with pytest.raises(BD1bSourceHold):
        build_coverage_inquiry(**args, self_id="A", readout=frames["A"])
    assert _files(bridge) == files
    assert all((o.retained, o.intent, o.skills, o.pending_questions, o.pattern_registry) == state[sid]
               for sid, o in bridge.owners.items())
