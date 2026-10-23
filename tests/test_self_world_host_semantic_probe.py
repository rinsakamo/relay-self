"""Host projection negative controls, synthetic source only. No model launcher."""
import copy
import hashlib
import json
from dataclasses import replace

import pytest

from adapters.mineflayer.self_world_observation_only_epoch_replay import (
    replay_w4_saved_self_world_epochs,
)
from experiments import self_world_host_semantic_probe as probe
from experiments import self_world_model_ab as original
from experiments.self_world_metadata_ablation import canonical
from relay_self.relay_engine import CognitionMode, ProviderDecision
from test_self_world_observation_only_epoch_replay import _case, _pin


@pytest.fixture
def setup(tmp_path, monkeypatch):
    source = tmp_path / 'source'
    report = _case(source)
    pins = _pin(source, report)

    def fake_real(root):
        replay = replay_w4_saved_self_world_epochs(**pins)
        return original.CognitionCase(
            'w4-original-empty', original.prepare_w4_offline_cognition_inputs(replay),
            'DEFER_RECHECK', 'DEFER_RECHECK', 'SYNTHETIC_DEV')

    monkeypatch.setattr(original, 'build_real_case', fake_real)
    root = tmp_path / 'evidence'
    root.mkdir()
    frozen = root / 'frozen.json'
    sha = probe.freeze(source, model='test-model', output=frozen)
    return dict(source_root=source, frozen=frozen, frozen_sha256=sha,
                output=root / 'execution.json')


def test_semantics_and_identity_blinding(setup):
    sources = probe.load_sources(setup['source_root'])
    for case, replay in sources:
        for epoch in ('prior', 'following'):
            raw = getattr(case.prepared, epoch + '_bounded')
            sem = probe.project(replay, epoch)
            assert replace(sem, request_id=raw.request_id, context=raw.context) == raw
            assert sem.request_id == probe.REQUEST_ID
            assert sem.context[0].provenance == probe.PSEUDO
            payload = json.loads(sem.context[0].value_json)
            positive = payload['positive_observed_entities']
            assert payload['positive_observed_count'] == len(positive)
            assert all(e['origin'] == 'observed' for e in positive)
            assert payload['action_success'] is None
            assert 'UNKNOWN' in payload['uncertainty']
            text = canonical(payload).decode()
            for key in ('self_id', 'session_id', 'epoch_id', 'source_ref', 'entity_ref',
                        'scenario_id', 'target_ref', 'prior_source', 'later_source'):
                assert key not in text
            for value in (replay.prior.self_id, replay.prior.session_id,
                          replay.prior.epoch_id, raw.request_id):
                assert value not in canonical(probe.asdict(sem)).decode()
            if epoch == 'following' and case.case_id == 'unknown':
                assert positive == []
                assert payload['prediction_review']['observed_value'] is None
                assert payload['prediction_review']['predicted_value'] == 'zombie'
                assert payload['prediction_review']['status'] == 'undetermined'
            if epoch == 'following' and case.case_id == 'mismatch':
                assert positive[0]['label'] == 'skeleton'
                assert payload['prediction_review']['predicted_value'] == 'zombie'
                assert payload['prediction_review']['observed_value'] == 'skeleton'


@pytest.mark.parametrize('attack', ['missing_source', 'foreign_self', 'foreign_session',
                                  'stale', 'private', 'forged_ATT', 'forged_PRD'])
def test_replay_mutation_rejected(setup, attack):
    _, replay = probe.load_sources(setup['source_root'])[1]
    before = replay.prior
    if attack == 'missing_source':
        before = replace(before, observation=None)
    elif attack == 'foreign_self':
        before = replace(before, self_id='foreign')
    elif attack == 'foreign_session':
        before = replace(before, session_id='foreign')
    elif attack == 'stale':
        before = replace(before, observation=replace(before.observation, native_seq=99))
    elif attack == 'private':
        before = replace(before, memories=('foreign-private',))
    elif attack == 'forged_ATT':
        replay = replace(replay, prior_attention=replay.following_attention)
    elif attack == 'forged_PRD':
        replay = replace(replay, prediction_review=replace(
            replay.prediction_review, observed_value='invented'))
    with pytest.raises(ValueError):
        probe.project(replace(replay, prior=before), 'following')


@pytest.mark.parametrize('attack', ['metadata', 'private', 'invented_observation',
                                  'unknown_absence', 'predicted_observed', 'manifest',
                                  'order', 'budget', 'instruction', 'pseudo_source'])
