"""CPU integration: synthetic JSONL, Paper and model; original motor/issuer/WAL."""
import asyncio
import json
from unittest.mock import patch

import pytest

from adapters.mineflayer.process_session import MineflayerProcessSession
from experiments.cognitive_physical_move_issue_dev import PhysicalMoveRefusal
from experiments.p0d_stage27_real_place_move_dev import stage27h_real_a_motor_hook
from relay_self.p0d_stage27h_bounded_l0_move_dev import Stage27hBoundedMoveLoop
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.skill_invocation import SkillBudget
from test_mineflayer_process_session import FakeProcess, observation_line
from test_p0d_real_preset_checkpoint_dev import source_recovered
from test_p0d_resident_llama_slot_owner_dev import ResidentFixture, _SyntheticLlamaServer
from test_p0d_resident_paper_presence_join_dev import WORLD
from test_p0d_stage26_gemma_l1_dev import _attach_and_audit
from test_p0d_stage27_owned_move_intent_dev import _one_a_choice
from test_stage27e_independent_evidence_dev import _paper_window


@pytest.mark.parametrize('enabled,bad_stop', [(True, False), (False, False), (True, True)])
def test_original_hook_with_jsonl_and_wal(tmp_path, enabled, bad_stop):
    http = _SyntheticLlamaServer()
    http.choice_id = '1'
    endpoint = http.start()
    f = ResidentFixture(tmp_path, 2, cognitive_work=True, allow_resident_move=True,
                        enable_sense=enabled, names=('A', 'B'))
    lane = _attach_and_audit(f, endpoint, tmp_path)
    f.bridge.enable_sense = enabled
    streams = {}
    audit = tmp_path / 'native.jsonl'
    paper_pre, paper_post = _paper_window()
    snapshots = []
    original_pre_action = Stage27hBoundedMoveLoop.pre_action

    def record_pre_action(self, *args, **kwargs):
        result = original_pre_action(self, *args, **kwargs)
        assert not result.extra_physical_authority
        snapshots.append(self.last_sense_input)
        return result

    class Stream:
        def __init__(self):
            self.queue = asyncio.Queue()

        async def readline(self):
            return await self.queue.get()

    async def launch(config):
        native = 'native-' + config.username
        process = FakeProcess([])
        process.stdout = Stream()
        state = {'seq': 0, 'x': 1.0, 'tick': 1210}

        def put(value):
            process.stdout.queue.put_nowait((json.dumps(value) + '\n').encode())

        def emit(kind, request_id=None):
            state['seq'] += 1
            state['tick'] += 8
            value = json.loads(observation_line())
            value.update(session_id=native, seq=state['seq'], kind=kind)
            value['snapshot'].update(health=20, food=20)
            value['snapshot']['position']['x'] = state['x']
            value['snapshot']['time'] = {'time_of_day': state['tick'], 'day': 0, 'is_day': True}
            if request_id is not None:
                value['request_id'] = request_id
            put(value)

        put({'type': 'adapter_started', 'session_id': native, 'seq': 0,
             'mineflayer_version': '4.39.0', 'config': {'host': config.host,
             'port': config.port, 'username': config.username, 'version': config.version}})
        emit('spawn')
        write = process.stdin.write

        def respond(data):
            write(data)
            command = json.loads(data)
            if command['type'] == 'observe':
                emit('probe', command['request_id'])
            elif command['type'] == 'effect':
                effect = command['effect']
                state['seq'] += 1
                put({'type': 'effect_result', 'session_id': native, 'seq': state['seq'],
                     'action_id': command['action_id'], 'effect': effect,
                     'result': 'rejected' if bad_stop and effect == 'clear_controls' else 'applied',
                     'error': 'synthetic failure' if bad_stop and effect == 'clear_controls' else None})
                if effect == 'set_control':
                    state['x'] = 1.8
                    emit('move')  # passive event between START ACK and STOP

        process.stdin.write = respond
        session = MineflayerProcessSession(process)
        session._started = await session.receive()
        streams[config.username] = (session, emit, state)
        return session

    async def scenario():
        f.bridge.launch = launch
        with patch('test_p0d_stage26_gemma_l1_dev.source_recovered',
                   side_effect=lambda sid: source_recovered(sid, budget=SkillBudget(4, 15000, 2.0, 256))):
            pre, ticket, witness, refreshed = await _one_a_choice(f, lane)
        session, emit, state = streams['A']
        session.start_raw_source_audit(audit)
        while state['seq'] < 11:
            emit('move')
            await session.receive()
        if enabled:
            assert f.bridge.current_sense('A') is not None, (session.observer_error, session._dispatch_error, f.owners['A'].fresh_native_observation_required)
        paper_reads = iter((paper_pre, paper_post))
        with patch.object(f.paper, 'read_owned_log', side_effect=lambda _: next(paper_reads)), \
             patch.object(Stage27hBoundedMoveLoop, 'pre_action', record_pre_action):
            args = dict(paper=f.paper, bridge=f.bridge, physical=f.physical, lane=lane,
                        owners=f.owners, world_epoch=pre.world_epoch,
                        prepared={'A': pre, 'B': object()}, tickets={'A': ticket, 'B': object()},
                        witnesses={'A': witness, 'B': witness}, refreshed={'A': refreshed, 'B': object()},
                        evidence=tmp_path, world_uuid=WORLD, native_audit=audit)
            if bad_stop:
                with pytest.raises(PhysicalMoveRefusal, match="failed native child ACK"):
                    await stage27h_real_a_motor_hook(**args)
            else:
                result = await stage27h_real_a_motor_hook(**args)
                assert result['stage27_native_action_count'] == 1
                receipt = result['stage27h_original_action_witnesses'][0]
                assert receipt['terminal_wal_status'] == 'NATIVE_PLACE_MOVE_SETTLED'
                assert receipt['stop_probe_actual'] >= 3
                assert receipt['all_stop_probes_native_stdout']['all_stop_probes_exact_once']
                effects = receipt['native_source']['exact_native_action_child_effect_results']
                assert [v[1] for v in effects] == [receipt['action'] + x for x in ('-look', '-start', '-stop')]
                assert all(v[3] == 'applied' for v in effects)
                rows = [json.loads(line) for line in audit.read_text().splitlines()]
                assert any(row['kind'] == 'move' and effects[1][0] < row['seq'] < effects[2][0]
                           for row in rows if row['type'] == 'observation')
        journal = PhysicalActionJournal.restore(f.owners['A'].files.physical_wal_file, self_id='A')
        assert bool(journal.unresolved) == bad_stop
        assert len(journal.records) == 1
        if bad_stop:
            assert journal.records[0]["status"] == "PREPARED_UNRESOLVED"
        if not bad_stop:
            assert journal.records[0]["action_id"] == receipt["action"]
            assert journal.records[0]["status"] == receipt["terminal_wal_status"]
            journal.require_clear()
            assert not f.physical.active_action_ids
        if enabled:
            sense = snapshots[0]
            assert sense.source_revision_ref == 'mineflayer:native-A:11'
            assert sense.position.x == 1 and sense.route_status == 'UNKNOWN'
            assert 'body_aabb' in sense.missing
            rows = [json.loads(line) for line in audit.read_text().splitlines()]
            source = [row for row in rows if row['seq'] == 11]
            assert len(source) == 1 and source[0]['session_id'] == 'native-A'
            assert source[0]['kind'] == 'move' and source[0]['snapshot']['position']['x'] == sense.position.x
        else:
            assert snapshots == [None]
        session.finish_raw_source_audit()
        if not bad_stop:
            for sid in f.names:
                await f.bridge.logout(sid)
        else:
            await f.bridge.logout('B')
            f.physical.hold_for_operator()

    try:
        asyncio.run(scenario())
    finally:
        f.stop_paper()
        http.stop()
