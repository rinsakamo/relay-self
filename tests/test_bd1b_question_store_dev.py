"""Synthetic owner admission tests: no Self decision issuer is attested."""
from dataclasses import replace

import pytest

import relay_self.bd1b_question_store_dev as store
from relay_self.exploration_continuity_dev import (
    AttemptPhase,
    AttemptRecord,
    ExplorationContinuity,
    QuestionRecord,
    _attempt_ref,
)
from relay_self.persistent_cognition import load_persistent_cognition, save_persistent_cognition
from relay_self.provenance import Provenance
from test_bd1b_owner_present_dev import _configured


def args(case, sid="A"):
    _, bridge, boot, world, links, _ = case
    resident = bridge.cognitive_work
    kw = dict(bridge=bridge, boot=boot, world=world, links=links, self_id=sid)
    return resident, kw, resident.read_coverage_inquiry_cpu(**kw)


def commit(resident, kw, inquiry, revision=0):
    # Explicit controlled test admission, not production decision authentication.
    return store._store_admitted_inquiry(resident, **kw, inquiry=inquiry,
                                         expected_revision=revision)


def test_original_owner_ab_history_and_duplicate(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    resident, kw, inquiry = args(case)
    owner = resident.owners['A']
    digest = 'a' * 64
    attempt = AttemptRecord(_attempt_ref('A', 'old', digest), 'old', digest,
                            AttemptPhase.RESERVED, Provenance('test', 'owner'))
    history = ExplorationContinuity('A', 4, (QuestionRecord('old', Provenance('test', 'old')),),
                                    (attempt,))
    owner.retained = replace(owner.retained, exploration_continuity=history)
    owner.pending_questions.update({'old', 'unrelated'})
    save_persistent_cognition(owner.files.cognition_file, owner.retained)
    before = (owner.intent, dict(owner.skills), owner.files.physical_wal_file.read_bytes())
    result = commit(resident, kw, inquiry, 4)
    assert result == load_persistent_cognition(owner.files.cognition_file)
    assert result.exploration_continuity.revision == 5
    assert result.exploration_continuity.questions[0] == history.questions[0]
    assert result.exploration_continuity.attempts == history.attempts
    assert owner.pending_questions == {'old', 'unrelated', inquiry.question_ref}
    assert commit(resident, kw, inquiry, 5) == result
    assert len(result.exploration_continuity.questions) == 2
    assert (owner.intent, owner.skills, owner.files.physical_wal_file.read_bytes()) == before
    rb, kb, ib = args(case, 'B')
    b = commit(rb, kb, ib)
    assert b == load_persistent_cognition(rb.owners['B'].files.cognition_file)
    assert b.exploration_continuity.revision == 1
    assert rb.owners['B'].pending_questions == {ib.question_ref}


@pytest.mark.parametrize('variant', ['foreign', 'stale', 'revision', 'epoch', 'fenced'])
def test_stale_and_foreign_refused(tmp_path, monkeypatch, variant):
    case = _configured(tmp_path, monkeypatch, need=True)
    resident, kw, inquiry = args(case)
    owner = resident.owners['A']
    before = (owner.retained, set(owner.pending_questions), owner.files.cognition_file.read_bytes())
    revision = 0
    if variant == 'foreign':
        inquiry = args(case, 'B')[2]
    elif variant == 'stale':
        inquiry = replace(inquiry, source_revision_refs=('stale',))
    elif variant == 'revision':
        revision = 2
    elif variant == 'epoch':
        resident._states['A'].world_epoch += 1
    else:
        resident.fence_self('A')
    with pytest.raises((ValueError, RuntimeError)):
        commit(resident, kw, inquiry, revision)
    assert (owner.retained, owner.pending_questions, owner.files.cognition_file.read_bytes()) == before


@pytest.mark.parametrize('variant', ['missing', 'tamper', 'symlink', 'write', 'after_replace', 'readback'])
def test_bad_file_and_uncertain_write_fence(tmp_path, monkeypatch, variant):
    case = _configured(tmp_path, monkeypatch, need=True)
    resident, kw, inquiry = args(case)
    owner = resident.owners['A']
    before = (owner.retained, set(owner.pending_questions))
    path = owner.files.cognition_file
    if variant == 'missing':
        path.unlink()
    elif variant == 'tamper':
        path.write_text('{}')
    elif variant == 'symlink':
        path.unlink()
        path.symlink_to(tmp_path / 'target')
    elif variant == 'write':
        monkeypatch.setattr(store, 'save_persistent_cognition', lambda *a: (_ for _ in ()).throw(OSError('write')))
    elif variant == 'after_replace':
        original_save = store.save_persistent_cognition
        def write_then_fail(path, cognition):
            original_save(path, cognition)
            raise OSError('after replace')
        monkeypatch.setattr(store, 'save_persistent_cognition', write_then_fail)
    else:
        original = store.load_persistent_cognition
        calls = 0
        def fail_readback(path):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError('readback')
            return original(path)
        monkeypatch.setattr(store, 'load_persistent_cognition', fail_readback)
    with pytest.raises((OSError, ValueError, RuntimeError)):
        commit(resident, kw, inquiry)
    assert (owner.retained, owner.pending_questions) == before
    assert resident._states['A'].mode == 'QUARANTINED'
    if variant in ('readback', 'after_replace'):
        assert load_persistent_cognition(path) != before[0]


def test_no_external_adopt_entry_or_caller_supplied_record(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    resident, kw, inquiry = args(case)
    owner = resident.owners['A']
    before = (owner.retained, set(owner.pending_questions), owner.files.cognition_file.read_bytes())
    assert not hasattr(resident, 'adopt_coverage_inquiry')
    with pytest.raises(TypeError):
        store._store_admitted_inquiry(resident, **kw, inquiry=inquiry,
                                      expected_revision=0, decision='ADOPT')
    with pytest.raises(store.QuestionStoreHold):
        commit(resident, kw, QuestionRecord(inquiry.question_ref, Provenance('external', 'fake')))
    assert (owner.retained, owner.pending_questions, owner.files.cognition_file.read_bytes()) == before


def test_missing_pending_ref_refused(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    resident, kw, inquiry = args(case)
    owner = resident.owners['A']
    state = ExplorationContinuity('A', 1, (QuestionRecord('old', Provenance('test', 'old')),))
    owner.retained = replace(owner.retained, exploration_continuity=state)
    save_persistent_cognition(owner.files.cognition_file, owner.retained)
    with pytest.raises(store.QuestionStoreHold):
        commit(resident, kw, inquiry, 1)
