"""Offline path/hash and fake child-environment checks; never invokes Node."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from experiments.epistemic_e12_native_owner import OriginalWireSession
from experiments.epistemic_e13_shared_runtime import (
    SharedRuntimeRejected,
    child_env,
    verify_node_files,
)


def files(tmp_path):
    root = tmp_path / 'external'
    adapter = tmp_path / 'source'
    root.mkdir()
    adapter.mkdir()
    for name in ('mineflayer', 'minecraft-protocol'):
        module = root / 'node_modules' / name
        module.mkdir(parents=True)
        (module / 'package.json').write_text(json.dumps({
            'version': '4.39.0' if name == 'mineflayer' else '1.68.0', 'main': 'index.js'}))
        (module / 'index.js').write_text('// synthetic offline file')
    source = Path(__file__).resolve().parents[1] / 'adapters/mineflayer'
    for name in ('package.json', 'package-lock.json'):
        (adapter / name).write_bytes((source / name).read_bytes())
        (root / name).write_bytes((source / name).read_bytes())
    return root, adapter


def test_explicit_external_paths_hashes_and_versions(tmp_path):
    root, adapter = files(tmp_path)
    result = verify_node_files(root, adapter)
    assert result['mineflayer']['version'] == '4.39.0'
    assert Path(result['minecraft-protocol']['entry']).is_relative_to(root)
    assert child_env(root, adapter)['RELAYSELF_RSEE_NODE_RUNTIME_ROOT'] == str(root)


@pytest.mark.parametrize('fault', ['lock', 'manifest', 'version', 'protocol-version',
                                  'root-symlink', 'module-symlink', 'entry-symlink',
                                  'missing', 'relative'])
def test_external_runtime_substitution_rejected(tmp_path, fault):
    root, adapter = files(tmp_path)
    if fault in ('lock', 'manifest'):
        (root / ('package-lock.json' if fault == 'lock' else 'package.json')).write_text('{}bad')
    elif fault in ('version', 'protocol-version'):
        name = 'mineflayer' if fault == 'version' else 'minecraft-protocol'
        (root / 'node_modules' / name / 'package.json').write_text('{"version":"0.0.0"}')
    elif fault == 'root-symlink':
        link = tmp_path / 'alias'
        link.symlink_to(root, target_is_directory=True)
        root = link
    elif fault == 'module-symlink':
        target = root / 'node_modules/minecraft-protocol'
        target.rename(tmp_path / 'escaped')
        target.symlink_to(tmp_path / 'escaped', target_is_directory=True)
    elif fault == 'entry-symlink':
        target = root / 'node_modules/mineflayer/index.js'
        target.unlink()
        target.symlink_to(adapter / 'package.json')
    elif fault == 'missing':
        (root / 'node_modules/minecraft-protocol/index.js').unlink()
    else:
        root = Path('relative')
    with pytest.raises((SharedRuntimeRejected, ValueError)):
        verify_node_files(root, adapter)


@pytest.mark.parametrize('variable', ['NODE_PATH', 'NODE_OPTIONS'])
def test_environment_overrides_reject_before_child_spawn(tmp_path, monkeypatch, variable):
    root, adapter = files(tmp_path)
    monkeypatch.setenv(variable, 'forbidden')
    with pytest.raises(SharedRuntimeRejected):
        child_env(root, adapter)


def test_original_owner_passes_only_verified_env_to_fake_child(tmp_path):
    import test_epistemic_e12_native_owner as fixture
    from adapters.mineflayer.python_protocol import MineflayerLaunchConfig
    root, adapter = files(tmp_path)
    bridge = adapter / 'bridge.mjs'
    bridge.write_text('// synthetic')
    process = fixture.FakeOwnedProcess(fixture.frame_set('external-fake'))
    calls = []
    async def spawn(*argv, **kwargs):
        calls.append(kwargs)
        return process
    async def scenario():
        session = await OriginalWireSession.launch_original(
            MineflayerLaunchConfig(version='1.21.8'), raw_path=tmp_path / 'raw',
            bridge_path=bridge, node_runtime_root=root, spawn=spawn)
        await session.receive()
        await session.close_original()
    asyncio.run(scenario())
    assert calls[0]['env']['RELAYSELF_RSEE_NODE_RUNTIME_ROOT'] == str(root)


def test_production_sources_never_import_test_owners():
    source = Path(__file__).resolve().parents[1]
    runner = (source / 'experiments/epistemic_e13_root_owner.py').read_text()
    assert 'test_postmain_' not in runner
    bridge = (source / 'adapters/mineflayer/dependency_runtime.mjs').read_text()
    assert "createRequire(join(root, 'package.json'))" in bridge
    assert 'protocolRequire = createRequire(mf)' in bridge
    assert "createRequire(sourceUrl)" in bridge


def test_nested_protocol_shadow_is_rejected(tmp_path):
    root, adapter = files(tmp_path)
    (root / 'node_modules/mineflayer/node_modules/minecraft-protocol').mkdir(parents=True)
    with pytest.raises(SharedRuntimeRejected, match='nested'):
        verify_node_files(root, adapter)
