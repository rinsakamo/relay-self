import shutil,json,hashlib,subprocess
from pathlib import Path
r=Path(__file__).parent;old=Path('/home/rinsa/evidence/l-cognitive-loop-20261102T034000Z')
shutil.copytree(old/'node-runtime',r/'node-runtime')
shutil.copyfile(old/'paper-active-config.yml',r/'paper-active-config.yml')
s=(old/'run_new_world_once.py').read_text().replace("assert '170 passed' in (r/'offline.log').read_text()","assert '192 passed' in (r/'offline-pytest.log').read_text()").replace("assert '12 passed' in (r/'gate-final.log').read_text()","assert '31 passed' in (r/'w3-custody.log').read_text()")
s=s.replace("'L_MP11_PAPER_EOF_DEV')","'L_MP11_PAPER_EOF_DEV','L_MP11_B1_CONTRACT_V2_DEV')")
s=s.replace("'--l-mp11-paper-eof-dev','--l-mp11-gemma-preflight-report'","'--l-mp11-paper-eof-dev','--l-mp11-b1-contract-v2-dev','--l-mp11-gemma-preflight-report'")
s=s.replace("'docs/l-cognitive-loop-prereg-20261102.md'","'docs/l-b1-explicit-forecast-abstention-20261102.md'")
(r/'run_new_world_once.py').write_text(s)
print('ASSETS_PREPARED')
