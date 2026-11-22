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
from relay_self.resident_llama_inference_lane_dev import LlamaSlotIdleReceipt
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
from relay_self.stage28_cognitive_recovery_gate_dev import (
    Stage28ForkPaperEpoch,
    Stage28NativePaperBodyLink,
    Stage28RecoveryHold,
    stage28_inert_cognitive_recovery,
    stage28_require_fresh_l1_eligibility,
)
from relay_self.world_resident_lifecycle_dev import (
    NativeLoginEvidence,
    WorldLifetime,
)


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


def test_schema1_refuses_registry_with_accepted_presets(tmp_path: Path, monkeypatch):
    _, _, _, cuts = _fixture(tmp_path)
    monkeypatch.setattr(type(cuts[0].pattern_registry), "accepted_presets", (object(),), raising=False)
    with pytest.raises(SelfOwnerCheckpointError, match="cannot encode accepted Presets"):
        save_self_owner_cut(tmp_path / "unsafe.json", cuts[0])


def test_explicit_digest_enables_schema2_without_presets(tmp_path: Path):
    world, store, specs, cuts = _fixture(tmp_path)
    for spec, cut in zip(specs, cuts):
        cognition = PersistentCognition(
            IdentitySpecification(cut.self_id, ("Continue as the same Self.",),
                                  Provenance("test-identity", cut.self_id)),
            pattern_registry=cut.pattern_registry,
        )
        save_persistent_cognition(spec.cognition_file, cognition)
        bound = replace(cut, cognition_sha256=hashlib.sha256(
            spec.cognition_file.read_bytes()).hexdigest())
        spec.owner_state_file.unlink()
        save_self_owner_cut(spec.owner_state_file, bound)
        assert json.loads(spec.owner_state_file.read_text())["payload"]["schema"] == 2
        assert load_self_owner_cut(spec.owner_state_file) == bound
    checkpoint = _capture(world, store, specs)
    assert all(c.cognition_sha256 for c in verify_typed_generation(checkpoint))


def test_explicit_digest_rejects_changed_cognition_without_presets(tmp_path: Path):
    world, store, specs, cuts = _fixture(tmp_path)
    spec, cut = specs[0], cuts[0]
    cognition = PersistentCognition(
        IdentitySpecification("A", ("original",), Provenance("test-identity", "A")),
        pattern_registry=cut.pattern_registry,
    )
    save_persistent_cognition(spec.cognition_file, cognition)
    bound = replace(cut, cognition_sha256=hashlib.sha256(
        spec.cognition_file.read_bytes()).hexdigest())
    spec.owner_state_file.unlink()
    save_self_owner_cut(spec.owner_state_file, bound)
    save_persistent_cognition(spec.cognition_file, replace(
        cognition, identity=replace(cognition.identity, directives=("modified",))))
    with pytest.raises(SelfOwnerCheckpointError, match="digest mismatch"):
        _capture(world, store, specs)
    assert latest_verified_generation(store) is None


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


def _stage28_fixture(tmp_path: Path):
    world, store, sources, cuts = _fixture(tmp_path)
    generation = _capture(world, store, sources)
    dest = tmp_path / "restored-staged-world"
    restore_generation(generation, dest, restore_id="stage28-new-world")
    return world, store, sources, cuts, generation, dest


def _stage28_new_native(plan):
    # The new Paper process uses its OWN clock starting at an independent
    # tick, which may be lower than the saved source's W110.
    new_boot_tick = 8
    world = WorldLifetime(
        plan.source_world_id, plan.fork_branch_id, "paper-owned-new", 1,
        new_boot_tick,
    )
    logins = tuple(NativeLoginEvidence(
        sid, 1, plan.source_world_id, plan.fork_branch_id,
        world.paper_session_id, world.epoch,
        "fresh-native-" + sid, new_boot_tick,
        "owned-native-fresh-probe:" + sid,
        True, True, True, True, True,
    ) for sid in plan.roster)
    slot = LlamaSlotIdleReceipt(
        "fresh-owned-backend", 0, 1, False, "GET /slots:0:idle",
    )
    boot = Stage28ForkPaperEpoch(
        plan.generation_id, plan.source_world_id, plan.source_branch_id,
        plan.declared_world_tick, plan.fork_branch_id,
        plan.source_committed_sha256, world.paper_session_id, "fresh-boot",
        world.epoch, new_boot_tick,
        "paper-main-thread:p0d:fresh-boot:nonce:sha256:" + "a" * 64,
        1001, tuple(sorted(dict(plan.old_native_sessions).values())),
    )
    return world, logins, slot, boot


def _stage28_body_links(world, logins, boot):
    # Synthetic contract witness only, not a live Paper/native attestation.
    return tuple(Stage28NativePaperBodyLink(
        self_id=p.self_id, native_session_id=p.native_session_id,
        native_probe_ref=p.observation_ref,
        native_world_time_tick=p.observed_world_tick,
        paper_session_id=p.paper_session_id,
        tick_boot_id=boot.paper_boot_id,
        presence_boot_id="distinct-resident-plugin-boot",
        paper_observed_tick=world.world_tick,
        paper_tick_source_ref=boot.paper_tick_source_ref,
        paper_log_sha256="b" * 64,
        paper_actor_uuid="actor-" + p.self_id,
    ) for p in logins)


