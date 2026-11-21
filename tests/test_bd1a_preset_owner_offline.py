"""Synthetic CPU/offline checks of original owner checkpoint and recovery."""
import hashlib
import json
import subprocess
import sys
from dataclasses import replace

import pytest

from relay_self.cognitive_minimal_dev import AcceptedSkillPreset, PresetAcceptanceReceipt
from relay_self.coordinated_checkpoint_dev import restore_generation
from relay_self.preset_registry_checkpoint import decode_pattern_registry, encode_pattern_registry
from relay_self.provenance import Provenance
from relay_self.self_owner_checkpoint_dev import verify_typed_generation
from relay_self.skill_invocation import SkillBudget, SkillConstraints, SkillParameterPreset
from test_checkpointed_cognitive_runtime_dev import RuntimeFixture


def _preset_registry(owner):
    prov = Provenance('offline-synthetic', owner.self_id)
    preset = SkillParameterPreset('hunger-eat', 'Bread', 1, 'skill:EAT:1',
                                  SkillConstraints(), SkillBudget(2, 1000), prov)
    receipt = PresetAcceptanceReceipt(owner.self_id, 'accept-' + owner.self_id,
                                     preset.preset_ref, prov)
    return replace(owner.pattern_registry, revision=1,
                   accepted_presets=(AcceptedSkillPreset(1, preset, receipt),))


