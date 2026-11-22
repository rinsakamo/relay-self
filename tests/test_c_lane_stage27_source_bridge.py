"""C Lane Stage27/28 cross-Draft seam tests: synthetic, NEVER real WAL proof."""
from __future__ import annotations

import sys
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from relay_self.action import ActionLifecycle
from relay_self.c_lane_stage27_source_bridge import (
    assemble_stage27_c1_from_canonical_wal,
    propose_for_stage28_original_owner,
)
from relay_self.cognitive_learning_contract import OutcomeAssessment
from relay_self.cognitive_learning_owner_adapter import C1AdmissionError
from relay_self.common_io import ScopeRef
from relay_self.intent import IntentCommitment
from relay_self.persistent_cognition import IdentitySpecification, PersistentCognition
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution

P = Provenance("test-source", "test-parent")
DIGEST = "a" * 64
SCOPE = ScopeRef("self-A", "native-old-1")


class FakeStatus(str, Enum):
    CONDITION_OBSERVED = "CONDITION_OBSERVED"
    OUTSIDE = "OUTSIDE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class FakeNativeProbe:
    session_id: str
    seq: int
    request_id: str
    snapshot: object
    provenance: Provenance
    kind: str = "probe"


class FakeInvocation:
    def __init__(self):
        self.scope = SCOPE
        self.skill_id = "MOVE"
        self.goal_id = "EXPLORE_WORLD"
        self.invocation_ref = "skill-invocation:v1@test-original"
        self.parameter_preset_ref = "skill-preset:v1@test-fixed"
        anchor = SimpleNamespace(x=2.0, y=64.0, z=0.0)
        contract = SimpleNamespace(
            target_ref="destination:1", goal_id=self.goal_id,
            contract_ref="target-contract:v1@test", anchor=anchor,
        )
        self.target = SimpleNamespace(ref="destination:1", contract=contract)


class FakeJournalError(ValueError):
    pass


class FakeJournalUnresolved(FakeJournalError):
    pass


class FakeJournal:
    rows = []
    digest = DIGEST
    unresolved = False
    restores = 0

    @classmethod
    def restore(cls, path, *, self_id):
        assert path == Path("/original/never-opened.json")
        assert self_id == "self-A"
        cls.restores += 1
        return cls()

    @property
    def records(self):
        return tuple(dict(x) for x in type(self).rows)

    def require_clear(self):
        if self.unresolved:
            raise FakeJournalUnresolved("unresolved")


class FakeTargetBody:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def fake_eval(contract, observation):
    status = FakeStatus.CONDITION_OBSERVED if observation.position.x == 2.0 else FakeStatus.OUTSIDE
    return SimpleNamespace(status=status, contract_ref=contract.contract_ref)


