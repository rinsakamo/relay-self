"""Read-only failed-run facts. Never promotes either mandatory audit FAIL."""
import json,hashlib,socket,math
from pathlib import Path
from dataclasses import asdict
from adapters.mineflayer.l_mp11_paper_eof_envelope import seal_after_shutdown,verified_complete_lines
from adapters.mineflayer.l_mp11_live_previous_action import LivePriorLedger
from adapters.mineflayer.l_mp11_live_l2_shadow import request_for_live_l2
from adapters.mineflayer.l_mp11_typed_feedback import numeric_value
from adapters.llama_cpp.relay_engine import render_llama_cpp_open_request
r=Path(__file__).parent
report=json.loads((r/'report.json').read_text());assert report['status']=='FAIL'
raw=(r/'paper-stdout-original.log.raw').read_bytes()
assert raw==(r/'paper-stdout-original.log').read_bytes()
assert report['mp11_paper_eof_predeclared'] is True
manifest=json.loads((r/'preworld-manifest.json').read_text());assert manifest['eof_predeclared'] is True
assert json.loads((r/'WORLD_ATTEMPT_STARTED.json').read_text())['manifest_sha256']==hashlib.sha256((r/'preworld-manifest.json').read_bytes()).hexdigest()
envelope=asdict(seal_after_shutdown(raw,predeclared=True))
verified_complete_lines(raw,envelope,predeclared=True)
w=report['l_mp11_live_prefix']['observations'][0]
assert len(report['l_mp11_live_prefix']['observations'])==1
assert hashlib.sha256(raw[:w['paper_prefix_length']]).hexdigest()==w['paper_prefix_sha256']
attempt=report['l_mp11_live_l2']['attempt_originals'][0]
source=json.loads(attempt['request']['context'][1]['value_json'])[0]
ledger=LivePriorLedger(session_id=report['session_id'],world_uuid=source['world_uuid'],subject_uuid=source['subject_uuid'])
obs=ledger.accept_completed(raw[:w['paper_prefix_length']],action_id=w['action_id'],marker_id=source['marker_id'],native_s16_seq=w['native_s16_seq'],native_outcome='S16_OUTCOME')
assert asdict(obs)=={k:tuple(v) if isinstance(getattr(obs,k),tuple) else v for k,v in source.items()}
req=request_for_live_l2(ledger)
assert json.loads(json.dumps(asdict(req)))==attempt['request']
http=json.loads((r/'llama-http-1.json').read_text())
wire_req=json.loads((r/'llama-request-1.raw.json').read_bytes())
wire_response=json.loads((r/'llama-response-1.raw.json').read_bytes())
assert http['request']==wire_req and http['response']==wire_response
expected=render_llama_cpp_open_request(req,model='relay-self-gemma4-12b-q4km')
expected.update(max_tokens=512,response_format={'type':'json_object'})
assert wire_req==expected
assert attempt['started_monotonic_ns']<http['started_monotonic_ns']<http['finished_monotonic_ns']<attempt['finished_monotonic_ns']
response=wire_response['choices'][0];assert response['finish_reason']=='length'
text=response['message']['content'];candidate=json.loads(text)
checks=[]
for c in candidate['numeric_evidence_refs']:
    expected_value=numeric_value(tuple(ledger.history),c['metric_role'],c['trial_ordinal'],c['pair_index'],feedback=None)
    checks.append({**c,'expected_value_m':expected_value,'matches_typed_source':math.isclose(c['value_m'],expected_value,rel_tol=0,abs_tol=1e-8)})
