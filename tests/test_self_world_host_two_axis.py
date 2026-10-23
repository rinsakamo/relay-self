"""Host fact boundaries only; no engine or provider execution."""
from dataclasses import asdict, replace

import pytest

from experiments import self_world_host_two_axis as reader
from experiments.self_world_metadata_ablation import digest
from test_self_world_rubric_audit import sources as fixture_sources


@pytest.fixture
def sources(tmp_path, monkeypatch):
    return fixture_sources.__wrapped__(tmp_path, monkeypatch)


def read(sources, monkeypatch, case=2, epoch='following', pin=None):
    monkeypatch.setattr(reader.probe, 'load_sources', lambda _: sources)
    c, r = sources[case]
    return reader.read_epoch(None, case_id=c.case_id, epoch=epoch,
                             expected_source_digest=pin or digest(asdict(r)))


def test_ten_epochs(sources, monkeypatch):
    monkeypatch.setattr(reader.probe, 'load_sources', lambda _: sources)
    pins = {c.case_id: digest(asdict(r)) for c, r in sources}
    rows = reader.read_ten_epochs(None, pins)
    assert [(r['observation']['positive_selected_count'], r['prediction']['review_status'])
            for r in rows] == [(0, 'NO_REVIEW'), (0, 'NO_REVIEW'),
                               (1, 'NO_REVIEW'), (1, 'MATCH'),
                               (1, 'NO_REVIEW'), (1, 'MISMATCH'),
                               (1, 'NO_REVIEW'), (0, 'UNDETERMINED'),
                               (0, 'NO_REVIEW'), (0, 'NO_REVIEW')]
    for i in (2, 4, 6):
        assert rows[i]['prediction']['forecast_present_in_view']
        assert rows[i]['prediction']['prior_forecast_present']
    for r in rows:
        assert not r['observation']['world_absence_established']
        assert not r['observation']['world_safety_established']
        assert r['prediction']['action_success'] is None
        assert r['prediction']['reward'] is None
        o = dict(r['observation'])
        assert o.pop('source_bound_digest') == digest({'binding': r['binding'], 'observation': o})
        p = dict(r['prediction'])
        assert p.pop('source_bound_review_digest') == digest({'binding': r['binding'], 'prediction': p})


def test_mismatch_keeps_both_facts(sources, monkeypatch):
    r = read(sources, monkeypatch)
    assert r['observation']['selected_positive_observations'][0]['label'] == 'skeleton'
    assert r['observation']['source_verified']
    assert r['prediction']['review_status'] == 'MISMATCH'
    assert r['prediction']['predicted_value'] == 'zombie'
    assert r['prediction']['observed_value'] == 'skeleton'
    assert r['prediction']['compared_property'] == 'entity_label'
    assert r['observation']['observation_provenance']


@pytest.mark.parametrize('attack', ['pin', 'review', 'attention', 'self', 'stale', 'forecast'])
def test_fail_closed(sources, monkeypatch, attack):
    c, r = sources[2]
    if attack == 'review':
        r = replace(r, prediction_review=replace(r.prediction_review, observed_value='zombie'))
    elif attack == 'attention':
        r = replace(r, following_attention=r.prior_attention)
    elif attack == 'self':
        r = replace(r, following=replace(r.following, self_id='foreign'))
    elif attack == 'stale':
        r = replace(r, following=r.prior)
    elif attack == 'forecast':
        r = replace(r, following=replace(r.following, forecasts=r.prior.forecasts))
    changed = list(sources)
    changed[2] = (c, r)
    with pytest.raises(ValueError):
        read(changed, monkeypatch, pin='0' * 64 if attack == 'pin' else None)


@pytest.mark.parametrize('case,epoch', [('foreign', 'prior'), ('match', 'foreign')])
def test_foreign_identity(case, epoch):
    with pytest.raises(ValueError):
        reader.read_epoch(None, case_id=case, epoch=epoch, expected_source_digest='0' * 64)


def test_missing_pins():
    with pytest.raises(ValueError):
        reader.read_ten_epochs(None, {})
