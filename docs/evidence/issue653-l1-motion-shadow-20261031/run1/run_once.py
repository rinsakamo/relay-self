import os,json,subprocess,socket,time,hashlib
from pathlib import Path
from datetime import datetime,timezone
r=Path('/home/rinsa/work/issue653-l1-shadow-evidence-20261031/run1'); repo=Path('/home/rinsa/work/relay-self-l1-motion-shadow-20261031')
pins=json.loads(Path('/home/rinsa/work/selfbody-s16-s50-evidence-20261031/assets/pins.json').read_text())
for k in ('server','plugin','config'):
 f=Path(pins[k]['path']); assert hashlib.sha256(f.read_bytes()).hexdigest()==pins[k]['sha256']
with socket.socket() as s:s.bind(('127.0.0.1',25565))
env=os.environ.copy(); env['PATH']='/usr/lib/jvm/java-21-openjdk-amd64/bin:/home/rinsa/.nvm/versions/node/v22.22.2/bin:'+env['PATH'];env['PYTHONPATH']='src:tests:.';env['PYTHONDONTWRITEBYTECODE']='1';env['S49_REAL_SERVER_CI']='1'
assert not env.get('NODE_OPTIONS')
assert not (r/'client-packet-original.jsonl').exists()
assert (r/'capture').is_dir() and not list((r/'capture').iterdir())
env['RELAYSELF_RSEE_NODE_RUNTIME_ROOT']='/home/rinsa/work/selfbody-s16-s50-evidence-20261031/node-runtime'
env['RELAYSELF_S50_PACKET_WITNESS_DEV']=str(r/'client-packet-original.jsonl')
py='/home/rinsa/relay-self-s60b1-venv/bin/python'
argv=[py,'-m','adapters.mineflayer.self_body_s50_world_dev','--report',str(r/'s49-report.json'),'--server-log',str(r/'server.log'),'--l16-capture-root',str(r/'capture'),'--l16-goal-target-x','0','--l16-goal-target-z','0','--l16-goal-tolerance-m','0.49','--l16-goal-stability-m','0.05','--l16-confirm','L16-S49-FIRST-ACTION-ORIGINAL-DEV','--l22-settling-probes','6','--selfbody-live-next-epoch-dev','--selfbody-l1-motion-shadow-dev']
for key,flag in [('server','server'),('plugin','plugin'),('config','config')]:
 argv += ['--l23-paper-'+flag+('-jar' if key!='config' else ''),pins[key]['path'],'--l23-paper-'+flag+'-sha256',pins[key]['sha256']]
def output(cmd):return subprocess.check_output(cmd,env=env,cwd=repo,stderr=subprocess.STDOUT,text=True).strip()
meta={'utc':datetime.now(timezone.utc).isoformat(),'head':output(['git','-C','/home/rinsa/work/relay-self-l1-motion-shadow-20261031','rev-parse','HEAD']),'executor_head':output(['git','rev-parse','HEAD']),'branch':output(['git','branch','--show-current']),'argv':argv,'assets':pins,'python':output([py,'-V']),'java':output(['java','-version']),'node':output(['node','-v']),'mineflayer':json.loads((Path(env['RELAYSELF_RSEE_NODE_RUNTIME_ROOT'])/'node_modules/mineflayer/package.json').read_text())['version'],'port_preflight_free':True,'fresh_world':'S49 creates fresh TemporaryDirectory; no existing World','goal_independent_owner':False,'max_world_runs':1,'action_owner':'S49 existing sole executor','qualification':'DEV_ONLY','learning_pairs':0}
(r/'environment.json').write_text(json.dumps(meta,indent=2)+'\n')
seen={}; roots=set(); asset_seen={}; last_asset_scan=0
with (r/'runner.stdout.log').open('xb') as log:
 p=subprocess.Popen(argv,cwd=repo,env=env,stdout=log,stderr=subprocess.STDOUT)
 while p.poll() is None:
  table={}
  for proc in Path('/proc').iterdir():
   if not proc.name.isdigit():continue
   try:
    fields=(proc/'stat').read_text().split(); table[int(proc.name)]=int(fields[3])
   except (OSError,ValueError):pass
  owned={p.pid}
  for _ in range(6):owned|={pid for pid,ppid in table.items() if ppid in owned}
  for pid in owned-{p.pid}:
   try:
    q=Path('/proc')/str(pid); cmd=(q/'cmdline').read_bytes().replace(b'\0',b' ').decode();cwd=os.readlink(q/'cwd')
    if pid not in seen:
     seen[pid]={'pid':pid,'ppid':table.get(pid),'argv':cmd,'cwd':cwd,'first_seen_utc':datetime.now(timezone.utc).isoformat()}
     (r/'process-ownership.json').write_text(json.dumps(list(seen.values()),indent=2)+'\n')
    if '/relay-self-s49-' in cwd:roots.add(cwd)
   except OSError:pass
  if time.monotonic()-last_asset_scan > 1:
   last_asset_scan=time.monotonic()
   for world_root in roots:
    for asset in Path(world_root).rglob('*'):
     try:
      if asset.is_file() and asset.suffix in ('.jar','.yml','.yaml','.properties'):
       key=str(asset); stat=asset.stat(); signature=[stat.st_size,stat.st_mtime_ns]
       if key not in asset_seen or asset_seen[key]['signature']!=signature:
        asset_seen[key]={'signature':signature,'sha256':hashlib.sha256(asset.read_bytes()).hexdigest()}
        if asset.suffix!='.jar':
         dest=r/'runtime-config'/asset.relative_to(world_root);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(asset.read_bytes())
     except OSError:pass
   (r/'runtime-assets-sha256.json').write_text(json.dumps(asset_seen,indent=2)+'\n')
  time.sleep(.1)
 rc=p.wait()
cleanup={'runner_exit':rc,'owned_processes':[{**v,'pid_gone':not Path('/proc',str(pid)).exists()} for pid,v in seen.items()],'world_roots':[{ 'path':q,'removed':not Path(q).exists()} for q in roots]}
with socket.socket() as s:
 try:s.bind(('127.0.0.1',25565));cleanup['port_rebind']=True
 except OSError as e:cleanup['port_rebind']=False;cleanup['port_error']=str(e)
(r/'cleanup.json').write_text(json.dumps(cleanup,indent=2)+'\n')
print(json.dumps({'exit':rc,'cleanup':cleanup}))
