"""Read-only partial evidence reconciliation. Never changes original FAIL."""
import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from adapters.mineflayer.l_mp11_live_previous_action import LivePriorLedger
from adapters.mineflayer.self_body_s50_l2_mp11_paper_audit import audit_multi_trial_paper
from tools.mp11_g2_s49_original_audit import audit_original

root = Path(__file__).resolve().parent
report = json.loads((root/'report.json').read_text())
original = (root/'paper-stdout-original.log').read_bytes()
assert report['status'] == 'FAIL'
assert report['node_exit'] == report['server_exit'] == 0
native = audit_original(report, require_completed_cleanup=False, expected_l2_calls=2)
complete_end = original.rfind(b'\n')+1
assert original[complete_end:] == b'> '
# This explicit diagnostic prefix is NOT substituted into the original G3 CLI.
complete = original[:complete_end]
proposals = report['l_mp11_live_l2']['proposals']
ledger = LivePriorLedger(session_id=report['session_id'],
                        world_uuid=proposals[0]['source_world_uuid'],
                        subject_uuid=proposals[0]['source_subject_uuid'])
markers = tuple(report['mp11_g3']['paper_markers'])
paper = audit_multi_trial_paper(complete, action_markers=markers,
                               world_uuid=ledger.world_uuid,
                               subject_uuid=ledger.subject_uuid,
                               surfaces=('GRASS_BLOCK',)*3)
windows = report['l_mp11_live_prefix']['observations']
for i, w in enumerate(windows):
    prefix = original[:w['paper_prefix_length']]
    assert hashlib.sha256(prefix).hexdigest() == w['paper_prefix_sha256']
    assert windows[i]['native_s16_seq'] == report['mp11_g2']['typed_s16_actions'][i]['native_seq']
    ledger.accept_completed(prefix, action_id=w['action_id'], marker_id=markers[i],
                            native_s16_seq=w['native_s16_seq'], native_outcome='S16_OUTCOME')
    if i < 2:
        call = json.loads((root/f'llama-http-{i+1}.json').read_text())
        body = json.loads(call['request']['messages'][1]['content'])
        attempt = report['l_mp11_live_l2']['attempt_originals'][i]
        assert body['request_id'] == attempt['request']['request_id'] == proposals[i]['request_id']
        assert body['context'][1]['value'] == json.loads(attempt['request']['context'][1]['value_json'])
        assert body['context'][1]['value'] == json.loads(json.dumps([asdict(x) for x in ledger.history]))
        assert call['response']['choices'][0]['message']['content'] == attempt['result']['text']
        assert call['response']['model'] == call['request']['model'] == 'relay-self-gemma4-12b-q4km'
        assert proposals[i]['source_last_prefix_sha256'] == w['paper_prefix_sha256']
        parsed = json.loads(attempt['result']['text'])
        assert all(1 <= ref <= i+1 for ref in parsed['referenced_prior_ordinals'])
        assert attempt['started_monotonic_ns'] < call['started_monotonic_ns'] < call['finished_monotonic_ns'] < attempt['finished_monotonic_ns']
        if i:assert report['l_mp11_live_l2']['attempt_originals'][i-1]['finished_monotonic_ns'] < attempt['started_monotonic_ns']
raw = (root/'native-stdout/w3-node-stdout.raw.jsonl').read_bytes()
seal = json.loads((root/'native-stdout/w3-node-stdout-receipt.json').read_text())
assert hashlib.sha256(raw).hexdigest() == seal['stdout_sha256'] == report['w3_node_stdout_capture']['stdout_sha256']
frames = [json.loads(line) for line in raw.splitlines()]
for a in report['actual_native_actions']:
    evidence = a['execution_evidence']
    for key in ('dispatch_receipt','cleanup_receipt','before_observation','after_observation'):
        receipt = evidence[key]
        frame = next(f for f in frames if f.get('seq') == receipt['seq'])
        assert frame['session_id'] == receipt['session_id']
        if key in ('dispatch_receipt','cleanup_receipt'):
            assert all(frame[k] == receipt[k] for k in ('action_id','effect','result'))
        else:
            assert frame['request_id'] == receipt['request_id']
cleanup = {'node_pid_absent':not Path('/proc/98997').exists(),
           'java_pid_absent':not Path('/proc/98865').exists(),
           'owned_llama_pid_absent':not Path('/proc/98374').exists(),
           'world_directory_absent':not Path('/tmp/relay-self-s49-91d9d6bs').exists()}
assert all(cleanup.values())
result = {'classification':'PARTIAL_DEV_SOURCE_RECONCILED_ORIGINAL_RUN_REMAINS_FAIL',
          'original_run_status':report['status'], 'required_g3_audit':'FAIL',
          'required_live_prefix_audit':'FAIL',
          'original_paper_sha256':hashlib.sha256(original).hexdigest(),
          'diagnostic_complete_line_prefix_sha256':hashlib.sha256(complete).hexdigest(),
          'uninterpreted_eof_suffix_hex':original[complete_end:].hex(),
          'original_report_sha256':hashlib.sha256((root/'report.json').read_bytes()).hexdigest(),
          'native_w3_sha256':seal['stdout_sha256'], 'all_three_live_prefix_hashes_match':True,
          's49_s16_clear_receipts':3, 'wait_ticks':[list(x.wait_ticks) for x in paper],
          'paper_forecast_pairs':21,'real_open_calls':2,
          'model_request_matches_reconstructed_prior_only_context':True,
          'independent_common_clock_attested':False,
          'cleanup':cleanup,
          'A':'REAL_GEMMA_LIVE_INPUT_AND_TWO_RESPONSES_OBSERVED_PARTIAL_DEV',
          'B':'PROPOSAL_FAMILY_AND_FALSIFICATION_CHANGED_CAUSAL_REVISION_UNDETERMINED',
          'C':'NOT_IMPLEMENTED', 'learning_admissions':0,'l0_promotions':0}
with (root/'supplementary-readback.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result,indent=2))
