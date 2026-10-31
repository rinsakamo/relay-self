"""Read sealed originals after exit; never send commands or change originals."""
import json, math, hashlib, socket
from pathlib import Path
from dataclasses import asdict
from collections import Counter
from adapters.mineflayer.l16_first_action_goal_originals import L16GoalPlan
from adapters.mineflayer.l22_post_s16_settling import inspect_l22_settling
from adapters.mineflayer.l23_paper_s7_settling import inspect_l23_paper_s7, _paper_rows
from tools.s50_l23_packet_world_readback import audit
r=Path('/home/rinsa/work/selfbody-s16-s50-evidence-20261031/run1'); c=r/'capture'
report=json.loads((r/'s49-report.json').read_bytes())
plan_raw=(c/'l16_pre_world_goal_plan.json').read_bytes(); p=json.loads(plan_raw)
plan=L16GoalPlan(p['target_x'],p['target_z'],p['tolerance_m'],p['stable_probe_delta_max_m'])
assert plan.original_bytes()==plan_raw
terminal=json.loads((c/'l18_s16_terminal_original.jsonl').read_bytes())
args=dict(received_original=(c/'native_bridge_received_original.jsonl').read_bytes(),sent_original=(c/'native_bridge_sent_original.jsonl').read_bytes(),s7_receipt=json.loads((c/'native_bridge_source_receipt.json').read_bytes()),s16_original=(c/'l18_s16_terminal_original.jsonl').read_bytes(),plan=plan,action_id=terminal['action_id'],session_id=terminal['session_id'])
paper=(r/'server.log').read_bytes(); begin=_paper_rows(paper,'S50_DEV_WAIT_BEGIN ')
l22=asdict(inspect_l22_settling(**args));l23=asdict(inspect_l23_paper_s7(**args,paper_original=paper,expected_world=begin[0]['world']))
# Compare JSON normalized tuples to report lists.
assert json.loads(json.dumps(l22))==report['l22_settling']['audit']
assert json.loads(json.dumps(l23))==report['l23_paper']['readback']
packet=audit(r/'s49-report.json',r/'server.log',r/'client-packet-original.jsonl',c)
rows=[json.loads(s) for s in (r/'client-packet-original.jsonl').read_bytes().splitlines()]
counts=Counter(x['packet_name'] for x in rows if x['kind']=='PACKET_WRITE_RETURNED')
effects=[x for x in rows if x['kind']=='NATIVE_CONTROL_EFFECT_RETURNED']
assert [x['effect'] for x in effects]==['set_control','clear_controls','shutdown_clear_controls']
assert effects[0]['controls_after_sample']['back'] is True
assert sum(effects[0]['controls_after_sample'].values())==1
assert all(not any(x['controls_after_sample'].values()) for x in effects[1:])
physics=[x for x in rows if x['kind']=='PHYSICS_EVENT_SAMPLE']
assert [x['physics_index'] for x in physics]==list(range(1,len(physics)+1))
assert all(0<=x.get('last_physics_index',0)<=len(physics) for x in rows[:-1])
wait=_paper_rows(paper,'S50_DEV_WAIT_TICK ');inputs=_paper_rows(paper,'S50_DEV_INPUT_TICK ')
assert [x['tick'] for x in inputs]==[x['tick'] for x in wait]
assert [int(x['index']) for x in inputs]==list(range(1,9))
assert len({x['subject_uuid'] for x in inputs})==1
frames=[json.loads(s) for s in args['received_original'].splitlines()]
commands=[json.loads(s) for s in args['sent_original'].splitlines()]
raw_effects=[x for x in frames if x['type']=='effect_result']
assert all(x['result']=='applied' and x['error'] is None for x in raw_effects)
assert not any(x['type']=='adapter_error' for x in frames)
cleanup=json.loads((r/'cleanup.json').read_bytes())
assert cleanup['runner_exit']==0 and cleanup['port_rebind']
assert all(x['pid_gone'] for x in cleanup['owned_processes'])
assert cleanup['world_roots'] and all(x['removed'] for x in cleanup['world_roots'])
with socket.socket() as s: s.bind(('127.0.0.1',25565))
result={'status':'DEV_PASS','l22':l22,'l23':l23,'packet':packet,'s16_original':terminal,'raw_effects':raw_effects,'raw_commands':commands,'packet_counts':{k:counts[k] for k in ['player_input','position','position_look','flying','look','entity_action']},'physics_samples':len(physics),'control_effects':effects,'trace_footer':rows[-1],'paper_phases':_paper_rows(paper,'M02_DEV_S50_PHASE '),'paper_begin':begin,'paper_wait':wait,'paper_input':inputs,'paper_input_events':_paper_rows(paper,'S50_DEV_INPUT_EVENT '),'paper_tick_displacements_m':[{'tick':int(x['tick']),'distance_m':math.dist([float(x['from_'+k]) for k in ['x','y','z']],[float(x[k]) for k in ['x','y','z']])} for x in wait],'cleanup':cleanup,'write_exception_observation_limit':'Only returned writes are traced. No adapter_error, rejected effect or process failure observed; caught write exceptions elsewhere are not instrumented.','clock_alignment':'NOT_ATTESTED'}
for name,data in [('independent-original-readback.json',result),('l22-diagnostic.json',l22),('l23-readback.json',l23)]:
 (r/name).write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['status','packet_counts','physics_samples','control_effects','paper_tick_displacements_m']}))

from tools.s50_selfbody_motion_readback import review_originals
producer=review_originals(report_original=(r/'s49-report.json').read_bytes(),paper_original=paper,client_original=(r/'client-packet-original.jsonl').read_bytes(),subject_uuid=inputs[0]['subject_uuid'])
join=report['selfbody_s50_join']
assert producer==join['source']
assert join['classification']=='DEV_WORLD_SELFBODY_S16_S50_JOIN_PASS'
assert join['in_process_original_identity_checks'] and join['same_selfbody_view_identity'] and join['same_s16_identity']
assert join['observation']['session_id']==terminal['session_id']
assert join['observation']['native_seq']==terminal['after_seq']
assert join['next_cognitive_epoch_referenced'] is False
assert report['selfbody_lease_final']['status']=='ONE_S50_DIAGNOSTIC_JOIN_CONSUMED'
assert report['selfbody_lease_final']['typed_original_ready'] is False
assert report['selfbody_lease_final']['original_closures_seen']==1
result['selfbody_join_diagnostic_rechecked']=True
result['typed_authenticity_scope']='Runtime identity assertions only; archived JSON is not a typed closure'
(r/'independent-original-readback.json').write_text(json.dumps(result,indent=2)+'\n')
print('SelfBody/S50 independent diagnostic correlation PASS; typed identity was checked only in live host')
