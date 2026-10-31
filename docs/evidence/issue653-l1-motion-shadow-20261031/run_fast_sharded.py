from pathlib import Path
import os,re,subprocess,json,time
root=Path(__file__).parent
files=re.findall(r'tests/\w+\.py',(root/'run_fast.sh').read_text())
env=os.environ.copy();env['PATH']='/home/rinsa/.nvm/versions/node/v22.22.2/bin:'+env['PATH'];env['PYTHONPATH']='src:tests:.';env['PYTHONDONTWRITEBYTECODE']='1'
runs=[]
for n in range(4):
    names=files[n::4];log=(root/f'fast-final-shard-{n}.log').open('xb')
    argv=['/home/rinsa/relay-self-s60b1-venv/bin/python','-m','pytest','-o','addopts=','-q',*names]
    p=subprocess.Popen(argv,env=env,stdout=log,stderr=subprocess.STDOUT)
    runs.append((n,p,log,names))
result=[]
for n,p,log,names in runs:
    rc=p.wait();log.close();result.append({'shard':n,'exit':rc,'files':names})
(root/'fast-final-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps([{'shard':r['shard'],'exit':r['exit']} for r in result]))
raise SystemExit(any(r['exit'] for r in result))
