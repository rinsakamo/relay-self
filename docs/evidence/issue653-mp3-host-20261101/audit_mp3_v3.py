"""Separate process read-only audit; no Minecraft execution or typed reauthentication."""
import hashlib,json,sys,math
from dataclasses import asdict
from pathlib import Path
from adapters.mineflayer.self_body_s50_l1_motion_prediction import from_archival_readback
from adapters.mineflayer.self_body_s50_l1_motion_prequential import freeze_for_target,TargetWorldIdentity
from adapters.mineflayer.self_body_s50_l1_motion_live_dev import score_live_dev
from adapters.mineflayer.m02_paper_dev.s50_live_paper_window import capture_s50_live_paper_window
from tools.selfbody_l1_shadow_readback import review


def audit(root):
 original=review(root)
 paper=(root/'paper-stdout-original.bin').read_bytes()
 assert paper==(root/'server.log').read_bytes()
 chunks=paper.split(b"\n")
 lines=[line+b"\n" for line in chunks[:-1]]+([chunks[-1]] if chunks[-1] else [])
 row=json.loads((root/'s49-report.json').read_text())
 prior=row['live_next_epoch']['window']
 window=capture_s50_live_paper_window((root/'live-paper-prefix.log').read_bytes(),session_id=prior['session_id'],action_id=prior['action_id'],world=prior['paper_world_uuid'],subject_uuid=prior['subject_uuid'])
 journal=[json.loads(x) for x in (root/'prediction-original.jsonl').read_text().splitlines()]
 assert [j['kind'] for j in journal]==['TRAINING_FIXED','ARM','TARGET_FIXED']+sum((['OBSERVED','PREDICTION_FIXED'] for _ in range(7)),[])+['OBSERVED']
 assert all(a['host_monotonic_ns']<b['host_monotonic_ns'] for a,b in zip(journal,journal[1:]))
 train=from_archival_readback(json.loads((Path(__file__).resolve().parent/'preflight/training-audit.json').read_text()))
 assert journal[0]['training']==json.loads(json.dumps(asdict(train)))
 target=TargetWorldIdentity(window.session_id,window.paper_world_uuid,window.action_id,window.subject_uuid)
 ticket=freeze_for_target(train,target,capture_mode='PROSPECTIVE_LOCAL_ORDER_NOT_EXTERNALLY_ATTESTED')
 assert journal[2]['ticket']==json.loads(json.dumps(asdict(ticket)))
 marker=window.marker_id
 assert journal[1]['session']==window.session_id and journal[1]['action']==window.action_id and journal[1]['marker']==marker
 source_positions=[]
 for j in journal:
  if 'source_line_sha256' in j:
   hits=[i for i,l in enumerate(lines) if hashlib.sha256(l).hexdigest()==j['source_line_sha256']]
   assert len(hits)==1
   source_positions.append(hits[0])
 assert source_positions==sorted(set(source_positions))
 assert b'phase=PRE_FORWARD' in lines[source_positions[0]]
 starts=[i for i,l in enumerate(lines) if b'S50_DEV_WAIT_BEGIN ' in l and ('marker_id='+marker).encode() in l]
 assert len(starts)==1 and source_positions[0]<starts[0]<source_positions[1]
 observed=[j for j in journal if j['kind']=='OBSERVED']
 predictions=[j for j in journal if j['kind']=='PREDICTION_FIXED']
 for i,(j,t) in enumerate(zip(observed,window.ticks)):
  assert j['tick']==t.world_tick and j['index']==i+1 and math.isclose(j['displacement_m'],t.displacement_m,rel_tol=1e-12,abs_tol=1e-15)
 for i,p in enumerate(predictions):
  assert p['target_tick']==observed[i+1]['tick'] and p['ticket_sha256']==ticket.ticket_sha256
  assert p['prediction_m']==ticket.model.slope*observed[i]['displacement_m']
  assert p['host_monotonic_ns']<observed[i+1]['host_monotonic_ns']
 scored=score_live_dev(ticket,train,window)
 assert all(math.isclose(p['prediction_m'],y,rel_tol=1e-12,abs_tol=1e-15) for p,y in zip(predictions,scored.predictions_m))
 return dict(classification='DEV_HOST_READ_ORDER_FORECAST_OBSERVED_PARTIAL_PHYSICAL_CHRONOLOGY_UNDETERMINED',original=original,ticket=asdict(ticket),score=asdict(scored),journal=journal,worlds=1,retries=0,host_order_verified=True,paper_physical_prequential_attested=False,subject_planned_before_and_verified_after=True,next_world_update='WITHHELD_PHYSICAL_CHRONOLOGY_UNDETERMINED',goal='UNDETERMINED',qualification='NO_GO',science='NOT_RUN')

if __name__=='__main__':
 result=audit(Path(sys.argv[1]))
 with Path(sys.argv[2]).open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print(result['classification'])
