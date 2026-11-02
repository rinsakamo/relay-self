import hashlib,json,subprocess,shutil
from pathlib import Path
r=Path(__file__).parent;repo=Path('/home/rinsa/work/l-z2b-real-validation-20261102')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
(r/'priors-before.json').write_text(json.dumps({str(p):sha(p) for p in (r/'priors').rglob('*') if p.is_file()},indent=2))
for p in (r/'priors').rglob('*'):
 if p.is_file():p.chmod(0o400)
(r/'protected-checkout-before.txt').write_bytes(subprocess.check_output(['git','-C','/home/rinsa/relay-self','status','--porcelain=v1']))
(r/'protected-main-before.txt').write_bytes(subprocess.check_output(['git','-C',str(repo),'rev-parse','main']))
(r/'assets').mkdir()
source=repo/'adapters/mineflayer/l_zombie_paper_dev/target/relay-l-zombie-paper-dev-0.1.0-dev.jar'
shutil.copyfile(source,r/'assets'/source.name)
for p in repo.rglob('__pycache__'):shutil.rmtree(p)
shutil.rmtree(source.parent)
(r/'worlds').mkdir();(r/'world-evidence').mkdir()
(r/'asset-sha256.json').write_text(json.dumps({str(p):sha(p) for p in [r/'assets'/source.name,Path('/home/rinsa/work/v8-five-world-20261017/assets/paper-1.21.8.jar')]},indent=2))
print((r/'asset-sha256.json').read_text())
