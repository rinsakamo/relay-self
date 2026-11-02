import shutil,json,hashlib
from pathlib import Path
r=Path(__file__).parent;d=Path('/home/rinsa/work/l-z2b-real-validation-20261102/docs/evidence/l-z2b-real-20261102')
d.mkdir(parents=True)
for p in r.iterdir():
 if p.is_file() and p.suffix!='.jar':shutil.copyfile(p,d/p.name)
for name in ['gemma-preparation','priors','world-evidence']:shutil.copytree(r/name,d/name)
for p in d.rglob('*'):
 if p.is_file():p.chmod(0o644)
manifest={str(p.relative_to(d)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(d.rglob('*')) if p.is_file()}
(d/'SHA256SUMS.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
print(len(manifest),'files',sum(p.stat().st_size for p in d.rglob('*') if p.is_file()),'bytes')
