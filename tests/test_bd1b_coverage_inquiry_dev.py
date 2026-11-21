"""Synthetic original-owner inquiry tests; no provider or world execution."""
from dataclasses import replace

import pytest

from relay_self.bd1b_coverage_inquiry_dev import CoverageInquiryHold, build_coverage_inquiry
from relay_self.bd1b_owner_source_dev import BD1bSourceHold
from relay_self.three_self_present import EpistemicStatus
from test_bd1b_owner_present_dev import _configured, _project
from test_bd1b_owner_source_dev import _files


def _inquire(case, sid, readout):
    return build_coverage_inquiry(bridge=case[1], boot=case[2], world=case[3],
                                  links=case[4], self_id=sid, readout=readout)


def test_current_both_and_no_mutation(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    bridge = case[1]
    files = _files(bridge)
    state = {sid: (o.retained, o.intent, dict(o.skills), set(o.pending_questions),
                   o.pattern_registry) for sid, o in bridge.owners.items()}
    proposals = []
    for sid in ("A", "B"):
        readout = _project(case, sid)
        proposal = _inquire(case, sid, readout)
        assert proposal == _inquire(case, sid, _project(case, sid))
        assert proposal.need_signal_ref == readout.exploration_need.signal.envelope.event_id
        assert proposal.coverage_claim_ref == readout.exploration_need.basis[0].present_ref
        assert proposal.source_revision_refs == readout.present.three_self.source_revision_refs
        assert proposal.epistemic_status is EpistemicStatus.UNKNOWN
        assert not hasattr(proposal, "action_refs") and not hasattr(proposal, "target")
        proposals.append(proposal)
    assert proposals[0].question_ref != proposals[1].question_ref
    assert _files(bridge) == files
    assert all((o.retained, o.intent, o.skills, o.pending_questions, o.pattern_registry) == state[sid]
               for sid, o in bridge.owners.items())


def test_absent_need_or_coverage(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch)
    assert _inquire(case, "A", _project(case)) is None


def test_absent_coverage_with_eligible_schema(tmp_path, monkeypatch):
    import relay_self.bd1b_owner_present_dev as module

    case = _configured(tmp_path, monkeypatch, need=True)
    monkeypatch.setattr(module, "MineflayerNearbyEntitiesCoverage", type(None))
    assert _inquire(case, "A", _project(case)) is None


@pytest.mark.parametrize("variant", ["foreign", "forged", "observed", "stale_schema"])
def test_altered_readout_rejected(tmp_path, monkeypatch, variant):
    case = _configured(tmp_path, monkeypatch, need=True)
    readout = _project(case, "B" if variant == "foreign" else "A")
    if variant == "forged":
        need = readout.exploration_need
        readout = replace(readout, exploration_need=replace(
            need, basis=(replace(need.basis[0], present_ref="forged"),)))
    elif variant == "observed":
        need = readout.exploration_need
        readout = replace(readout, exploration_need=replace(
            need, basis=(replace(need.basis[0], status=EpistemicStatus.OBSERVED),)))
    elif variant == "stale_schema":
        readout = replace(readout, schema=replace(readout.schema, revision=2))
    with pytest.raises(CoverageInquiryHold):
        _inquire(case, "A", readout)


@pytest.mark.parametrize("variant", ["native", "paper", "epoch", "retired", "registry"])
def test_current_source_revalidated(tmp_path, monkeypatch, variant):
    case = _configured(tmp_path, monkeypatch, need=True)
    readout = _project(case)
    bridge = case[1]
    if variant == "native":
        bridge.owners["A"].current_worldbody_observation = replace(bridge.last_login_observations["A"])
    elif variant == "paper":
        bridge.paper._session_id = "foreign"
    elif variant == "epoch":
        bridge.cognitive_work._states["A"].world_epoch += 1
    elif variant == "retired":
        bridge.cognitive_work.fence_self("A")
    else:
        bridge.owners["A"].pattern_registry = replace(bridge.owners["A"].pattern_registry, revision=2)
    with pytest.raises((BD1bSourceHold, RuntimeError)):
        _inquire(case, "A", readout)
