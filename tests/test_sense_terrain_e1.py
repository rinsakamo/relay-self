"""E Lane E1 bounded native SENSE terrain: synthetic/offline, no World authority."""
import copy
import json
from dataclasses import replace

import pytest

from adapters.mineflayer.python_protocol import (
    MineflayerAdapterProtocolError,
    MineflayerPosition,
    MineflayerStreamDecoder,
    MineflayerTerrainObservation,
    encode_sense_terrain,
    parse_mineflayer_line,
)
from adapters.mineflayer.sense_projection import (
    SenseRefusal,
    sense_terrain_for_l0_move,
    sense_terrain_for_self_world,
    sense_terrain_from_native,
    sense_terrain_obstacle_hint,
)
from relay_self.common_io import ScopeRef
from relay_self.three_self_present import EpistemicStatus, Lens, LensView


def packet(*, collision=True, all_unknown=False):
    cells = []
    known = 0
    for dx in range(-2, 3):
        for dz in range(-2, 3):
            for dy in range(-1, 3):
                x, y, z = dx, 64 + dy, dz
                shape = []
                if y == 63:
                    shape = [[x, 63, z, x + 1, 64, z + 1]]
                if collision and (x, y, z) == (1, 64, 0):
                    shape = [[1, 64, 0, 2, 65, 1]]
                if all_unknown:
                    cells.append(dict(position=[x, y, z], name=None, shapes=None))
                else:
                    known += 1
                    cells.append(dict(position=[x, y, z], name="stone" if shape else "air",
                                      shapes=shape))
    return dict(
        type="terrain_observation", session_id="native-a", seq=7,
        request_id="sense-a-7",
        terrain=dict(
            source_scope="mineflayer_loaded_blocks",
            sample_monotonic_ns="123456789",
            position={"x": 0.5, "y": 64, "z": 0.5},
            dimension="minecraft:overworld", body_pose="standing",
            body_aabb=[0.2, 64, 0.2, 0.8, 65.8, 0.8],
            radius=2, dy_min=-1, dy_max=2,
            expected_cells=100, known_cells=known, complete=known == 100,
            cells=cells,
        ),
    )


def decode(payload=None):
    return parse_mineflayer_line(json.dumps(payload if payload is not None else packet()))


def frame(payload=None, **overrides):
    options = dict(
        scope=ScopeRef("self-a", "world-a"),
        expected_native_session="native-a",
        expected_request_id="sense-a-7",
        previous_seq=6,
    )
    options.update(overrides)
    return sense_terrain_from_native(decode(payload), **options)


def test_e1_roundtrip_to_l0_and_selfworld_is_not_authorization():
    f = frame()
    assert isinstance(f.observation, MineflayerTerrainObservation)
    move = sense_terrain_for_l0_move(f)
    assert move.complete
    assert len(move.cells) == 100
    assert move.body_aabb == (0.2, 64, 0.2, 0.8, 65.8, 0.8)
    assert move.route_status == "UNKNOWN"
    assert sense_terrain_obstacle_hint(f, MineflayerPosition(1, 64, 0.5)) == (
        "POTENTIAL_COLLISION"
    )
    assert sense_terrain_obstacle_hint(f, MineflayerPosition(0.5, 64, -0.5)) == (
        "UNKNOWN"
    )
    with pytest.raises(SenseRefusal, match="cannot grant"):
        replace(move, route_status="CLEAR")
    claims = sense_terrain_for_self_world(f)
    view = LensView(
        scope=f.scope, epoch_ref="e1", lens=Lens.SELF_WORLD,
        source_revision_refs=(f.source_revision_ref,), claims=claims,
    )
    claim = view.read("sense.terrain.local")
    assert claim.status is EpistemicStatus.OBSERVED
    assert claim.source_refs == (f.observation.provenance,)
    assert claim.coverage_ref.endswith("terrain-coverage")
    assert view.read("sense.terrain.unobserved").status is EpistemicStatus.UNKNOWN


def test_no_terrain_never_means_air_or_route_clear():
    f = frame(packet(all_unknown=True))
    assert f.terrain.known_cells == 0
    assert not f.terrain.complete
    assert sense_terrain_for_self_world(f)[0].status is EpistemicStatus.UNKNOWN
    assert sense_terrain_obstacle_hint(f, MineflayerPosition(1, 64, 0.5)) == "UNKNOWN"
    assert sense_terrain_for_l0_move(f).route_status == "UNKNOWN"


def test_body_geometry_missing_cannot_promote_route():
    p = packet()
    p["terrain"]["body_aabb"] = None
    f = frame(p)
    assert sense_terrain_obstacle_hint(f, MineflayerPosition(1, 64, 0.5)) == "UNKNOWN"
    assert sense_terrain_for_l0_move(f).body_aabb is None


@pytest.mark.parametrize("mutation", [
    lambda p: p["terrain"].update(known_cells=2),
    lambda p: p["terrain"].update(complete=False),
    lambda p: p["terrain"].update(radius=3),
    lambda p: p["terrain"].update(expected_cells=99),
    lambda p: p["terrain"].update(source_scope="paper_authoritative"),
    lambda p: p["terrain"]["cells"].pop(),
    lambda p: p["terrain"]["cells"].append(copy.deepcopy(p["terrain"]["cells"][0])),
    lambda p: p["terrain"]["cells"][0].update(position=[100, 63, -2]),
    lambda p: p["terrain"]["cells"][0].update(name=None),
    lambda p: p["terrain"]["cells"][0].update(shapes=None),
    lambda p: p["terrain"]["cells"][0].update(shapes=[[0, 0, 0, 999, 1, 1]]),
    lambda p: p["terrain"].update(body_aabb=[-1, 64, -1, 10, 65.8, 10]),
    lambda p: p["terrain"].update(sample_monotonic_ns="unknown"),
    lambda p: p["terrain"].update(body_pose=None),
])
def test_malformed_unbounded_or_fake_geometry_refused(mutation):
    p = packet()
    mutation(p)
    with pytest.raises(MineflayerAdapterProtocolError):
        decode(p)


@pytest.mark.parametrize("overrides", [
    {"expected_native_session": "native-b"},
    {"expected_request_id": "wrong"},
    {"previous_seq": 7},
    {"previous_seq": 8},
    {"previous_seq": True},
    {"scope": ScopeRef("self-a")},
])
def test_source_scope_and_replay_refused(overrides):
    with pytest.raises(SenseRefusal):
        frame(**overrides)


def test_stream_parser_keeps_original_sequence_contract():
    import adapters.mineflayer.python_protocol as native

    decoder = MineflayerStreamDecoder()
    started = {
        "type": "adapter_started", "session_id": "native-a", "seq": 0,
        "mineflayer_version": native.MINEFLAYER_VERSION,
        "config": {"host": "127.0.0.1", "port": 25565,
                   "username": "Self", "version": None},
    }
    decoder.decode(json.dumps(started))
    p = packet()
    p["seq"] = 1
    decoder.decode(json.dumps(p))
    with pytest.raises(MineflayerAdapterProtocolError, match="sequence"):
        decoder.decode(json.dumps(p))


def test_native_command_is_correlated_and_not_physical_effect():
    assert json.loads(encode_sense_terrain("sense-7")) == {
        "type": "sense_terrain", "request_id": "sense-7",
    }
    for bad in ("", "bad space", "-bad"):
        with pytest.raises(MineflayerAdapterProtocolError):
            encode_sense_terrain(bad)
