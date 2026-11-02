import json,os,signal,time,socket,subprocess,hashlib
from pathlib import Path
from tools.l_mp11_next_trial_gate import read_proc_status
r=Path(__file__).parent
p=json.loads((r/'model-process-identity.json').read_text());now=read_proc_status(p['pid']);assert now and all(now[k]==p[k] for k in ('pid','start_ticks','exe','argv','cwd'))
os.kill(p['pid'],signal.SIGINT)
for i in range(100):
 now=read_proc_status(p['pid'])
 if now is None or now['start_ticks']!=p['start_ticks']:break
 time.sleep(.1)
assert now is None or now['start_ticks']!=p['start_ticks']
ports={}
for port in (8080,25565):
 with socket.socket() as s:s.bind(('127.0.0.1',port));ports[str(port)]='BIND_PASS'
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
old=json.loads((r/'historical-originals-before.json').read_text());changed=[p for p,v in old.items() if sha(p)!=v];assert not changed
assert subprocess.check_output(['git','show-ref','--heads'])==(r/'protected-refs-before.txt').read_bytes()
assert subprocess.check_output(['git','-C','/home/rinsa/relay-self','status','--porcelain'])+subprocess.check_output(['git','-C','/home/rinsa/relay-self','rev-parse','HEAD'])==(r/'protected-checkout-before.txt').read_bytes()
(r/'final-closure.json').write_text(json.dumps({'model_pid':p['pid'],'model_pid_gone':True,'ports':ports,'historical_original_files_verified':len(old),'historical_changed':changed,'other_branch_refs_unchanged':True,'main_unchanged':True,'execution_worktree_clean':not bool(subprocess.check_output(['git','status','--porcelain']).strip())},indent=2))
(r/'gpu-after.txt').write_bytes(subprocess.check_output(['nvidia-smi']))
print((r/'final-closure.json').read_text())
