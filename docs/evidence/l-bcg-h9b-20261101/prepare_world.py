import json,hashlib,subprocess,sys
from pathlib import Path
from datetime import datetime,timezone
from relay_self.l_bcg_h9b_dev_holdout import SLOTS, validate_plan, source_digest
root=Path(__file__).resolve().parent
slot=sys.argv[1];index=[r[0] for r in SLOTS].index(slot);slot,arm,role=SLOTS[index]
plan_raw=(root/'protocol.json').read_bytes();plan=json.loads(plan_raw);plan_sha=validate_plan(plan,raw=plan_raw)
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==plan['executor_head']
assert not subprocess.check_output(['git','status','--porcelain'],text=True).strip()
for prior,_,_ in SLOTS[:index]:assert (root/'worlds'/prior/'audited-complete.json').is_file()
assert all(not (root/'worlds'/future/'run1/WORLD_ATTEMPT_STARTED.json').exists() for future,_,_ in SLOTS[index:])
frozen_sha=source_digest((root/'frozen-model.json').read_bytes()) if role=='dev_eval' else None
if role=='dev_eval':
 boundary=json.loads((root/'frozen-model.boundary.json').read_bytes());assert boundary['frozen_original_sha256']==frozen_sha
 assert datetime.fromisoformat(boundary['frozen_utc'])<datetime.now(timezone.utc)
pins=json.loads(Path('/home/rinsa/work/selfbody-s16-s50-evidence-20261031/assets/pins.json').read_bytes())
p=json.loads(Path('docs/evidence/l-bcg-h9a-20261101/a/predeclared.json').read_bytes())
p.update(executor_head=plan['executor_head'],purpose='H9b DEV past FIT body experience prediction of unused EVAL World motion proxy',runtime_preflight=str(root/'preflight/runtime-preflight.json'),runtime_assets=pins,sequence='A-F1 B-F1 B-F2 A-F2 B-E1 A-E1 A-E2 B-E2; stop on first failure; no replacement',evidence_root=str(root/'worlds'/slot),declared_utc=datetime.now(timezone.utc).isoformat(),h9b={'slot_id':slot,'role':role,'plan_sha256':plan_sha,'frozen_model_sha256':frozen_sha},arm_id=arm,requested_distance_m=2.0 if arm=='A' else 3.5,launcher_sha256=source_digest((root/'run_one_world.py').read_bytes()))
w=root/'worlds'/slot;w.mkdir(parents=True,exist_ok=False);(w/'run1/capture').mkdir(parents=True)
raw=(json.dumps(p,indent=2,ensure_ascii=False)+'\n').encode()
with (w/'predeclared.json').open('xb') as out:out.write(raw)
with (w/'predeclared.sha256').open('x') as out:out.write(source_digest(raw)+'  predeclared.json\n')
(w/'run1/run_once.py').write_bytes((root/'run_one_world.py').read_bytes())
print(json.dumps({'slot':slot,'role':role,'prereg_sha256':source_digest(raw),'worlds_started':index}))
