import hashlib,json,subprocess,urllib.request
from pathlib import Path
b=Path('/home/rinsa/evidence/l-z2c-real-h2-20261103T030200Z'); own=json.loads((b/'owned-model-pid.json').read_text()); pid=own['pid']; p=Path(f'/proc/{pid}')
cmd=p.joinpath('cmdline').read_bytes().split(b'\0')[:-1]; assert [x.decode() for x in cmd]==own['argv']
maps=p.joinpath('maps').read_text(); gguf=Path(own['argv'][2]); assert str(gguf) in maps and 'libggml-cuda' in maps
sha=hashlib.file_digest(gguf.open('rb'),'sha256').hexdigest(); assert sha=='c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed'
assert str(p.joinpath('exe').resolve())==own['argv'][0]
for route in ('health','v1/models','props'):
 raw=urllib.request.urlopen('http://127.0.0.1:18083/'+route,timeout=5).read(); (b/(route.replace('/','-')+'.json')).write_bytes(raw)
models=json.loads((b/'v1-models.json').read_bytes()); assert any(x['id']=='relay-self-gemma4-12b-q4km' for x in models['data'])
listeners=subprocess.check_output(['ss','-ltnp'],text=True); assert f'pid={pid},' in next(x for x in listeners.splitlines() if ':18083 ' in x)
procs=[]
for path in Path('/proc').glob('[0-9]*/comm'):
 try:
  if path.read_text().strip() in ('llama-server','ollama','vllm'): procs.append(int(path.parent.name))
 except OSError: pass
assert procs==[pid],procs
report={'pid':pid,'argv':own['argv'],'exe':str(p.joinpath('exe').resolve()),'stat':p.joinpath('stat').read_text(),'gguf_sha256':sha,'maps':maps,'listeners':listeners,'competing_model_pids':[],'gpu':subprocess.check_output(['nvidia-smi'],text=True),'endpoint':'http://127.0.0.1:18083/v1/chat/completions','model':'relay-self-gemma4-12b-q4km'}
assert str(pid) in report['gpu']; (b/'runtime-pre-http.json').write_text(json.dumps(report,indent=2)+'\n')
print('LIVE_RUNTIME_GGUF_MAPPING_GPU_ENDPOINT_PASS',pid)
