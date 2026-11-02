from pathlib import Path
import json,hashlib,socket,os
from tools.l_mp11_gemma_structured_preflight import verify_preflight_report
r=Path(__file__).parent;w=r/'world'
probe=verify_preflight_report(r/'gemma-strict-wire-probe/gemma-structured-preflight.json',endpoint='http://127.0.0.1:8080/v1/chat/completions',model='relay-self-gemma4-12b-q4km')
response=json.loads((r/'gemma-strict-wire-probe/llama-response-1.raw.json').read_text());msg=response['choices'][0]['message']
processes=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  exe=os.readlink(p/'exe')
  if Path(exe).name in ('node','java','llama-server'):processes.append({'pid':int(p.name),'exe':exe,'argv':(p/'cmdline').read_bytes().decode().split('\0')[:-1]})
 except (OSError,UnicodeError):pass
ports={}
for port in (8080,25565):
 with socket.socket() as s:s.bind(('127.0.0.1',port));ports[str(port)]='BIND_SUCCESS'
old=json.loads((r/'historical-originals-before.json').read_text());changes=[p for p,h in old.items() if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
report=json.loads((w/'report.json').read_text());raw=(w/'paper-stdout-original.log.raw').read_bytes()
result={'classification':'REAL_GEMMA_SYNTHETIC_PROBE_PASS_WORLD_APPARATUS_FAIL_NO_RETRY','probe_raw_sha_readback':'PASS','probe_request_count':1,'probe_finish_reason':response['choices'][0]['finish_reason'],'probe_completion_tokens':response['usage']['completion_tokens'],'reasoning_content_present':'reasoning_content' in msg,'reasoning_tokens_reported':response['usage'].get('completion_tokens_details',{}).get('reasoning_tokens'),'reasoning_markers_observed':False,'probe_is_body_experience':False,'world_starts':1,'retries':0,'world_status':report['status'],'world_http_raw_files':len(list(w.glob('llama-request-*.raw.json'))),'s49_actions':len(report['actual_native_actions']),'s15_clear_receipts':0,'s16_outcomes':len(report['mp11_g2']['typed_s16_actions']),'valid_world_open':0,'native_sequence':'UNAVAILABLE_W3_CONSTRUCTOR_FAILED_NO_CAPTURE','h1':None,'h2':None,'prediction_observation_error':None,'mandatory_audits':json.loads((w/'mandatory-audit-status.json').read_text()),'A':'NOT_ESTABLISHED_APPARATUS_BLOCKED','B1':'NOT_EVALUATED_NO_H1_H2','B2':'NOT_ESTABLISHED_NO_HOLDOUT','C':'NOT_RUN_BY_DESIGN','server_exit':report.get('server_exit'),'node_exit':report.get('node_exit'),'node_spawn':'ATTEMPTED_BEFORE_W3_CONSTRUCTOR; PID_AND_EXIT_NOT_IN_ORIGINAL_REPORT','native_stop_ack':'NOT_AVAILABLE_NO_W3_CAPTURE','current_runtime_processes':processes,'ports':ports,'current_s49_temp_directories':[str(p) for p in Path('/tmp').glob('relay-self-s49-*')],'world_exact_pid_cwd_independent_attestation':False,'world_pid_cwd_limitation':'External snapshot predicate compared exact minecraft.jar argv instead of absolute jar path; no PID/cwd captured. Empty set must not imply exact-owned cleanup PASS. Original flawed derived readback is preserved separately.','historical_original_files_checked':len(old),'historical_changes':changes,'paper_raw_equals_log':raw==(w/'paper-stdout-original.log').read_bytes(),'paper_sha256':hashlib.sha256(raw).hexdigest(),'qualification':'NO_GO','science':'NOT_RUN'}
(r/'independent-final-readback.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
