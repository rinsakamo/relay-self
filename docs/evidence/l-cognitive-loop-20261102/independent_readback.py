import json,hashlib,os,signal,time,socket,subprocess
from pathlib import Path
from tools.l_mp11_next_trial_gate import read_proc_status
from tools.l_mp11_gemma_structured_preflight import _check_schema_output, _unique_object
from adapters.mineflayer.l_mp11_gemma_wire_contract import enforce_gemma_thinking_off,REQUIRED,pin_gemma_wire
r=Path(__file__).parent;w=r/'world';report=json.loads((w/'report.json').read_text())
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while b:=f.read(1048576):h.update(b)
 return h.hexdigest()
checks={}; wire=[]
for i in (1,2):
 req=json.loads((w/f'llama-request-{i}.raw.json').read_text());res=json.loads((w/f'llama-response-{i}.raw.json').read_text());journal=json.loads((w/f'llama-http-{i}.json').read_text());frozen=json.loads((w/f'l2-frozen-{i}.json').read_text())
 assert req==journal['request'] and res==journal['response']
 assert pin_gemma_wire(req,evidence_ids=True)==req
 enforce_gemma_thinking_off(res)
 choice=res['choices'][0];assert choice['finish_reason']=='stop'
 text=choice['message']['content'];output=json.loads(text,object_pairs_hook=_unique_object)
 assert set(output)==set(REQUIRED);_check_schema_output(output,req)
 assert text==frozen['attempt']['result']['text']
 assert frozen['proposal']==report['l_mp11_live_l2']['proposals'][i-1]
 assert frozen['attempt']==report['l_mp11_live_l2']['attempt_originals'][i-1]
 # Source replay independently performed by mandatory feedback audit.
 payload=json.loads(req['messages'][1]['content'])
 assert report['mp11_g2']['typed_s16_actions'][2]['action_id'] not in req['messages'][1]['content']
 wire.append({'ordinal':i,'request_sha256':sha(w/f'llama-request-{i}.raw.json'),'response_sha256':sha(w/f'llama-response-{i}.raw.json'),'finish_reason':choice['finish_reason'],'completion_tokens':res['usage']['completion_tokens'],'prompt_tokens':res['usage']['prompt_tokens'],'reasoning_content_present':'reasoning_content' in choice['message'],'reasoning_tokens':res['usage'].get('completion_tokens_details',{}).get('reasoning_tokens','UNREPORTED'),'full_schema_checked':True,'frozen_and_report_and_raw_match':True,'proposal_sha256':frozen['proposal']['proposal_sha256']})
feedback=[x['value'] for x in payload['context'] if x['key']=='previous_L2_hypothesis_typed_feedback'][0]
assert feedback['previous_proposal_sha256']==report['l_mp11_live_l2']['proposals'][0]['proposal_sha256']
assert feedback['previous_prediction_m'] is None and feedback['prior_prediction_abs_error_m'] is None
checks['wire']=wire;checks['feedback']=feedback
checks['paper_sha256']=sha(w/'paper-stdout-original.log.raw');assert checks['paper_sha256']==sha(w/'paper-stdout-original.log')==report['mp11_g3']['original_sha256']
raw=w/'native-stdout/w3-node-stdout.raw.jsonl';receipt=report['w3_node_stdout_capture'];assert sha(raw)==receipt['stdout_sha256'] and raw.stat().st_size==receipt['byte_count'];assert receipt['eof_observed'] and receipt['shutdown_ack_count']==1 and receipt['process_exit_code']==0
frames=[json.loads(s) for s in raw.read_text().splitlines()];checks['native_seq_range']=[receipt['first_seq'],receipt['last_seq']];checks['native_frame_count']=len(frames);checks['native_shutdown_ack_count']=receipt['shutdown_ack_count'];checks['w3_sha256']=sha(raw)
checks['typed_s16']=report['mp11_g2']['typed_s16_actions'];checks['wait8_totals_m']=[sum(v) for v in report['mp11_g3']['motion_m']]
processes={}
for line in (r/'l-next-world-owned-processes.jsonl').read_text().splitlines():
 for p in json.loads(line)['owned_processes']:
  if Path(p['exe']).name in ('java','node'):processes[(p['pid'],p['start_ticks'])]=p
assert {Path(p['exe']).name for p in processes.values()}=={'java','node'}
cleanup=[]
for p in processes.values():
 now=read_proc_status(p['pid']);gone=now is None or now['start_ticks']!=p['start_ticks'];assert gone
 cleanup.append({'identity':p,'owned_pid_gone':gone,'cwd_removed':not Path(p['cwd']).exists()})
checks['world_process_cleanup']=cleanup
identity=json.loads((r/'model-process-identity.json').read_text());now=read_proc_status(identity['pid'])
assert now and all(now[k]==identity[k] for k in ('pid','start_ticks','exe','argv'))
checks['model_identity_before_cleanup']=now
os.kill(identity['pid'],signal.SIGINT)
for _ in range(100):
 now=read_proc_status(identity['pid'])
 if now is None or now['start_ticks']!=identity['start_ticks'] or now['state']=='Z':break
 time.sleep(.1)
checks['model_after_signal']=now
checks['model_pid_gone']=now is None or now['start_ticks']!=identity['start_ticks']
checks['model_exited']=checks['model_pid_gone'] or now['state']=='Z'
assert checks['model_exited']
ports={}
for port in (8080,25565):
 with socket.socket() as s:s.bind(('127.0.0.1',port));ports[str(port)]='BIND_PASS'
checks['ports']=ports
historical=json.loads((r/'historical-originals-before.json').read_text());changed=[p for p,v in historical.items() if sha(Path(p))!=v];assert not changed
checks['historical_original_files_verified']=len(historical);checks['historical_originals_changed']=changed
before=dict(line.split()[::-1] for line in (r/'protected-refs-before.json').read_text().splitlines());after=dict(line.split()[::-1] for line in subprocess.check_output(['git','show-ref','--heads'],text=True).splitlines());checks['local_other_branch_changes']={k:[v,after.get(k)] for k,v in before.items() if not k.endswith('dev/l-cognitive-loop-world-20261102') and after.get(k)!=v};assert not checks['local_other_branch_changes']
checks['main_checkout']=subprocess.check_output(['git','-C','/home/rinsa/relay-self','status','--porcelain=v1'],text=True)+subprocess.check_output(['git','-C','/home/rinsa/relay-self','rev-parse','HEAD'],text=True);assert checks['main_checkout']==(r/'protected-checkout-before.txt').read_text()
checks['A']='PASS_DEV_ORIGINAL_LIVE_H1_H2_RECONSTRUCTED';checks['B1']='NOT_ESTABLISHED_NO_NUMERIC_FORECAST_OR_PREDICTION_ERROR_AND_WAIT_TIME_UNIT_CONFUSION';checks['B2']='NOT_ESTABLISHED_NO_HOLDOUT';checks['C']='NOT_RUN_BY_DESIGN';checks['mission']='NUMERIC_PREDICTION_ERROR_COGNITIVE_LOOP_NOT_ACHIEVED'
with (r/'independent-final-readback.json').open('x') as f:json.dump(checks,f,indent=2)
(r/'gpu-after.txt').write_bytes(subprocess.check_output(['nvidia-smi']))
print(json.dumps({k:checks[k] for k in ('A','B1','B2','C','ports','historical_original_files_verified','wait8_totals_m','model_pid_gone')},indent=2))
