"""Mutate only isolated copies; every original remains immutable."""
import json, tempfile, shutil
from pathlib import Path
from tools.selfbody_route_b_readback import review
root=Path('/home/rinsa/work/issue651-route-b-evidence-20261031/run1')
results=[]
for fault in ['missing_third','fake_third','early_third','third_move','unknown_s16','foreign_session','foreign_action','foreign_world','reverse_seq','missing_wait','input_gap','paper_sha','double_read','missing_footer']:
 with tempfile.TemporaryDirectory(prefix='route-b-negative-') as tmp:
  r=Path(tmp)/'run'; shutil.copytree(root,r)
  report=json.loads((r/'s49-report.json').read_bytes()); c=r/'capture'; p=c/'pre-next-l0-prefix'
  def edit_json(path, fn):
   v=json.loads(path.read_bytes());fn(v);path.write_text(json.dumps(v)+'\n')
  if fault=='missing_third':report['decisions'].pop()
  if fault=='fake_third':
   f=c/'native_bridge_received_original.jsonl';rows=[json.loads(x) for x in f.read_bytes().splitlines()];rows[report['decisions'][2]['event_seq']]['type']='probe'; f.write_text(''.join(json.dumps(x)+'\n' for x in rows))
  if fault=='early_third':report['live_next_epoch']['last_prior_probe_seq']=report['decisions'][2]['event_seq']
  if fault=='third_move':report['decisions'][2]['selected']='MOVE_AWAY'
  if fault=='unknown_s16':edit_json(c/'l18_s16_terminal_original.jsonl',lambda v:v.update(source_status='unknown'))
  if fault=='foreign_session':report['session_id']='foreign'
  if fault=='foreign_action':report['live_next_epoch']['window']['action_id']='foreign'
  if fault=='foreign_world':report['live_next_epoch']['window']['paper_world_uuid']='foreign'
  if fault=='reverse_seq':report['decisions'][2]['event_seq'],report['decisions'][2]['probe_seq']=report['decisions'][2]['probe_seq'],report['decisions'][2]['event_seq']
  if fault in ['missing_wait','input_gap','paper_sha']:
   f=r/'live-paper-prefix.log';raw=f.read_bytes()
   if fault=='missing_wait': raw=b'\n'.join(x for x in raw.split(b'\n') if b'S50_DEV_WAIT_TICK ' not in x)
   if fault=='input_gap': raw=b'\n'.join(x for x in raw.split(b'\n') if not(b'S50_DEV_INPUT_TICK ' in x and b'index=4 ' in x))
   if fault=='paper_sha':raw=raw.replace(b'INFO',b'INFX',1)
   f.write_bytes(raw)
  if fault=='double_read':report['live_next_epoch']['lease']['next_l0_provisional_paper_reads']=2
  if fault=='missing_footer':
   f=r/'client-packet-original.jsonl';f.write_bytes(b'\n'.join(f.read_bytes().splitlines()[:-1])+b'\n')
  (r/'s49-report.json').write_text(json.dumps(report)+'\n')
  try:review(r)
  except Exception as e:results.append({'fault':fault,'rejected':True,'exception':type(e).__name__,'reason':str(e)})
  else:results.append({'fault':fault,'rejected':False})
  # Preserve mutated inputs for reproducibility, avoiding duplicate unchanged runtime assets.
  out=root.parent/'negative-inputs'/fault;out.mkdir(parents=True)
  for rel in ['s49-report.json','live-paper-prefix.log','client-packet-original.jsonl','capture/l18_s16_terminal_original.jsonl','capture/native_bridge_received_original.jsonl']:
   dest=out/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((r/rel).read_bytes())
(root.parent/'negative-original-readback.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results));assert all(x['rejected'] for x in results)
