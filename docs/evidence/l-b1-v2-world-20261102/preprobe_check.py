import json,subprocess,hashlib
from pathlib import Path
r=Path(__file__).parent
assert '192 passed' in (r/'offline-pytest.log').read_text()
assert '31 passed' in (r/'w3-custody.log').read_text()
assert 'All checks passed!' in (r/'ruff.log').read_text()
assert 'Repository contract check passed.' in (r/'contracts.log').read_text()
assert 'BUILD SUCCESS' in (r/'plugin-build.log').read_text()
assert not subprocess.check_output(['git','status','--porcelain']).strip()
assert subprocess.check_output(['git','rev-parse','HEAD']).decode().strip()==(r/'execution-head.txt').read_text().strip()
assert not (r/'gemma-strict-wire-probe').exists()
props=json.loads((r/'props.json').read_text());assert props['total_slots']==1 and props['default_generation_settings']['n_ctx']==8192
print('ALL_PREPROBE_GATES_PASS')
