"""Read-only DEV audit of frozen choices; no provider or engine invocation.

Axes describe verified sources, not new grades or World truth. NO_REVIEW is
epoch-local: prior epochs can carry a forecast without a later review yet.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from adapters.mineflayer.self_world_observation_only_cognition import (
    prepare_w4_offline_cognition_inputs,
)
from experiments import self_world_host_semantic_probe as probe
from experiments.self_world_metadata_ablation import digest


def require(condition, reason):
    if not condition:
        raise probe.Blocked(reason)


def axes(replay, epoch):
    """Use original ATT/PRD verification; never infer review from model text."""
    require(epoch in ('prior', 'following'), 'invalid epoch')
    prepared = prepare_w4_offline_cognition_inputs(replay)
    request = getattr(prepared, epoch + '_bounded')
    values = {d.key: json.loads(d.value_json) for d in request.context}
    selected = values['self_world_observed']
    review = values.get('self_world_prediction_review')
    view = replay.prior if epoch == 'prior' else replay.following
    return {
        'observation_axis': 'SELECTED_POSITIVE' if selected else 'NO_SELECTED_POSITIVE',
        'positive_count': len(selected),
        'labels': [e['label'] for e in selected],
        'prediction_axis': review['status'].upper() if review else 'NO_REVIEW',
        'forecast_present_in_epoch': bool(view.forecasts),
        'review': review,
        'world_absence_established': False,
    }


def reconcile(plan, result, journal):
    """Check every saved call/row and preserve original rubric flags, warmups too."""
    rows, calls = result['rows'], result['calls']
    require(result['terminal'] is None, 'incomplete historical experiment')
    require(len(rows) == result['bounded_requests'] == 100, 'row count differs')
    require(len(calls) == result['provider_calls'] == 100, 'call count differs')
    require(journal[0] == {
        'event': 'begin', 'frozen_sha256': result['frozen_sha256'],
        'schedule_sha256': digest(plan['schedule']),
    }, 'journal begin differs')
    require(journal[-1] == {
        'event': 'terminal', 'error': None, 'provider_calls': 100,
    }, 'journal terminal differs')
    # This retained run has one resolved BOUNDED call per row, no THINK.
    require(len(journal) == 402, 'unexpected journal event count')
    for i, (step, row, call) in enumerate(zip(plan['schedule'], rows, calls, strict=True)):
        e, arm = step['epoch_index'], step['arm']
        epoch = plan['epochs'][e]
        identity = {**step, 'index': i}
        expected = epoch['expected_choice']
        request_sha = epoch['request_sha256'][arm]['bounded']
        require(all(row[k] == v and call[k] == v for k, v in identity.items()),
                'schedule identity differs')
        require(row['case_id'] == epoch['case_id'] and row['epoch'] == epoch['epoch'],
                'source epoch differs')
        require(row['expected_choice'] == expected, 'original rubric differs')
        require(row['request_sha256'] == call['request_sha256'] == request_sha,
                'provider-bound frozen request differs')
        require(call['call'] == i + 1 and call['mode'] == 'bounded', 'call order differs')
        require(row['provider_calls'] == 1 and row['think_calls'] == 0,
                'historical escalation differs')
        require(row['status'] == call['status'] == call['response']['status'] == 'resolved',
                'historical resolution differs')
        require(row['choice_id'] == call['choice_id'] == call['response']['choice_id'],
                'saved response choice differs')
        require(row['choice_id'] in ('INSPECT_SOURCE', 'DEFER_RECHECK'), 'foreign choice')
        require(row['correct_rubric'] == (row['choice_id'] == expected),
                'original scoring flag differs')
        require(call['response_sha256'] == digest(call['response']), 'response digest differs')
        events = journal[1 + i * 4:5 + i * 4]
        require([x['event'] for x in events] == [
            'request_start', 'provider_start', 'provider_end', 'request_end',
        ], 'journal event order differs')
        require({k: v for k, v in events[2].items() if k != 'event'} == call,
                'provider journal differs')
        require({k: v for k, v in events[3].items() if k != 'event'} == row,
                'request journal differs')
        for event, final in ((events[0], row), (events[1], call)):
            require(all(final.get(k) == v for k, v in event.items() if k != 'event'),
                    'journal start differs')
    summary = []
    for e, epoch in enumerate(plan['epochs']):
        entry = {'epoch_index': e, 'case_id': epoch['case_id'], 'epoch': epoch['epoch'],
                 'original_expected': epoch['expected_choice'], 'arms': {}}
        for arm in ('RAW', 'SEM'):
            group = [r for r in rows if r['epoch_index'] == e and r['arm'] == arm]
            measured = [r for r in group if not r['warmup']]
            require(len(group) == 5 and len(measured) == 4, 'repeat count differs')
            entry['arms'][arm] = {
                'inspect': sum(r['choice_id'] == 'INSPECT_SOURCE' for r in measured),
                'defer': sum(r['choice_id'] == 'DEFER_RECHECK' for r in measured),
                'original_correct': sum(r['correct_rubric'] for r in measured),
                'warmup_choice': next(r['choice_id'] for r in group if r['warmup']),
            }
        summary.append(entry)
    return summary


def audit(source_root: Path, evidence_root: Path):
    """Return derived data only. Caller owns exclusive external serialization."""
    frozen = evidence_root / 'frozen-requests.json'
    frozen_sha = hashlib.sha256(frozen.read_bytes()).hexdigest()
    plan = probe.validate_frozen(source_root, frozen, frozen_sha)
    result = json.loads((evidence_root / 'execution.json').read_bytes())
    journal_bytes = (evidence_root / 'execution.json.journal.jsonl').read_bytes()
    require(result['frozen_sha256'] == frozen_sha, 'frozen digest differs')
    require(result['journal_sha256'] == hashlib.sha256(journal_bytes).hexdigest(),
            'journal digest differs')
    summary = reconcile(plan, result, [json.loads(x) for x in journal_bytes.splitlines()])
    sources = probe.load_sources(source_root)
    for row, epoch in zip(summary, plan['epochs'], strict=True):
        _, replay = sources[row['epoch_index'] // 2]
        require(digest(probe.asdict(replay)) == epoch['source_receipt_sha256'],
                'replayed source differs')
        row.update(axes(replay, row['epoch']))
        row['source_receipt_sha256'] = epoch['source_receipt_sha256']
    totals = {arm: sum(r['arms'][arm]['original_correct'] for r in summary)
              for arm in ('RAW', 'SEM')}
    original_report = json.loads((evidence_root / 'report.json').read_bytes())
    require(original_report['head'] == '3e2b04ef0877a1b272a7ee60a43e7e76c80b66bb',
            'historical head differs')
    require(totals == {'RAW': 20, 'SEM': 36}, 'historical totals differ')
    require(all(original_report['metrics'][arm]['scored_correct'] == total
                for arm, total in totals.items()), 'published report differs')
    return {'epochs': summary, 'original_rubric_totals': totals,
            'saved_provider_calls_verified': 100, 'new_provider_calls': 0,
            'new_scores': None, 'scope': 'DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN'}
