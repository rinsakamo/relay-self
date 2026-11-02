import json,subprocess,os,sys
from pathlib import Path
r=Path(__file__).parent;w=r/'world';py=sys.executable
env=dict(os.environ,PYTHONPATH='src:tests:.',PYTHONDONTWRITEBYTECODE='1')
base=['--report',str(w/'report.json'),'--original-paper',str(w/'paper-stdout-original.log.raw')]
cmds={
'g3':[py,'-B','-m','tools.mp11_g3_paper_one_world_audit',*base,'--output',str(w/'g3-independent.json'),'--expected-live-l2-calls','2'],
'live-prefix':[py,'-B','-m','tools.l_mp11_live_paper_postrun_audit',*base,'--output',str(w/'live-prefix-independent.json')],
'feedback':[py,'-B','-c',"import json,sys;from pathlib import Path;from tools.l_mp11_feedback_original_audit import audit_feedback_originals;r=Path(sys.argv[1]);out=audit_feedback_originals(json.loads((r/'report.json').read_text()),(r/'paper-stdout-original.log.raw').read_bytes());(r/'feedback-independent.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))",str(w)]}
status={}
for name,cmd in cmds.items():
 with (w/(name+'-independent-original.log')).open('xb') as f:
  p=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT)
 status[name]={'returncode':p.returncode,'argv':cmd,'status':'PASS' if p.returncode==0 else 'FAIL'}
(w/'mandatory-audit-status.json').write_text(json.dumps(status,indent=2))
print(json.dumps(status,indent=2))
