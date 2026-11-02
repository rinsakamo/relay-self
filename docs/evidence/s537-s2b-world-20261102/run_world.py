import json
import os
from pathlib import Path
import socket
import subprocess
import time

root = Path(__file__).parent
wt = Path('/home/rinsa/work/relay-self-s2b-world-20261102')
python = '/home/rinsa/relay-self-s60b1-venv/bin/python'
env = os.environ.copy()
assert not env.get('NODE_OPTIONS')
env.update(PYTHONPATH='src:.:tests', S49_REAL_SERVER_CI='1',
           S49_COMPLETED_L0_DEV_ONLY='1', S537_S2B_OWNER_WITNESS_DEV_ONLY='1',
           PYTHONDONTWRITEBYTECODE='1')
env['PATH'] = '/home/rinsa/.nvm/versions/node/v22.22.2/bin:/usr/bin:/bin'
args = [python, '-m', 'tools.s537_s2b_original_owner_witness_dev',
        '--m-owner-dir', '/home/rinsa/work/s2a-m-owner-20261102',
        '--wb-owner-dir', '/home/rinsa/work/s2a-wb-owner-20261102',
        '--report', str(root / 's49.json'), '--server-log', str(root / 'server.log'),
        '--s2b-report', str(root / 's2b.json'), '--live-world-dev']
meta = {'execution_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=wt, text=True).strip(),
        'm_pin': '9afce6bde1079f8a42aaf3c4e515ef35fc6b0396',
        'wb_pin': '944db858186a4d9449946b6acdcb8c8e5998e071',
        's49_pin': '702f75c9fab3c42053ca0c89af670db1e306c892',
        'argv': args, 'world_attempts': 1, 'retry': 0, 'started_ns': time.time_ns()}
with (root / 'execution.json').open('x') as f:
    json.dump(meta, f, indent=2)
seen = {}
with (root / 'world-console.log').open('x') as log:
    proc = subprocess.Popen(args, cwd=wt, env=env, stdout=log, stderr=subprocess.STDOUT)
    while proc.poll() is None:
        records = {}
        for path in Path('/proc').glob('[0-9]*'):
            try:
                stat = (path / 'stat').read_text().split(') ', 1)[1].split()
                records[int(path.name)] = (int(stat[1]), path)
            except (OSError, ValueError, IndexError):
                pass
        family = {proc.pid}
        for _ in range(8):
            family.update(pid for pid, (ppid, _) in records.items() if ppid in family)
        for pid in family:
            if pid in seen or pid not in records:
                continue
            path = records[pid][1]
            try:
                seen[pid] = {'pid': pid, 'cmdline': (path / 'cmdline').read_bytes().decode().split('\0'),
                             'cwd': os.readlink(path / 'cwd'), 'observed_ns': time.time_ns()}
            except OSError:
                pass
        time.sleep(.2)
meta.update(exit_code=proc.returncode, ended_ns=time.time_ns(), python_pid=proc.pid)
for row in seen.values():
    row['pid_absent_after'] = not Path(f"/proc/{row['pid']}").exists()
    if row['cmdline'] and row['cmdline'][0] == 'java':
        row['world_root_absent_after'] = not Path(row['cwd']).exists()
meta['processes'] = list(seen.values())
try:
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 25565))
    meta['port_25565_normal_bind'] = True
except OSError as exc:
    meta['port_25565_normal_bind'] = repr(exc)
with (root / 'lifecycle.json').open('x') as f:
    json.dump(meta, f, indent=2)
print(json.dumps({'exit_code': proc.returncode, 'process_count': len(seen)}))
