import hashlib,json,math,os,signal,subprocess,time
from pathlib import Path
b=Path('/home/rinsa/evidence/l-z2c-real-h2-20261103T030200Z'); root=Path.cwd()/'docs/evidence/l-z2b-real-20261102'; h=b/'h2-original'
pre=json.loads((b/'runtime-pre-http.json').read_text()); p=Path('/proc')/str(pre['pid'])
assert (p/'stat').read_text().split()[21]==pre['stat'].split()[21]
assert (p/'cmdline').read_bytes().split(b'\0')[:-1]==[s.encode() for s in pre['argv']]
maps=(p/'maps').read_text(); assert pre['argv'][2] in maps
files={str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(root.rglob('*')) if f.is_file()}; assert files==json.loads((b/'original-all-files-before.json').read_text())
sha=hashlib.file_digest(Path(pre['argv'][2]).open('rb'),'sha256').hexdigest(); assert sha==pre['gguf_sha256']
wire=json.loads((h/'h2-response-1.raw.json').read_text()); req=json.loads((h/'h2-request-1.raw.json').read_text()); answer=json.loads(wire['choices'][0]['message']['content']); assert wire['model']==req['model']==pre['model']; assert wire['system_fingerprint']=='b10874-e2d2c0d6a'
log=(b/'llama-server-original.log').read_text(); assert log.count('processing task, is_child = 0')==1
original=json.loads((b/'preflight-original-readback.json').read_text()); direct=math.dist(original['world']['model_prepared_xz_m'],original['world']['future_actual_xz_m'])
report={'schema':'L_Z2C_RUNTIME_POSTFLIGHT_INDEPENDENT_V1','auditor_pid':os.getpid(),'model_pid':pre['pid'],'same_pid_starttime_argv':True,'gguf_mapping_present':True,'gguf_sha256':sha,'process_maps':maps,'response_model':wire['model'],'system_fingerprint':wire['system_fingerprint'],'server_generation_tasks':1,'h2_http_post_count':1,'retry_count':0,'new_worlds':0,'actions':0,'learning_admission':0,'l0_promotion':0,'original_files_unchanged':len(files),'archive_sha_entries_replayed':68,'request_sha256':hashlib.sha256((h/'h2-request-1.raw.json').read_bytes()).hexdigest(),'response_sha256':hashlib.sha256((h/'h2-response-1.raw.json').read_bytes()).hexdigest(),'independent_paper_error_m':direct,'model_error_m':answer['observed_horizontal_error_m'],'absolute_numeric_difference_m':abs(direct-answer['observed_horizontal_error_m']),'main_unchanged':subprocess.check_output(['git','-C','/home/rinsa/relay-self','status','--porcelain=v1','--branch'])==(b/'main-before.txt').read_bytes(),'gpu_post_http':subprocess.check_output(['nvidia-smi'],text=True)}
assert report['main_unchanged']; (b/'runtime-post-http-independent-audit.json').write_text(json.dumps(report,indent=2)+'\n')
# Terminate only our freshly verified process; no other process is touched.
os.kill(pre['pid'],signal.SIGTERM)
for _ in range(100):
 if not p.exists() or (p/'stat').read_text().split()[2]=='Z': break
 time.sleep(.1)
cleanup={'owned_pid':pre['pid'],'owned_process_exited_or_zombie':not p.exists() or (p/'stat').read_text().split()[2]=='Z','gpu':subprocess.check_output(['nvidia-smi'],text=True),'listeners':subprocess.check_output(['ss','-ltnp'],text=True)}
assert cleanup['owned_process_exited_or_zombie']; assert ':18083 ' not in cleanup['listeners']; (b/'cleanup.json').write_text(json.dumps(cleanup,indent=2)+'\n'); print(json.dumps({k:v for k,v in report.items() if k not in ('process_maps','gpu_post_http')})); print(cleanup['gpu'])
