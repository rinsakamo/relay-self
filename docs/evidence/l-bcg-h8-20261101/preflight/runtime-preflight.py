import json,hashlib,socket,subprocess,platform,os
from pathlib import Path
root=Path('/home/rinsa/work/l-bcg-h8-evidence-20261101/preflight')
pins=json.loads(Path('/home/rinsa/work/selfbody-s16-s50-evidence-20261031/assets/pins.json').read_text())
assets={k:{**pins[k], 'actual_sha256':hashlib.sha256(Path(pins[k]['path']).read_bytes()).hexdigest()} for k in ('server','plugin','config')}
for v in assets.values():v['matches']=v['sha256']==v['actual_sha256']
def run(argv):
 try:
  p=subprocess.run(argv,capture_output=True,text=True,errors='replace',timeout=15);return {'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
 except OSError as e:return {'error':str(e)}
with socket.socket() as sock:
 try:sock.bind(('127.0.0.1',25565));port=True
 except OSError:port=False
mf=Path('/home/rinsa/work/selfbody-s16-s50-evidence-20261031/node-runtime/node_modules/mineflayer/package.json')
r={'world_grant':'L_BCG_CONTINUING_DEV_GRANT_6552384315','world_runs':0,'kernel':platform.release(),'os_release':Path('/etc/os-release').read_text(),'windows':run(['cmd.exe','/c','ver']),'python':run(['/home/rinsa/relay-self-s60b1-venv/bin/python','-V']),'java':run(['/usr/lib/jvm/java-21-openjdk-amd64/bin/java','-version']),'node':run(['/home/rinsa/.nvm/versions/node/v22.22.2/bin/node','-v']),'mineflayer':json.loads(mf.read_text())['version'],'assets':assets,'port_25565_bindable':port,'gpu':run(['nvidia-smi','--query-gpu=name,memory.used,utilization.gpu','--format=csv,noheader']),'node_options_present':bool(os.environ.get('NODE_OPTIONS')),'existing_s49_world_dirs':[str(p) for p in Path('/tmp').glob('relay-self-s49-*')],'runner':'adapters.mineflayer.self_body_s50_world_dev','world_creation':'existing TemporaryDirectory; only after dedicated grant','paper_profile':pins['intervention'],'effective_clear':'NOT_ATTESTED','cleanup':'NO_WORLD_OR_OWNED_NODE_JAVA_SERVER_STARTED'}
(root/'runtime-preflight.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r,indent=2))
