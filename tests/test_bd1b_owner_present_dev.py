"""Synthetic original bridge/owner integration, never real Paper attestation."""
from dataclasses import replace

import pytest

from relay_self.bd1b_owner_present_dev import BD1bPresentHold, build_bd1b_owner_present
from relay_self.bd1b_owner_source_dev import BD1bSourceHold
from relay_self.cognitive_minimal_dev import initial_patterns_with_relative_move
from relay_self.innate_schema import SchemaActivation, SchemaMode, SchemaModuleSpec, SchemaSnapshot
from relay_self.provenance import Provenance
from relay_self.resident_cognitive_work_owner_dev import (
    ResidentCognitiveWorkError,
    ResidentCognitiveWorkOwner,
)
from test_bd1b_owner_source_dev import _files, _read
from test_stage28c2c_fresh_recovered_l1_dev import _ready


def _schema(sid, revision, mode=SchemaMode.FULL, *, need=False):
    spec = SchemaModuleSpec("exploratory", 1, frozenset({SchemaMode.FULL}),
                            (("QUESTION_CANDIDATE", "EXPLORATION_NEED") if need
                             else ("QUESTION_CANDIDATE",)), (), Provenance("test", "bootstrap"))
    return SchemaSnapshot(sid, revision, (SchemaActivation(spec, mode),))


def _configured(tmp_path, monkeypatch, *, need=False):
    original = ResidentCognitiveWorkOwner.bind_login
    def bind(resident, *, self_id, **kwargs):
        resident.owners[self_id].pattern_registry = initial_patterns_with_relative_move()
        resident.register_present_schema(self_id, _schema(self_id, 1, need=need))
        original(resident, self_id=self_id, **kwargs)
    monkeypatch.setattr(ResidentCognitiveWorkOwner, "bind_login", bind)
    return _ready(tmp_path, monkeypatch)


def _project(case, sid="A"):
    _, bridge, boot, world, links, _ = case
    return build_bd1b_owner_present(bridge=bridge, boot=boot, world=world,
                                    links=links, self_id=sid)


def test_original_both_selves_read_only(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch)
    bridge = case[1]
    before = _files(bridge)
    state = {sid: (o.retained, o.intent, dict(o.skills), set(o.pending_questions))
             for sid, o in bridge.owners.items()}
    for sid in ("A", "B"):
        result = _project(case, sid)
        assert result.schema.get("exploratory").mode is SchemaMode.FULL
        assert result.present.three_self.scope.self_id == sid
        assert result.present.three_self.scope.world_session_id == result.source.paper_session_id
        assert result.present.frame_revision == result.source.resident_epoch
        assert result.present.registry_revision == bridge.owners[sid].pattern_registry.revision
        assert result.source.native_probe_ref in result.present.three_self.source_revision_refs[0]
        assert not result.present.signals
        assert result.no_candidate_reason == "NO_VERIFIED_ACTION_CATALOG"
    assert _files(bridge) == before
    assert all((o.retained, o.intent, o.skills, o.pending_questions) == state[sid]
               for sid, o in bridge.owners.items())


@pytest.mark.parametrize("failure", ["unregistered", "registry", "native", "paper", "epoch", "fenced", "swap"])
def test_projection_rechecks_current_state(tmp_path, monkeypatch, failure):
    case = _configured(tmp_path, monkeypatch, need=True)
    bridge = case[1]
    _read(case)
    if failure == "unregistered":
        del bridge.cognitive_work._present_schemas["A"]
    elif failure == "registry":
        bridge.owners["A"].pattern_registry = replace(bridge.owners["A"].pattern_registry, revision=2)
    elif failure == "native":
        bridge.owners["A"].current_worldbody_observation = replace(bridge.last_login_observations["A"])
    elif failure == "paper":
        bridge.paper._session_id = "foreign"
    elif failure == "epoch":
        bridge.cognitive_work._states["A"].world_epoch += 1
    elif failure == "fenced":
        bridge.cognitive_work.fence_self("A")
    else:
        bridge.owners["A"].current_worldbody_observation = bridge.last_login_observations["B"]
    with pytest.raises((BD1bPresentHold, BD1bSourceHold)):
        _project(case)


def test_no_online_replacement_or_external_present(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch)
    resident = case[1].cognitive_work
    with pytest.raises(ResidentCognitiveWorkError):
        resident.register_present_schema("A", _schema("A", 1))
    with pytest.raises(TypeError):
        build_bd1b_owner_present(bridge=case[1], boot=case[2], world=case[3],
                                 links=case[4], self_id="A", present=_project(case).present)


