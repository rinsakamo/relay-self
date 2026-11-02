import json,hashlib,subprocess,socket
from pathlib import Path
from tools.l_mp11_next_trial_gate import read_proc_status
r=Path(__file__).parent
p=json.loads((r/'model-process-identity.json').read_text());now=read_proc_status(p['pid']);assert now is None or now['start_ticks']!=p['start_ticks']
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
old=json.loads((r/'historical-originals-before.json').read_text());changed=[p for p,v in old.items() if sha(p)!=v];assert not changed
before=dict(x.split()[::-1] for x in (r/'protected-refs-before.txt').read_text().splitlines());after=dict(x.split()[::-1] for x in subprocess.check_output(['git','show-ref','--heads'],text=True).splitlines());assert all(after.get(k)==v for k,v in before.items())
assert subprocess.check_output(['git','-C','/home/rinsa/relay-self','status','--porcelain'])+subprocess.check_output(['git','-C','/home/rinsa/relay-self','rev-parse','HEAD'])==(r/'protected-checkout-before.txt').read_bytes()
ports={}
for port in (8080,25565):
 with socket.socket() as s:s.bind(('127.0.0.1',port));ports[str(port)]='BIND_PASS'
a={'model_pid':p['pid'],'model_pid_gone':True,'ports':ports,'historical_original_files_verified':len(old),'historical_changed':changed,'existing_other_branch_refs_unchanged':True,'main_unchanged':True,'execution_worktree_clean':not bool(subprocess.check_output(['git','status','--porcelain']).strip()),'initial_cleanup_port_check':'8080 TIME_WAIT caused EADDRINUSE after model exited; no listeners; later plain bind verified'}
(r/'final-closure.json').write_text(json.dumps(a,indent=2));(r/'gpu-after.txt').write_bytes(subprocess.check_output(['nvidia-smi']));print(json.dumps(a,indent=2))
