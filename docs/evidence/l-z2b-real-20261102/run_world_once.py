"""Operator supervisor: one unchanged CLI, /proc and disk custody only."""
import os,sys,subprocess,json,time,hashlib,secrets
from pathlib import Path
r=Path(__file__).parent;repo=Path('/home/rinsa/work/l-z2b-real-validation-20261102')
prep=json.loads((r/'gemma-preparation/request-status.json').read_text());assert prep['status']=='PREPARED_POLICY_CONTRACT_PASS_NOT_PHYSICALLY_QUALIFIED'
assert subprocess.check_output(['git','-C',str(repo),'status','--porcelain']).strip()==b''
run=secrets.token_hex(8);world=r/'worlds'/f'l-z1-world-{run}'
env=os.environ.copy();env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONPATH='src:tests:.',PATH='/home/rinsa/.nvm/versions/node/v22.22.2/bin:/home/rinsa/work/s50-p1-flat-native-evidence-20261017/jdk21/runtime/bin:'+env['PATH'],RELAYSELF_RSEE_NODE_RUNTIME_ROOT='/home/rinsa/work/l-b1-v2-evidence-20261102/node-runtime',L_ZOMBIE_Z1_ONE_WORLD_DEV='1',L_ZOMBIE_Z1_PURSUIT_DEV='1',L_ZOMBIE_Z2A_CHEAP_DEV='1',L_ZOMBIE_Z2B_PREPARED_DEV='1')
plugin=r/'assets/relay-l-zombie-paper-dev-0.1.0-dev.jar';sha=hashlib.sha256(plugin.read_bytes()).hexdigest()
args=[sys.executable,'-m','tools.l_zombie_z1_one_world_dev','--confirm','Z2B_ONE_PREPARED_L2_SHADOW_WORLD_DEV_NO_RETRY','--pursuit-dev','--prospective-cheap-dev','--prepared-l2-root',str(r/'gemma-preparation'),'--z1b-prior-original',str(next((r/'priors/z1b').rglob('paper-console-original.raw'))),'--z2a-prior-original',str(next((r/'priors/z2a').rglob('paper-console-original.raw'))),'--repo',str(repo),'--expected-head','ca4877579a69eea8351778d808e0e7459aa40bec','--paper-jar','/home/rinsa/work/v8-five-world-20261017/assets/paper-1.21.8.jar','--plugin-jar',str(plugin),'--plugin-sha256',sha,'--world-parent',str(r/'worlds'),'--evidence-parent',str(r/'world-evidence'),'--run-id',run]
with (r/'world-attempt-started.json').open('x') as f:json.dump({'run_id':run,'args':args,'head':'ca4877579a69eea8351778d808e0e7459aa40bec','world_max':1,'retries':0},f,indent=2)
with (r/'world-runner-original.log').open('xb') as log:p=subprocess.Popen(args,cwd=repo,env=env,stdout=log,stderr=subprocess.STDOUT)
seen=set();snap=set()
with (r/'world-process-custody.jsonl').open('x') as records:
 while p.poll() is None:
  for proc in Path('/proc').iterdir():
   if not proc.name.isdigit() or proc.name in seen:continue
   try:
    cwd=os.readlink(proc/'cwd');argv=(proc/'cmdline').read_bytes().decode().split('\0')
    if cwd!=str(world) and not (str(repo/'adapters/mineflayer/bridge.mjs') in argv):continue
    if Path(argv[0]).name not in ('java','node'):continue
    obj={'pid':int(proc.name),'argv':argv,'cwd':cwd,'exe':os.readlink(proc/'exe'),'stat':(proc/'stat').read_text(),'maps':(proc/'maps').read_text(),'observed_ns':time.time_ns()}
    records.write(json.dumps(obj)+'\n');records.flush();os.fsync(records.fileno());seen.add(proc.name)
   except (OSError,ValueError):pass
  for rel in ('server.properties','eula.txt','plugins/RelayZombieTickDev/config.yml','plugins/relay-l-zombie-paper-dev-0.1.0-dev.jar'):
   path=world/rel
   if path.is_file() and rel not in snap:
    raw=path.read_bytes();dest=r/('world-original-'+path.name)
    with dest.open('xb') as f:f.write(raw)
    snap.add(rel)
  time.sleep(.02)
(r/'world-runner-exit.json').write_text(json.dumps({'returncode':p.returncode,'run_id':run,'captured_pids':sorted(seen),'world_absent':not world.exists()},indent=2))
print('WORLD_RETURN',p.returncode,'RUN',run)
print((r/'world-runner-original.log').read_text())
raise SystemExit(p.returncode)
