"""B + B+D + R0 integration: original owner identity and negative controls.

This test uses the *original* synthetic Bridge and immutable B owner sources.
No GPU, Paper process, World run, alternate owner or self-issued ADOPT.
"""
from dataclasses import FrozenInstanceError, replace

import pytest

from relay_self.bd1b_coverage_adoption_turn_dev import prepare_coverage_adoption_turn
from relay_self.r0_cognitive_context_dev import (
    CognitiveContext,
    R0ContextHold,
    context_is_live,
    read_original_owner_current,
)
from test_b_np1b_normal_present_poll_dev import pair as pair
from test_bd1b_owner_present_dev import _configured
from test_bd1b_owner_source_dev import _files


def _args(case, self_id):
    _, bridge, boot, world, links, _ = case
    return dict(bridge=bridge, boot=boot, world=world, links=links, self_id=self_id)


@pytest.mark.parametrize("self_id", ("A", "B"))
def test_bd_inquiry_and_r0_signal_share_one_original_resident(
    tmp_path, monkeypatch, self_id,
):
    case = _configured(tmp_path, monkeypatch, need=True)
    bridge = case[1]
    resident = bridge.cognitive_work
    before_files = _files(bridge)
    before = {
        sid: (owner.retained, owner.intent, owner.pattern_registry,
              dict(owner.skills), set(owner.pending_questions))
        for sid, owner in bridge.owners.items()
    }
    assert resident is not None
    assert resident.owners[self_id] is bridge.owners[self_id]
    kwargs = _args(case, self_id)
    present = resident.read_present_cpu(**kwargs)
    assert present.exploration_need is not None
    current = read_original_owner_current(
        **kwargs, signals=(present.exploration_need.signal,),
    )
    inquiry = prepare_coverage_adoption_turn(**kwargs)
    assert inquiry.self_id == self_id
    assert inquiry.inquiry == resident.read_coverage_inquiry_cpu(**kwargs)
    assert current.scope.self_id == inquiry.self_id
    assert current.owner_epoch == resident.current_scope(self_id)[0]
    assert context_is_live(
        CognitiveContext(current), bridge=bridge,
        boot=case[2], world=case[3], links=case[4],
    )
    # Preparing an inquiry and reading R0 CURRENT is never an ADOPT or mutation.
    assert _files(bridge) == before_files
    assert all(
        (owner.retained, owner.intent, owner.pattern_registry,
         owner.skills, owner.pending_questions) == before[sid]
        for sid, owner in bridge.owners.items()
    )


def test_r0_context_cannot_requalify_after_paper_source_drift(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    kwargs = _args(case, "A")
    context = CognitiveContext(read_original_owner_current(**kwargs))
    assert context_is_live(
        context, bridge=case[1], boot=case[2], world=case[3], links=case[4],
    )
    case[1].paper._session_id = "unrelated-paper-session"
    assert not context_is_live(
        context, bridge=case[1], boot=case[2], world=case[3], links=case[4],
    )


def test_r0_readonly_context_has_no_adoption_or_physical_issuer(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    current = read_original_owner_current(**_args(case, "A"))
    context = CognitiveContext(current)
    with pytest.raises(FrozenInstanceError):
        context.current = current
    with pytest.raises(R0ContextHold):
        replace(current, need_refs=("not-issued-by-schema",))
    assert not hasattr(context, "retain_memory")
    assert not hasattr(context, "commit_intent")
    assert not hasattr(context, "execute_physical_action")


def test_b_rejoin_pair_still_points_to_original_owner_not_shadow(pair):
    fixture = pair[0]
    bridge = fixture.bridge
    resident = bridge.cognitive_work
    assert resident is not None
    assert set(bridge.owners) == {"A", "B"}
    assert resident.owners["A"] is bridge.owners["A"]
    assert resident.owners["B"] is bridge.owners["B"]
    assert resident.owners["A"] is not resident.owners["B"]
