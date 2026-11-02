import hashlib
import json
from pathlib import Path
import subprocess

root=Path(__file__).parent
wt=Path('/home/rinsa/work/relay-self-s2b-world-20261102')
pre=json.loads((root/'preflight.json').read_text())
changed=[p for p,h in pre['immutable_sha256'].items() if not Path(p).is_file() or hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
refs=dict(row.split(' ',1)[::-1] for row in subprocess.check_output(['git','show-ref','--heads'],cwd=wt,text=True).splitlines())
oldrefs=dict(row.split(' ',1)[::-1] for row in pre['protected_branch_refs'].splitlines())
branch='refs/heads/dev/s537-s2b-original-owner-epoch-read-20261102'
assert all(refs.get(k)==v for k,v in oldrefs.items() if k!=branch)
assert not changed
life=json.loads((root/'lifecycle.json').read_text())
assert life['exit_code']==0 and life['port_25565_normal_bind'] is True
assert all(r['pid_absent_after'] for r in life['processes'])
java=[r for r in life['processes'] if r['cmdline'][0]=='java']
node=[r for r in life['processes'] if r['cmdline'][0]=='node']
assert len(java)==len(node)==1 and java[0]['world_root_absent_after']
s49=json.loads((root/'s49.json').read_text())
assert s49['server_exit']==s49['node_exit']==0
result={'status':'PASS','immutable_file_count':len(pre['immutable_sha256']), 'changed_originals':changed,'other_branch_refs_unchanged':True,'java_count':len(java),'node_count':len(node),'owned_pids_absent':True,'world_deleted':True,'port_25565_released':True}
(root/'preservation.json').write_text(json.dumps(result,indent=2)+'\n')
manifest={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file() and p.name!='SHA256SUMS.json'}
(root/'SHA256SUMS.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(result))
