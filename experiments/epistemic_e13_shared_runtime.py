"""Read-only RSEE files verification. Never starts Node/Java or installs."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

BASE = Path('/home/rinsa/.local/share/relay-self/rsee-1.0-20261011')
NPM_SHA256 = {
    'package.json': '8fc9d7868b38843e1741909e999d6c1d1b70c257fe04c55d8c841694e30ded2d',
    'package-lock.json': '545e32a148b1f3649ba199dac9383fca72d0aaae17afbe740dc26163491ae568',
}
JAR_SHA256 = '2349d9a8f0d4be2c40e7692890ef46a4b07015e7955b075460d02793be7fbbe7'


class SharedRuntimeRejected(ValueError):
    pass


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def physical(path):
    if path.resolve() != path or not path.exists():
        raise SharedRuntimeRejected(f'physical original path required: {path}')
    return path


def verify_node_files(root: Path, adapter: Path):
    if not root.is_absolute():
        raise SharedRuntimeRejected('explicit absolute runtime root required')
    physical(root)
    physical(root / 'node_modules')
    if root == adapter or adapter in root.parents or root in adapter.parents:
        raise SharedRuntimeRejected('external root required')
    result = {'node_runtime_root': str(root)}
    for name in ('package.json', 'package-lock.json'):
        original = physical(adapter / name)
        external = physical(root / name)
        if sha(original) != NPM_SHA256[name] or sha(original) != sha(external):
            raise SharedRuntimeRejected('source manifest/lock mismatch')
        result[name + '_sha256'] = sha(original)
    # Node resolves dependencies from the importing Mineflayer file upward.
    # Reject nested protocol shadows before accepting the top-level original.
    for nested in (root / 'node_modules/mineflayer/node_modules/minecraft-protocol',):
        if nested.exists() or nested.is_symlink():
            raise SharedRuntimeRejected('nested transitive protocol substitution')
    lock = json.loads((root / 'package-lock.json').read_text())['packages']
    for name in ('mineflayer', 'minecraft-protocol'):
        directory = physical(root / 'node_modules' / name)
        metadata = physical(directory / 'package.json')
        package = json.loads(metadata.read_text())
        expected = lock['node_modules/' + name]['version']
        if package['version'] != expected or (name == 'mineflayer' and expected != '4.39.0'):
            raise SharedRuntimeRejected('installed version differs from original lock')
        entry = physical(directory / package.get('main', 'index.js'))
        if root not in entry.parents:
            raise SharedRuntimeRejected('module realpath escape')
        result[name] = {'version': expected, 'metadata': str(metadata),
                        'entry': str(entry), 'entry_sha256': sha(entry),
                        'metadata_sha256': sha(metadata)}
    return result


def child_env(root, adapter):
    if os.environ.get('NODE_PATH') or os.environ.get('NODE_OPTIONS'):
        raise SharedRuntimeRejected('Node environment override forbidden')
    verify_node_files(root, adapter)
    return {**os.environ, 'RELAYSELF_RSEE_NODE_RUNTIME_ROOT': str(root)}


def verify_shared_files(adapter: Path):
    if (Path(sys.prefix) != BASE / 'venv' or sys.version_info[:2] != (3, 12)
            or Path(sys.executable) != BASE / 'venv/bin/python'):
        raise SharedRuntimeRejected('existing shared Python3.12 required')
    import httpx
    import pytest
    if pytest.__version__ != '9.1.1' or httpx.__version__ != '0.28.1':
        raise SharedRuntimeRejected('shared Python package version differs')
    for module in (pytest, httpx):
        if BASE / 'venv' not in Path(module.__file__).resolve().parents:
            raise SharedRuntimeRejected('Python package escaped shared prefix')
    child_env(BASE / 'npm-mineflayer-4.39.0', adapter)
    result = verify_node_files(BASE / 'npm-mineflayer-4.39.0', adapter)
    jar = physical(BASE / 'minecraft-1.21.8.jar')
    if sha(jar) != JAR_SHA256:
        raise SharedRuntimeRejected('original Minecraft jar SHA256 differs')
    result.update(python=sys.executable, python_realpath=str(Path(sys.executable).resolve()),
                  python_sha256=sha(Path(sys.executable).resolve()),
                  pytest_realpath=str(Path(pytest.__file__).resolve()),
                  httpx_realpath=str(Path(httpx.__file__).resolve()),
                  prefix=sys.prefix, pytest=pytest.__version__, httpx=httpx.__version__,
                  jar_sha256=sha(jar), classification='OFFLINE_FILES_ONLY_NOT_PHYSICAL')
    return result


if __name__ == '__main__':
    print(json.dumps(verify_shared_files(Path(__file__).resolve().parents[1] /
                                        'adapters/mineflayer'), indent=2))
