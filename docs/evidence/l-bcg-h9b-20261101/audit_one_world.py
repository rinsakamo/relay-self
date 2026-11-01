import json,sys,hashlib,subprocess,socket
from pathlib import Path
from datetime import datetime,timezone
from dataclasses import asdict
from relay_self.l_bcg_h9b_dev_holdout import SLOTS,validate_plan,source_digest
from tools.l_bcg_h9b_dev_holdout import _predeclared_record,_prospective_config_audit
root=Path(__file__).resolve().parent;slot=sys.argv[1];idx=[x[0] for x in SLOTS].index(slot);_,arm,role=SLOTS[idx];w=root/'worlds'/slot;r=w/'run1'
# Persist originals even if independent audit rejects.
manifest={str(p.relative_to(r)):source_digest(p.read_bytes()) for p in sorted(r.rglob('*')) if p.is_file()}
with (w/'original-sha256.json').open('x') as out:out.write(json.dumps(manifest,indent=2)+'\n')
py='/home/rinsa/relay-self-s60b1-venv/bin/python'
with (w/'independent-audit.log').open('x') as out:
 rc=subprocess.call([py,'tools/l_bcg_h8_world_readback.py',str(r),'--output',str(w/'independent-audit.json')],stdout=out,stderr=subprocess.STDOUT)
assert rc==0,'H8 independent original audit rejected; STOP'
raw=(root/'protocol.json').read_bytes();plan=json.loads(raw);sha=validate_plan(plan,raw=raw)
record,started=_predeclared_record(slot=slot,arm=arm,role=role,evidence_root=w,plan_sha=sha,executor_head=plan['executor_head'],frozen_sha=source_digest((root/'frozen-model.json').read_bytes()) if role=='dev_eval' else None)
config_shas=_prospective_config_audit(tuple(root/'worlds'/s for s,_,_ in SLOTS[:idx+1]))
# Check immutable source and currently released resources again.
cleanup=json.loads((r/'cleanup.json').read_bytes());assert all(x['pid_gone'] and not Path('/proc',str(x['pid'])).exists() for x in cleanup['owned_processes'])
assert all(x['removed'] and not Path(x['path']).exists() for x in cleanup['world_roots'])
with socket.socket() as s:s.bind(('127.0.0.1',25565))
with (w/'arm-review.json').open('x') as out:out.write(json.dumps(asdict(record),indent=2)+'\n')
with (w/'audited-complete.json').open('x') as out:out.write(json.dumps({'slot':slot,'completed_utc':datetime.now(timezone.utc).isoformat(),'original_manifest_sha256':source_digest((w/'original-sha256.json').read_bytes()),'h8_audit_sha256':source_digest((w/'independent-audit.json').read_bytes()),'config_raw_shas_to_here':config_shas,'worlds':1,'actions':1,'s16':1,'retries':0,'port_rebind':True})+'\n')
print(json.dumps({'slot':slot,'source':asdict(record.arm),'config_comparison':'PASS','cleanup':'PASS'}))
