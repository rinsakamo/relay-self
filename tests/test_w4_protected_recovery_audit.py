"""Versioned DEV adoption: historical path provenance and exact current bytes.

The historical pins remain in the original W4 lease test. Approval authorizes
inspection/adoption, not runtime success. No network or World is used here.
"""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from test_self_world_stage_w4_lease import PROTECTED_BLOBS

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'docs/w4-protected-adoption-v2.json'
HISTORICAL_SOURCE = '1473c74e4448bb9a527747de0619c8e55ffbd827'
ACCEPTED_SOURCE = 'f34ccc0bf86f271849034c21abd254e5e3de780f'
ADOPTED = frozenset('adapters/mineflayer/' + name for name in (
    'process_session.py', 's31a_real_server_ci.py',
    's34_native_world_cognition_ci.py', 's49_normal_session_real_ci.py',
))
APPROVALS = {
    6356863445: 'https://github.com/rinsakamo/relay-self/issues/633#issuecomment-6356863445',
    6356864256: 'https://github.com/rinsakamo/relay-self/pull/634#issuecomment-6356864256',
}
APPROVAL_BODY_SHA256 = '929e3af21189bd45bafcf015dbac2f0f052babbacd1fac93369b6a3d3a9e16a2'


def git(*args, root=ROOT):
    return subprocess.check_output(['git', *args], cwd=root)


def load_manifest():
    return json.loads(MANIFEST.read_text())


def validate_authority(manifest):
    assert manifest['schema'] == 'W4_PROTECTED_BLOB_ADOPTION_V2'
    assert manifest['version'] == 'v2'
    assert manifest['historical_source_commit'] == HISTORICAL_SOURCE
    assert manifest['effective_source_head'] == ACCEPTED_SOURCE
    assert manifest['classification'] == [
        'DEV_ONLY', 'QUALIFICATION_NO_GO', 'SCIENCE_NOT_RUN', 'NO_NEW_WORLD_RUN',
    ]
    approvals = manifest['approvals']
    assert len(approvals) == 2
    assert {a['id'] for a in approvals} == set(APPROVALS)
    for a in approvals:
        assert a['user'] == 'rinsakamo' and a['url'] == APPROVALS[a['id']]
        assert a['body_sha256'] == APPROVAL_BODY_SHA256
        assert hashlib.sha256(a['body'].encode()).hexdigest() == APPROVAL_BODY_SHA256
    rows = manifest['files']
    assert len(rows) == 19
    assert {r['path'] for r in rows} == set(PROTECTED_BLOBS)
    assert {r['path'] for r in rows if 'prospective_git_blob' in r} == ADOPTED
    for row in rows:
        path = row['path']
        assert row['historical_source_commit'] == HISTORICAL_SOURCE, path
        assert row['historical_path'] == path, path
        assert row['historical_git_blob'] == PROTECTED_BLOBS[path], path
        if path in ADOPTED:
            assert row['version'] == 'v2' and row['owner'] == 'rinsakamo', path
            assert row['effective_source_head'] == ACCEPTED_SOURCE, path
            assert set(row['approval_urls']) == set(APPROVALS.values()), path
            assert row['reason'] and row['related_tests'], path
            assert all((ROOT / p).is_file() for p in row['related_tests']), path


def validate_historical(manifest, *, root=ROOT):
    validate_authority(manifest)
    for row in manifest['files']:
        path = row['path']
        spec = row['historical_source_commit'] + ':' + row['historical_path']
        assert git('cat-file', '-t', spec, root=root).strip() == b'blob', path
        assert git('rev-parse', spec, root=root).decode().strip() == row['historical_git_blob'], path
        # Read the real object, not merely an arbitrary object with this SHA.
        raw = git('cat-file', 'blob', spec, root=root)
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == PROTECTED_BLOBS[path], path


def validate_current(manifest, *, root=ROOT, contents=None):
    validate_authority(manifest)
    for row in manifest['files']:
        path = row['path']
        raw = (root / path).read_bytes() if contents is None else contents[path]
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        if path in ADOPTED:
            # Anchor reviewed bytes to the existing local candidate as well as
            # the manifest: editing both current bytes and manifest cannot pass.
            accepted = git('rev-parse', ACCEPTED_SOURCE + ':' + path, root=root).decode().strip()
            assert row['prospective_git_blob'] == accepted, path
            assert blob == accepted, path
            assert hashlib.sha256(raw).hexdigest() == row['prospective_content_sha256'], path
        else:
            assert blob == PROTECTED_BLOBS[path], path


