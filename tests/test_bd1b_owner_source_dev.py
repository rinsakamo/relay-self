"""Synthetic CPU source reconciliation, not real Paper attestation."""
import hashlib
from dataclasses import replace

import pytest

from relay_self.bd1b_owner_source_dev import BD1bSourceHold, build_bd1b_owner_source
from test_stage28c2c_fresh_recovered_l1_dev import _ready


def _read(case, sid="A", *, links=None, boot=None, world=None):
    _, bridge, original_boot, original_world, original_links, _ = case
    return build_bd1b_owner_source(
        bridge=bridge, boot=boot or original_boot, world=world or original_world,
        links=original_links if links is None else links, self_id=sid,
    )


def _files(bridge):
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for owner in bridge.owners.values()
            for p in owner.files.self_root.rglob("*") if p.is_file()}


def test_original_sources_are_read_only_for_both_selves(tmp_path, monkeypatch):
    case = _ready(tmp_path, monkeypatch)
    bridge = case[1]
    before = _files(bridge)
    cognition = {s: (o.retained, o.intent, o.pattern_registry)
                 for s, o in bridge.owners.items()}
    for sid in ("A", "B"):
        source = _read(case, sid)
        probe = bridge.owners[sid].current_worldbody_observation
        assert source.self_id == sid
        assert source.native_probe_ref == probe.request_id
        assert source.native_probe_seq == probe.seq
        assert source.native_session_id == probe.session_id
        assert source.resident_epoch == bridge.cognitive_work.current_scope(sid)[0]
        assert source.paper_actor_uuid == "actor-" + sid
        assert source.native_world_time_tick == 0
    assert _files(bridge) == before
    assert all((o.retained, o.intent, o.pattern_registry) == cognition[s]
               for s, o in bridge.owners.items())


@pytest.mark.parametrize("failure", [
    "probe", "native-session", "resident-epoch", "world-epoch", "paper-session",
    "boot", "swap", "missing", "duplicate", "actor", "paper-source", "fenced", "action",
])
def test_rejects_stale_or_forged_sources_without_writes(tmp_path, monkeypatch, failure):
    case = _ready(tmp_path, monkeypatch)
    _, bridge, boot, world, links, _ = case
    if failure == "probe":
        bridge.owners["A"].current_worldbody_observation = replace(bridge.last_login_observations["A"])
    elif failure == "native-session":
        bridge.sessions["A"].started.session_id = "foreign"
    elif failure == "resident-epoch":
        bridge.cognitive_work._states["A"].world_epoch += 1
    elif failure == "world-epoch":
        world = replace(world, epoch=world.epoch + 1)
    elif failure == "paper-session":
        bridge.paper._session_id = "foreign"
    elif failure == "boot":
        boot = replace(boot, paper_boot_id="foreign")
    elif failure == "swap":
        links = (replace(links[0], self_id="B"), replace(links[1], self_id="A"))
    elif failure == "missing":
        links = links[:1]
    elif failure == "duplicate":
        links = (links[0], links[0])
    elif failure == "actor":
        links = (replace(links[0], paper_actor_uuid="forged"), links[1])
    elif failure == "paper-source":
        links = (replace(links[0], paper_log_sha256="0" * 64), links[1])
    elif failure == "fenced":
        bridge.cognitive_work.fence_self("A")
    else:
        bridge.physical._observation_only = False
    before = _files(bridge)
    with pytest.raises(BD1bSourceHold):
        _read(case, links=links, boot=boot, world=world)
    assert _files(bridge) == before
