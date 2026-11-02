import json,hashlib,subprocess,ast
from pathlib import Path
r=Path(__file__).parent;repo=Path.cwd();old=Path('/home/rinsa/evidence/l-cognitive-loop-20261102T034000Z')
def sha(p):return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
files={str(p):sha(p) for p in old.rglob('*') if p.is_file()}
tracked=repo/'docs/evidence/l-cognitive-loop-20261102'
files.update({str(p):sha(p) for p in tracked.rglob('*') if p.is_file()})
(r/'historical-originals-before.json').write_text(json.dumps(files,indent=2))
(r/'protected-refs-before.txt').write_bytes(subprocess.check_output(['git','show-ref','--heads']))
(r/'protected-checkout-before.txt').write_bytes(subprocess.check_output(['git','-C','/home/rinsa/relay-self','status','--porcelain'])+subprocess.check_output(['git','-C','/home/rinsa/relay-self','rev-parse','HEAD']))
(r/'execution-head.txt').write_bytes(subprocess.check_output(['git','rev-parse','HEAD']))
for p in ['adapters/mineflayer/l_mp11_b1_forecast_contract.py','adapters/mineflayer/l_mp11_live_l2_shadow.py','adapters/mineflayer/l_mp11_gemma_wire_contract.py','adapters/mineflayer/l_mp11_typed_feedback.py','adapters/mineflayer/l_mp11_evidence_id_selection.py','adapters/mineflayer/s49_normal_session_real_ci.py','tools/l_mp11_gemma_structured_preflight.py','tools/l_mp11_next_trial_gate.py','tools/l_mp11_feedback_original_audit.py']:ast.parse((repo/p).read_text())
(r/'syntax.json').write_text(json.dumps({'ast_parse':'PASS','files':9}))
(r/'preregistration.json').write_text(json.dumps({'head':(r/'execution-head.txt').read_text().strip(),'repo':str(repo),'root':str(r),'authority':['current user B1 V2 mission','live #537 2026-10-14 DEV policy + 2026-11-01 L development policy'],'preflight_http_max':1,'world_max':1,'world_retries':0,'mineflayer_sessions_max':1,'s49_actions_max':3,'world_open_max':2,'l2_actions':0,'l2_condition_changes':0,'learning_admission':0,'l0_promotion':0,'classification_ceiling':'DEV_ONLY / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN','historical_files_protected':len(files)},indent=2))
print('PREPARED',len(files))