node=(r/'native-stdout/w3-node-stdout.raw.jsonl').read_bytes()
seal=json.loads((r/'native-stdout/w3-node-stdout-receipt.json').read_text())
assert hashlib.sha256(node).hexdigest()==seal['stdout_sha256']==report['w3_node_stdout_capture']['stdout_sha256']
frames=[json.loads(x) for x in node.splitlines()]
assert [f['seq'] for f in frames]==list(range(len(frames)))
assert {f['session_id'] for f in frames}=={report['session_id']}
aid=w['action_id'];dispatch=[f for f in frames if f.get('action_id')==aid and f.get('result')=='applied']
clear=[f for f in frames if f.get('action_id')==aid+'-s15-clear' and f.get('effect')=='clear_controls' and f.get('result')=='applied']
before=[f for f in frames if f.get('request_id')==f"s15:{report['session_id']}:{aid}:before"]
after=[f for f in frames if f.get('request_id')==f"s15:{report['session_id']}:{aid}:after"]
assert len(dispatch)==len(clear)==len(before)==len(after)==1
assert before[0]['seq']<dispatch[0]['seq']<clear[0]['seq']<after[0]['seq']==w['native_s16_seq']
all_dispatch=[f for f in frames if f.get('type')=='action_result' and f.get('effect')=='set_control']
# Count actual original movement effect independently of the host list, which
# is appended only after the failing OPEN callback and therefore remains empty.
print('DISPATCH_FRAME_TYPE',dispatch[0]['type'])
move_effects=[f for f in frames if f.get('effect')==dispatch[0]['effect'] and f.get('result')=='applied']
assert len(move_effects)==1
b=before[0]['snapshot']['position'];a=after[0]['snapshot']['position']
movement=math.dist([b[k] for k in ('x','y','z')],[a[k] for k in ('x','y','z')])
snaps=[json.loads(x) for x in (r/'world-process-snapshots.jsonl').read_text().splitlines()]
children={p['pid']:p for row in snaps for p in row['processes']}
assert len(children)==2
worlds={p['cwd'] for p in children.values() if 'minecraft.jar' in ' '.join(p['argv'])}
assert len(worlds)==1
cleanup={'owned_child_pids_absent':all(not Path('/proc',str(pid)).exists() for pid in children),'model_pid_absent':not Path('/proc/103190').exists(),'world_directory_absent':all(not Path(p).exists() for p in worlds),'node_exit':report['node_exit'],'java_exit':report['server_exit']}
for port in (25565,8080):
    with socket.socket() as s:s.bind(('127.0.0.1',port))
    cleanup[f'port_{port}_bindable']=True
assert all(v is True or type(v)is int and v==0 for v in cleanup.values())
result={'classification':'FAILED_WORLD_REMAINS_FAIL_PARTIAL_ORIGINAL_FACTS_ONLY','mandatory_g3':'FAIL','mandatory_live_prefix':'FAIL','world_attempts':1,'retries':0,'sessions':1,'actual_original_actions_from_raw':1,'original_s15_clear':1,'typed_s16_outcome':1,'native_sequence':{'before':before[0]['seq'],'dispatch':dispatch[0]['seq'],'clear':clear[0]['seq'],'s16_after':after[0]['seq']},'movement_m':movement,'original_host_actual_native_actions_count':len(report['actual_native_actions']),'host_list_incomplete_due_to_open_failure':True,'world_uuid':source['world_uuid'],'session_id':report['session_id'],'prefix_sha_matched':'1/1; 3/3 NOT_REACHED','wait_ticks':list(obs.paper_wait_ticks),'wait8_total_m':obs.paper_wait_total_m,'paper_forecast_pairs':7,'eof_shape_only':envelope,'genuine_http_attempts':1,'validated_open_calls':0,'provider_finish_reason':response['finish_reason'],'usage':wire_response['usage'],'http_elapsed_s':(http['finished_monotonic_ns']-http['started_monotonic_ns'])/1e9,'candidate_not_admitted':candidate,'numeric_citation_checks':checks,'free_text_error':'0.032m called prediction error, but it is pair1 predicted displacement 0.0321699224m; actual pair1 abs error 0.0226263175m. No global-offset causal evidence.','H1':'NOT_ADMITTED','H2':'NOT_REACHED','prior_prediction_next_observation_error':'NOT_AVAILABLE','A':'FAIL_VALID_OPEN_0_OF_2','B1':'NOT_REACHED','B2':'NOT_ESTABLISHED','C':'NOT_RUN_BY_DESIGN','cleanup':cleanup,'child_identities':list(children.values()),'learning_admissions':0,'l0_promotions':0,'qualification':'NO_GO','science':'NOT_RUN'}
with (r/'independent-failed-run-readback.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result,indent=2))
