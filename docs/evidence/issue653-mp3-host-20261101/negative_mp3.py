"""Mutated COPY audits only. No World or original writes."""
import copy,importlib.util,json,shutil,tempfile
from pathlib import Path
root=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('mp3audit',root/'audit_mp3_v3.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
original=[json.loads(x) for x in (root/'run1/prediction-original.jsonl').read_text().splitlines()]
negative=root/'negative-journals';negative.mkdir()
cases={
 'prediction':lambda r:r[4].update(prediction_m=1.0),
 'timestamp':lambda r:r[4].update(host_monotonic_ns=r[5]['host_monotonic_ns']+1),
 'ticket':lambda r:r[2]['ticket']['target'].update(subject_uuid='foreign'),
 'source_digest':lambda r:r[3].update(source_line_sha256='0'*64),
 'sample':lambda r:r[3].update(displacement_m=99),
 'missing_prediction':lambda r:r.pop(4),
 'target_tick':lambda r:r[4].update(target_tick=9999),
 'arm_identity':lambda r:r[1].update(session='foreign'),
}
results=[]
with tempfile.TemporaryDirectory(prefix='mp3-negative-copies-') as tmp:
 base=Path(tmp)/'baseline';shutil.copytree(root/'run1',base)
 assert module.audit(base)['host_order_verified']
 for name,mutate in cases.items():
  candidate=Path(tmp)/name;shutil.copytree(root/'run1',candidate)
  rows=copy.deepcopy(original);mutate(rows)
  raw=''.join(json.dumps(r)+'\n' for r in rows)
  (candidate/'prediction-original.jsonl').write_text(raw)
  (negative/(name+'.jsonl')).write_text(raw)
  try:module.audit(candidate)
  except (AssertionError,ValueError,KeyError) as exc:results.append(dict(case=name,rejected=True,error=type(exc).__name__,detail=str(exc)))
  else:results.append(dict(case=name,rejected=False))
with (root/'negative-results.json').open('x') as out:json.dump(dict(baseline_copy_pass=True,results=results),out,indent=2);out.write('\n')
assert all(r['rejected'] for r in results)
print(f'{len(results)}/{len(results)} mutated copies rejected')
