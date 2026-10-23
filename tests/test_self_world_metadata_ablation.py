"""Counterfactual DEV apparatus, no physical model or World calls."""
import hashlib
import json
from dataclasses import replace

import pytest

from adapters.llama_cpp.relay_engine import LlamaCppProviderError
from experiments.self_world_metadata_ablation import (
    ARMS,
    METADATA,
    ORDER,
    W4ModelABBlocked,
    build_arms,
    execute_factorial,
    freeze_requests,
    validate_arms,
)
from experiments.self_world_model_ab import _synthetic_cases
from relay_self.provenance import Provenance
from relay_self.relay_engine import CognitionDatum, CognitionMode, ProviderDecision


@pytest.fixture
def sources():
    synthetic = _synthetic_cases()[-1].prepared.following_bounded
    real = replace(synthetic, request_id='w4-offline-1e86a714f3ea3374-after-bounded', context=(
        CognitionDatum.from_value('self_world_observer', {
            'coverage_truncated': False, 'status': 'observed',
            'self_id': 'w4-offline-observer',
            'session_id': '05a331a2-393b-4f24-a2cd-9b5bfc6438e8',
            'epoch_id': 'w4-1e86a714f3ea3374-after-5',
            'source_ref': 'present:05a331a2-393b-4f24-a2cd-9b5bfc6438e8:5:w4-after-1e86a714f3ea3374',
        }, Provenance('mineflayer', '05a331a2-393b-4f24-a2cd-9b5bfc6438e8:5')),
        CognitionDatum.from_value('self_world_observed', [], Provenance(
            'mineflayer', '05a331a2-393b-4f24-a2cd-9b5bfc6438e8:5')),
    ))
    return real, synthetic


def test_four_arms_and_frozen_diff(sources, tmp_path):
    before = repr(sources)
    arms = build_arms(*sources)
    assert arms['A'] == sources[0] and arms['D'] == sources[1]
    assert arms['B'].context == arms['A'].context
    assert arms['C'].context == arms['D'].context
    path = tmp_path/'frozen.json'
    sha = freeze_requests(arms, model='gemma4-12b-q4km', output=path)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == sha
    manifest = json.loads(path.read_bytes())
    m = ['/context/0/value/' + k for k in METADATA]
    m += ['/context/0/provenance/reference', '/context/1/provenance/reference']
    assert manifest['differences_from_A']['A'] == []
    assert manifest['differences_from_A']['B'] == ['/request_id']
    assert set(manifest['differences_from_A']['C']) == set(m)
    assert set(manifest['differences_from_A']['D']) == {*m, '/request_id'}
    for a in ARMS:
        for mode in ('bounded', 'think'):
            body = manifest['rendered'][a][mode]
            assert body['temperature'] == 0 and body['cache_prompt'] is False
            assert body['reasoning_effort'] == 'none'
            assert body['response_format']['type'] == 'json_schema'
    assert repr(sources) == before


@pytest.mark.parametrize('field,value', [
    ('instruction', 'changed'), ('focus', 'changed'), ('intent_id', 'changed'),
    ('think_allowed', False), ('soft_wall_time_budget_s', 2),
    ('request_id', 'changed'), ('context', ()),
])
def test_changed_source_rejected(sources, field, value):
    with pytest.raises(W4ModelABBlocked):
        build_arms(replace(sources[0], **{field: value}), sources[1])


@pytest.mark.parametrize('kind', ['choices', 'order', 'observer', 'reference', 'source', 'extra'])
def test_fixed_choices_context_and_bundle_rejected(sources, kind):
    arms = build_arms(*sources)
    b = arms['B']
    if kind in ('choices', 'order'):
        b = replace(b, choices=b.choices[::-1] if kind == 'order' else (
            replace(b.choices[0], description='changed'), b.choices[1]))
    else:
        context = list(b.context)
        if kind == 'observer':
            v = json.loads(context[0].value_json)
            v['session_id'] = 'foreign'
            context[0] = CognitionDatum.from_value(context[0].key, v, context[0].provenance)
        elif kind in ('reference', 'source'):
            p = context[1].provenance
            context[1] = replace(context[1], provenance=Provenance(
                'other' if kind == 'source' else p.source,
                'foreign' if kind == 'reference' else p.reference))
        else:
            context.append(context[-1])
        b = replace(b, context=tuple(context))
    arms['B'] = b
    with pytest.raises(W4ModelABBlocked):
        validate_arms(arms)


