import hashlib,json,os,subprocess
from pathlib import Path
from tools.l_zombie_z2c_h2_original_feedback import original_z2b_h2_sources
base=Path('/home/rinsa/evidence/l-z2c-real-h2-20261103T030200Z')
root=Path.cwd()/'docs/evidence/l-z2b-real-20261102'
h1,world,receipt=original_z2b_h2_sources(root)
files={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file()}
assert subprocess.check_output(['git','diff','58d72e8e2a3e5c3c633e196ac8ee43cd43eba20e','HEAD','--',str(root)],text=True)==''
for name,value in [('preflight-original-readback.json',{'h1':h1,'world':world,'receipt':receipt}),('original-all-files-before.json',files)]:
 (base/name).write_text(json.dumps(value,indent=2)+'\n')
(base/'main-before.txt').write_bytes(subprocess.check_output(['git','-C','/home/rinsa/relay-self','status','--porcelain=v1','--branch']))
(base/'refs-before.txt').write_bytes(subprocess.check_output(['git','show-ref']))
(base/'gpu-before.txt').write_bytes(subprocess.check_output(['nvidia-smi']))
exe='/home/rinsa/src/llama.cpp/build/bin/llama-server'
version=subprocess.check_output([exe,'--version'],stderr=subprocess.STDOUT)
assert b'10874' in version
(base/'llama-version.txt').write_bytes(version)
argv=[exe,'--model','/home/rinsa/models/gguf/gemma-4-12B-it-Q4_K_M.gguf','--alias','relay-self-gemma4-12b-q4km','--host','127.0.0.1','--port','18083','-ngl','999','-c','8192','-np','1','--no-context-shift','--flash-attn','on','--jinja']
log=(base/'llama-server-original.log').open('xb')
p=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
(base/'owned-model-pid.json').write_text(json.dumps({'pid':p.pid,'argv':argv,'start_stat':Path(f'/proc/{p.pid}/stat').read_text()},indent=2)+'\n')
print(json.dumps({'original_files':len(files),'replayed':receipt['archived_files_checked'],'pid':p.pid}))