def _owner_fixture(n=2, *, started=True):
    cognition = PersistentCognition(
        IdentitySpecification(self_id="self-A", directives=("explore",), provenance=P)
    )
    intent = IntentCommitment()
    intent.commit("intent-1", objective="EXPLORE_WORLD", at_ns=10, provenance=P)
    skill = SkillExecution.start(
        "child-run-1", skill_id="MOVE", intent_commitment=intent,
        at_ns=20, provenance=P,
    )
    actions, rows = [], []
    inv = FakeInvocation()
    for idx in range(n):
        begin = 30 + idx * 20
        action = ActionLifecycle.propose(
            f"action-{idx}", skill_execution=skill, intent_commitment=intent,
            at_ns=begin, provenance=P,
        ).authorize(
            at_ns=begin + 1, provenance=P, authority="original",
        ).issue(
            at_ns=begin + 2, deadline_ns=begin + 15, provenance=P,
        ).record_outcome(at_ns=begin + 3, provenance=P)
        actions.append(action)
        original_seq, after_seq = (11, 18) if idx == 0 else (20, 29)
        rows.append({
            "action_id": action.action_id,
            "session_id": SCOPE.world_session_id,
            "capability": "MOVE_PLACE",
            "skill_execution_id": skill.execution_id,
            "intent_id": skill.intent_id,
            "invocation_ref": inv.invocation_ref,
            "preset_ref": inv.parameter_preset_ref,
            "target_ref": inv.target.ref,
            "target_contract_ref": inv.target.contract.contract_ref,
            "source_ref": f"{SCOPE.world_session_id}:{original_seq}",
            "probe_seq": original_seq,
            "probe_request_id": f"req-{original_seq}",
            "after_seq": after_seq,
            "status": "NATIVE_PLACE_MOVE_SETTLED",
            "started_position": {"x": 0.0, "y": 64.0, "z": 0.0},
            "settled_position": {"x": 2.0, "y": 64.0, "z": 0.0},
            "target_position": {"x": 2.0, "y": 64.0, "z": 0.0},
        })
    if not started:
        skill = skill.succeed(reason="bounded child finished", at_ns=100, provenance=P)
    FakeJournal.rows = rows
    FakeJournal.digest = DIGEST
    FakeJournal.unresolved = False
    FakeJournal.restores = 0
    def probe(seq, position, full_time):
        return FakeNativeProbe(
            SCOPE.world_session_id, seq, f"req-{seq}",
            SimpleNamespace(
                position=SimpleNamespace(x=position, y=64.0, z=0.0),
                time=SimpleNamespace(day=0, time_of_day=full_time),
            ),
            Provenance("mineflayer", f"{SCOPE.world_session_id}:{seq}"),
        )
    return dict(
        cognition=cognition, intent=intent, skill=skill,
        actions=tuple(actions), journal_path=Path("/original/never-opened.json"),
        original_wal_sha256=DIGEST, selected_invocation=inv,
        before_probe=probe(11, 0.0, 100),
        after_probe=probe(rows[-1]["after_seq"], 2.0, 120),
        world_id="world-uuid-1", world_epoch=7,
        selected_provenance=P,
    )


@pytest.fixture
def stub_source(monkeypatch):
    import relay_self.c_lane_stage27_source_bridge as bridge

    monkeypatch.setattr(bridge, "_original_stage27_types", lambda: (
        FakeNativeProbe, FakeJournal, FakeJournalError, FakeJournalUnresolved,
        FakeInvocation, FakeTargetBody, FakeStatus, fake_eval,
    ))


def test_real_owner_snapshots_two_action_one_episode_and_no_mutation(stub_source):
    data = _owner_fixture(started=False)
    before_memory = data["cognition"].memories
    before_intent = data["intent"].events
    exp = assemble_stage27_c1_from_canonical_wal(**data)
    assert exp is not None
    assert exp.action_ids == ("action-0", "action-1")
    assert exp.target_outcome is OutcomeAssessment.SUCCESS  # TARGET, not Goal
    assert data["intent"].current_intent is not None
    assert FakeJournal.restores == 2  # original readback and race-fence readback
    assert data["cognition"].memories == before_memory
    assert data["intent"].events == before_intent
    assert assemble_stage27_c1_from_canonical_wal(**data).memory_id == exp.memory_id


def test_running_child_holds_even_with_terminal_native_actions(stub_source):
    assert assemble_stage27_c1_from_canonical_wal(
        **_owner_fixture(started=True)
    ) is None


def test_original_prepared_wal_never_accepted_as_success(stub_source):
    data = _owner_fixture(started=False)
    FakeJournal.unresolved = True
    assert assemble_stage27_c1_from_canonical_wal(**data) is None


