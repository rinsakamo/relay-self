"""Mutate byte copies only; never edit originals or reconstruct SelfBody."""
import json
from copy import deepcopy
from pathlib import Path
from adapters.mineflayer.m02_paper_dev.s50_selfbody_motion_source import project_s50_body_motion_source
from adapters.mineflayer.l23_paper_s7_settling import _paper_rows
r=Path(__file__).parent;report=json.loads((r/'s49-report.json').read_bytes());po=(r/'server.log').read_bytes();co=(r/'client-packet-original.jsonl').read_bytes();rb=report['l23_paper']['readback'];inputs=_paper_rows(po,'S50_DEV_INPUT_TICK ')
base=dict(paper_original=po,client_original=co,l23_source_readback=rb,session_id=report['session_id'],action_id=report['actual_native_actions'][0]['action'],world=rb['paper_world'],subject_uuid=inputs[0]['subject_uuid'],first_tick=rb['paper_first_tick'])
cases={}
for attack in ['missing_paper','missing_client','missing_paper_tick','incomplete_node','wrong_world']:
 args=deepcopy(base)
 if attack=='missing_paper':args['paper_original']=b''
 elif attack=='missing_client':args['client_original']=b''
 elif attack=='missing_paper_tick':args['paper_original']=b'\n'.join(line for line in po.splitlines() if not(b'S50_DEV_INPUT_TICK ' in line and b'index=4 ' in line))+b'\n'
 elif attack=='incomplete_node':args['client_original']=b'\n'.join(co.splitlines()[:-1])+b'\n'
 elif attack=='wrong_world':args['world']='00000000-0000-0000-0000-000000000000'
 try:project_s50_body_motion_source(**args)
 except ValueError as exc:cases[attack]={'rejected':True,'error':type(exc).__name__,'reason':str(exc)}
 else:raise AssertionError('source negative admitted: '+attack)
(r/'negative-source-readback.json').write_text(json.dumps(cases,indent=2)+'\n');print('5 real-source byte-copy negatives rejected')
