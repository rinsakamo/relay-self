import os,json,time,hashlib,subprocess,socket,shutil
from pathlib import Path
r=Path(__file__).parent
repo=Path('/home/rinsa/work/relay-self-l-gemma-local-validation-20261102')
py='/home/rinsa/work/relay-lm/.venv/bin/python'
old=Path('/home/rinsa/work/l-gemma-feedback-world-evidence-20261101')
w=r/'world';w.mkdir()
env=os.environ.copy()
env.update(PATH='/home/rinsa/.nvm/versions/node/v22.22.2/bin:/home/rinsa/work/s50-p1-flat-native-evidence-20261017/jdk21/runtime/bin:'+env['PATH'],PYTHONPATH='src:tests:.',PYTHONDONTWRITEBYTECODE='1',NODE_OPTIONS='',RELAYSELF_RSEE_NODE_RUNTIME_ROOT=str(r/'node-runtime'))
for k in ('S49_REAL_SERVER_CI','MP11_S49_THREE_ACTION_DEV','MP11_G3_PAPER_THREE_WINDOWS_DEV','L_MP11_LIVE_PREFIX_DEV','L_MP11_LIVE_L2_DEV','L_MP11_EVIDENCE_IDS_DEV','L_MP11_GEMMA_STRICT_SCHEMA_DEV','L_MP11_PAPER_EOF_DEV'):env[k]='1'
os.chdir(repo)
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
assert head==(r/'world-execution-head.txt').read_text().strip()
assert not subprocess.check_output(['git','status','--porcelain'],text=True).strip()
assert '271 passed' in (r/'offline-final-preworld.log').read_text()
with socket.socket() as s:s.bind(('127.0.0.1',25565))
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while b:=f.read(1048576):h.update(b)
 return h.hexdigest()
# Read-only source reuse; dependency files are copied to a fresh physical root.
nr=r/'node-runtime';nr.mkdir()
for name in ('package.json','package-lock.json'):shutil.copy2(old/name,nr/name)
shutil.copytree(old/'node_modules',nr/'node_modules',symlinks=True)
shutil.copy2(old/'paper-active-config-original.yml',r/'paper-active-config.yml')
node_check=subprocess.check_output(['node','-e',"const p=require('mineflayer/package.json');require('mineflayer');console.log(JSON.stringify({node:process.version,mineflayer:p.version,resolved:require.resolve('mineflayer')}));if(p.version!=='4.39.0')process.exit(2)"],cwd=nr,env=env,text=True)
(r/'node-import-preflight.json').write_text(node_check)
from tools.l_mp11_gemma_structured_preflight import verify_preflight_report
probe=r/'gemma-strict-wire-probe/gemma-structured-preflight.json'
verify_preflight_report(probe,endpoint='http://127.0.0.1:8080/v1/chat/completions',model='relay-self-gemma4-12b-q4km')
protected=[p for p in old.iterdir() if p.is_file()]+[p for p in (old/'native-stdout').rglob('*') if p.is_file()]
(r/'historical-originals-before.json').write_text(json.dumps({str(p):sha(p) for p in protected},indent=2))
plugin=r/'plugin-build-target/relay-metabolism-paper-dev-0.2.0-dev.jar'
paper=Path('/home/rinsa/work/v8-five-world-20261017/assets/paper-1.21.8.jar')
manifest={'head':head,'probe_execution_head':(r/'execution-head.txt').read_text().strip(),'mode':'DEV_ONLY','authority':['current user mission 2026-11-02','https://github.com/rinsakamo/relay-self/issues/537','https://github.com/rinsakamo/relay-self/issues/431','https://github.com/rinsakamo/relay-self/issues/653'],'worlds':1,'retries':0,'sessions':1,'s49_action_max':3,'live_gemma_open_max':2,'probe_http':1,'l2_actions':0,'l2_condition_changes':0,'learning_admission':0,'l0_promotion':0,'predeclared_eof':True,'file_sha256':{str(p):sha(p) for p in (plugin,paper,r/'paper-active-config.yml',probe,repo/'docs/l-gemma-local-validation-prereg-20261102.md')},'flags':{k:v for k,v in env.items() if k.startswith(('L_MP11_','MP11_','S49_REAL'))},'model_pid':json.loads((r/'owned-model-pid.json').read_text())['pid'],'python':subprocess.check_output([py,'--version'],text=True),'node_import':json.loads(node_check),'java':subprocess.check_output(['java','-version'],env=env,stderr=subprocess.STDOUT,text=True)}
with (r/'preworld-manifest.json').open('x') as f:json.dump(manifest,f,indent=2);f.flush();os.fsync(f.fileno())
cmd=[py,'-B','-m','adapters.mineflayer.s49_normal_session_real_ci','--mp11-three-actions-dev','--l-mp11-live-prefix-dev','--l-mp11-evidence-ids-dev','--l-mp11-paper-eof-dev','--l-mp11-gemma-preflight-report',str(probe),'--l-mp11-live-l2-endpoint','http://127.0.0.1:8080/v1/chat/completions','--l-mp11-live-l2-model','relay-self-gemma4-12b-q4km','--mp11-g3-paper-jar',str(paper),'--mp11-g3-plugin-jar',str(plugin),'--mp11-g3-config',str(r/'paper-active-config.yml'),'--raw-capture-root',str(w/'native-stdout'),'--report',str(w/'report.json'),'--server-log',str(w/'paper-stdout-original.log')]
with (r/'WORLD_ATTEMPT_STARTED.json').open('x') as f:json.dump({'head':head,'manifest_sha256':sha(r/'preworld-manifest.json'),'monotonic_ns':time.monotonic_ns(),'budget_consumed':True,'argv':cmd},f);f.flush();os.fsync(f.fileno())
with (w/'runner-original.log').open('xb') as out:
 proc=subprocess.Popen(cmd,env=env,stdout=out,stderr=subprocess.STDOUT)
 with (w/'world-process-snapshots.jsonl').open('x') as snapshots:
  while proc.poll() is None:
   row={'monotonic_ns':time.monotonic_ns(),'runner_pid':proc.pid,'processes':[]}
   for p in Path('/proc').iterdir():
    if not p.name.isdigit():continue
    try:
     args=(p/'cmdline').read_bytes().decode(errors='strict').split('\0')[:-1]
     if args and ((args[0].endswith('/java') or args[0]=='java') and 'minecraft.jar' in args or (args[0].endswith('/node') or args[0]=='node') and any(x.endswith('bridge.mjs') for x in args)):
      row['processes'].append({'pid':int(p.name),'argv':args,'cwd':os.readlink(p/'cwd'),'exe':os.readlink(p/'exe')})
    except (OSError,ValueError):pass
   snapshots.write(json.dumps(row)+'\n');snapshots.flush();time.sleep(1)
print('WORLD_RUNNER_EXIT',proc.returncode,flush=True)
(r/'world-runner-exit.json').write_text(json.dumps({'exit_code':proc.returncode}))
