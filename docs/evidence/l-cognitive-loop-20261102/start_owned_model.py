import subprocess,socket,json,time,os,urllib.request,hashlib
from pathlib import Path
from tools.l_mp11_next_trial_gate import read_proc_status
r=Path(__file__).parent
for port in (8080,25565):
 with socket.socket() as s:s.bind(('127.0.0.1',port))
assert not any('llama-server' in (p/'comm').read_text() for p in Path('/proc').iterdir() if p.name.isdigit() and (p/'comm').exists())
argv=['/home/rinsa/src/llama.cpp/build/bin/llama-server','--model','/home/rinsa/models/gguf/gemma-4-12B-it-Q4_K_M.gguf','--alias','relay-self-gemma4-12b-q4km','--host','127.0.0.1','--port','8080','-ngl','999','-c','8192','-np','1','--no-context-shift','--flash-attn','on','--jinja']
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  while b:=f.read(1048576):h.update(b)
 return h.hexdigest()
(r/'model-files.sha256.json').write_text(json.dumps({p:sha(p) for p in (argv[0],argv[2])},indent=2))
(r/'llama-version.txt').write_bytes(subprocess.check_output([argv[0],'--version'],stderr=subprocess.STDOUT))
with (r/'llama-server-original.log').open('xb') as f:p=subprocess.Popen(argv,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
(r/'owned-model-pid.json').write_text(json.dumps(read_proc_status(p.pid),indent=2))
for i in range(120):
 if p.poll() is not None:raise RuntimeError(f'llama exited {p.returncode}')
 try:
  with urllib.request.urlopen('http://127.0.0.1:8080/health',timeout=2) as q:data=q.read()
  (r/'health.json').write_bytes(data);break
 except Exception:time.sleep(.5)
else:raise RuntimeError('model readiness timeout')
for url,name in [('v1/models','v1-models.json'),('props','props.json'),('slots','slots.json')]:
 with urllib.request.urlopen('http://127.0.0.1:8080/'+url,timeout=5) as q:(r/name).write_bytes(q.read())
pd=Path('/proc')/str(p.pid)
identity=read_proc_status(p.pid);identity['maps']=(pd/'maps').read_text()
assert argv[2] in identity['maps']
(r/'model-process-identity.json').write_text(json.dumps(identity,indent=2))
props=json.loads((r/'props.json').read_text());(r/'chat-template-original.jinja').write_text(props['chat_template'])
(r/'gpu-loaded.txt').write_bytes(subprocess.check_output(['nvidia-smi']))
print('OWNED_MODEL_READY',p.pid)
