"""I1 E native JSONL -> original B source/Present; synthetic Paper/Native only."""
import asyncio
import json
import time
from dataclasses import replace
from types import SimpleNamespace

import pytest

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import MINEFLAYER_VERSION
from adapters.mineflayer.sense_projection import sense_from_native
from relay_self.bd1b_owner_present_dev import BD1bPresentHold
from relay_self.common_io import ScopeRef
from relay_self.i_lane_cpu_readout_dev import read_i0_owner_cpu
from relay_self.i_lane_i1_cpu_schema_probe_dev import prepare_i1_cpu_schema_probe
from relay_self.three_self_present import EpistemicStatus
from test_bd1b_owner_present_dev import _configured
from test_bd1b_owner_source_dev import _files
from test_mineflayer_process_session import FakeProcess, observation_line


def _args(case, sid="A"):
    return dict(bridge=case[1], boot=case[2], world=case[3],
                links=case[4], self_id=sid)


def _passive_from_probe(bridge, sid="A", *, seq=3):
    probe = bridge.owners[sid].current_worldbody_observation
    return replace(probe, seq=seq, kind="move", request_id=None)


def _inject(bridge, world, sid="A"):
    """Only for source-negative tests; the main test uses the real decoder."""
    bridge.enable_sense = True
    if not hasattr(bridge, "_sense"):
        bridge._sense = {}
        bridge._sense_received_at = {}
    session = bridge.sessions[sid]
    session.observer_error = None
    session._dispatch_error = None
    frame = sense_from_native(
        _passive_from_probe(bridge, sid), scope=ScopeRef(sid, world.paper_session_id),
        expected_native_session=session.started.session_id, previous_seq=2,
    )
    bridge._sense[sid] = frame
    bridge._sense_received_at[sid] = time.monotonic()
    return frame