def test_preset_original_owner_capture_fresh_process_restore(tmp_path):
    f = RuntimeFixture(tmp_path)
    f.baseline()
    for owner in f.owners:
        owner.pattern_registry = _preset_registry(owner)
    result = f.runtime.run_if_due(0.0)
    generation = result.generation
    cuts = verify_typed_generation(generation)
    assert [c.self_id for c in cuts] == ['A', 'B']
    dest = tmp_path / 'restore'
    restore_generation(generation, dest, restore_id='offline-bd1a')
    files = sorted(p for p in generation.rglob('*') if p.is_file())
    hashes = {str(p.relative_to(generation)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    script = '''
import hashlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "src"))
from relay_self.checkpointed_cognitive_runtime_dev import staged_recover_cognition_cohort
from relay_self.self_owner_checkpoint_dev import verify_typed_generation
from relay_self.stage28_cognitive_recovery_gate_dev import stage28_inert_cognitive_recovery
g, d = map(Path, sys.argv[1:])
cuts = verify_typed_generation(g)
owners = staged_recover_cognition_cohort(g, d)
plan = stage28_inert_cognitive_recovery(g, d, expected_self_ids=("A", "B"), expected_source_world_id="world-1")
assert not plan.old_l1_decision_reusable and not plan.physical_action_issue_authorized
assert [(x.semantic.cut.world_id, x.semantic.cut.generation_id, x.self_id) for x in owners] == [("world-1", g.name, "A"), ("world-1", g.name, "B")]
for c, o in zip(cuts, owners):
 assert o.retained.identity.self_id == c.self_id
 assert o.retained.pattern_registry == c.pattern_registry == o.semantic.pattern_registry
 assert c.pattern_registry.accepted_presets[0].receipt.self_id == c.self_id
 assert o.semantic.intent.current_intent.intent_id == "goal-" + c.self_id
 assert len(o.semantic.skill_histories) == 1 and len(c.peer_deliveries) == 1
 assert not o.issue_authorized and not o.native_session_bound
 assert not o.semantic.old_skill_resume_authorized and not o.semantic.new_physical_action_issue_authorized
print(json.dumps({str(p.relative_to(g)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(g.rglob("*")) if p.is_file()}, sort_keys=True))
'''
    proc = subprocess.run([sys.executable, '-c', script, str(generation), str(dest)],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout) == hashes
    assert all(json.loads((generation / 'selves' / sid / 'owner-state.json').read_text())['payload']['schema'] == 2 for sid in ('A', 'B'))


@pytest.mark.parametrize('mutation', ['digest', 'self', 'missing_pattern', 'receipt'])
def test_registry_rejects_tamper(tmp_path, mutation):
    f = RuntimeFixture(tmp_path)
    reg = _preset_registry(f.owners[0])
    wire = encode_pattern_registry(reg, self_id='A')
    if mutation == 'digest':
        wire['accepted_presets'][0]['preset']['version'] = 2
    if mutation == 'self':
        wire['self_id'] = 'B'
    if mutation == 'missing_pattern':
        wire['patterns'] = []
    if mutation == 'receipt':
        wire['accepted_presets'][0]['receipt']['event_id'] = ''
    # Re-sign the envelope so structural and per-Preset validation are exercised,
    # independently of the outer registry checksum.
    body = {k: v for k, v in wire.items() if k != 'registry_ref'}
    wire['registry_ref'] = 'schema-registry:v2@' + hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    ).hexdigest()
    with pytest.raises(ValueError):
        decode_pattern_registry(wire, expected_self_id='A')


@pytest.mark.parametrize('fault', ['foreign_self', 'revision', 'swap', 'missing_cognition', 'uncommitted'])
def test_precommit_rejects_inconsistent_cohort(tmp_path, fault):
    from relay_self.persistent_cognition import load_persistent_cognition, save_persistent_cognition
    from relay_self.self_owner_checkpoint_dev import save_self_owner_cut
    from test_self_owner_checkpoint_dev import _capture, _fixture

    world, store, specs, cuts = _fixture(tmp_path)
    for spec, cut in zip(specs, cuts):
        owner = type('Owner', (), {'self_id': cut.self_id, 'pattern_registry': cut.pattern_registry})()
        registry = _preset_registry(owner)
        cognition = load_persistent_cognition(spec.cognition_file)
        save_persistent_cognition(spec.cognition_file, replace(cognition, pattern_registry=registry))
        spec.owner_state_file.unlink()
        save_self_owner_cut(spec.owner_state_file, replace(
            cut, pattern_registry=registry,
            cognition_sha256=hashlib.sha256(spec.cognition_file.read_bytes()).hexdigest()))
    if fault == 'foreign_self':
        data = specs[1].cognition_file.read_bytes()
        specs[0].cognition_file.write_bytes(data)
    elif fault == 'revision':
        cognition = load_persistent_cognition(specs[0].cognition_file)
        save_persistent_cognition(specs[0].cognition_file, replace(
            cognition, pattern_registry=replace(cognition.pattern_registry, revision=99)))
        from relay_self.self_owner_checkpoint_dev import load_self_owner_cut
        cut = load_self_owner_cut(specs[0].owner_state_file)
        specs[0].owner_state_file.unlink()
        save_self_owner_cut(specs[0].owner_state_file, replace(
            cut, cognition_sha256=hashlib.sha256(specs[0].cognition_file.read_bytes()).hexdigest()))
    elif fault == 'swap':
        a, b = [s.cognition_file.read_bytes() for s in specs]
        specs[0].cognition_file.write_bytes(b)
        specs[1].cognition_file.write_bytes(a)
    elif fault == 'missing_cognition':
        specs[0].cognition_file.unlink()
    elif fault == 'uncommitted':
        generation = _capture(world, store, specs)
        (generation / 'COMMITTED.json').unlink()
        with pytest.raises(Exception):
            verify_typed_generation(generation)
        return
    with pytest.raises(Exception):
        _capture(world, store, specs)
    assert not (store / 'g-000000000001' / 'COMMITTED.json').exists()


def test_mixed_generation_owner_cognition_holds_before_commit(tmp_path):
    from relay_self.coordinated_checkpoint_dev import SelfSnapshotSource
    from relay_self.persistent_cognition import load_persistent_cognition, save_persistent_cognition
    from relay_self.self_owner_checkpoint_dev import save_self_owner_cut
    from test_self_owner_checkpoint_dev import _capture, _fixture

    world, store, specs, cuts = _fixture(tmp_path)
    for spec, cut in zip(specs, cuts):
        owner = type('Owner', (), {'self_id': cut.self_id, 'pattern_registry': cut.pattern_registry})()
        reg = _preset_registry(owner)
        save_persistent_cognition(spec.cognition_file, replace(
            load_persistent_cognition(spec.cognition_file), pattern_registry=reg))
        spec.owner_state_file.unlink()
        save_self_owner_cut(spec.owner_state_file, replace(
            cut, pattern_registry=reg,
            cognition_sha256=hashlib.sha256(spec.cognition_file.read_bytes()).hexdigest()))
    first = _capture(world, store, specs)
    for spec in specs:
        cut = next(c for c in verify_typed_generation(first) if c.self_id == spec.self_id)
        cognition = load_persistent_cognition(spec.cognition_file)
        save_persistent_cognition(spec.cognition_file, replace(
            cognition, identity=replace(cognition.identity, directives=('later generation',))))
        spec.owner_state_file.unlink()
        save_self_owner_cut(spec.owner_state_file, replace(
            cut, generation_id='g-000000000002',
            cognition_sha256=hashlib.sha256(spec.cognition_file.read_bytes()).hexdigest()))
    old_a = first / 'selves' / 'A' / 'cognition.json'
    mixed = (SelfSnapshotSource('A', old_a, specs[0].physical_wal_file, specs[0].owner_state_file), specs[1])
    with pytest.raises(ValueError, match='cognition digest mismatch'):
        _capture(world, store, mixed, sequence=2)
    assert not (store / 'g-000000000002' / 'COMMITTED.json').exists()


def test_freeze_write_failure_keeps_cohort_held(tmp_path, monkeypatch):
    from relay_self import checkpointed_cognitive_runtime_dev as runtime

    f = RuntimeFixture(tmp_path)
    for owner in f.owners:
        owner.pattern_registry = _preset_registry(owner)
    def fail(*args, **kwargs):
        raise OSError('synthetic write failure')
    monkeypatch.setattr(runtime, 'save_persistent_cognition', fail)
    with pytest.raises(Exception):
        f.runtime.run_if_due(0.0)
    assert f.runtime.held_after_failure
    assert not f.gate_open
    assert not (f.store / 'g-000000000000' / 'COMMITTED.json').exists()


def test_pattern_only_owner_keeps_schema1_layout(tmp_path):
    from relay_self.self_owner_checkpoint_dev import load_self_owner_cut
    from test_self_owner_checkpoint_dev import _capture, _fixture

    world, store, specs, cuts = _fixture(tmp_path)
    for spec, cut in zip(specs, cuts):
        payload = json.loads(spec.owner_state_file.read_text())['payload']
        assert payload['schema'] == 1
        assert set(payload['pattern_registry']) == {'revision', 'patterns'}
        assert load_self_owner_cut(spec.owner_state_file) == cut
    assert verify_typed_generation(_capture(world, store, specs)) == cuts
