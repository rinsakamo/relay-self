"""C1/C1-R/C3 offline hostile tests over the ORIGINAL Owner and canonical WAL."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from relay_self.action import ActionLifecycle
from relay_self.action_supervision import ActionSupervisor
from relay_self.c_lane_retention_reuse_dev import (
    C1RetentionHold,
    OriginalWalPrefixPin,
    assemble_original_intent,
    assemble_quiescent_original_intent,
    c3_next_epoch_read,
    propose_intent_memory,
    retain_original_intent_memory,
    retain_quiescent_original_intent_memory,
)
from relay_self.checkpointed_cognitive_runtime_dev import (
    CheckpointedCognitiveOwner,
    CognitionOwnerCohort,
    CognitiveOwnerFiles,
    ExternalPhysicalFence,
    ExternalRejoin,
    staged_recover_cognition_cohort,
)
from relay_self.cognitive_learning_contract import (
    Comparison,
    ConditionalReuseCandidate,
    CurrentCue,
    EvidenceOrigin,
    GuardCondition,
    OutcomeAssessment,
    RevisionTarget,
    UnderstandingProposal,
)
from relay_self.cognitive_learning_owner_adapter import (
    BoundedSkillRead,
    TargetRead,
    WalActionRead,
    WalDisposition,
    WorldBodyRead,
)
from relay_self.cognitive_minimal_dev import initial_patterns
from relay_self.common_io import Clock, ClockStamp, ScopeRef
from relay_self.coordinated_autosave_runtime_dev import (
    CoordinatedAutosaveRuntime,
    RestartedWorldReceipt,
    StoppedWorldReceipt,
    WorldRuntimeHooks,
)
from relay_self.coordinated_checkpoint_dev import restore_generation, verify_generation
from relay_self.intent import IntentCommitment
from relay_self.persistent_cognition import (
    IdentitySpecification,
    Memory,
    PersistentCognition,
    load_persistent_cognition,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.physical_issue_admission_dev import PhysicalIssueAdmission
from relay_self.provenance import Provenance
from relay_self.relay_engine import BoundedChoice
from relay_self.self_owner_checkpoint_dev import verify_typed_generation
from relay_self.skill import SkillExecution
from relay_self.three_self_present import EpistemicStatus, Lens

P = Provenance("fixture", "synthetic-not-authenticated")


def _fixture(tmp_path, count=3, two_self=False):
    scope = ScopeRef("A", "native-source-1")
    cognition = PersistentCognition(
        IdentitySpecification("A", ("do not acquire new Action rights",), P)
    )
    intent = IntentCommitment()
    intent.commit("intent-A", objective="explore", at_ns=10, provenance=P)
    skill = SkillExecution.start(
        "S1", skill_id="MOVE", intent_commitment=intent, at_ns=20, provenance=P,
    )
    actions = []
    rows = []
    for i in range(count):
        at = 30 + i * 15
        action = ActionLifecycle.propose(
            f"S1-A{i}", skill_execution=skill, intent_commitment=intent,
            at_ns=at, provenance=P,
        ).authorize(at_ns=at + 1, provenance=P, authority="original")
        action = action.issue(at_ns=at + 2, deadline_ns=at + 10, provenance=P)
        action = action.record_outcome(at_ns=at + 3, provenance=P)
        actions.append(action)
        seq = 10 + i * 20
        before_tick = 100 + i * 30
        rows.append({
            "session_id": scope.world_session_id,
            "intent_id": "intent-A", "skill_execution_id": "S1",
            "action_id": action.action_id,
            "capability": "MOVE", "target_ref": "relative:forward",
            "probe_seq": seq, "probe_request_id": f"probe-{i}",
            "source_ref": f"{scope.world_session_id}:{seq}",
            "status": "NATIVE_MOVE_SETTLED", "effect_seqs": [seq + 1, seq + 2],
            "after_seq": seq + 5, "food_before": None, "food_after": None,
            "count_before": None, "count_after": None,
            "control": "forward",
            "started_position": {"x": float(i), "y": 64.0, "z": 0.0},
            "settled_position": {"x": float(i) + 0.2, "y": 64.0, "z": 0.0},
            "initial_stop_seq": seq + 3, "first_stable_seq": seq + 4,
            "initial_stop_tick": before_tick, "first_stable_tick": before_tick + 8,
            "settled_tick": before_tick + 16, "displacement_m": 0.2,
        })
    skill = skill.succeed(reason="skill reviewed", at_ns=120, provenance=P)
    intent.complete("intent-A", reason="original terminal", at_ns=130, provenance=P)
    root = tmp_path / "A"
    root.mkdir()
    journal = PhysicalActionJournal.create(root / "physical-wal.json", self_id="A")
    journal._commit(rows)  # synthetic Native fixture ONLY; never in product code
    pin = OriginalWalPrefixPin(1, journal.certified_prefix_digest(1), "earlier:pin")
    wal = tuple(WalActionRead(
        action.action_id, scope, "world-A",
        WalDisposition.TERMINAL_OUTCOME, P, journal.digest,
    ) for action in actions)
    before = WorldBodyRead(
        scope, "world-A", 7, 10, ClockStamp(Clock.WORLD_TICK, 100),
        (P,), origin=EvidenceOrigin.WORLD_BODY_OBSERVED,
    )
    after = replace(
        before, epoch=8, source_seq=100, clock=ClockStamp(Clock.WORLD_TICK, 200),
    )
    read = BoundedSkillRead(
        cognition=cognition, intent=intent, skill=skill, actions=tuple(actions),
        wal=wal, scope=scope, world_id="world-A",
        goal_ref="EXPLORE", target_ref="target-known", preset_ref="fixed",
        bound_selection_ref=P, before=before, after=after,
        target=TargetRead(OutcomeAssessment.SUCCESS, P, P),
    )
    owner = CheckpointedCognitiveOwner(
        retained=cognition, intent=intent, pattern_registry=initial_patterns(),
        native_session_id=scope.world_session_id, last_observed_tick=200,
        files=CognitiveOwnerFiles(root, root / "cognition.json", journal.path),
        physical_supervisor=ActionSupervisor(), skills=(skill,),
    )
    participants = [owner]
    if two_self:
        other_root = tmp_path / "B"
        other_root.mkdir()
        other_journal = PhysicalActionJournal.create(
            other_root / "physical-wal.json", self_id="B",
        )
        other = CheckpointedCognitiveOwner(
            retained=PersistentCognition(
                IdentitySpecification("B", ("separate memory",), P),
            ),
            intent=IntentCommitment(), pattern_registry=initial_patterns(),
            native_session_id="native-source-B", last_observed_tick=200,
            files=CognitiveOwnerFiles(
                other_root, other_root / "cognition.json", other_journal.path,
            ),
            physical_supervisor=ActionSupervisor(),
        )
        participants.append(other)
    CognitionOwnerCohort(
        owners=tuple(participants), world_id="world-A", branch_id="main",
        external_close_physical=lambda: ExternalPhysicalFence("fence", True, ()),
        external_release_physical=lambda _: None,
        external_native_rejoin=lambda sid, server, old: ExternalRejoin(
            "new-session-" + sid, True, True, True,
        ),
    )
    return owner, read, pin, journal


def _candidate(experience):
    return ConditionalReuseCandidate(
        proposal=UnderstandingProposal(
            "c2:hypothesis", experience.episode_key, 0, Lens.SELF_BODY,
            RevisionTarget.APPLICABILITY, "owner:A", 1,
            "original-choice", Comparison.NO_PREDICTION,
            ("condition:surface",), (), P,
        ),
        candidate_ref="original-choice",
        guard=(GuardCondition("surface", "stone"),),
        rollback_ref="original:fallback", expected_l1_cost_ns=10, provenance=P,
    )


def _c3_args(experience):
    scope = ScopeRef("A", "fresh-reJOIN-session")
    return dict(
        candidate=_candidate(experience), current_scope=scope, current_world_id="world-A",
        current_source_revision_refs=("revision:new",),
        cues=(CurrentCue(
            scope, "surface", "stone", EpistemicStatus.OBSERVED,
            ("revision:new",), (P,),
        ),),
        choice_set=(BoundedChoice("1", "original MOVE"), BoundedChoice("2", "DEFER")),
        viability_confirmed=True, cost_budget_ns=50,
    )


def test_original_intent_multi_action_retention_readback_and_duplicate(tmp_path):
    owner, read, pin, _ = _fixture(tmp_path, count=3)
    episode = assemble_original_intent(owner, (read,), prefix_pin=pin)
    assert episode.action_ids == ("S1-A0", "S1-A1", "S1-A2")
    assert episode.target_outcome is OutcomeAssessment.SUCCESS
    memory = propose_intent_memory(episode, integration_provenance=P)
    assert owner.retained.memories == ()
    retain_original_intent_memory(owner, episode, memory)
    assert load_persistent_cognition(owner.files.cognition_file) == owner.retained
    assert len(owner.retained.memories) == 1
    with pytest.raises(C1RetentionHold, match="duplicate"):
        retain_original_intent_memory(owner, episode, memory)


def test_c3_retained_historical_experience_next_session_and_no_write(tmp_path):
    owner, read, pin, _ = _fixture(tmp_path)
    episode = assemble_original_intent(owner, (read,), prefix_pin=pin)
    retain_original_intent_memory(
        owner, episode, propose_intent_memory(episode, integration_provenance=P),
    )
    restored = load_persistent_cognition(owner.files.cognition_file)
    args = _c3_args(episode)
    prior = owner.files.cognition_file.read_bytes()
    choices, datum, reason = c3_next_epoch_read(restored, **args)
    assert choices == args["choice_set"]
    assert datum is not None and "SHADOW_REUSE" in datum.value_json
    assert reason == "NOT_RETAINED"
    assert owner.files.cognition_file.read_bytes() == prior
    assert len(restored.memories) == 1
    # Fresh native session is not silently treated as the old World observation.
    assert args["current_scope"].world_session_id != episode.episode_key[1]


@pytest.mark.parametrize("override", [
    {"current_world_id": "another-world"},
    {"viability_confirmed": False},
    {"contradictions": ("observed:opposite",)},
    {"current_source_revision_refs": ("old-revision",)},
])
def test_c3_world_contradiction_source_and_viability_abstain(tmp_path, override):
    owner, read, pin, _ = _fixture(tmp_path)
    episode = assemble_original_intent(owner, (read,), prefix_pin=pin)
    retain_original_intent_memory(
        owner, episode, propose_intent_memory(episode, integration_provenance=P),
    )
    kwargs = _c3_args(episode) | override
    choices, datum, reason = c3_next_epoch_read(owner.retained, **kwargs)
    assert choices == kwargs["choice_set"] and datum is None
    assert reason in {
        "WORLD_MISMATCH", "WORLD_BODY_VIABILITY_UNKNOWN",
        "CURRENT_COUNTEREXAMPLE", "STALE_CUE_SOURCE",
    }


def test_c3_unknown_sensor_foreign_self_and_unretained_abstain(tmp_path):
    owner, read, pin, _ = _fixture(tmp_path)
    episode = assemble_original_intent(owner, (read,), prefix_pin=pin)
    args = _c3_args(episode)
    assert c3_next_epoch_read(owner.retained, **args)[1] is None
    cue = args["cues"][0]
    assert c3_next_epoch_read(
        owner.retained, **(args | {
            "cues": (replace(cue, value=None, status=EpistemicStatus.UNKNOWN,
                             source_revision_refs=()),),
        })
    )[1] is None
    with pytest.raises(C1RetentionHold, match="foreign"):
        c3_next_epoch_read(
            owner.retained,
            **(args | {"current_scope": ScopeRef("B", "fresh-session")}),
        )


def test_rehashed_wal_prefix_rewrite_refused_by_earlier_pin(tmp_path):
    owner, read, pin, journal = _fixture(tmp_path)
    # Native row is rewritten, new canonical SHA is valid, but historic pin is not.
    changed = [dict(v) for v in journal.records]
    changed[0]["settled_position"] = {"x": 0.3, "y": 64.0, "z": 0.0}
    changed[0]["displacement_m"] = 0.3
    journal._commit(changed)
    assert PhysicalActionJournal.restore(journal.path, self_id="A").digest == journal.digest
    with pytest.raises(C1RetentionHold, match="historical"):
        assemble_original_intent(owner, (read,), prefix_pin=pin)


def test_stale_session_and_missing_child_or_unattempted_intent_refused(tmp_path):
    owner, read, pin, _ = _fixture(tmp_path)
    with pytest.raises(C1RetentionHold, match="missing/duplicate"):
        assemble_original_intent(owner, (read, read), prefix_pin=pin)
    with pytest.raises(C1RetentionHold, match="session"):
        assemble_original_intent(
            owner, (replace(read, scope=ScopeRef("A", "old-session")),),
            prefix_pin=pin,
        )
    owner.intent.commit("intent-unattempted", objective="idle", at_ns=140, provenance=P)
    # No Skill/Action exists for this newly committed Goal.
    with pytest.raises(C1RetentionHold, match="terminal"):
        assemble_original_intent(owner, (replace(read, skill=replace(
            read.skill, intent_id="intent-unattempted",
        )),), prefix_pin=pin)


def test_target_unknown_never_promotes_skill_or_goal_success(tmp_path):
    owner, read, pin, _ = _fixture(tmp_path)
    read = replace(read, target=TargetRead(OutcomeAssessment.UNKNOWN))
    episode = assemble_original_intent(owner, (read,), prefix_pin=pin)
    assert episode.target_outcome is OutcomeAssessment.UNKNOWN
    payload = json.loads(propose_intent_memory(episode, integration_provenance=P).content)
    assert payload["target_outcome"] == "UNKNOWN"
    assert payload["skill_runs"][0]["target_outcome"] == "UNKNOWN"


def test_c1_rejects_changed_memory_revision_and_wrong_self(tmp_path):
    owner, read, pin, _ = _fixture(tmp_path)
    episode = assemble_original_intent(owner, (read,), prefix_pin=pin)
    memory = propose_intent_memory(episode, integration_provenance=P)
    with pytest.raises(C1RetentionHold, match="altered"):
        retain_original_intent_memory(
            owner, episode, replace(memory, content=memory.content.replace(
                "target-known", "invented-target",
            )),
        )
    owner.retain_memory(Memory("other", "existing knowledge", P, P))
    assert owner.retained.memories[0].memory_id == "other"
    with pytest.raises(C1RetentionHold, match="revision"):
        assemble_original_intent(owner, (read,), prefix_pin=pin)


def test_c1_failed_readback_quarantines_original_cohort(tmp_path, monkeypatch):
    from relay_self import c_lane_retention_reuse_dev as module

    owner, read, pin, _ = _fixture(tmp_path)
    episode = assemble_original_intent(owner, (read,), prefix_pin=pin)
    memory = propose_intent_memory(episode, integration_provenance=P)
    def broken(_path):
        raise OSError("synthetic readback failure")

    monkeypatch.setattr(module, "load_persistent_cognition", broken)
    with pytest.raises(OSError, match="readback"):
        retain_original_intent_memory(owner, episode, memory)
    assert owner.cohort.hold


def test_checkpoint_original_cohort_cut_rejoin_and_two_self_isolation(tmp_path):
    """Existing B checkpoint freeze/rebind captures retained C1, not a C runtime."""
    owner, read, pin, _ = _fixture(tmp_path, two_self=True)
    peer = next(part for part in owner.cohort.owners if part.self_id == "B")
    episode = assemble_original_intent(owner, (read,), prefix_pin=pin)
    retain_original_intent_memory(
        owner, episode, propose_intent_memory(episode, integration_provenance=P),
    )
    assert len(owner.retained.memories) == 1
    assert peer.retained.memories == ()
    checkpoint_admission = owner.cohort.close()
    a_cut = owner.cohort.freeze("A", "g-000000000001")
    b_cut = owner.cohort.freeze("B", "g-000000000001")
    assert a_cut.snapshot.owner_state_file.is_file()
    assert b_cut.snapshot.owner_state_file.is_file()
    assert a_cut.snapshot.cognition_file == owner.files.cognition_file
    assert b_cut.snapshot.cognition_file == peer.files.cognition_file
    assert owner.cohort.rebind("A", "paper-new").new_native_session_id == "new-session-A"
    assert owner.cohort.rebind("B", "paper-new").new_native_session_id == "new-session-B"
    for sid in ("A", "B"):
        owner.cohort.observe_fenced_rejoin_world_tick(
            self_id=sid, native_session_id="new-session-" + sid, world_tick=210,
        )
    owner.cohort.release(checkpoint_admission.token)
    # The existing persisted cognition files are read in a new logical session.
    restored_a = load_persistent_cognition(owner.files.cognition_file)
    restored_b = load_persistent_cognition(peer.files.cognition_file)
    assert restored_a.identity.self_id == "A"
    assert restored_b.identity.self_id == "B"
    assert len(restored_a.memories) == 1
    assert restored_b.memories == ()
    assert owner.native_session_id == "new-session-A"
    assert peer.native_session_id == "new-session-B"
    choices, datum, _ = c3_next_epoch_read(restored_a, **_c3_args(episode))
    assert datum is not None and choices == _c3_args(episode)["choice_set"]
    assert c3_next_epoch_read(
        restored_b, **(_c3_args(episode) | {
            "current_scope": ScopeRef("B", "new-session-B"),
            "cues": (replace(_c3_args(episode)["cues"][0],
                             scope=ScopeRef("B", "new-session-B")),),
        })
    )[1] is None


def test_c3_known_historical_counterexample_and_unknown_outcome_abstain(tmp_path):
    owner, read, pin, _ = _fixture(tmp_path)
    read = replace(read, target=TargetRead(OutcomeAssessment.UNKNOWN))
    episode = assemble_original_intent(owner, (read,), prefix_pin=pin)
    retain_original_intent_memory(
        owner, episode, propose_intent_memory(episode, integration_provenance=P),
    )
    _, datum, why = c3_next_epoch_read(owner.retained, **_c3_args(episode))
    assert datum is None and why == "HISTORICAL_RESULT_NOT_SUCCESS"
    (tmp_path / "another").mkdir()
    owner2, read2, pin2, _ = _fixture(tmp_path / "another")
    second = assemble_original_intent(owner2, (read2,), prefix_pin=pin2)
    retain_original_intent_memory(
        owner2, second, propose_intent_memory(second, integration_provenance=P),
    )
    args = _c3_args(second)
    candidate = args["candidate"]
    known = replace(
        candidate,
        proposal=replace(
            candidate.proposal, counterexample_refs=("known:negative",),
        ),
    )
    _, datum, why = c3_next_epoch_read(
        owner2.retained, **(args | {"candidate": known}),
    )
    assert datum is None and why == "KNOWN_COUNTEREXAMPLE_NOT_RECONCILED"


def test_original_issuer_quiescent_lock_guards_read_and_retention(tmp_path):
    owner, read, pin, _ = _fixture(tmp_path)
    issuer = PhysicalIssueAdmission(
        {"A": owner.native_session_id},
        resident_mode=True,
        allow_resident_move=True,
    )
    experience = assemble_quiescent_original_intent(
        owner, (read,), physical=issuer, prefix_pin=pin,
    )
    memory = propose_intent_memory(experience, integration_provenance=P)
    with issuer.lease(
        self_id="A", native_session_id="native-source-1",
        action_id="new-original-inflight", effect_family="MOVE",
    ):
        with pytest.raises(C1RetentionHold, match="quiescent"):
            assemble_quiescent_original_intent(
                owner, (read,), physical=issuer, prefix_pin=pin,
            )
        with pytest.raises(C1RetentionHold, match="quiescent"):
            retain_quiescent_original_intent_memory(
                owner, experience, memory, physical=issuer,
                reads=(read,), prefix_pin=pin,
            )
        assert not owner.retained.memories
    retain_quiescent_original_intent_memory(
        owner, experience, memory, physical=issuer,
        reads=(read,), prefix_pin=pin,
    )
    assert load_persistent_cognition(owner.files.cognition_file) == owner.retained
    issuer.hold_for_operator()
    with pytest.raises(C1RetentionHold, match="quiescent"):
        assemble_quiescent_original_intent(
            owner, (read,), physical=issuer, prefix_pin=pin,
        )


def test_c1_full_typed_generation_fork_separate_process_c3_no_replay(tmp_path):
    """B-cohort actual generation capture -> external fork -> inert typed restore."""
    owner, read, pin, _ = _fixture(tmp_path, two_self=True)
    peer = next(part for part in owner.cohort.owners if part.self_id == "B")
    experience = assemble_original_intent(owner, (read,), prefix_pin=pin)
    retain_original_intent_memory(
        owner, experience,
        propose_intent_memory(experience, integration_provenance=P),
    )
    world = tmp_path / "world"
    world.mkdir()
    (world / "level.dat").write_bytes(b"CPU-offline-original-World-fixture")
    store = tmp_path / "store"
    store.mkdir()
    paper_session = ["paper-old"]

    def stop():
        return StoppedWorldReceipt(
            "world-A", "main", paper_session[0], 210,
            "synthetic:tick", "synthetic:stopped-process", 0, True,
        )

    def restart():
        paper_session[0] = "paper-restarted"
        return RestartedWorldReceipt("world-A", "main", paper_session[0], True)

    runtime = CoordinatedAutosaveRuntime(
        source_world=world, store=store, world_id="world-A",
        branch_id="main", participants=owner.cohort.participant_hooks(),
        admission=owner.cohort.admission_hooks(),
        world=WorldRuntimeHooks(stop, restart),
        strict_typed_owner_cut=True,
    )
    saved = runtime.run_if_due(0.0)
    assert saved is not None and saved.typed_owner_cut_validated
    assert saved.saved_self_ids == ("A", "B")
    assert verify_generation(saved.generation)["roster"] == ["A", "B"]
    assert len(verify_typed_generation(saved.generation)) == 2
    assert owner.native_session_id == "new-session-A"
    assert peer.native_session_id == "new-session-B"
    assert owner.fresh_native_observation_required
    assert peer.fresh_native_observation_required
    # Post-save actions must not be silently backported into committed memory.
    owner.observe_world_tick(session_id="new-session-A", world_tick=211)
    owner.retain_memory(Memory("future", "not in W210", P, P))
    restored_path = tmp_path / "separate-restored-world"
    receipt = restore_generation(
        saved.generation, restored_path, restore_id="c1-a-b-rollback",
    )
    inert = staged_recover_cognition_cohort(saved.generation, restored_path)
    assert receipt["physical_action_issue_authorized"] is False
    assert receipt["replay_performed"] is False
    assert tuple(x.self_id for x in inert) == ("A", "B")
    a, b = inert
    assert [m.memory_id for m in a.retained.memories] == [experience.memory_id]
    assert b.retained.memories == ()
    assert a.semantic.intent.current_intent is None
    assert a.fresh_worldbody_required and not a.issue_authorized
    assert b.fresh_worldbody_required and not b.issue_authorized
    choices, datum, why = c3_next_epoch_read(
        a.retained, **_c3_args(experience),
    )
    assert choices == _c3_args(experience)["choice_set"]
    assert datum is not None and why == "NOT_RETAINED"
    # Fresh unrelated B cannot reuse A's episode.
    b_args = _c3_args(experience)
    b_cue = replace(b_args["cues"][0], scope=ScopeRef("B", "brand-new-session-B"))
    with pytest.raises(C1RetentionHold, match="foreign"):
        c3_next_epoch_read(
            a.retained, **(b_args | {
                "current_scope": ScopeRef("B", "brand-new-session-B"),
                "cues": (b_cue,),
            }),
        )
    assert c3_next_epoch_read(
        b.retained, **(b_args | {
            "current_scope": ScopeRef("B", "brand-new-session-B"),
            "cues": (b_cue,),
        }),
    )[1] is None
    # Separate interpreter: original B/I typed restore, never a C-owned loader.
    inspect = (
        "import json,sys;"
        "from relay_self.checkpointed_cognitive_runtime_dev import "
        "staged_recover_cognition_cohort;"
        "r=staged_recover_cognition_cohort("
        " __import__('pathlib').Path(sys.argv[1]),"
        " __import__('pathlib').Path(sys.argv[2]));"
        "print(json.dumps({x.self_id:"
        " {'memories':[m.memory_id for m in x.retained.memories],"
        " 'can_issue':x.issue_authorized,'needs_native':x.fresh_worldbody_required}"
        " for x in r},sort_keys=True))"
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    process = subprocess.run(
        [sys.executable, "-B", "-c", inspect, str(saved.generation), str(restored_path)],
        check=True, capture_output=True, text=True, env=env,
    )
    output = json.loads(process.stdout)
    assert output["A"]["memories"] == [experience.memory_id]
    assert output["B"]["memories"] == []
    assert output["A"]["needs_native"] and not output["A"]["can_issue"]
    assert output["B"]["needs_native"] and not output["B"]["can_issue"]
    # Commit hash inventory refuses byte-level tamper, independent of C3 parsing.
    archived = saved.generation / "selves" / "A" / "cognition.json"
    archived.write_bytes(archived.read_bytes() + b" ")
    with pytest.raises(Exception, match="checksum|digest|Self snapshot"):
        verify_generation(saved.generation)


def test_issuer_commit_reassembles_and_refuses_arbitrary_c1_success_claim(tmp_path):
    owner, read, pin, _ = _fixture(tmp_path)
    issuer = PhysicalIssueAdmission(
        {"A": "native-source-1"}, resident_mode=True, allow_resident_move=True,
    )
    source = assemble_quiescent_original_intent(
        owner, (read,), physical=issuer, prefix_pin=pin,
    )
    # Source says UNKNOWN; caller may not replace the Experience with SUCCESS.
    original_unknown = replace(read, target=TargetRead(OutcomeAssessment.UNKNOWN))
    uncertain = assemble_quiescent_original_intent(
        owner, (original_unknown,), physical=issuer, prefix_pin=pin,
    )
    fake = replace(uncertain, target_outcome=OutcomeAssessment.SUCCESS)
    forged_memory = propose_intent_memory(fake, integration_provenance=P)
    with pytest.raises(C1RetentionHold, match="differs from freshly"):
        retain_quiescent_original_intent_memory(
            owner, fake, forged_memory, physical=issuer,
            reads=(original_unknown,), prefix_pin=pin,
        )
    assert source.target_outcome is OutcomeAssessment.SUCCESS
    assert owner.retained.memories == ()
    original_memory = propose_intent_memory(uncertain, integration_provenance=P)
    with pytest.raises(C1RetentionHold, match="differs from freshly"):
        retain_quiescent_original_intent_memory(
            owner, uncertain, original_memory, physical=issuer,
            reads=(read,), prefix_pin=pin,
        )
    assert not owner.files.cognition_file.exists()
    retain_quiescent_original_intent_memory(
        owner, uncertain, original_memory, physical=issuer,
        reads=(original_unknown,), prefix_pin=pin,
    )
    assert len(load_persistent_cognition(owner.files.cognition_file).memories) == 1


def test_parent_intent_two_child_skillruns_mixed_unknown_not_partial(tmp_path):
    owner, first, pin, journal = _fixture(tmp_path)
    # Synthetic second original child under the SAME completed parent Intent.
    # Never install the cloned fixture Skill as a product-side Skill.
    second_skill = replace(first.skill, execution_id="S2")
    second_action = replace(
        first.actions[0], action_id="S2-A0", skill_execution_id="S2",
    )
    owner.skills["S2"] = second_skill
    row = dict(journal.records[-1])
    row.update({
        "skill_execution_id": "S2",
        "action_id": "S2-A0",
        "probe_seq": 100,
        "probe_request_id": "probe-S2",
        "source_ref": "native-source-1:100",
        "effect_seqs": [101, 102],
        "initial_stop_seq": 103,
        "first_stable_seq": 104,
        "after_seq": 105,
        "initial_stop_tick": 220,
        "first_stable_tick": 228,
        "settled_tick": 236,
        "started_position": {"x": 4.0, "y": 64.0, "z": 0.0},
        "settled_position": {"x": 4.2, "y": 64.0, "z": 0.0},
    })
    journal._commit([*journal.records, row])  # synthetic fixture WAL only
    first = replace(
        first, wal=tuple(replace(w, digest_sha256=journal.digest) for w in first.wal),
    )
    second = replace(
        first, skill=second_skill, actions=(second_action,),
        wal=(WalActionRead(
            "S2-A0", first.scope, first.world_id,
            WalDisposition.TERMINAL_OUTCOME, P, journal.digest,
        ),),
        before=replace(
            first.before, source_seq=90, clock=ClockStamp(Clock.WORLD_TICK, 210),
        ),
        after=replace(
            first.after, source_seq=106, clock=ClockStamp(Clock.WORLD_TICK, 240),
        ),
        target=TargetRead(OutcomeAssessment.UNKNOWN),
    )
    exp = assemble_original_intent(owner, (first, second), prefix_pin=pin)
    assert len(exp.skill_runs) == 2
    assert exp.action_ids == ("S1-A0", "S1-A1", "S1-A2", "S2-A0")
    assert exp.target_outcome is OutcomeAssessment.UNKNOWN
    assert exp.skill_runs[0].target_outcome is OutcomeAssessment.SUCCESS
    assert exp.skill_runs[1].target_outcome is OutcomeAssessment.UNKNOWN
    assert len(set(exp.action_ids)) == 4
    forged_second = replace(second, actions=(first.actions[0],))
    with pytest.raises(Exception, match="WAL/Action bijection|foreign Skill"):
        assemble_original_intent(owner, (first, forged_second), prefix_pin=pin)


def test_original_skill_snapshot_identity_required_not_structural_clone(tmp_path):
    owner, read, pin, _ = _fixture(tmp_path)
    clone = replace(read.skill)
    assert clone == read.skill and clone is not read.skill
    with pytest.raises(C1RetentionHold, match="foreign or stale child"):
        assemble_original_intent(
            owner, (replace(read, skill=clone),), prefix_pin=pin,
        )
    assert assemble_original_intent(owner, (read,), prefix_pin=pin).action_ids
