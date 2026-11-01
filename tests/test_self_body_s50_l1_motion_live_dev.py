"""Synthetic typed handoff tests: NOT a newly observed Minecraft World."""
from dataclasses import replace

import pytest

from adapters.mineflayer.m02_paper_dev.s50_live_paper_window import (
    S50LivePaperTick,
    S50LivePaperWindow,
)
from adapters.mineflayer.self_body_s50_l1_motion_live_dev import score_live_dev
from adapters.mineflayer.self_body_s50_l1_motion_prediction import (
    MotionPredictionRejected,
    evaluate_heldout,
    from_live_window,
)
from adapters.mineflayer.self_body_s50_l1_motion_prequential import (
    freeze_for_target,
    update_after_score,
)
from test_self_body_s50_l1_motion_prediction import pair
from test_self_body_s50_l1_motion_prequential import target


def fixture():
    train, old = pair()
    # Explicit synthetic new identities; old measured values are ONLY fixtures.
    window = S50LivePaperWindow(
        'synthetic-mp3-session', 'synthetic-action',
        'synthetic-action-synthetic-mp3-session', 'synthetic-world',
        old.subject_uuid, 'a' * 64, 100,
        tuple(S50LivePaperTick(s.world_tick, s.displacement_m, False) for s in old.steps),
        0,
    )
    ticket = freeze_for_target(train, target(from_live_window(window)),
                              capture_mode='PROSPECTIVE_LOCAL_ORDER_NOT_EXTERNALLY_ATTESTED')
    return train, window, ticket


def test_explicit_transition_preserves_ceilings_and_cheap_parity():
    train, window, ticket = fixture()
    scored = score_live_dev(ticket, train, window)
    assert scored.errors.l1_linear == scored.errors.cheap_same_linear
    assert scored.classification == 'CHEAP_EQUIVALENT'
    assert len(scored.predictions_m) == len(scored.measured_m) == 7
    assert not scored.chronology_attested
    assert not scored.s16_outcome_verified
    assert not scored.cleanup_verified
    assert train.source_ceiling == 'ARCHIVAL_READBACK_NOT_REAUTHENTICATED'
    with pytest.raises(MotionPredictionRejected):
        evaluate_heldout(train, from_live_window(window))
    with pytest.raises(MotionPredictionRejected):
        update_after_score(ticket, train, from_live_window(window), scored)


@pytest.mark.parametrize('mutation', [
    'session', 'world', 'action', 'subject', 'digest', 'input', 'goal',
    'stability', 'complete', 'clear', 'p1', 's10', 's11', 'packet',
    'ticket', 'model', 'archive_mode', 'ticks', 'nan',
])
def test_reject_foreign_or_promoted_source_and_changed_ticket(mutation):
    train, window, ticket = fixture()
    fields = {'session': 'session_id', 'world': 'paper_world_uuid',
              'action': 'action_id', 'subject': 'subject_uuid'}
    if mutation in fields:
        window = replace(window, **{fields[mutation]: 'foreign'})
    elif mutation == 'digest':
        window = replace(window, paper_prefix_sha256=train.paper_prefix_sha256)
    elif mutation in ('input', 'ticks', 'nan'):
        ticks = list(window.ticks)
        if mutation == 'input':
            ticks[0] = replace(ticks[0], last_reported_input_active=True)
        elif mutation == 'ticks':
            ticks[1] = replace(ticks[1], world_tick=0)
        else:
            ticks[1] = replace(ticks[1], displacement_m=float('nan'))
        window = replace(window, ticks=tuple(ticks))
    elif mutation == 'ticket':
        ticket = replace(ticket, ticket_sha256='f' * 64)
    elif mutation == 'model':
        ticket = replace(ticket, model=replace(ticket.model, slope=42.0))
    elif mutation == 'archive_mode':
        ticket = freeze_for_target(train, ticket.target)
    else:
        field, value = {
            'goal': ('goal_admitted', True), 'stability': ('physical_stability_attested', True),
            'complete': ('node_trace_complete', True), 'clear': ('effective_clear_tick', '251'),
            'p1': ('p1_wait_granted', 8), 's10': ('s10_updates', 1),
            's11': ('s11_grants', 1), 'packet': ('client_packet_writes_attested', True),
        }[mutation]
        window = replace(window, **{field: value})
    with pytest.raises(MotionPredictionRejected):
        score_live_dev(ticket, train, window)
