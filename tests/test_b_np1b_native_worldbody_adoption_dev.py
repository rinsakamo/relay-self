"""Fresh bootstrap and original bridge native probe adoption, CPU/offline."""
import asyncio
from dataclasses import replace

import pytest

from relay_self.owned_resident_physical_bridge_dev import (
    OwnedResidentBridgeError,
    OwnedResidentPhysicalBridge,
)
from relay_self.resident_cognitive_work_owner_dev import ResidentCognitiveWorkOwner
from relay_self.schema_bootstrap_dev import (
    SchemaBootstrapConfig,
    bootstrap_fresh_schemas,
    create_fresh_owner,
)
from test_p0d_resident_physical_issuer_dev import ResidentFixture


def fixture(tmp_path, **kwargs):
    f = ResidentFixture(tmp_path, 2, **kwargs)
    config = SchemaBootstrapConfig(True)
    owners = {}
    for sid, old in f.owners.items():
        owners[sid] = create_fresh_owner(
            config=config, retained=old.retained, intent=old.intent,
            native_session_id=old.native_session_id, last_observed_tick=old.last_observed_tick,
            files=old.files, physical_supervisor=old.supervisor,
        )
    resident = ResidentCognitiveWorkOwner(owners)
    bootstrap_fresh_schemas(resident, config)
    f.owners = owners
    f.cognitive = resident
    old_bridge = f.bridge
    f.bridge = OwnedResidentPhysicalBridge(
        lifecycle=f.lifecycle, physical=f.physical, paper=f.paper,
        configs=f.configs, owners=owners, launch=old_bridge.launch,
        cognitive_work=resident, adopt_login_worldbody_dev=True,
    )
    return f


def test_fresh_bootstrap_bridge_adopts_original_probe_for_both(tmp_path):
    f = fixture(tmp_path)
    before = {sid: (o.retained, o.intent, o.pattern_registry, dict(o.skills),
                    set(o.pending_questions), o.files.physical_wal_file.read_bytes())
              for sid, o in f.owners.items()}
    async def run():
        for sid in f.names:
            await f.bridge.login(sid)
            assert f.owners[sid].current_worldbody_observation is f.bridge.last_login_observations[sid]
        assert f.owners[f.names[0]].current_worldbody_observation is not f.owners[f.names[1]].current_worldbody_observation
    try:
        asyncio.run(run())
        assert all((o.retained, o.intent, o.pattern_registry, o.skills, o.pending_questions,
                    o.files.physical_wal_file.read_bytes()) == before[sid]
                   for sid, o in f.owners.items())
    finally:
        f.stop_paper()


@pytest.mark.parametrize('mutation', ['request', 'session', 'time', 'epoch', 'fence', 'old_scope'])
def test_rejects_stale_or_foreign_source(tmp_path, mutation):
    f = fixture(tmp_path)
    sid = f.names[0]
    async def run():
        await f.bridge.login(sid)
        bridge = f.bridge
        scope = f.cognitive.current_scope(sid)
        probe = bridge.last_login_observations[sid]
        f.owners[sid].current_worldbody_observation = None
        if mutation == 'request':
            bridge.last_login_evidence[sid] = replace(bridge.last_login_evidence[sid], observation_ref='foreign')
        elif mutation == 'session':
            bridge.last_login_observations[sid] = replace(probe, session_id='foreign')
        elif mutation == 'time':
            bridge.last_login_evidence[sid] = replace(bridge.last_login_evidence[sid], observed_world_tick=999)
        elif mutation == 'epoch':
            f.cognitive._states[sid].world_epoch += 1
        elif mutation == 'fence':
            f.cognitive.fence_self(sid)
        else:
            scope = (scope[0] - 1, scope[1], scope[2])
        with pytest.raises((OwnedResidentBridgeError, RuntimeError)):
            bridge._adopt_login_worldbody_dev(sid, scope)
        assert f.owners[sid].current_worldbody_observation is None
    try:
        asyncio.run(run())
    finally:
        f.stop_paper()


def test_logout_and_delayed_old_session_refused(tmp_path):
    f = fixture(tmp_path)
    sid = f.names[0]
    async def run():
        await f.bridge.login(sid)
        old_scope = f.cognitive.current_scope(sid)
        old_probe = f.bridge.last_login_observations[sid]
        await f.bridge.logout(sid)
        with pytest.raises(RuntimeError):
            f.bridge._adopt_login_worldbody_dev(sid, old_scope)
        await f.bridge.login(sid)
        current = f.bridge.last_login_observations[sid]
        assert current is f.owners[sid].current_worldbody_observation
        with pytest.raises(RuntimeError):
            f.bridge._adopt_login_worldbody_dev(sid, old_scope)
        assert f.owners[sid].current_worldbody_observation is current
        assert current is not old_probe
    try:
        asyncio.run(run())
    finally:
        f.stop_paper()


def test_adoption_failure_fences_without_publishing_observation(tmp_path, monkeypatch):
    f = fixture(tmp_path)
    sid = f.names[0]
    def fail(*args, **kwargs):
        raise RuntimeError('adoption failed')
    monkeypatch.setattr(f.owners[sid], 'accept_rejoined_worldbody', fail)
    async def run():
        with pytest.raises(RuntimeError, match='adoption failed'):
            await f.bridge.login(sid)
        assert f.owners[sid].current_worldbody_observation is None
        assert sid not in f.bridge.last_login_observations
        with pytest.raises(RuntimeError):
            f.cognitive.current_scope(sid)
    try:
        asyncio.run(run())
    finally:
        f.stop_paper()