def test_stage28_typed_world_a_b_recovery_is_inert_and_fresh_only(tmp_path: Path):
    _, _, _, _, generation, dest = _stage28_fixture(tmp_path)
    plan = stage28_inert_cognitive_recovery(
        generation, dest,
        expected_self_ids=("A", "B"), expected_source_world_id="world-1",
    )
    assert plan.roster == ("A", "B")
    assert plan.declared_world_tick == 110
    assert plan.cut_ticks == (("A", 105), ("B", 105))
    assert [c.semantic.cut.self_id for c in plan.candidates] == ["A", "B"]
    assert plan.candidates[0].semantic.pattern_registry.revision == 1
    assert plan.candidates[0].semantic.intent.current_intent.intent_id == "intent-A"
    assert plan.candidates[1].semantic.skill_histories[0].state is SkillState.STARTED
    assert plan.old_action_replay_authorized is False
    assert plan.old_skill_resume_authorized is False
    assert plan.old_message_redelivery_authorized is False
    assert plan.old_l1_decision_reusable is False
    assert plan.physical_action_issue_authorized is False
    assert plan.l1_reevaluation_eligible is False

    world, logins, idle, boot = _stage28_new_native(plan)
    receipt = stage28_require_fresh_l1_eligibility(
        plan, world=world, logins=logins, idle=idle, boot=boot,
        links=_stage28_body_links(world, logins, boot),
    )
    assert receipt.l1_reevaluation_eligible is True
    assert receipt.physical_action_issue_authorized is False
    assert receipt.old_l1_decision_reusable is False
    assert receipt.old_skill_resume_authorized is False
    assert receipt.source_saved_world_tick == 110
    assert receipt.new_process_boot_tick == 8
    assert receipt.source_and_new_ticks_comparable is False
    assert receipt.native_sessions == (
        ("A", "fresh-native-A"), ("B", "fresh-native-B"),
    )


def test_stage28_world_only_archive_is_not_cognition_checkpoint(tmp_path: Path):
    # The Stage24g world-only layout cannot be upgraded by synthetic Self IDs.
    generation = tmp_path / "world-only-000000000000"
    generation.mkdir()
    (generation / "WORLD_ONLY_COMMITTED.json").write_text("{}")
    with pytest.raises(Stage28RecoveryHold, match="typed World"):
        stage28_inert_cognitive_recovery(
            generation, tmp_path,
            expected_self_ids=("A", "B"), expected_source_world_id="world-1",
        )


@pytest.mark.parametrize("failure", [
    "world-file", "foreign-world", "missing-self", "restored-self",
])
def test_stage28_foreign_or_corrupt_recovery_holds(
    tmp_path: Path, failure: str,
):
    _, _, _, _, generation, dest = _stage28_fixture(tmp_path)
    expected_ids = ("A", "B")
    expected_world = "world-1"
    if failure == "world-file":
        (dest / "world" / "entities" / "r.0.0.mca").write_bytes(
            b"future-zombie-dead"
        )
    elif failure == "foreign-world":
        expected_world = "foreign-world"
    elif failure == "missing-self":
        expected_ids = ("A",)
    else:
        (dest / "selves" / "B" / "cognition.json").write_bytes(b"tampered")
    with pytest.raises(Stage28RecoveryHold):
        stage28_inert_cognitive_recovery(
            generation, dest, expected_self_ids=expected_ids,
            expected_source_world_id=expected_world,
        )


def test_stage28_later_cognition_tick_cannot_join_earlier_world(
    tmp_path: Path,
):
    world, store, sources, cuts = _fixture(tmp_path)
    # Source-cut timestamp C111 cannot coexist with World W110 even when
    # both are internally valid and the owner envelope SHA matches.
    altered = replace(cuts[1], last_observed_world_tick=111)
    sources[1].owner_state_file.unlink()
    save_self_owner_cut(sources[1].owner_state_file, altered)
    generation = _capture(world, store, sources)
    dest = tmp_path / "restored"
    restore_generation(generation, dest, restore_id="stage28-too-late")
    with pytest.raises(Stage28RecoveryHold, match="roster/tick"):
        stage28_inert_cognitive_recovery(
            generation, dest,
            expected_self_ids=("A", "B"), expected_source_world_id="world-1",
        )


@pytest.mark.parametrize("failure", [
    "old-native", "stale-gpu", "stale-transport",
    "foreign-paper", "wrong-world-epoch", "stale-worldbody",
    "busy-slot", "missing-b", "different-world", "duplicate-native",
])
def test_stage28_renewed_l1_requires_fresh_a_b_world_gpu_sources(
    tmp_path: Path, failure: str,
):
    _, _, _, _, generation, dest = _stage28_fixture(tmp_path)
    plan = stage28_inert_cognitive_recovery(
        generation, dest,
        expected_self_ids=("A", "B"), expected_source_world_id="world-1",
    )
    world, logins, idle, boot = _stage28_new_native(plan)
    if failure == "old-native":
        logins = (replace(logins[0], native_session_id="old-session-A"), logins[1])
    elif failure == "stale-gpu":
        logins = (replace(logins[0], stale_gpu_fenced=False), logins[1])
    elif failure == "stale-transport":
        logins = (replace(logins[1], stale_transport_fenced=False), logins[0])
    elif failure == "foreign-paper":
        logins = (replace(logins[0], paper_session_id="old-paper"), logins[1])
    elif failure == "wrong-world-epoch":
        logins = (replace(logins[0], world_epoch=0), logins[1])
    elif failure == "stale-worldbody":
        logins = (
            replace(logins[0], observed_world_tick=-1),
            logins[1],
        )
    elif failure == "busy-slot":
        idle = replace(idle, is_processing=True)
    elif failure == "missing-b":
        logins = (logins[0],)
    elif failure == "different-world":
        world = replace(world, world_id="other-world")
    else:
        logins = (logins[0], replace(
            logins[1], native_session_id=logins[0].native_session_id,
        ))
    with pytest.raises(Stage28RecoveryHold):
        stage28_require_fresh_l1_eligibility(
            plan, world=world, logins=logins, idle=idle, boot=boot,
            links=_stage28_body_links(world, logins, boot),
        )
