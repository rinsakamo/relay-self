import json,hashlib,shutil
from pathlib import Path
r=Path(__file__).parent;dest=Path('/home/rinsa/work/l-b1-v2-delivery-20261102/docs/evidence/l-b1-v2-world-20261102')
a=json.loads((r/'independent-final-readback.json').read_text())
semantic={'A':'PASS_DEV','B1_N':'NOT_ESTABLISHED_NO_NUMERIC_H1','B1_U':'PASS_DEV_NARROW_UNSCORABLE_RECOGNITION','B1_Q':'NOT_ESTABLISHED_NO_SPECIFIC_COMPARISON_OR_KEEP_JUSTIFICATION','B1_overall':'PARTIAL_DEV_ONLY_NUMERIC_SELF_CORRECTION_NOT_ESTABLISHED','B2':'NOT_ESTABLISHED_NO_INDEPENDENT_HOLDOUT','C':'NOT_RUN_BY_DESIGN','H1_abstention':'ABSTAIN_INSUFFICIENT_EVIDENCE; numeric null; reason invokes absence of prior prediction, does not explain why one displacement observation cannot ground a next-trial estimate','H2_recognition':'Explicitly says H1 lacked a numeric forecast; correctly avoids a scored error claim','H2_qualitative_limit':'T1_W8 and T2_W8 resolve correctly, but output gives no equal/different trend or magnitude comparison and no specific reason to KEEP','units':'No wait-duration/displacement confusion in H1/H2; actual IDs bind total displacement meters over eight World ticks','falsification_limit':'VARY_INPUT_DURATION is an unexecuted proposal with no predicted discriminating outcome','prompt_integrity':'KNOWN_DEFECT: execution HEAD appended fourteen-key V2 instruction after EXACT ten keys legacy instruction; fixed only in delivery child, no additional inference/World','clean_V2_prompt_physical_validation':'NOT_RUN','formal_source_audits':'ALL_PASS_AT_PINNED_EXECUTION_HEAD','qualification':'NO_GO','science':'NOT_RUN'}
(r/'semantic-original-review.json').write_text(json.dumps(semantic,indent=2,ensure_ascii=False))
(r/'operator-preparation-notes.json').write_text(json.dumps({'preprobe_first_clean_check':'Failed only because offline Maven target/ was untracked; moved generated target to external evidence before HTTP. No HTTP or World consumed by that check.','cleanup_first_bind':'After model SIGINT/PID disappearance, plain 8080 bind initially EADDRINUSE due TIME_WAIT, no listener; retained tool terminal and script; later independent read-only closure plain bind PASS. No process or trial restarted.','original_audits_source_head':'88f620776c22ac75a86a691624c73feea0ed28d6','final_code_is_not_execution_code':True},indent=2))
files={}
for p in sorted(r.rglob('*')):
 rel=p.relative_to(r)
 if not p.is_file() or any(x in ('node-runtime','plugin-build-target') for x in rel.parts) or p.name=='SHA256SUMS.json':continue
 with p.open('rb') as f:files[str(rel)]=hashlib.file_digest(f,'sha256').hexdigest()
(r/'SHA256SUMS.json').write_text(json.dumps(files,indent=2))
dest.mkdir(parents=True,exist_ok=False)
for rel in [*files,'SHA256SUMS.json']:
 p=dest/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(r/rel,p)
print('SEALED',len(files),'files')