def validate_adoption(*, root=ROOT):
    manifest = load_manifest()
    validate_historical(manifest, root=root)
    validate_current(manifest, root=root)


def test_a_historical_original_commit_path_and_all_19_blobs():
    validate_historical(load_manifest())


def test_b_unchanged_15_and_c_adopted_four_blob_and_sha256():
    validate_current(load_manifest())


def test_d_authority_and_original_owner_identities():
    from adapters.mineflayer import s31a_real_server_ci as s31a
    from adapters.mineflayer import s34_native_world_cognition_ci as s34
    from adapters.mineflayer import s49_normal_session_real_ci as s49
    from adapters.mineflayer.process_session import MineflayerProcessSession

    validate_authority(load_manifest())
    assert s49._new_session is s34._new_session
    assert s49._ready_server is s31a._ready_server
    assert s34.MineflayerProcessSession is MineflayerProcessSession
    assert MineflayerProcessSession.receive.__module__ == 'adapters.mineflayer.process_session'
    # Current bytes pin sole collector/reader; remaining 15 pin Action/S10.
    validate_current(load_manifest())


@pytest.mark.parametrize('path', tuple(PROTECTED_BLOBS))
def test_reject_each_falsified_original_sha(path):
    manifest = load_manifest()
    next(r for r in manifest['files'] if r['path'] == path)['historical_git_blob'] = '0' * 40
    with pytest.raises(AssertionError, match=path):
        validate_historical(manifest)


@pytest.mark.parametrize('field,value', [
    ('historical_source_commit', ACCEPTED_SOURCE),
    ('historical_path', 'src/relay_self/action.py'),
])
def test_reject_source_commit_substitution_and_wrong_history_path(field, value):
    manifest = load_manifest()
    manifest['files'][0][field] = value
    with pytest.raises(AssertionError):
        validate_historical(manifest)


@pytest.mark.parametrize('path', tuple(PROTECTED_BLOBS))
def test_reject_each_current_mutation_including_s18_action_s10(path):
    contents = {p: (ROOT / p).read_bytes() for p in PROTECTED_BLOBS}
    contents[path] += b'\n# unauthorized mutation\n'
    with pytest.raises(AssertionError, match=path):
        validate_current(load_manifest(), contents=contents)


@pytest.mark.parametrize('field', ['prospective_git_blob', 'prospective_content_sha256'])
def test_reject_manifest_new_hash_mismatch(field):
    manifest = load_manifest()
    row = next(r for r in manifest['files'] if r['path'] in ADOPTED)
    row[field] = '0' * len(row[field])
    with pytest.raises(AssertionError, match=row['path']):
        validate_current(manifest)


def test_reject_coordinated_unreviewed_source_and_manifest_mutation():
    manifest = load_manifest()
    row = next(r for r in manifest['files'] if r['path'] in ADOPTED)
    contents = {p: (ROOT / p).read_bytes() for p in PROTECTED_BLOBS}
    raw = contents[row['path']] + b'\n# unreviewed\n'
    contents[row['path']] = raw
    row['prospective_git_blob'] = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    row['prospective_content_sha256'] = hashlib.sha256(raw).hexdigest()
    with pytest.raises(AssertionError, match=row['path']):
        validate_current(manifest, contents=contents)


@pytest.mark.parametrize('mutation', ['missing', 'foreign_owner', 'body', 'unlisted_path', 'adopt_action', 'missing_row_approval'])
def test_reject_missing_or_invalid_authority_and_unlisted_path(mutation):
    manifest = copy.deepcopy(load_manifest())
    if mutation == 'missing':
        manifest['approvals'] = []
    elif mutation == 'foreign_owner':
        manifest['approvals'][0]['user'] = 'other'
    elif mutation == 'body':
        manifest['approvals'][0]['body'] += ' altered'
    elif mutation == 'unlisted_path':
        manifest['files'].append(dict(manifest['files'][0], path='unlisted.py'))
    elif mutation == 'adopt_action':
        next(r for r in manifest['files'] if r['path'] == 'src/relay_self/action.py')['prospective_git_blob'] = '0' * 40
    else:
        next(r for r in manifest['files'] if r['path'] in ADOPTED)['approval_urls'] = []
    with pytest.raises(AssertionError):
        validate_adoption_manifest_for_negative(manifest)


def validate_adoption_manifest_for_negative(manifest):
    validate_historical(manifest)
    validate_current(manifest)