def setup_run(sources, tmp_path):
    arms = build_arms(*sources)
    frozen = tmp_path/'frozen.json'
    sha = freeze_requests(arms, model='test', output=frozen)
    return dict(arms=arms, frozen=frozen, frozen_sha256=sha, output=tmp_path/'result.json')


@pytest.mark.parametrize('unresolved', [False, True])
def test_order_call_ceiling_think_and_journal(sources, tmp_path, unresolved):
    kwargs = setup_run(sources, tmp_path)
    seen = []
    def provider(request, *, mode):
        seen.append(mode)
        return (ProviderDecision.unresolved() if unresolved
                else ProviderDecision.resolved('DEFER_RECHECK'))
    result = execute_factorial(provider=provider, **kwargs)
    assert len(result['rows']) == 20
    assert result['provider_calls'] == (40 if unresolved else 20)
    assert [r['arm'] for r in result['rows']] == [a for order in ORDER for a in order]
    scored = [r for r in result['rows'] if not r['warmup']]
    assert all(sum(r['arm'] == a for r in scored) == 4 for a in ARMS)
    assert all({ORDER[i][p] for i in range(1, 5)} == set(ARMS) for p in range(4))
    assert seen.count(CognitionMode.THINK) == (20 if unresolved else 0)
    journal = tmp_path/'result.json.journal.jsonl'
    assert hashlib.sha256(journal.read_bytes()).hexdigest() == result['journal_sha256']
    assert len([r for r in map(json.loads, journal.read_text().splitlines())
                if r['event'] == 'provider']) == len(seen)


@pytest.mark.parametrize('error', [LlamaCppProviderError('failed'), KeyboardInterrupt()])
def test_failure_cancel_retains_first_terminal(sources, tmp_path, error):
    kwargs = setup_run(sources, tmp_path)
    before = kwargs['frozen'].read_bytes()
    def provider(request, *, mode):
        raise error
    with pytest.raises(type(error)):
        execute_factorial(provider=provider, **kwargs)
    result = json.loads(kwargs['output'].read_bytes())
    assert result['classification'] == 'DEV_FAIL'
    assert result['provider_calls'] == len(result['rows']) == 1
    assert result['calls'][0]['error_type'] == type(error).__name__
    assert kwargs['frozen'].read_bytes() == before
    with pytest.raises(W4ModelABBlocked):
        execute_factorial(provider=provider, **kwargs)


@pytest.mark.parametrize('existing', ['result.json', 'result.json.journal.jsonl'])
def test_exclusive_before_provider(sources, tmp_path, existing):
    kwargs = setup_run(sources, tmp_path)
    (tmp_path/existing).write_text('immutable')
    with pytest.raises(W4ModelABBlocked):
        execute_factorial(provider=lambda *a, **k: pytest.fail('called'), **kwargs)
    assert (tmp_path/existing).read_text() == 'immutable'
    with pytest.raises(W4ModelABBlocked):
        freeze_requests(kwargs['arms'], model='test', output=kwargs['frozen'])


def test_changed_frozen_manifest_rejected(sources, tmp_path):
    kwargs = setup_run(sources, tmp_path)
    kwargs['frozen'].write_bytes(kwargs['frozen'].read_bytes() + b' ')
    with pytest.raises(W4ModelABBlocked):
        execute_factorial(provider=lambda *a, **k: pytest.fail('called'), **kwargs)
