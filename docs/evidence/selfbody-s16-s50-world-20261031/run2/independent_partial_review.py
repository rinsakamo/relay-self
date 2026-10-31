"""Read-only partial audit: never change failed report or reconstruct typed owners."""
import json
from pathlib import Path
from dataclasses import asdict
from adapters.mineflayer.l16_first_action_goal_originals import L16GoalPlan
from adapters.mineflayer.l22_post_s16_settling import inspect_l22_settling
from adapters.mineflayer.l23_paper_s7_settling import inspect_l23_paper_s7, _paper_rows
from adapters.mineflayer.m02_paper_dev.s50_client_packet_source import inspect_s50_client_packets
from adapters.mineflayer.m02_paper_dev.s50_selfbody_motion_source import project_s50_body_motion_source
r=Path(__file__).parent;c=r/'capture';report=json.loads((r/'s49-report.json').read_bytes());p=json.loads((c/'l16_pre_world_goal_plan.json').read_bytes());plan=L16GoalPlan(p['target_x'],p['target_z'],p['tolerance_m'],p['stable_probe_delta_max_m']);terminal=json.loads((c/'l18_s16_terminal_original.jsonl').read_bytes());paper=(r/'server.log').read_bytes();client=(r/'client-packet-original.jsonl').read_bytes();begin=_paper_rows(paper,'S50_DEV_WAIT_BEGIN ');inputs=_paper_rows(paper,'S50_DEV_INPUT_TICK ')
args=dict(received_original=(c/'native_bridge_received_original.jsonl').read_bytes(),sent_original=(c/'native_bridge_sent_original.jsonl').read_bytes(),s7_receipt=json.loads((c/'native_bridge_source_receipt.json').read_bytes()),s16_original=(c/'l18_s16_terminal_original.jsonl').read_bytes(),plan=plan,action_id=terminal['action_id'],session_id=terminal['session_id'])
l22=asdict(inspect_l22_settling(**args));l23=asdict(inspect_l23_paper_s7(**args,paper_original=paper,expected_world=begin[0]['world']))
assert json.loads(json.dumps(l22))==report['l22_settling']['audit'];assert json.loads(json.dumps(l23))==report['l23_paper']['readback']
packet=inspect_s50_client_packets(client,paper,session_id=terminal['session_id'],marker_id=l23['marker_id'],world=l23['paper_world'])
source=asdict(project_s50_body_motion_source(paper_original=paper,client_original=client,l23_source_readback=json.loads(json.dumps(l23)),session_id=terminal['session_id'],action_id=terminal['action_id'],world=l23['paper_world'],subject_uuid=inputs[0]['subject_uuid'],first_tick=l23['paper_first_tick']))
cleanup=json.loads((r/'cleanup.json').read_bytes());assert cleanup['runner_exit']==1 and cleanup['port_rebind'];assert all(p['pid_gone'] for p in cleanup['owned_processes']);assert cleanup['world_roots'] and all(p['removed'] for p in cleanup['world_roots']);assert report['node_exit']==report['server_exit']==0
assert report['status']=='FAIL';assert report['selfbody_original_lease']['typed_original_ready'];assert report['selfbody_lease_final']['status']=='REVOKED_ON_INVALID_S50_SOURCE'
result={'classification':'PARTIAL_S49_S16_NATIVE_SELFBODY_READY_S50_SOURCE_PASS_JOIN_FAIL','report_unchanged_failure':True,'l22':l22,'l23':l23,'s50_packet':packet,'s50_producer':source,'typed_authenticity_scope':'Runtime lease diagnostic only; no archived reconstruction','cleanup':cleanup}
(r/'independent-partial-readback.json').write_text(json.dumps(result,indent=2)+'\n');print(result['classification'])
