"""#860 typed owner rollback: deterministic A/B cognition + peer exchange contracts."""
from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from relay_self.cognitive_minimal_dev import (
    Origin,
    PatternKind,
    Predicate,
    SchemaPattern,
    accept_learned_pattern,
    initial_patterns,
)
from relay_self.coordinated_autosave_runtime_dev import (
    AdmissionCloseReceipt,
    AdmissionHooks,
    AutosaveBarrierError,
    CoordinatedAutosaveRuntime,
    ReboundSelfReceipt,
    RestartedWorldReceipt,
    SelfFrozenReceipt,
    SelfRuntimeHooks,
    StoppedWorldReceipt,
    WorldRuntimeHooks,
)
from relay_self.coordinated_checkpoint_dev import (
    SelfSnapshotSource,
    capture_generation,
    latest_verified_generation,
    restore_generation,
)
from relay_self.intent import IntentCommitment
from relay_self.persistent_cognition import (
    IdentitySpecification,
    PersistentCognition,
    save_persistent_cognition,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.provenance import Provenance
from relay_self.self_owner_checkpoint_dev import (
    PeerDelivery,
    SelfOwnerCheckpointError,
    SelfOwnerCut,
    capture_typed_generation,
    load_self_owner_cut,
    prepare_typed_owner_restore,
    rehydrate_self_owner,
    save_self_owner_cut,
    verify_typed_generation,
)
from relay_self.skill import SkillExecution, SkillState


def _fixture(tmp_path: Path, *, peer: bool = True, complete_a: bool = True):
    world = tmp_path / "world-source"
    world.mkdir()
    (world / "level.dat").write_bytes(b"checkpoint-world-W100")
    (world / "entities").mkdir()
    (world / "entities" / "r.0.0.mca").write_bytes(b"Z1-uuid-preserved-alive")
    store = tmp_path / "store"
    store.mkdir()
    specs = []
    cuts = []
    messages = (PeerDelivery("m-1", "A", "B", 101, 102, "payload-sha256:123"),) if peer else ()
    for sid in ("A", "B"):
        d = tmp_path / sid
        d.mkdir()
        memory = d / "cognition.json"
        save_persistent_cognition(
            memory, PersistentCognition(IdentitySpecification(
                sid, ("Continue as the same Self.",),
                Provenance("test-identity", sid),
            )),
        )
        journal = d / "wal.json"
        PhysicalActionJournal.create(journal, self_id=sid)
        owner = IntentCommitment()
        prov = Provenance("test-owner", sid)
        owner.commit("intent-" + sid, objective="DEFEND_SELF",
                     at_ns=1000, provenance=prov)
        skill = SkillExecution.start(
            "skill-" + sid, skill_id="ATTACK", intent_commitment=owner,
            at_ns=1010, provenance=prov,
        )
        if sid == "A" and complete_a:
            skill = skill.succeed(reason="observed", at_ns=1020, provenance=prov)
        patterns = initial_patterns()
        if sid == "A":
            learned = SchemaPattern(
                "adaptive-food", 1, "homeostatic", PatternKind.GOAL,
                Predicate.HUNGRY, "HUNGER_RELIEF", "EAT", 1, "FOOD",
                Origin.LEARNED, Provenance("test-learning", "A:pattern"),
            )
            patterns = accept_learned_pattern(
                patterns, learned, accepted_by_self=True,
                expected_revision=patterns.revision,
                allowed_skills=frozenset({("EAT", 1)}),
            )
        cut = SelfOwnerCut(
            generation_id="g-000000000001", self_id=sid,
            world_id="world-1", branch_id="source",
            former_native_session_id="old-session-" + sid,
            last_observed_world_tick=105, intent_events=owner.events,
            skill_executions=(skill,), pattern_registry=patterns,
            peer_deliveries=messages, pending_question_refs=("question-" + sid,),
        )
        owner_file = d / "owner-state.json"
        save_self_owner_cut(owner_file, cut)
        cuts.append(cut)
        specs.append(SelfSnapshotSource(sid, memory, journal, owner_file))
    return world, store, tuple(specs), tuple(cuts)


def _capture(world: Path, store: Path, sources, *, sequence: int = 1):
    return capture_typed_generation(
        world, store, sequence=sequence,
        expected_self_ids=("A", "B"), selves=sources,
        world_id="world-1", branch_id="source", logical_tick=110,
        tick_source_ref="mock:tick110",
        stopped_server_ref="mock:process-exit-0",
        quiesced_selves_ref="mock:all-writers-fenced",
    )


def test_typed_two_self_generation_and_inert_restore(tmp_path: Path):
    world, store, specs, cuts = _fixture(tmp_path)
    assert cuts[0].pattern_registry.revision == 1
    checkpoint = _capture(world, store, specs)
    loaded = verify_typed_generation(checkpoint)
    assert loaded == cuts
    assert len(loaded[0].peer_deliveries) == 1
    assert loaded[0].skill_executions[0].state is SkillState.SUCCEEDED
    assert loaded[1].skill_executions[0].state is SkillState.STARTED
    assert latest_verified_generation(store) == checkpoint

    (world / "entities" / "r.0.0.mca").write_bytes(b"future-zombie-dead")
    # Mutate only the LIVE Source Self A owner after a committed generation.
    new_owner = rehydrate_self_owner(cuts[0]).intent
    prov = Provenance("future-owner", "A")
    new_owner.complete(
        "intent-A", reason="completed after checkpoint",
        at_ns=9999, provenance=prov,
    )
    new_owner.commit(
        "future-intent", objective="EXPLORE",
        at_ns=10000, provenance=prov,
    )
    altered = replace(cuts[0], intent_events=new_owner.events, peer_deliveries=())
    specs[0].owner_state_file.unlink()
    save_self_owner_cut(specs[0].owner_state_file, altered)

    dest = tmp_path / "new-branch"
    receipt = restore_generation(checkpoint, dest, restore_id="reset1")
    candidates = prepare_typed_owner_restore(checkpoint, dest)
    assert receipt["physical_action_issue_authorized"] is False
    assert receipt["replay_performed"] is False
    assert len(candidates) == 2
    assert candidates[0].intent.current_intent.intent_id == "intent-A"
    assert candidates[0].pattern_registry.revision == 1
    assert candidates[1].skill_histories[0].state is SkillState.STARTED
    assert candidates[1].old_skill_resume_authorized is False
    assert candidates[1].old_native_session_invalid is True
    assert candidates[1].old_message_redelivery_authorized is False
    assert candidates[1].new_physical_action_issue_authorized is False
    assert (dest / "world" / "entities" / "r.0.0.mca").read_bytes() == (
        b"Z1-uuid-preserved-alive"
    )
    assert load_self_owner_cut(specs[0].owner_state_file).intent_events != (
        candidates[0].cut.intent_events
    )


@pytest.mark.parametrize("failure", ["missing-b", "message-mismatch", "wrong-generation",
                                     "foreign-session", "foreign-roster"])
def test_bad_cross_self_cut_cannot_commit(tmp_path: Path, failure: str):
    world, store, specs, cuts = _fixture(tmp_path)
    if failure == "missing-b":
        specs = specs[:1]
    else:
        edited = cuts[1]
        if failure == "message-mismatch":
            edited = replace(edited, peer_deliveries=(
                replace(edited.peer_deliveries[0], payload_ref="different"),
            ))
        elif failure == "wrong-generation":
            edited = replace(edited, generation_id="g-000000000002")
        elif failure == "foreign-session":
            edited = replace(
                edited, former_native_session_id=cuts[0].former_native_session_id,
            )
        else:
            edited = replace(edited, peer_deliveries=(
                replace(edited.peer_deliveries[0], sender_self_id="C"),
            ))
        specs[1].owner_state_file.unlink()
        save_self_owner_cut(specs[1].owner_state_file, edited)
    with pytest.raises((SelfOwnerCheckpointError, ValueError)):
        _capture(world, store, specs)
    assert latest_verified_generation(store) is None
    if (store / "g-000000000001").exists():
        assert not (store / "g-000000000001" / "COMMITTED.json").exists()


def test_modified_owner_payload_and_digest_rejected(tmp_path: Path):
    world, store, specs, _ = _fixture(tmp_path)
    tamper = json.loads(specs[0].owner_state_file.read_text())
    tamper["payload"]["intent_events"][0]["intent_id"] = "forged"
    specs[0].owner_state_file.write_text(json.dumps(tamper))
    with pytest.raises(SelfOwnerCheckpointError, match="digest"):
        load_self_owner_cut(specs[0].owner_state_file)
    with pytest.raises(SelfOwnerCheckpointError):
        _capture(world, store, specs)
    assert latest_verified_generation(store) is None


def test_semantically_impossible_intent_rejected_even_if_hash_recomputed(tmp_path: Path):
    world, store, specs, _ = _fixture(tmp_path)
    file = specs[0].owner_state_file
    raw = json.loads(file.read_text())
    ev = raw["payload"]["intent_events"][0]
    ev["kind"] = "completed"
    ev["reason"] = "unsupported-close"
    ev["objective"] = None
    blob = (json.dumps(raw["payload"], ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()
    raw["sha256"] = hashlib.sha256(blob).hexdigest()
    file.write_text(json.dumps(raw))
    with pytest.raises(SelfOwnerCheckpointError, match="transition"):
        load_self_owner_cut(file)
    with pytest.raises(SelfOwnerCheckpointError):
        _capture(world, store, specs)


def test_generic_opaque_generation_is_not_typed_owner_recovery(tmp_path: Path):
    world, store, specs, _ = _fixture(tmp_path)
    specs[1].owner_state_file.unlink()
    specs[1].owner_state_file.write_text('{"opaque":"placeholder"}')
    legacy = capture_generation(
        world, store, sequence=1,
        expected_self_ids=("A", "B"), selves=specs,
        world_id="world-1", branch_id="source", logical_tick=110,
        tick_source_ref="operator:tick", stopped_server_ref="operator:stop",
        quiesced_selves_ref="operator:fence",
    )
    assert legacy.exists()
    with pytest.raises(SelfOwnerCheckpointError):
        verify_typed_generation(legacy)


def test_started_skill_is_snapshot_only_not_physical_permission(tmp_path: Path):
    _, _, _, cuts = _fixture(tmp_path, peer=False, complete_a=False)
    materialized = rehydrate_self_owner(cuts[0])
    assert materialized.intent.current_intent.intent_id == "intent-A"
    assert materialized.skill_histories[0].state is SkillState.STARTED
    assert materialized.old_skill_resume_authorized is False
    assert materialized.new_physical_action_issue_authorized is False


def test_restore_cannot_accept_modified_peer_or_foreign_receipt(tmp_path: Path):
    world, store, specs, _ = _fixture(tmp_path)
    checkpoint = _capture(world, store, specs)
    destination = tmp_path / "branch"
    restore_generation(checkpoint, destination, restore_id="r1")
    receipt_file = destination / "RESTORE_PREPARED.json"
    receipt = json.loads(receipt_file.read_bytes())
    receipt["generation_id"] = "g-000000000099"
    receipt_file.write_text(json.dumps(receipt))
    with pytest.raises(SelfOwnerCheckpointError, match="same generation"):
        prepare_typed_owner_restore(checkpoint, destination)



def _runtime_typed_cohort(world, store, specs):
    """Synthetic external hooks. Strict owner check is real; Paper is NOT."""
    observations = []
    state = {"closed": False}

    def close():
        state["closed"] = True
        observations.append("close")
        return AdmissionCloseReceipt("admission-owner", True, True, True)

    def release(token):
        assert state["closed"] and token == "admission-owner"
        observations.append("release")
        state["closed"] = False

    hooks = []
    for item in specs:
        def frozen(generation, source=item):
            assert state["closed"]
            observations.append("freeze:" + source.self_id)
            return SelfFrozenReceipt(
                source.self_id, source, "old-session-" + source.self_id,
                generation + ":fenced", (), (), True, True, True,
            )

        def rebound(_server_session, source=item):
            assert state["closed"]
            observations.append("rebind:" + source.self_id)
            return ReboundSelfReceipt(
                source.self_id, "new-session-" + source.self_id,
                "world-1", "source", True, True, True, True,
            )

        hooks.append(SelfRuntimeHooks(item.self_id, frozen, rebound))

    def stop():
        observations.append("stop")
        return StoppedWorldReceipt(
            "world-1", "source", "paper-old", 110,
            "mock:tick", "mock:exit0", 0, True,
        )

    def start():
        observations.append("restart")
        return RestartedWorldReceipt("world-1", "source", "paper-new", True)

    runtime = CoordinatedAutosaveRuntime(
        source_world=world, store=store, world_id="world-1",
        branch_id="source", participants=tuple(hooks),
        world=WorldRuntimeHooks(stop, start),
        admission=AdmissionHooks(close, release),
        strict_typed_owner_cut=True,
    )
    return runtime, observations


def test_runtime_strict_typed_cut_commits_before_paper_restarts(tmp_path: Path):
    world, store, specs, _ = _fixture(tmp_path)
    # Leave an uncommitted generation 0 so the typed saved cuts use g-1.
    (store / "g-000000000000").mkdir()
    runtime, events = _runtime_typed_cohort(world, store, specs)
    result = runtime.run_if_due(0.0)
    assert result is not None and result.sequence == 1
    assert result.typed_owner_cut_validated is True
    assert len(verify_typed_generation(result.generation)) == 2
    assert events == [
        "close", "freeze:A", "freeze:B", "stop", "restart",
        "rebind:A", "rebind:B", "release",
    ]


def test_runtime_holds_when_peer_delivery_missing_before_restart(tmp_path: Path):
    world, store, specs, cuts = _fixture(tmp_path)
    (store / "g-000000000000").mkdir()
    modified_b = replace(cuts[1], peer_deliveries=())
    file = specs[1].owner_state_file
    file.unlink()
    save_self_owner_cut(file, modified_b)
    runtime, events = _runtime_typed_cohort(world, store, specs)
    with pytest.raises(AutosaveBarrierError, match="admission must remain held"):
        runtime.run_if_due(0.0)
    assert runtime.held_after_failure
    assert latest_verified_generation(store) is None
    assert "restart" not in events and "release" not in events
    assert not (store / "g-000000000001" / "COMMITTED.json").exists()



@pytest.mark.parametrize("corruption", ["missing-cognition", "legacy-downgrade"])
def test_accepted_preset_two_cut_mismatch_refuses_generation_before_commit(
    tmp_path: Path, corruption: str,
) -> None:
    """No original physical issue or COMMITTED marker on skewed Self learning."""
    from relay_self.cognitive_minimal_dev import (
        PatternRegistry,
        PresetAcceptanceReceipt,
        accept_skill_parameter_preset,
    )
    from relay_self.initial_skill_ir import initial_skill_definitions
    from relay_self.persistent_cognition import load_persistent_cognition
    from relay_self.skill_invocation import (
        SkillBudget,
        SkillConstraints,
        SkillParameterPreset,
    )

    world, store, specs, cuts = _fixture(tmp_path)
    definition = next(d for d in initial_skill_definitions() if d.skill_id == "EAT")
    preset = SkillParameterPreset(
        "hunger-eat", "SourceOnly", 1, definition.definition_ref,
        SkillConstraints(), SkillBudget(1, 2000),
        Provenance("l2-proposal", "A:accepted"),
    )
    accepted = accept_skill_parameter_preset(
        cuts[0].pattern_registry, preset, definition=definition,
        receipt=PresetAcceptanceReceipt(
            "A", "A-event", preset.preset_ref,
            Provenance("self-owner", "A:decision"),
        ),
        accepted_by_self=True,
        expected_revision=cuts[0].pattern_registry.revision,
        available_skills=frozenset({("EAT", 1)}),
    )
    file = specs[0].owner_state_file
    file.unlink()
    if corruption == "missing-cognition":
        # v2 typed owner retains accepted parameters, v3 cognitive Self file
        # was not committed alongside it.
        save_self_owner_cut(file, replace(cuts[0], pattern_registry=accepted))
    else:
        # v3 cognition contains the adopted revision but owner cut is an
        # old schema-1 projection that silently omits the Preset.
        old = load_persistent_cognition(specs[0].cognition_file)
        save_persistent_cognition(
            specs[0].cognition_file,
            old.retain_schema_registry(accepted),
        )
        legacy = PatternRegistry(accepted.revision, accepted.patterns)
        save_self_owner_cut(file, replace(cuts[0], pattern_registry=legacy))
    with pytest.raises(SelfOwnerCheckpointError, match="disagree"):
        _capture(world, store, specs)
    assert latest_verified_generation(store) is None
    assert not (store / "g-000000000001" / "COMMITTED.json").exists()
