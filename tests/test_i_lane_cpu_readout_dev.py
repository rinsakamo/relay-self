"""I0 original Owner readout, synthetic Paper/native evidence only."""
from dataclasses import replace

import pytest

import relay_self.i_lane_cpu_readout_dev as integration
from relay_self.bd1b_coverage_inquiry_dev import CoverageInquiryHold
from relay_self.bd1b_owner_source_dev import BD1bSourceHold
from test_bd1b_owner_present_dev import _configured
from test_bd1b_owner_source_dev import _files


def _args(case, self_id="A"):
    return dict(bridge=case[1], boot=case[2], world=case[3],
                links=case[4], self_id=self_id)


def test_one_coherent_readout_for_both_original_selves(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    bridge = case[1]
    before_files = _files(bridge)
    before_owner = {
        sid: (owner.retained, owner.intent, dict(owner.skills),
              set(owner.pending_questions), owner.pattern_registry)
        for sid, owner in bridge.owners.items()
    }
    a = integration.read_i0_owner_cpu(**_args(case, "A"))
    b = integration.read_i0_owner_cpu(**_args(case, "B"))
    assert a.coverage_inquiry is not None
    assert b.coverage_inquiry is not None
    assert a.coverage_inquiry.question_ref != b.coverage_inquiry.question_ref
    for result, sid in ((a, "A"), (b, "B")):
        assert result.source_revision_refs == result.present.present.three_self.source_revision_refs
        assert result.coverage_inquiry.source_revision_refs == result.source_revision_refs
        assert result.present.source.self_id == sid
        assert result.model_invoked is False
        assert result.action_issue_authorized is False
    assert _files(bridge) == before_files
    assert all(
        (owner.retained, owner.intent, owner.skills, owner.pending_questions,
         owner.pattern_registry) == before_owner[sid]
        for sid, owner in bridge.owners.items()
    )


def test_no_qualified_need_means_no_question_proposal(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=False)
    result = integration.read_i0_owner_cpu(**_args(case))
    assert result.coverage_inquiry is None
    assert result.present.exploration_need is None


def test_reject_source_change_during_inquiry(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    original = integration.build_coverage_inquiry

    def changed(*, bridge, boot, world, links, self_id, readout):
        result = original(bridge=bridge, boot=boot, world=world,
                          links=links, self_id=self_id, readout=readout)
        probe = bridge.owners[self_id].current_worldbody_observation
        bridge.owners[self_id].current_worldbody_observation = replace(
            probe, seq=probe.seq + 1,
        )
        return result

    monkeypatch.setattr(integration, "build_coverage_inquiry", changed)
    with pytest.raises((BD1bSourceHold, CoverageInquiryHold, integration.I0OwnerCPUHold)):
        integration.read_i0_owner_cpu(**_args(case))


def test_reject_forged_inquiry_after_original_owner_review(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    original = integration.build_coverage_inquiry

    def forged(**kwargs):
        proposal = original(**kwargs)
        assert proposal is not None
        return replace(proposal, source_revision_refs=("forged",))

    monkeypatch.setattr(integration, "build_coverage_inquiry", forged)
    with pytest.raises(integration.I0OwnerCPUHold):
        integration.read_i0_owner_cpu(**_args(case))


def test_changed_world_generation_and_owner_fence_fail_closed(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    args = _args(case)
    with pytest.raises(BD1bSourceHold):
        integration.read_i0_owner_cpu(**{**args, "world": replace(case[3], epoch=case[3].epoch + 1)})
    case[1].cognitive_work.fence_self("A")
    with pytest.raises(BD1bSourceHold):
        integration.read_i0_owner_cpu(**args)
