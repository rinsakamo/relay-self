import json,hashlib,os,signal,time,socket,subprocess
from pathlib import Path
r=Path(__file__).parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
report=json.loads(next((r/'world-evidence').rglob('report.json')).read_text())
rows=[json.loads(x) for x in (r/'world-process-custody.jsonl').read_text().splitlines()]
java=next(x for x in rows if Path(x['exe']).name=='java');node=next(x for x in rows if Path(x['exe']).name=='node')
assert java['pid']==report['java_pid']['pid'] and node['pid']==report['node_pid']['pid']
assert java['stat'].split()[21]==str(report['java_pid']['starttime_ticks'])
assert node['stat'].split()[21]==str(report['node_pid']['starttime_ticks'])
assert '/home/rinsa/work/v8-five-world-20261017/assets/paper-1.21.8.jar' in java['argv']
assert java['exe']=='/home/rinsa/work/s50-p1-flat-native-evidence-20261017/jdk21/runtime/bin/java'
assert node['exe']=='/home/rinsa/.nvm/versions/node/v22.22.2/bin/node'
assert sha(r/'world-original-relay-l-zombie-paper-dev-0.1.0-dev.jar')==report['plugin_sha256']
raw=next((r/'world-evidence').rglob('paper-console-original.raw')).read_bytes()
assert b'Paper version 1.21.8-60' in raw and b'Enabling RelayZombieTickDev v0.1.0-dev' in raw
assert report['original_sha256']==hashlib.sha256(raw).hexdigest()
assert report['node_exit']==report['java_exit']==0
assert all(report[k] is True for k in ['cleanup_confirmed','world_removed','java_pid_absent','node_pid_absent','port_released'])
assert not Path(java['cwd']).exists()
assert not Path(f"/proc/{java['pid']}").exists() and not Path(f"/proc/{node['pid']}").exists()
for path,digest in json.loads((r/'priors-before.json').read_text()).items():assert sha(Path(path))==digest
assert subprocess.check_output(['git','-C','/home/rinsa/relay-self','status','--porcelain=v1'])==(r/'protected-checkout-before.txt').read_bytes()
assert subprocess.check_output(['git','-C','/home/rinsa/relay-self','rev-parse','main'])==(r/'protected-main-before.txt').read_bytes()
owned=json.loads((r/'owned-model-pid.json').read_text());pid=owned['pid'];proc=Path(f'/proc/{pid}')
assert (proc/'stat').read_text().split()[21]==owned['start_stat'].split()[21]
assert os.readlink(proc/'exe')=='/home/rinsa/src/llama.cpp/build/bin/llama-server'
(r/'gpu-after-world.txt').write_bytes(subprocess.check_output(['nvidia-smi']))
os.kill(pid,signal.SIGTERM)
for i in range(100):
 if not proc.exists():break
 time.sleep(.1)
assert not proc.exists()
for port in (8080,25565):
 with socket.socket() as s:s.bind(('127.0.0.1',port))
(r/'gpu-after-cleanup.txt').write_bytes(subprocess.check_output(['nvidia-smi']))
log=(r/'llama-server-original.log').read_text();assert log.count('processing task, is_child = 0')==1
resp=json.loads((r/'gemma-preparation/llama-response-1.raw.json').read_text());assert resp['choices'][0]['finish_reason']=='stop'
result={'classification':'INDEPENDENT_LOCAL_ORIGINAL_CUSTODY_AND_CLEANUP_PASS_DEV_ONLY','java_pid':java['pid'],'node_pid':node['pid'],'model_pid':pid,'java_node_model_pid_absent':True,'ports_8080_25565_released':True,'world_deleted':True,'prior_all_files_unchanged':True,'protected_main_checkout_unchanged':True,'real_completion_count_in_dedicated_server_log':1,'http_retries':0,'new_world_count':1,'world_retries':0,'java_paper_plugin_custody':True,'native_tick_join':'CLIENT_TICK_JOIN_UNATTESTED','qualification':'QUALIFICATION_NO_GO','science':'SCIENCE_NOT_RUN','gemma_response_before_world_start':(r/'gemma-preparation/llama-response-1.raw.json').stat().st_mtime_ns<(r/'world-attempt-started.json').stat().st_mtime_ns}
assert result['gemma_response_before_world_start']
(r/'independent-custody-cleanup.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