def test_source_bound_sense_composite_keeps_original_b_coverage_and_owner(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    bridge, world = case[1], case[3]
    before = _files(bridge)
    frame = _inject(bridge, world)
    current = bridge.cognitive_work.read_present_cpu(**_args(case))
    claims = current.present.three_self.self_world
    assert current.present.three_self.source_revision_refs[-1] == frame.source_revision_ref
    assert claims.read("sense.position").source_refs == (frame.provenance,)
    assert claims.read("sense.position").value_ref == frame.source_revision_ref + ":position"
    assert claims.read("sense.terrain_collision").status is EpistemicStatus.UNKNOWN
    assert claims.read("sense.nearby_entities_coverage").status is EpistemicStatus.OBSERVED
    assert current.exploration_need is not None
    inquiry = bridge.cognitive_work.read_coverage_inquiry_cpu(**_args(case))
    assert inquiry.source_revision_refs == current.present.three_self.source_revision_refs
    assert inquiry.coverage_claim_ref.startswith("native-coverage:")
    whole = read_i0_owner_cpu(**_args(case))
    assert whole.coverage_inquiry == inquiry
    cpu = prepare_i1_cpu_schema_probe(**_args(case))
    assert cpu.original.source_revision_refs == inquiry.source_revision_refs
    assert cpu.percept.source == frame.provenance
    assert cpu.percept.sequence == frame.observation.seq
    assert cpu.schema.options == ()  # no verified action catalogue or target
    assert _files(bridge) == before
    # B never adopts A's SENSE automatically.
    b = bridge.cognitive_work.read_present_cpu(**_args(case, "B"))
    assert len(b.present.three_self.source_revision_refs) == 2
    assert b.present.three_self.scope.self_id == "B"


def test_cpu_schema_uses_latest_qualified_sense_body_without_rewriting_login_probe(
    tmp_path, monkeypatch,
):
    case = _configured(tmp_path, monkeypatch, need=True)
    bridge, world = case[1], case[3]
    original_probe = bridge.owners["A"].current_worldbody_observation
    original_food = original_probe.snapshot.food
    frame = _inject(bridge, world)
    changed_food = 5.0 if original_food >= 10 else 20.0
    bridge._sense["A"] = replace(
        frame, observation=replace(
            frame.observation,
            snapshot=replace(frame.observation.snapshot, food=changed_food),
        ),
    )
    cpu = prepare_i1_cpu_schema_probe(**_args(case))
    assert cpu.percept.hunger == int(changed_food)
    assert cpu.percept.source == bridge._sense["A"].provenance
    assert bridge.owners["A"].current_worldbody_observation is original_probe
    assert bridge.owners["A"].current_worldbody_observation.snapshot.food == original_food


def test_composite_refuses_forged_scope_and_changed_revision(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    bridge, world = case[1], case[3]
    original = _inject(bridge, world)
    before = _files(bridge)
    for wrong in (
        replace(original, scope=ScopeRef("B", world.paper_session_id)),
        replace(original, source_revision_ref="mineflayer:foreign:3"),
        replace(original, observation=replace(original.observation, session_id="foreign")),
    ):
        bridge._sense["A"] = wrong
        # current_sense fails closed; no forged native claim is projected.
        readout = bridge.cognitive_work.read_present_cpu(**_args(case))
        assert len(readout.present.three_self.source_revision_refs) == 2
    bridge._sense["A"] = original
    bridge._sense_received_at["A"] = time.monotonic()
    import relay_self.bd1b_owner_present_dev as projection

    original_project = projection.project_present_frame

    def changed_during_projection(**kwargs):
        result = original_project(**kwargs)
        bridge._sense["A"] = replace(
            original, observation=replace(original.observation, seq=4),
            source_revision_ref=f"mineflayer:{original.observation.session_id}:4",
        )
        bridge._sense_received_at["A"] = time.monotonic()
        return result

    monkeypatch.setattr(projection, "project_present_frame", changed_during_projection)
    with pytest.raises(BD1bPresentHold, match="source changed"):
        bridge.cognitive_work.read_present_cpu(**_args(case))
    assert _files(bridge) == before


def test_real_native_decoder_dispatch_to_b_original_present(tmp_path, monkeypatch):
    """A real Python ProcessSession decoder, synthetic JSONL/Paper fixtures."""
    case = _configured(tmp_path, monkeypatch, need=True)
    bridge, world = case[1], case[3]
    config = bridge.configs["A"]
    native_id = bridge.sessions["A"].started.session_id
    original_files = _files(bridge)

    def line(value):
        return (json.dumps(value) + "\n").encode()

    def observation(seq, kind, x, request_id=None):
        value = json.loads(observation_line())
        value.update(session_id=native_id, seq=seq, kind=kind)
        value["snapshot"]["position"]["x"] = x
        if request_id is not None:
            value["request_id"] = request_id
        return line(value)

    class Stream:
        def __init__(self):
            self.queue = asyncio.Queue()

        async def readline(self):
            return await self.queue.get()

    async def scenario():
        process = FakeProcess([])
        process.pid = 7000
        process.stdout = Stream()
        process.stdout.queue.put_nowait(line({
            "type": "adapter_started", "session_id": native_id, "seq": 0,
            "mineflayer_version": MINEFLAYER_VERSION,
            "config": {"host": config.host, "port": config.port,
                       "username": config.username, "version": config.version},
        }))
        session = MineflayerProcessSession(process)
        session._started = await session.receive()
        bridge.sessions["A"] = session
        bridge.enable_sense = True
        bridge._sense = {}
        bridge._sense_received_at = {}
        bridge._start_sense("A", session, SimpleNamespace(world=world))
        process.stdout.queue.put_nowait(observation(1, "spawn", 1))
        process.stdout.queue.put_nowait(
            observation(2, "probe", 2, bridge.last_login_observations["A"].request_id)
        )
        process.stdout.queue.put_nowait(observation(3, "move", 3))
        for _ in range(3):
            await asyncio.wait_for(session.receive(), 1.5)
        frame = bridge.current_sense("A")
        assert frame is not None and frame.position.x == 3
        out = read_i0_owner_cpu(**_args(case))
        assert out.source_revision_refs[-1] == f"mineflayer:{native_id}:3"
        assert out.present.present.three_self.self_world.read(
            "sense.position"
        ).value_ref == f"mineflayer:{native_id}:3:position"
        assert out.coverage_inquiry.source_revision_refs == out.source_revision_refs
        process.stdout.queue.put_nowait(line({
            "type": "effect_result", "session_id": native_id, "seq": 4,
            "action_id": "synthetic-stop", "effect": "clear_controls",
            "result": "applied", "error": None,
        }))
        terminal = await asyncio.wait_for(session.receive(), 1.5)
        assert terminal.action_id == "synthetic-stop"
        assert bridge.current_sense("A") is frame
        process.stdout.queue.put_nowait(observation(5, "move", 5))
        await asyncio.wait_for(session.receive(), 1.5)
        assert bridge.current_sense("A").source_revision_ref.endswith(":5")
        # A changed Native revision changes the current Present revision.
        assert bridge.cognitive_work.read_present_cpu(
            **_args(case)
        ).present.three_self.source_revision_refs[-1].endswith(":5")
        bridge.cognitive_work.fence_self("A")
        assert bridge.current_sense("A") is None
        await session.terminate()

    asyncio.run(scenario())
    assert _files(bridge) == original_files
