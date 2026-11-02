import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess

root = Path(__file__).parent
wt = Path('/home/rinsa/work/relay-self-s2b-world-20261102')
env = os.environ.copy()
env['PATH'] = '/home/rinsa/.nvm/versions/node/v22.22.2/bin:/usr/bin:/bin'
assert not env.get('NODE_OPTIONS')
def run(args, cwd=wt):
    return subprocess.check_output(args, cwd=cwd, env=env, text=True, stderr=subprocess.STDOUT).strip()
owners = {}
for name, pin in [('m', '9afce6bde1079f8a42aaf3c4e515ef35fc6b0396'), ('wb', '944db858186a4d9449946b6acdcb8c8e5998e071')]:
    path = Path(f'/home/rinsa/work/s2a-{name}-owner-20261102')
    assert run(['git', 'rev-parse', 'HEAD'], path) == pin
    assert run(['git', 'status', '--porcelain'], path) == ''
    owners[name] = {'head': pin, 'root': str(path), 'clean': True}
with socket.socket() as sock:
    sock.bind(('127.0.0.1', 25565))
immutable = {}
for base in [Path('/home/rinsa/work/s1-live-evidence-20261102'), Path('/home/rinsa/work/s2a-world-evidence-20261102')]:
    for path in base.rglob('*'):
        if path.is_file():
            immutable[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
source_hashes = {}
for rel in ['normal_action.py', 'self_action_evidence.py', 's49_completed_decision_bridge.py']:
    path = 'adapters/mineflayer/' + rel
    frozen = subprocess.check_output(['git', 'show', '702f75c9fab3c42053ca0c89af670db1e306c892:' + path], cwd=wt)
    assert frozen == (wt / path).read_bytes()
    source_hashes[path] = hashlib.sha256(frozen).hexdigest()
assert run(['git', 'status', '--porcelain']) == ''
outputs = [str(root / n) for n in ['s49.json', 's2b.json', 'server.log']]
assert all(not Path(p).exists() for p in outputs)
data = {'owners': owners, 'execution_head': run(['git', 'rev-parse', 'HEAD']),
        'protected_branch_refs': run(['git', 'show-ref', '--heads']),
        'immutable_sha256': immutable, 's49_unchanged_source_hashes': source_hashes,
        'port_bind_before': True, 'python': run(['/home/rinsa/relay-self-s60b1-venv/bin/python', '--version']),
        'java': run(['java', '-version']), 'node': run(['node', '--version']),
        'mineflayer': run(['node', '-p', "require('./adapters/mineflayer/node_modules/mineflayer/package.json').version"]),
        'processes_before': run(['ps', '-eo', 'pid,ppid,args']),
        'existing_world_roots': [str(p) for p in Path('/tmp').glob('relay-self-s49-*')],
        'outputs': outputs, 'budget': {'world': 1, 'original_actions_max': 2, 'model': 0, 'retry': 0},
        'authority': 'Issue #537 live DEV policy 2026-10-14 plus current S2-B mission; no historical single-use grant reused'}
assert data['mineflayer'] == '4.39.0'
with (root / 'preflight.json').open('x') as f:
    json.dump(data, f, indent=2)
print('preflight PASS')