def test_manifest_payload_substitution_rejected_before_provider(setup, attack):
    plan = json.loads(setup['frozen'].read_bytes())
    datum = plan['epochs'][7]['requests']['SEM']['context'][0]
    payload = json.loads(datum['value_json'])
    if attack == 'metadata':
        payload['session_id'] = 'leak'
    elif attack == 'private':
        payload['private_memory'] = 'foreign'
    elif attack == 'invented_observation':
        payload['positive_observed_entities'].append({'label': 'invented'})
    elif attack == 'unknown_absence':
        payload['absence'] = True
    elif attack == 'predicted_observed':
        payload['prediction_review']['observed_value'] = 'zombie'
    elif attack == 'manifest':
        plan['epochs'][0]['source_receipt']['run_id'] = 'foreign'
    elif attack == 'order':
        plan['schedule'] = plan['schedule'][::-1]
    elif attack == 'budget':
        plan['max_provider_calls'] = 201
    elif attack == 'instruction':
        plan['epochs'][0]['requests']['SEM']['instruction'] = 'different'
    elif attack == 'pseudo_source':
        datum['provenance']['source'] = 'mineflayer'
    datum['value_json'] = json.dumps(payload)
    setup['frozen'].write_bytes(canonical(plan))
    # Even replacing the claimed outer SHA cannot substitute a source/SEM plan.
    setup['frozen_sha256'] = hashlib.sha256(setup['frozen'].read_bytes()).hexdigest()
    with pytest.raises(probe.Blocked):
        probe.execute(provider=lambda *a, **k: pytest.fail('provider called'), **setup)
    assert not setup['output'].exists()


@pytest.mark.parametrize('kind', ['deleted', 'modified'])
def test_original_source_mutation_rejected(setup, kind):
    source = setup['source_root'] / 'node.stdout.jsonl'
    if not source.exists():
        source = next(setup['source_root'].glob('*.jsonl'))
    if kind == 'deleted':
        source.unlink()
    else:
        source.write_bytes(source.read_bytes() + b'corrupt')
    with pytest.raises((ValueError, OSError)):
        probe.validate_frozen(setup['source_root'], setup['frozen'], setup['frozen_sha256'])


@pytest.mark.parametrize('unresolved', [False, True])
def test_exact_schedule_and_ceiling(setup, unresolved):
    def provider(request, *, mode):
        assert mode in (CognitionMode.BOUNDED, CognitionMode.THINK)
        return (ProviderDecision.unresolved() if unresolved else
                ProviderDecision.resolved('DEFER_RECHECK'))
    result = probe.execute(provider=provider, **setup)
    assert result['bounded_requests'] == 100
    assert result['provider_calls'] == (200 if unresolved else 100)
    schedule = json.loads(setup['frozen'].read_bytes())['schedule']
    assert [{k: row[k] for k in schedule[0]} for row in result['rows']] == schedule
    assert len([r for r in result['rows'] if not r['warmup']]) == 80
    assert hashlib.sha256(setup['output'].with_name(
        'execution.json.journal.jsonl').read_bytes()).hexdigest() == result['journal_sha256']
    with pytest.raises(probe.Blocked):
        probe.execute(provider=provider, **setup)


def test_original_failure_retained_no_retry(setup):
    def provider(request, *, mode):
        raise RuntimeError('retained-first-failure')
    with pytest.raises(RuntimeError, match='retained-first-failure'):
        probe.execute(provider=provider, **setup)
    result = json.loads(setup['output'].read_bytes())
    assert result['provider_calls'] == 1
    assert result['terminal']['error'] == 'retained-first-failure'
    assert len(result['rows']) == 1


@pytest.mark.parametrize('target', ['output', 'journal', 'source', 'repo', 'frozen'])
def test_path_collisions_before_provider(setup, target):
    if target == 'output':
        setup['output'].touch()
    elif target == 'journal':
        setup['output'].with_name('execution.json.journal.jsonl').touch()
    elif target == 'source':
        setup['output'] = setup['source_root'] / 'new.json'
    elif target == 'repo':
        setup['output'] = probe.Path(probe.__file__).resolve().parents[1] / 'new.json'
    else:
        setup['output'] = setup['frozen']
    with pytest.raises(probe.Blocked):
        probe.execute(provider=lambda *a, **k: pytest.fail('provider called'), **setup)


def test_source_receipt_changes_even_with_equivalent_semantics(setup):
    sources = list(probe.load_sources(setup['source_root']))
    case, replay = sources[1]
    sources[1] = (replace(case, prepared=replace(case.prepared, prior_selected=42)), replay)
    with pytest.raises(probe.Blocked):
        probe.make_plan(tuple(sources), 'test')
    changed = copy.deepcopy(json.loads(setup['frozen'].read_bytes()))
    changed['epochs'][0]['request_sha256']['SEM']['bounded'] = '0' * 64
    setup['frozen'].write_bytes(canonical(changed))
    with pytest.raises(probe.Blocked):
        probe.validate_frozen(setup['source_root'], setup['frozen'], setup['frozen_sha256'])


@pytest.mark.parametrize('option', ['--repeats', '--warmup-pairs', '--include-open',
                                    '--endpoint', '--max-provider-calls'])
def test_unregistered_arguments_rejected(option):
    with pytest.raises(SystemExit):
        probe.offline_args(['--source-root', '/tmp/source', '--model', 'test',
                            '--output', '/tmp/new', option, '999'])
