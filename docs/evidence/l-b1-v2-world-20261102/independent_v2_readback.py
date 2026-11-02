import json,hashlib,subprocess,socket
from pathlib import Path
from tools.l_mp11_next_trial_gate import read_proc_status
from tools.l_mp11_gemma_structured_preflight import _check_schema_output,_unique_object,verify_preflight_report
from adapters.mineflayer.l_mp11_gemma_wire_contract import enforce_gemma_thinking_off,REQUIRED,pin_gemma_wire
from adapters.mineflayer.l_mp11_b1_forecast_contract import V2_EXTRA_FIELDS
r=Path(__file__).parent;w=r/'world';report=json.loads((w/'report.json').read_text())
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
checks={'wire':[]}
verify_preflight_report(r/'gemma-strict-wire-probe/gemma-structured-preflight.json',endpoint='http://127.0.0.1:8080/v1/chat/completions',model='relay-self-gemma4-12b-q4km',b1_contract_v2=True)
for i in (1,2):
 req=json.loads((w/f'llama-request-{i}.raw.json').read_text());res=json.loads((w/f'llama-response-{i}.raw.json').read_text());journal=json.loads((w/f'llama-http-{i}.json').read_text());frozen=json.loads((w/f'l2-frozen-{i}.json').read_text())
 assert req==journal['request'] and res==journal['response']
 assert pin_gemma_wire(dict(req),evidence_ids=True,b1_contract_v2=True)==req
 enforce_gemma_thinking_off(res)
 choice=res['choices'][0];assert choice['finish_reason']=='stop'
 text=choice['message']['content'];output=json.loads(text,object_pairs_hook=_unique_object)
 assert set(output)==set(REQUIRED)|V2_EXTRA_FIELDS
 _check_schema_output(output,req,b1_contract_v2=True)
 assert text==frozen['attempt']['result']['text']
 assert frozen['proposal']==report['l_mp11_live_l2']['proposals'][i-1]
 assert frozen['attempt']==report['l_mp11_live_l2']['attempt_originals'][i-1]
 assert report['mp11_g2']['typed_s16_actions'][2]['action_id'] not in req['messages'][1]['content']
 checks['wire'].append({'ordinal':i,'output':output,'request_sha256':sha(w/f'llama-request-{i}.raw.json'),'response_sha256':sha(w/f'llama-response-{i}.raw.json'),'finish_reason':choice['finish_reason'],'usage':res['usage'],'reasoning_tokens':res['usage'].get('completion_tokens_details',{}).get('reasoning_tokens','UNREPORTED'),'proposal_sha256':frozen['proposal']['proposal_sha256']})
payload=json.loads(req['messages'][1]['content']);feedback=[x['value'] for x in payload['context'] if x['key']=='previous_L2_hypothesis_typed_feedback'][0]
h1=report['l_mp11_live_l2']['proposals'][0];h2=report['l_mp11_live_l2']['proposals'][1]
assert feedback['previous_proposal_sha256']==h1['proposal_sha256']
assert feedback['previous_prediction_m']==h1['predicted_wait_total_m']
assert feedback['prior_prediction_abs_error_m']==(None if h1['predicted_wait_total_m'] is None else abs(h1['predicted_wait_total_m']-feedback['target_observed_m']))
checks['feedback']=feedback
checks['wait8_totals_m']=[sum(v) for v in report['mp11_g3']['motion_m']]
checks['typed_s16']=report['mp11_g2']['typed_s16_actions']
assert checks['paper_sha256'] if False else True
checks['paper_sha256']=sha(w/'paper-stdout-original.log.raw');assert checks['paper_sha256']==sha(w/'paper-stdout-original.log')==report['mp11_g3']['original_sha256']
raw=w/'native-stdout/w3-node-stdout.raw.jsonl';receipt=report['w3_node_stdout_capture'];assert sha(raw)==receipt['stdout_sha256'] and raw.stat().st_size==receipt['byte_count'];assert receipt['eof_observed'] and receipt['shutdown_ack_count']==1 and receipt['process_exit_code']==0
checks['native']={'seq_range':[receipt['first_seq'],receipt['last_seq']],'frame_count':len(raw.read_text().splitlines()),'sha256':sha(raw),'shutdown_ack':receipt['shutdown_ack_count']}
processes={}
for line in (r/'l-next-world-owned-processes.jsonl').read_text().splitlines():
 for p in json.loads(line)['owned_processes']:
  if Path(p['exe']).name in ('java','node'):processes[(p['pid'],p['start_ticks'])]=p
assert {Path(p['exe']).name for p in processes.values()}=={'java','node'}
checks['world_cleanup']=[]
for p in processes.values():
 now=read_proc_status(p['pid']);gone=now is None or now['start_ticks']!=p['start_ticks'];assert gone
 if Path(p['exe']).name=='java':assert not Path(p['cwd']).exists()
 checks['world_cleanup'].append({'identity':p,'owned_pid_gone':gone,'cwd_removed':not Path(p['cwd']).exists()})
with socket.socket() as s:s.bind(('127.0.0.1',25565))
checks['port25565']='BIND_PASS'
checks['mandatory_audits']=json.loads((w/'mandatory-audit-status.json').read_text());assert all(x['status']=='PASS' for x in checks['mandatory_audits'].values())
checks['scope']={k:report['l_mp11_live_l2'][k] for k in ('experiments_selected_and_executed_by_l2','new_action_issuers','learning_admissions','l0_promotions')};assert all(v==0 for v in checks['scope'].values())
checks['formal_source_status']='PASS';checks['semantic_judgment']='SEPARATE_MANUAL_REVIEW_REQUIRED'
with (r/'independent-final-readback.json').open('x') as f:json.dump(checks,f,indent=2)
print(json.dumps(checks,indent=2))
