"""H5 separate-process read-only audit. Never invokes World or Action."""
import json, hashlib, sys
from pathlib import Path
from tools.selfbody_l1_shadow_readback import review
from tools.l_bcg_world_report_preflight import review_bcg_host_report
root=Path(sys.argv[1])
original=review(root)
report=json.loads((root/'s49-report.json').read_bytes())
host=review_bcg_host_report(report)
s=report['l_bcg_shadow']
assert s['action_authority'] is False
assert s['used_physical_training_worlds']==0
assert s['original_selection']=='WAIT'
assert s['advice']=='DEFER_UNKNOWN'
assert s['reason']=='CURRENT_GOAL_GAIT_P1_M_OBSTACLE_SOURCE_NOT_ADMITTED'
manifest={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file()}
result=dict(classification='DEV_H5_ORIGINAL_CHAIN_AND_BCG_DEFER_VERIFIED',original=original,host_self_consistency=host,l_bcg_shadow=s,original_sha256=manifest,worlds=1,actions=1,retries=0,model_calls=0,qualified_training_worlds=0,effective_clear='NOT_ATTESTED',goal='UNDETERMINED',qualification='NO_GO',science='NOT_RUN',ceiling='Independent process correlation of saved S7/S16/Paper collector originals; no external physical attestation')
with Path(sys.argv[2]).open('x') as out:json.dump(result,out,indent=2);out.write('\n')
print(result['classification'])
