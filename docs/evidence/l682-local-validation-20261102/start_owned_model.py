import subprocess,socket,json,time,os,urllib.request
from pathlib import Path
r=Path(__file__).parent
for port in (8080,25565):
 with socket.socket() as s:s.bind(('127.0.0.1',port))
procs=subprocess.check_output(['ps','-eo','pid,args'],text=True)
assert not any('/llama-server ' in line or ' -jar minecraft.jar' in line for line in procs.splitlines()),'existing runtime'
argv=['/home/rinsa/src/llama.cpp/build/bin/llama-server','--model','/home/rinsa/models/gguf/gemma-4-12B-it-Q4_K_M.gguf','--alias','relay-self-gemma4-12b-q4km','--host','127.0.0.1','--port','8080','-ngl','999','-c','8192','-np','1','--no-context-shift','--flash-attn','on','--jinja']
with (r/'llama-server-original.log').open('xb') as f:p=subprocess.Popen(argv,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
(r/'owned-model-pid.json').write_text(json.dumps({'pid':p.pid,'argv':argv}))
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
(r/'model-process-identity.json').write_text(json.dumps({'pid':p.pid,'exe':os.readlink(pd/'exe'),'argv':(pd/'cmdline').read_bytes().decode().split('\0')[:-1],'maps':(pd/'maps').read_text(),'stat':(pd/'stat').read_text()},indent=2))
(r/'gpu-loaded.txt').write_bytes(subprocess.check_output(['nvidia-smi']))
print('OWNED_MODEL_READY',p.pid)
