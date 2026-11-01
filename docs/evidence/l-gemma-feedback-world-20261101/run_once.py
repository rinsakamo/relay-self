import os,sys,json,time,hashlib,subprocess,socket,signal
from pathlib import Path
r=Path(__file__).parent
repo=Path('/home/rinsa/work/relay-self-l-gemma-feedback-world-20261101')
py='/home/rinsa/work/relay-lm/.venv/bin/python'
env=os.environ.copy()
env.update(PATH='/home/rinsa/.nvm/versions/node/v22.22.2/bin:/home/rinsa/work/s50-p1-flat-native-evidence-20261017/jdk21/runtime/bin:'+env['PATH'],PYTHONPATH='src:tests:.',PYTHONDONTWRITEBYTECODE='1',NODE_OPTIONS='',RELAYSELF_RSEE_NODE_RUNTIME_ROOT=str(r),S49_REAL_SERVER_CI='1',MP11_S49_THREE_ACTION_DEV='1',MP11_G3_PAPER_THREE_WINDOWS_DEV='1',L_MP11_LIVE_PREFIX_DEV='1',L_MP11_LIVE_L2_DEV='1',L_MP11_PAPER_EOF_DEV='1')
os.chdir(repo)
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
assert head=='bfd8bbb486cc230d4191cdbca7358686c2b517ea'
assert not subprocess.check_output(['git','status','--porcelain'],text=True).strip()
with socket.socket() as s:s.bind(('127.0.0.1',25565))
files=[repo/'docs/l-gemma-feedback-world-prereg-20261101.md',Path('/home/rinsa/models/gguf/gemma-4-12B-it-Q4_K_M.gguf'),Path('/home/rinsa/src/llama.cpp/build/bin/llama-server'),Path('/home/rinsa/work/v8-five-world-20261017/assets/paper-1.21.8.jar'),r/'source-built-plugin.jar',r/'paper-active-config-original.yml']
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while b:=f.read(1048576):h.update(b)
    return h.hexdigest()
manifest={'execution_head':head,'mode':'DEV_ONLY','purpose':'Genuine Gemma H1-P1 -> next real WAIT8 -> H1 assessment H2; future-only EOF','budget':{'worlds':1,'sessions':1,'original_actions_max':3,'gemma_open_max':2,'retries':0,'l2_actions':0,'l2_condition_changes':0,'learning_admissions':0,'l0_promotions':0},'eof_predeclared':True,'file_sha256':{str(p):sha(p) for p in files},'flags':{k:env[k] for k in ('S49_REAL_SERVER_CI','MP11_S49_THREE_ACTION_DEV','MP11_G3_PAPER_THREE_WINDOWS_DEV','L_MP11_LIVE_PREFIX_DEV','L_MP11_LIVE_L2_DEV','L_MP11_PAPER_EOF_DEV')},'ci_all_completed_success':[41317304179,41317304238,41317304246,41317304249,41317304219],'model_pid':103190,'ctx_size':8192,'output_tokens':512,'python':subprocess.check_output([py,'--version'],text=True),'node':subprocess.check_output(['node','--version'],env=env,text=True),'java':subprocess.check_output(['java','-version'],env=env,stderr=subprocess.STDOUT,text=True)}
with (r/'preworld-manifest.json').open('x') as f:json.dump(manifest,f,indent=2);f.flush();os.fsync(f.fileno())
with (r/'WORLD_ATTEMPT_STARTED.json').open('x') as f:json.dump({'head':head,'manifest_sha256':sha(r/'preworld-manifest.json'),'monotonic_ns':time.monotonic_ns(),'budget_consumed':True},f);f.flush();os.fsync(f.fileno())
cmd=[py,'-B','-m','adapters.mineflayer.s49_normal_session_real_ci','--mp11-three-actions-dev','--l-mp11-live-prefix-dev','--l-mp11-paper-eof-dev','--l-mp11-live-l2-endpoint','http://127.0.0.1:8080/v1/chat/completions','--l-mp11-live-l2-model','relay-self-gemma4-12b-q4km','--mp11-g3-paper-jar','/home/rinsa/work/v8-five-world-20261017/assets/paper-1.21.8.jar','--mp11-g3-plugin-jar',str(r/'source-built-plugin.jar'),'--mp11-g3-config',str(r/'paper-active-config-original.yml'),'--raw-capture-root',str(r/'native-stdout'),'--report',str(r/'report.json'),'--server-log',str(r/'paper-stdout-original.log')]
with (r/'runner-original.log').open('xb') as out:
    proc=subprocess.Popen(cmd,env=env,stdout=out,stderr=subprocess.STDOUT)
    with (r/'world-process-snapshots.jsonl').open('x') as snapshots:
        while proc.poll() is None:
            row={'monotonic_ns':time.monotonic_ns(),'runner_pid':proc.pid,'processes':[]}
            for p in Path('/proc').iterdir():
                if not p.name.isdigit():continue
                try:
                    args=(p/'cmdline').read_bytes().decode(errors='replace').split('\0')[:-1]
                    if not args:continue
                    if (args[0].endswith('/java') or args[0]=='java') and 'minecraft.jar' in ' '.join(args) or (args[0].endswith('/node') or args[0]=='node') and any(x.endswith('bridge.mjs') for x in args):
                        row['processes'].append({'pid':int(p.name),'argv':args,'cwd':os.readlink(p/'cwd'),'exe':os.readlink(p/'exe')})
                except (OSError,ValueError):pass
            snapshots.write(json.dumps(row)+'\n');snapshots.flush()
            time.sleep(1)
print('WORLD_RUNNER_EXIT',proc.returncode,flush=True)
# Mandatory auditors run even if runtime failed; first failure logs retained.
audit=[]
for tool,name,extra in [('tools/mp11_g3_paper_one_world_audit.py','independent-g3',['--expected-live-l2-calls','2']),('tools/l_mp11_live_paper_postrun_audit.py','independent-l2-prefix',[])]:
    args=[py,tool,'--report',str(r/'report.json'),'--original-paper',str(r/'paper-stdout-original.log.raw'),'--output',str(r/(name+'.json'))]+extra
    with (r/(name+'.log')).open('xb') as f:rc=subprocess.run(args,env=env,stdout=f,stderr=subprocess.STDOUT).returncode
    audit.append({'tool':tool,'exit_code':rc});print(name,rc,flush=True)
with (r/'mandatory-audit-status.json').open('x') as f:json.dump(audit,f,indent=2)
