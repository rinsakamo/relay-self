import os,json,hashlib,subprocess,socket,zipfile
from pathlib import Path
from tools.l_mp11_next_trial_gate import read_proc_status
r=Path(__file__).parent; repo=Path.cwd(); py='/home/rinsa/work/relay-lm/.venv/bin/python'
head=(r/'execution-head.txt').read_text().strip()
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==head
assert not subprocess.check_output(['git','status','--porcelain'],text=True).strip()
assert '170 passed' in (r/'offline.log').read_text()
assert '12 passed' in (r/'gate-final.log').read_text()
cap=r/'world/native-stdout'
assert cap.is_absolute() and cap.is_dir() and not list(cap.iterdir())
assert not any(p.is_symlink() for p in (cap,*cap.parents))
assert (r/'l-next-world-capture-ready.json').is_file() and not (r/'l-next-world-attempt-started.json').exists()
env=os.environ.copy();env.update(PATH='/home/rinsa/.nvm/versions/node/v22.22.2/bin:/home/rinsa/work/s50-p1-flat-native-evidence-20261017/jdk21/runtime/bin:'+env['PATH'],PYTHONPATH='src:tests:.',PYTHONDONTWRITEBYTECODE='1',NODE_OPTIONS='',RELAYSELF_RSEE_NODE_RUNTIME_ROOT=str(r/'node-runtime'))
flags=('S49_REAL_SERVER_CI','MP11_S49_THREE_ACTION_DEV','MP11_G3_PAPER_THREE_WINDOWS_DEV','L_MP11_LIVE_PREFIX_DEV','L_MP11_LIVE_L2_DEV','L_MP11_EVIDENCE_IDS_DEV','L_MP11_GEMMA_STRICT_SCHEMA_DEV','L_MP11_PAPER_EOF_DEV')
for k in flags:env[k]='1'
with socket.socket() as s:s.bind(('127.0.0.1',25565))
identity=json.loads((r/'model-process-identity.json').read_text());current=read_proc_status(identity['pid'])
assert all(current[k]==identity[k] for k in ('pid','start_ticks','exe','argv','cwd'))
assert '/home/rinsa/models/gguf/gemma-4-12B-it-Q4_K_M.gguf' in (Path('/proc')/str(current['pid'])/'maps').read_text()
node=subprocess.check_output(['node','-e',"require('mineflayer');console.log(JSON.stringify({node:process.version,mineflayer:require('mineflayer/package.json').version,resolved:require.resolve('mineflayer')}))"],env=env,cwd=r/'node-runtime',text=True)
assert json.loads(node)['mineflayer']=='4.39.0'
(r/'node-import-preflight.json').write_text(node)
paper=Path('/home/rinsa/work/v8-five-world-20261017/assets/paper-1.21.8.jar');plugin=r/'plugin-build-target/relay-metabolism-paper-dev-0.2.0-dev.jar';config=r/'paper-active-config.yml';probe=r/'gemma-strict-wire-probe/gemma-structured-preflight.json'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while b:=f.read(1048576):h.update(b)
 return h.hexdigest()
with zipfile.ZipFile(paper) as z:
 version=z.read('version.json');(r/'paper-version-original.json').write_bytes(version)
 assert json.loads(version)['id']=='1.21.8'
manifest={'head':head,'mode':'DEV_ONLY','authority':['current user mission 2026-11-02','https://github.com/rinsakamo/relay-self/issues/537'],'world_max':1,'retry_max':0,'session_max':1,'s49_action_max':3,'world_gemma_open_max':2,'preflight_http_max':1,'l2_actions':0,'l2_condition_changes':0,'learning_admission':0,'l0_promotion':0,'flags':{k:env[k] for k in flags},'files':{str(p):sha(p) for p in (paper,plugin,config,probe,repo/'docs/l-cognitive-loop-prereg-20261102.md')},'java':subprocess.check_output(['java','-version'],env=env,stderr=subprocess.STDOUT,text=True),'python':subprocess.check_output([py,'--version'],text=True),'node':json.loads(node),'model_identity':current,'capture_empty':True,'started_absent':True}
with (r/'preworld-manifest.json').open('x') as f:json.dump(manifest,f,indent=2);f.flush();os.fsync(f.fileno())
cmd=[py,'-B','-m','tools.l_mp11_next_trial_gate','run','--evidence-root',str(r),'--repo',str(repo),'--expected-head',head,'--',py,'-B','-m','adapters.mineflayer.s49_normal_session_real_ci','--mp11-three-actions-dev','--l-mp11-live-prefix-dev','--l-mp11-evidence-ids-dev','--l-mp11-paper-eof-dev','--l-mp11-gemma-preflight-report',str(probe),'--l-mp11-live-l2-endpoint','http://127.0.0.1:8080/v1/chat/completions','--l-mp11-live-l2-model','relay-self-gemma4-12b-q4km','--mp11-g3-paper-jar',str(paper),'--mp11-g3-plugin-jar',str(plugin),'--mp11-g3-config',str(config),'--raw-capture-root',str(cap),'--report',str(r/'world/report.json'),'--server-log',str(r/'world/paper-stdout-original.log')]
with (r/'world-controller-original.log').open('xb') as f:
 result=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT)
print('WORLD_GATE_EXIT',result.returncode)
