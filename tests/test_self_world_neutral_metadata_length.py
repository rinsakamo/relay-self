"""Offline negative controls; no physical calls."""
import json
from dataclasses import replace

import pytest

from experiments.self_world_metadata_ablation import build_arms
from experiments.self_world_model_ab import _synthetic_cases
from experiments.self_world_neutral_metadata_length import (
    ARMS,
    ORDER,
    W4ModelABBlocked,
    execute_control,
    freeze_control,
    neutral,
    validate_control,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import CognitionDatum, ProviderDecision


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


def setup(sources, tmp_path):
    old = build_arms(*sources)
    arms = dict(zip(ARMS, (old['B'], old['D'], neutral(old['D'], 200), neutral(old['D'], 10))))
    frozen = tmp_path/'frozen.json'
    sha = freeze_control(arms, model='gemma4-12b-q4km', output=frozen,
                         token_evidence={'counts': dict(zip(ARMS, (486, 360, 486, 360)))})
    return dict(arms=arms, frozen=frozen, frozen_sha256=sha, output=tmp_path/'result.json')


@pytest.mark.parametrize('arm', ARMS)
def test_nonmetadata_changes_block(sources, tmp_path, arm):
    kwargs = setup(sources, tmp_path)
    kwargs['arms'][arm] = replace(kwargs['arms'][arm], request_id='foreign')
    with pytest.raises(W4ModelABBlocked):
        validate_control(kwargs['arms'])


def test_padding_and_count_gate(sources, tmp_path):
    kwargs = setup(sources, tmp_path)
    with pytest.raises(W4ModelABBlocked):
        neutral(kwargs['arms']['S'], 1025)
    with pytest.raises(W4ModelABBlocked):
        freeze_control(kwargs['arms'], model='test', output=tmp_path/'other.json',
                       token_evidence={'counts': {}})
    kwargs['arms']['NS'] = kwargs['arms']['NL']
    context = list(kwargs['arms']['NS'].context)
    value = json.loads(context[0].value_json)
    value['session_id'] = 'foreign'
    context[0] = CognitionDatum.from_value(context[0].key, value, context[0].provenance)
    kwargs['arms']['NS'] = replace(kwargs['arms']['NS'], context=tuple(context))
    with pytest.raises(W4ModelABBlocked):
        validate_control(kwargs['arms'])


@pytest.mark.parametrize('unresolved', (False, True))
def test_finite_order_and_fsync_journal(sources, tmp_path, unresolved):
    kwargs = setup(sources, tmp_path)
    def provider(request, *, mode):
        return ProviderDecision.unresolved() if unresolved else ProviderDecision.resolved('DEFER_RECHECK')
    result = execute_control(provider=provider, **kwargs)
    assert result['provider_calls'] == (40 if unresolved else 20)
    assert [r['arm'] for r in result['rows']] == [a for order in ORDER for a in order]
    with pytest.raises(W4ModelABBlocked):
        execute_control(provider=provider, **kwargs)


def test_error_retained(sources, tmp_path):
    kwargs = setup(sources, tmp_path)
    def provider(request, *, mode):
        raise RuntimeError('original')
    with pytest.raises(RuntimeError, match='original'):
        execute_control(provider=provider, **kwargs)
    result = json.loads(kwargs['output'].read_text())
    assert result['provider_calls'] == 1 and result['terminal']['error'] == 'original'