@pytest.mark.parametrize("variant", ["foreign", "revision", "missing-pattern", "version"])
def test_bad_bootstrap_rejected(tmp_path, monkeypatch, variant):
    original = ResidentCognitiveWorkOwner.bind_login
    def bind(resident, *, self_id, **kwargs):
        owner = resident.owners[self_id]
        owner.pattern_registry = initial_patterns_with_relative_move()
        snapshot = _schema(("B" if self_id == "A" else "A") if variant == "foreign" else self_id,
                           2 if variant == "revision" else 1,
                           SchemaMode.OFF if variant == "off" else SchemaMode.FULL)
        if variant == "missing-pattern":
            owner.pattern_registry = replace(owner.pattern_registry, patterns=())
        if variant == "version":
            activation = snapshot.modules[0]
            snapshot = replace(snapshot, modules=(replace(activation, spec=replace(activation.spec, version=2)),))
        with pytest.raises(ResidentCognitiveWorkError):
            resident.register_present_schema(self_id, snapshot)
        original(resident, self_id=self_id, **kwargs)
    monkeypatch.setattr(ResidentCognitiveWorkOwner, "bind_login", bind)
    case = _ready(tmp_path, monkeypatch)
    with pytest.raises(BD1bPresentHold):
        _project(case)


def test_need_from_bounded_current_probe_without_actions(tmp_path, monkeypatch):
    case = _configured(tmp_path, monkeypatch, need=True)
    bridge = case[1]
    before = _files(bridge)
    state = {sid: (o.retained, o.intent, dict(o.skills), set(o.pending_questions), o.pattern_registry)
             for sid, o in bridge.owners.items()}
    results = [_project(case, sid) for sid in ("A", "B")]
    for result in results:
        need = result.exploration_need
        assert need is not None and result.present.signals == (need.signal,)
        assert need.signal.signal_kind == "EXPLORATION_NEED"
        assert need.signal.schema_id == "exploratory"
        assert need.signal.module_version == result.schema.get("exploratory").spec.version
        assert need.signal.registry_revision == result.schema.revision
        assert need.signal.question_candidate is None
        assert need.signal.source_revision_refs == result.present.three_self.source_revision_refs
        assert need.signal.envelope.provenance == bridge.owners[result.source.self_id].current_worldbody_observation.provenance
        assert need.other_needs == () and need.disposition is None
        claim = result.present.three_self.self_world.claims[0]
        assert claim.claim_key == need.basis[0].present_ref
        assert "world-knowledge-not-comprehensive" in claim.value_ref
        assert claim.status.value == "INFERRED"
        assert result.no_candidate_reason == "NO_VERIFIED_ACTION_CATALOG"
    assert results[0].exploration_need.signal.envelope.event_id != results[1].exploration_need.signal.envelope.event_id
    assert _files(bridge) == before
    assert all((o.retained, o.intent, o.skills, o.pending_questions, o.pattern_registry) == state[sid]
               for sid, o in bridge.owners.items())


def test_need_rejects_forged_and_upgraded_evidence(tmp_path, monkeypatch):
    from relay_self.exploration_need_dev import ExplorationContractError, propose_exploration_need
    from relay_self.three_self_present import EpistemicStatus

    result = _project(_configured(tmp_path, monkeypatch, need=True))
    need = result.exploration_need
    kwargs = dict(present=replace(result.present, signals=()), snapshot=result.schema,
                  schema_id="exploratory", other_needs=(), disposition=None,
                  signal_envelope=need.signal.envelope,
                  current_registry_revision=result.schema.revision,
                  current_source_revision_refs=result.present.three_self.source_revision_refs)
    assert propose_exploration_need(evidence=(), **kwargs) is None
    for item in (replace(need.basis[0], present_ref="coverage:forged"),
                 replace(need.basis[0], status=EpistemicStatus.OBSERVED)):
        with pytest.raises(ExplorationContractError):
            propose_exploration_need(evidence=(item,), **kwargs)
    assert result.present.three_self.self_world.read("target:unconfirmed").status is EpistemicStatus.UNKNOWN


def test_missing_coverage_returns_empty_present(tmp_path, monkeypatch):
    import relay_self.bd1b_owner_present_dev as present_module

    case = _configured(tmp_path, monkeypatch, need=True)
    monkeypatch.setattr(present_module, "MineflayerNearbyEntitiesCoverage", type(None))
    result = _project(case)
    assert result.exploration_need is None
    assert result.no_need_reason == "NO_COVERAGE_EVIDENCE"
    assert result.present.signals == ()
    assert result.present.three_self.self_world.claims == ()
