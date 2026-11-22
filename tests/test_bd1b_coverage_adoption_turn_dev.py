"""Synthetic CPU preparation only; no model decision is asserted."""
from dataclasses import replace

import pytest

from relay_self.bd1b_coverage_adoption_turn_dev import (
    CHOICES,
    CoverageAdoptionTurnHold,
    prepare_coverage_adoption_turn,
    validate_coverage_adoption_turn_cpu,
)
from relay_self.exploration_continuity_dev import ExplorationContinuity
from relay_self.provenance import Provenance
from test_bd1b_owner_present_dev import _configured
from test_bd1b_owner_source_dev import _files


def arguments(case, sid="A"):
    _, bridge, boot, world, links, _ = case
    return dict(bridge=bridge, boot=boot, world=world, links=links, self_id=sid)


def check(kw, turn):
    return validate_coverage_adoption_turn_cpu(**{k: v for k, v in kw.items() if k != 'self_id'}, turn=turn)


def test_both_original_owners_and_read_only(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    bridge = case[1]
    files = _files(bridge)
    before = {sid: (o.retained, o.intent.events, dict(o.skills), set(o.pending_questions))
              for sid, o in bridge.owners.items()}
    a = prepare_coverage_adoption_turn(**arguments(case))
    b = prepare_coverage_adoption_turn(**arguments(case, 'B'))
    again = prepare_coverage_adoption_turn(**arguments(case))
    for turn in (a, b, again):
        check(arguments(case, turn.self_id), turn)
        assert turn.request.choices == CHOICES
        assert turn.request.think_allowed is False
        assert turn.request.focus == turn.inquiry.question_ref
        assert len(turn.candidate_set_sha256) == 64
        assert turn.request.identity_context is not None
    assert a.inquiry != b.inquiry
    assert a.request.choices == again.request.choices
    assert a.work_ref != again.work_ref and a.request.request_id != again.request.request_id
    assert _files(bridge) == files
    assert all((o.retained, o.intent.events, o.skills, o.pending_questions) == before[sid]
               for sid, o in bridge.owners.items())


def test_no_need_refuses(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=False)
    with pytest.raises(CoverageAdoptionTurnHold):
        prepare_coverage_adoption_turn(**arguments(case))


@pytest.mark.parametrize('variant', ['foreign', 'choices', 'digest', 'native', 'paper',
                                   'world_epoch', 'resident_epoch', 'schema', 'continuity',
                                   'intent', 'fence', 'lane'])
def test_stale_and_tampered_turns_refused(tmp_path, monkeypatch, variant):
    case = _configured(tmp_path, monkeypatch, need=True)
    kw = arguments(case)
    bridge = case[1]
    turn = prepare_coverage_adoption_turn(**kw)
    owner = bridge.owners['A']
    if variant == 'foreign':
        turn = replace(turn, inquiry=prepare_coverage_adoption_turn(**arguments(case, 'B')).inquiry)
    elif variant == 'choices':
        turn = replace(turn, request=replace(turn.request, choices=tuple(reversed(CHOICES))))
    elif variant == 'digest':
        turn = replace(turn, candidate_set_sha256='0' * 64)
    elif variant == 'native':
        owner.current_worldbody_observation = replace(owner.current_worldbody_observation)
    elif variant == 'paper':
        bridge.paper._session_id = 'foreign'
    elif variant == 'world_epoch':
        kw['world'] = replace(kw['world'], epoch=kw['world'].epoch + 1)
    elif variant == 'resident_epoch':
        bridge.cognitive_work._states['A'].epoch += 1
    elif variant == 'schema':
        owner.pattern_registry = replace(owner.pattern_registry, revision=2)
    elif variant == 'continuity':
        owner.retained = replace(owner.retained, exploration_continuity=ExplorationContinuity('A', 1))
    elif variant == 'intent':
        owner.intent.commit('new', objective='test', at_ns=1, provenance=Provenance('test', 'intent'))
    elif variant == 'fence':
        bridge.cognitive_work.fence_self('A')
    else:
        bridge.inference_lane = object()
    with pytest.raises((ValueError, RuntimeError)):
        check(kw, turn)


def test_retired_owner_refuses(tmp_path, monkeypatch):
    import asyncio

    case = _configured(tmp_path, monkeypatch, need=True)
    kw = arguments(case)
    turn = prepare_coverage_adoption_turn(**kw)
    resident = case[1].cognitive_work
    resident.fence_self('A')
    receipt = asyncio.run(resident.retire_self('A'))
    resident.mark_offline(receipt)
    with pytest.raises((ValueError, RuntimeError)):
        check(kw, turn)
    with pytest.raises((ValueError, RuntimeError)):
        prepare_coverage_adoption_turn(**kw)


def test_no_coverage_no_inquiry(tmp_path, monkeypatch):
    import relay_self.bd1b_owner_present_dev as present

    case = _configured(tmp_path, monkeypatch, need=True)
    monkeypatch.setattr(present, 'MineflayerNearbyEntitiesCoverage', type(None))
    with pytest.raises(CoverageAdoptionTurnHold):
        prepare_coverage_adoption_turn(**arguments(case))