def test_canonical_wal_digest_replay_native_and_target_mismatch_fail_closed(stub_source):
    data = _owner_fixture(started=False)
    with pytest.raises(C1AdmissionError, match="digest differs"):
        assemble_stage27_c1_from_canonical_wal(
            **(data | {"original_wal_sha256": "b" * 64})
        )
    data = _owner_fixture(started=False)
    FakeJournal.rows[1]["session_id"] = "foreign-native"
    with pytest.raises(C1AdmissionError, match="lineage mismatch"):
        assemble_stage27_c1_from_canonical_wal(**data)
    data = _owner_fixture(started=False)
    bad_probe = replace(data["after_probe"], session_id="foreign-native")
    with pytest.raises(C1AdmissionError, match="native probe"):
        assemble_stage27_c1_from_canonical_wal(**(data | {"after_probe": bad_probe}))
    data = _owner_fixture(started=False)
    data["selected_invocation"].target.contract.anchor.x = 9.0
    with pytest.raises(C1AdmissionError, match="positions/probes"):
        assemble_stage27_c1_from_canonical_wal(**data)


def test_unknown_target_is_not_fabricated_success(stub_source, monkeypatch):
    data = _owner_fixture(started=False)
    import relay_self.c_lane_stage27_source_bridge as bridge

    monkeypatch.setattr(bridge, "_original_stage27_types", lambda: (
        FakeNativeProbe, FakeJournal, FakeJournalError, FakeJournalUnresolved,
        FakeInvocation, FakeTargetBody, FakeStatus,
        lambda contract, observation: SimpleNamespace(
            status=FakeStatus.UNKNOWN, contract_ref=contract.contract_ref
        ),
    ))
    exp = assemble_stage27_c1_from_canonical_wal(**data)
    assert exp.target_outcome is OutcomeAssessment.UNKNOWN


def test_stage27_original_source_is_present_in_this_integration_only_branch():
    # This separate branch is based on the Stage27 HEAD itself; availability
    # does not imply that a *real* World WAL has been authenticated.
    import relay_self.c_lane_stage27_source_bridge as bridge
    from relay_self.physical_action_journal import PhysicalActionJournal

    assert bridge._original_stage27_types()[1] is PhysicalActionJournal


def test_stage28_original_owner_only_proposes_memory_and_rejects_stale(monkeypatch, stub_source):
    import adapters.mineflayer.python_protocol as native
    from relay_self.cognitive_learning_owner_adapter import propose_existing_memory

    exp = assemble_stage27_c1_from_canonical_wal(**_owner_fixture(started=False))
    module = ModuleType("relay_self.checkpointed_cognitive_runtime_dev")

    class FakeRecovered:
        def __init__(self):
            self.self_id = "self-A"
            self.native_session_id = "native-new-2"
            self.retained = _owner_fixture(started=False)["cognition"]
            self.cohort = object()
            self.fresh_native_observation_required = False
            self.current_worldbody_observation = None

    module.CheckpointedCognitiveOwner = FakeRecovered
    monkeypatch.setitem(sys.modules, module.__name__, module)
    monkeypatch.setattr(native, "MineflayerObservation", FakeNativeProbe)
    owner = FakeRecovered()
    new_probe = FakeNativeProbe(
        "native-new-2", 8, "new-probe",
        SimpleNamespace(time=SimpleNamespace(day=1, time_of_day=8)),
        Provenance("mineflayer", "native-new-2:8"),
    )
    owner.current_worldbody_observation = new_probe
    candidate = propose_for_stage28_original_owner(
        exp, recovered_owner=owner,
        verified_world_id="world-uuid-1", new_native_probe=new_probe,
        integration_provenance=P,
    )
    assert candidate == propose_existing_memory(owner.retained, exp, integration_provenance=P)
    assert owner.retained.memories == ()
    with pytest.raises(C1AdmissionError, match="unqualified"):
        propose_for_stage28_original_owner(
            exp, recovered_owner=owner, verified_world_id="different-world",
            new_native_probe=new_probe, integration_provenance=P,
        )
    owner.fresh_native_observation_required = True
    with pytest.raises(C1AdmissionError, match="unqualified"):
        propose_for_stage28_original_owner(
            exp, recovered_owner=owner, verified_world_id="world-uuid-1",
            new_native_probe=new_probe, integration_provenance=P,
        )
