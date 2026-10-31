import json,hashlib,sys
from pathlib import Path
from dataclasses import asdict
from adapters.mineflayer.l16_first_action_goal_originals import L16GoalPlan
from adapters.mineflayer.l22_post_s16_settling import inspect_l22_settling
from adapters.mineflayer.l23_paper_s7_settling import inspect_l23_paper_s7,_paper_rows
r=Path('/home/rinsa/work/s50-input-evidence-20261031')/sys.argv[1]; c=r/'capture'
received=(c/'native_bridge_received_original.jsonl').read_bytes(); sent=(c/'native_bridge_sent_original.jsonl').read_bytes();s16=(c/'l18_s16_terminal_original.jsonl').read_bytes(); terminal=json.loads(s16)
args=dict(received_original=received,sent_original=sent,s7_receipt=json.loads((c/'native_bridge_source_receipt.json').read_bytes()),s16_original=s16,plan=L16GoalPlan(0,0,.49,.05),action_id=terminal['action_id'],session_id=terminal['session_id'])
paper=(r/'server.log').read_bytes();begin=_paper_rows(paper,'S50_DEV_WAIT_BEGIN ')
summary={'l22':asdict(inspect_l22_settling(**args))}
try: summary['l23']=asdict(inspect_l23_paper_s7(**args,paper_original=paper,expected_world=begin[0]['world']))
except ValueError as exc: summary['l23']={'status':'PAPER_SOURCE_REJECTED','error':str(exc)}
frames=[json.loads(x) for x in received.splitlines()];commands=[json.loads(x) for x in sent.splitlines()]
summary['raw_effects']=[f for f in frames if f.get('type')=='effect_result']
summary['raw_commands']=commands
summary['s16_original']=terminal
summary['paper_phases']=_paper_rows(paper,'M02_DEV_S50_PHASE ')
summary['paper_begin']=begin
summary['paper_samples']=_paper_rows(paper,'S50_DEV_WAIT_TICK ')
summary['paper_log_line_numbers']=[{'line':i,'text':line} for i,line in enumerate(paper.decode().splitlines(),1) if any(k in line for k in ('M02_DEV_S50_PHASE ','S50_DEV_WAIT_BEGIN ','S50_DEV_WAIT_TICK '))]
summary['cleanup']=json.loads((r/'cleanup.json').read_bytes())
summary['classification']='DEV_ONLY / CLOCK_ALIGNMENT_NOT_ATTESTED / STABILITY_UNPROVEN / GOAL_UNDETERMINED / L10_PAIRS_0 / P1_WAIT_0 / QUALIFICATION_NO_GO / SCIENCE_NOT_RUN'
(r/'original-readback.json').write_text(json.dumps(summary,indent=2)+'\n')
(r/'l22-diagnostic.json').write_text(json.dumps(summary['l22'],indent=2)+'\n')
(r/'l23-readback.json').write_text(json.dumps(summary['l23'],indent=2)+'\n')
print(json.dumps({k:summary[k] for k in ('l22','l23','s16_original')},indent=2))
