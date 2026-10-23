"""Offline semantic boundaries and tampered archive controls; no provider calls."""
import copy
import json
from dataclasses import replace

import pytest

from adapters.mineflayer.self_world_observation_only_epoch_replay import (
    replay_w4_saved_self_world_epochs,
)
from experiments import self_world_host_semantic_probe as probe
from experiments import self_world_model_ab as original
from experiments import self_world_rubric_audit as audit
from experiments.self_world_metadata_ablation import digest
from test_self_world_observation_only_epoch_replay import _case, _offline_lines, _pin


@pytest.fixture
def sources(tmp_path, monkeypatch):
    root = tmp_path / 'source'
    def empty_lines():
        first, second, lines = _offline_lines()
        changed = []
        for raw in lines:
            item = json.loads(raw)
            if item.get('type') == 'observation':
                item['snapshot']['nearby_entities'] = []
                item['snapshot']['nearby_entities_coverage']['candidate_count'] = 0
            changed.append((json.dumps(item) + '\n').encode())
        return first, second, changed

    with monkeypatch.context() as patch:
        patch.setattr('test_self_world_observation_only_epoch_replay._offline_lines', empty_lines)
        report = _case(root)

    def fake_real(_):
        replay = replay_w4_saved_self_world_epochs(**_pin(root, report))
        return original.CognitionCase(
            'w4-original-empty', original.prepare_w4_offline_cognition_inputs(replay),
            'DEFER_RECHECK', 'DEFER_RECHECK', 'SYNTHETIC_DEV')

    monkeypatch.setattr(original, 'build_real_case', fake_real)
    return probe.load_sources(root)


def test_independent_axes_and_forecast_without_review(sources):
    states = []
    for _, replay in sources:
        states.extend(audit.axes(replay, e) for e in ('prior', 'following'))
    assert [(r['positive_count'], r['prediction_axis']) for r in states] == [
        (0, 'NO_REVIEW'), (0, 'NO_REVIEW'),
        (1, 'NO_REVIEW'), (1, 'MATCH'),
        (1, 'NO_REVIEW'), (1, 'MISMATCH'),
        (1, 'NO_REVIEW'), (0, 'UNDETERMINED'),
        (0, 'NO_REVIEW'), (0, 'NO_REVIEW'),
    ]
    assert states[2]['forecast_present_in_epoch']
    assert states[2]['review'] is None
    assert states[5]['labels'] == ['skeleton']
    assert states[5]['review']['predicted_value'] == 'zombie'
    assert states[5]['review']['observed_value'] == 'skeleton'
    assert states[7]['review']['reason'] == 'target_or_property_unobserved'
    assert states[7]['review']['predicted_value'] == 'zombie'
    assert states[7]['review']['observed_value'] is None
    assert all(not r['world_absence_established'] for r in states)


@pytest.mark.parametrize('attack', ['review', 'attention', 'epoch'])
def test_axes_reject_unverified_sources(sources, attack):
    replay = sources[2][1]
    epoch = 'following'
    if attack == 'review':
        replay = replace(replay, prediction_review=replace(
            replay.prediction_review, observed_value='zombie'))
    elif attack == 'attention':
        replay = replace(replay, following_attention=replay.prior_attention)
    else:
        epoch = 'invented'
    with pytest.raises(ValueError):
        audit.axes(replay, epoch)


@pytest.fixture
def archive(sources):
    """Construct archive structure without executing an engine/provider."""
    plan = probe.make_plan(sources, 'offline-test')
    result = {'rows': [], 'calls': [], 'terminal': None, 'bounded_requests': 100,
              'provider_calls': 100, 'frozen_sha256': 'test-only'}
    journal = [{'event': 'begin', 'frozen_sha256': 'test-only',
                'schedule_sha256': digest(plan['schedule'])}]
    for i, step in enumerate(plan['schedule']):
        epoch = plan['epochs'][step['epoch_index']]
        row = {**step, 'index': i, 'case_id': epoch['case_id'], 'epoch': epoch['epoch'],
               'expected_choice': epoch['expected_choice'],
               'request_sha256': epoch['request_sha256'][step['arm']]['bounded']}
        call = {**step, 'index': i, 'call': i + 1, 'mode': 'bounded',
                'request_sha256': row['request_sha256']}
        journal.extend([{'event': 'request_start', **row}, {'event': 'provider_start', **call}])
        choice = 'INSPECT_SOURCE'
        response = {'status': 'resolved', 'choice_id': choice}
        call.update(status='resolved', choice_id=choice, response=response,
                    response_sha256=digest(response))
        row.update(status='resolved', choice_id=choice, provider_calls=1, think_calls=0,
                   correct_rubric=choice == epoch['expected_choice'])
        journal.extend([{'event': 'provider_end', **call}, {'event': 'request_end', **row}])
        result['rows'].append(row)
        result['calls'].append(call)
    journal.append({'event': 'terminal', 'error': None, 'provider_calls': 100})
    return plan, result, journal


def test_reconciliation_retains_mismatch_inspect_as_original_error(archive):
    plan, result, journal = archive
    before = json.dumps(archive, sort_keys=True)
    rows = audit.reconcile(plan, result, journal)
    assert rows[5]['original_expected'] == 'DEFER_RECHECK'
    assert rows[5]['arms']['SEM']['inspect'] == 4
    assert rows[5]['arms']['SEM']['original_correct'] == 0
    assert json.dumps(archive, sort_keys=True) == before


@pytest.mark.parametrize('attack', [
    'score', 'choice', 'request', 'schedule', 'journal', 'start', 'rubric', 'response',
    'count', 'terminal', 'event_order',
])
def test_archive_tampering_rejected(archive, attack):
    plan, result, journal = copy.deepcopy(archive)
    row = result['rows'][0]
    if attack == 'score':
        row['correct_rubric'] = not row['correct_rubric']
    elif attack == 'choice':
        row['choice_id'] = 'DEFER_RECHECK'
    elif attack == 'request':
        row['request_sha256'] = 'foreign'
    elif attack == 'schedule':
        row['epoch_index'] = 9
    elif attack == 'journal':
        journal[4]['choice_id'] = 'foreign'
    elif attack == 'start':
        journal[1]['case_id'] = 'foreign'
    elif attack == 'rubric':
        row['expected_choice'] = 'INSPECT_SOURCE'
    elif attack == 'response':
        result['calls'][0]['response']['choice_id'] = 'DEFER_RECHECK'
    elif attack == 'count':
        result['provider_calls'] = 99
    elif attack == 'terminal':
        result['terminal'] = {'error': 'failed'}
    else:
        journal[1], journal[2] = journal[2], journal[1]
    with pytest.raises(ValueError):
        audit.reconcile(plan, result, journal)
