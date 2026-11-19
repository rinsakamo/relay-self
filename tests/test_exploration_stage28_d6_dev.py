"""D Lane D6: actual B Stage28 owner close/freeze and restore (CPU DEV).

All tests use the real unmodified B owner/cohort/runtime/recovery classes. Native
and stopped-Paper receipts are SYNTHETIC; no real server/model/physical run.
"""
from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from adapters.mineflayer.python_protocol import (
    MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
    MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
    MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
    MineflayerNearbyEntitiesCoverage,
    MineflayerObservation,
    MineflayerPosition,
    MineflayerSnapshot,
    MineflayerTime,
)
from relay_self.action_supervision import ActionSupervisor
from relay_self.checkpointed_cognitive_runtime_dev import (
    CheckpointedCognitiveOwner,
    CognitionOwnerCohort,
    CognitiveOwnerFiles,
    ExternalPhysicalFence,
    ExternalRejoin,
    LiveCognitionCheckpointError,
)
from relay_self.coordinated_autosave_runtime_dev import (
    AutosaveBarrierError,
    CoordinatedAutosaveRuntime,
    RestartedWorldReceipt,
    StoppedWorldReceipt,
    WorldRuntimeHooks,
)
from relay_self.coordinated_checkpoint_dev import restore_generation
from relay_self.exploration_checkpoint_bridge_dev import (
    D4OwnerHold,
    ResidentD4Scope,
    inspect_d4_inert_recovery,
    reserve_resident_l2,
)
from relay_self.exploration_continuity_dev import (
    AttemptPhase,
    ExplorationContinuityError,
    open_question_refs,
    validate_persisted_l2_reservation,
)
from relay_self.exploration_stage28_fresh_gate_dev import (
    D6FreshReconsiderationHold,
    inspect_d6_new_exploration_reevaluation,
)
from relay_self.persistent_cognition import (
    load_persistent_cognition,
    save_persistent_cognition,
)
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.resident_cognitive_work_owner_dev import ResidentCognitiveWorkError
from relay_self.resident_llama_inference_lane_dev import LlamaSlotIdleReceipt
from relay_self.self_owner_checkpoint_dev import verify_typed_generation
from relay_self.stage28_cognitive_recovery_gate_dev import (
    Stage28ForkPaperEpoch,
    Stage28NativePaperBodyLink,
)
from relay_self.stage28c2_recovered_resident_owner_dev import (
    prepare_recovered_a_b_resident_owners,
)
from relay_self.world_resident_lifecycle_dev import NativeLoginEvidence, WorldLifetime
from test_exploration_goal_dev_v01 import (
    OWNER,
    build,
    choose,
    d3_question,
    d3_reserved,
    setup,
)


def _original_b_cohort(
    tmp_path: Path, *, bad_a_pending: bool = False, skip_b_l2_attempt: bool = False,
):
    owners = []
    old_tasks = {}
    original = {}
    for sid in ("A", "B"):
        c = setup(sid, with_target=False, with_preset=(sid == "A"))
        if sid == "A":
            c["retained"] = c["retained"].retain_schema_registry(c["registry"])
        d3_question(c)
        task = None
        if sid != "B" or not skip_b_l2_attempt:
            c["retained"], task = d3_reserved(
                c, native_session_ref="native-old-" + sid,
            )
            assert task is not None
        root = tmp_path / sid
        root.mkdir()
        wal = root / "physical-wal.json"
        PhysicalActionJournal.create(wal, self_id=sid)
        files = CognitiveOwnerFiles(
            root, root / "cognition.json", wal,
        )
        save_persistent_cognition(files.cognition_file, c["retained"])
        owner = CheckpointedCognitiveOwner(
            retained=c["retained"], intent=c["owner"],
            pattern_registry=c["registry"], native_session_id="native-old-" + sid,
            last_observed_tick=100, files=files,
            physical_supervisor=ActionSupervisor(),
            pending_questions=(
                () if bad_a_pending and sid == "A"
                else c["present"].active_question_refs
            ),
        )
        owners.append(owner)
        old_tasks[sid] = task
        original[sid] = c
    status = {"closed": False, "released": False}

    def close_physical():
        assert not status["closed"]
        status["closed"] = True
        return ExternalPhysicalFence("external-physical-closed", True, ())

    def release_physical(ref):
        assert status["closed"] and ref == "external-physical-closed"
        status["released"] = True
        status["closed"] = False

    def rejoin_native(sid, server_session, old):
        assert status["closed"]
        assert server_session == "paper-next"
        assert old == "native-old-" + sid
        return ExternalRejoin(
            "native-next-" + sid, True, True, True,
        )

    cohort = CognitionOwnerCohort(
        owners=tuple(owners), world_id="world-A", branch_id="source",
        external_close_physical=close_physical,
        external_release_physical=release_physical,
        external_native_rejoin=rejoin_native,
    )
    world = tmp_path / "world"
    world.mkdir()
    (world / "level.dat").write_bytes(b"W110-local-synthetic")
    (world / "entities").mkdir()
    (world / "entities" / "r.0.0.mca").write_bytes(b"zombie-still-alive")
    # Stage28c2 requires the ACTUAL B typed three-dimension Paper layout.
    for dimension_name in ("world_nether", "world_the_end"):
        dimension = tmp_path / dimension_name
        dimension.mkdir()
        (dimension / "region").mkdir()
        (dimension / "region" / "r.0.0.mca").write_bytes(b"saved-synthetic")
    store = tmp_path / "generations"
    store.mkdir()

    def stop_world():
        assert status["closed"]
        return StoppedWorldReceipt(
            "world-A", "source", "paper-old", 110,
            "synthetic:main-tick", "synthetic:paper-stopped", 0, True,
        )

    def restart_world():
        assert status["closed"]
        return RestartedWorldReceipt(
            "world-A", "source", "paper-next", True,
        )

    autosave = CoordinatedAutosaveRuntime(
        source_world=world, store=store, world_id="world-A",
        branch_id="source",
        participants=cohort.participant_hooks(),
        world=WorldRuntimeHooks(stop_world, restart_world),
        admission=cohort.admission_hooks(),
        strict_typed_owner_cut=True, paper_layout=True,
        freeze_workers=2,
    )
    return owners, original, old_tasks, cohort, autosave, status


def _actual_cut_and_restore(tmp_path, *, skip_b_l2_attempt: bool = False):
    owners, context, tasks, cohort, autosave, state = _original_b_cohort(
        tmp_path, skip_b_l2_attempt=skip_b_l2_attempt,
    )
    result = autosave.run_if_due(60.0)
    assert result is not None
    assert result.typed_owner_cut_validated
    assert result.saved_self_ids == ("A", "B")
    assert state["released"]
    generation = result.generation
    restored = tmp_path / "forked"
    restore_receipt = restore_generation(generation, restored, restore_id="d6-restart")
    assert restore_receipt["physical_action_issue_authorized"] is False
    assert restore_receipt["replay_performed"] is False
    digest = hashlib.sha256(
        (generation / "COMMITTED.json").read_bytes()
    ).hexdigest()
    return (
        owners, context, tasks, cohort, autosave, generation, restored,
        restore_receipt, digest,
    )


def test_d6_actual_b_original_cohort_freeze_commits_questions_presets_and_attempts(tmp_path):
    (owners, contexts, attempts, cohort, runtime, gen,
     fork, receipt, digest) = _actual_cut_and_restore(tmp_path)
    cuts = verify_typed_generation(gen)
    assert len(cuts) == 2
    assert len(cuts[0].pattern_registry.accepted_presets) == 1
    assert len(cuts[1].pattern_registry.accepted_presets) == 0
    assert cuts[0].pending_question_refs == ("question:ridge",)
    assert cuts[1].pending_question_refs == ("question:forest",)
    assert all(x.former_native_session_id == "native-old-" + x.self_id for x in cuts)
    assert owners[0].native_session_id == "native-next-A"
    assert owners[1].native_session_id == "native-next-B"
    assert all(o.fresh_native_observation_required for o in owners)
    for sid in ("A", "B"):
        retained = load_persistent_cognition(gen / "selves" / sid / "cognition.json")
        assert open_question_refs(retained, expected_self_id=sid) == (
            contexts[sid]["present"].active_question_refs[0],
        )
        assert retained.exploration_continuity.attempts[0].phase is AttemptPhase.RESERVED
        assert retained.exploration_continuity.attempts[0].attempt_ref == (
            attempts[sid].attempt_ref
        )
    plan = inspect_d4_inert_recovery(
        gen, fork, expected_self_ids=("A", "B"),
        expected_source_world_id="world-A", expected_committed_sha256=digest,
    )
    assert plan.generation_id == gen.name
    assert plan.current_native_session_attested is False
    assert plan.l2_dispatch_authorized is False
    assert plan.physical_action_issue_authorized is False
    assert tuple(s.self_id for s in plan.restored) == ("A", "B")
    assert (fork / "world" / "entities" / "r.0.0.mca").read_bytes() == (
        b"zombie-still-alive"
    )
    assert runtime.held_after_failure is False
    assert cohort.closed is False


def test_d6_freeze_old_l2_reservation_cannot_be_reused_after_native_rebind(tmp_path):
    (owners, contexts, attempts, _, _, gen, fork, _,
     _) = _actual_cut_and_restore(tmp_path)
    for sid in ("A", "B"):
        old = attempts[sid]
        with pytest.raises(ExplorationContinuityError, match="stale L2 session"):
            validate_persisted_l2_reservation(
                fork / "selves" / sid / "cognition.json",
                reservation=old, current_scope=contexts[sid]["scope"],
                current_native_session_ref="native-next-" + sid,
                current_intent_owner_revision=4,
                current_source_revision_refs=contexts[sid]["sources"],
            )


def test_d6_actual_b_restore_remains_offline_until_new_login(tmp_path):
    (_, contexts, attempts, _, _, gen, fork, receipt,
     digest) = _actual_cut_and_restore(tmp_path)
    rebuilt = prepare_recovered_a_b_resident_owners(
        gen, fork, expected_world_id="world-A",
        expected_source_branch_id="source",
        expected_committed_sha256=digest,
        expected_fork_branch_id=receipt["fork_branch_id"],
    )
    assert rebuilt.physical.all_residents_offline
    assert tuple(sorted(rebuilt.owners)) == ("A", "B")
    for sid in ("A", "B"):
        owner = rebuilt.owners[sid]
        assert owner.fresh_native_observation_required
        assert owner.native_session_id == "native-old-" + sid
        assert owner.retained.exploration_continuity.attempts[0].phase is (
            AttemptPhase.RESERVED
        )
        assert owner.retained.identity.self_id == sid
        assert not owner.supervisor.open_actions
        with pytest.raises(ResidentCognitiveWorkError, match="not online"):
            rebuilt.cognitive_work.current_scope(sid)
        with pytest.raises(D4OwnerHold):
            reserve_resident_l2(
                owner, rebuilt.cognitive_work,
                scope=ResidentD4Scope(
                    sid, contexts[sid]["scope"].world_session_id, 1,
                    "native-old-" + sid, 1, 0, None,
                ),
                round_=build(contexts[sid]),
                selection=choose(
                    contexts[sid], build(contexts[sid]), "ESCALATE_L2",
                ),
                owner_provenance=OWNER,
            )


def _synthetic_native_probe(*, self_id: str, native: str, tick: int):
    """Typed Mineflayer probe constructed offline; not a witnessed Paper join."""
    return MineflayerObservation(
        kind="probe", seq=1, session_id=native,
        request_id="d6-new-probe-" + self_id,
        snapshot=MineflayerSnapshot(
            health=20, food=20, food_saturation=5, oxygen_level=None,
            position=MineflayerPosition(0.0, 64.0, 0.0),
            time=MineflayerTime(time_of_day=tick % 24000,
                                day=tick // 24000, is_day=True),
            inventory=(), nearby_entities=(),
            nearby_entities_coverage=MineflayerNearbyEntitiesCoverage(
                MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
                MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
                MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES, 0, False,
            ),
        ),
    )


def test_d6_new_probe_and_new_l1_turn_keep_old_l2_attempt_suppressed(tmp_path):
    (_, contexts, old_tasks, _, _, generation, fork, receipt,
     digest) = _actual_cut_and_restore(tmp_path)
    recovered = prepare_recovered_a_b_resident_owners(
        generation, fork, expected_world_id="world-A",
        expected_source_branch_id="source",
        expected_committed_sha256=digest,
        expected_fork_branch_id=receipt["fork_branch_id"],
    )
    for sid in ("A", "B"):
        owner = recovered.owners[sid]
        new_native = "new-recovery-native-" + sid
        recovered.cognitive_work.bind_login(
            self_id=sid, native_session_id=new_native,
            world_epoch=2, world_tick=100,
        )
        probe = _synthetic_native_probe(self_id=sid, native=new_native, tick=100)
        owner.accept_rejoined_worldbody(
            probe, request_id=probe.request_id,
        )
        epoch, native, world_epoch = recovered.cognitive_work.current_scope(sid)
        # This is a fresh CPU-created Present/numbered L1 selection; it is
        # not old-GPU-response replay or external Gemma inference.
        current = setup(sid, with_target=False, with_preset=False)
        current["owner"] = owner.intent
        now = build(current, owner_revision=5)
        assert now.present.active_question_refs == (
            "question:ridge" if sid == "A" else "question:forest",
        )
        selected = choose(current, now, "ESCALATE_L2")
        assert selected.status == "ESCALATE_L2"
        ticket = reserve_resident_l2(
            owner, recovered.cognitive_work,
            scope=ResidentD4Scope(
                sid, current["scope"].world_session_id, epoch,
                native, world_epoch, len(owner.intent.events),
                owner.intent.last_at_ns,
            ),
            round_=now, selection=selected, owner_provenance=OWNER,
        )
        assert ticket is None  # Same Question+evidence, already RESERVED
        assert owner.retained.exploration_continuity.attempts[0].attempt_ref == (
            old_tasks[sid].attempt_ref
        )
        assert load_persistent_cognition(owner.files.cognition_file) == owner.retained
    assert recovered.physical.all_residents_offline
    assert recovered.physical.active_action_ids == ()


def test_d6_missing_question_at_original_freeze_blocks_commit_and_release(tmp_path):
    owners, _, _, cohort, runtime, state = _original_b_cohort(
        tmp_path, bad_a_pending=True,
    )
    with pytest.raises(AutosaveBarrierError, match="checkpoint failed"):
        runtime.run_if_due(60.0)
    assert runtime.held_after_failure
    assert cohort.hold
    assert cohort.closed
    assert state["closed"] and not state["released"]
    assert (tmp_path / "generations" / "g-000000000000").is_dir()
    assert not (
        tmp_path / "generations" / "g-000000000000" / "COMMITTED.json"
    ).exists()
    for owner in owners:
        with pytest.raises(LiveCognitionCheckpointError):
            owner.retain_memory(
                __import__("relay_self.persistent_cognition",
                           fromlist=["Memory"]).Memory(
                    "new", "forbidden during freeze", OWNER, OWNER,
                ),
            )



def _d6_new_world_sources(plan):
    """Synthetic exact-shape witnesses checked by the actual B Stage28 gate."""
    world = WorldLifetime(
        plan.source_world_id, plan.fork_branch_id, "paper-owned-d6-fork", 2, 8,
    )
    logins = tuple(
        NativeLoginEvidence(
            sid, 1, world.world_id, world.branch_id,
            world.paper_session_id, world.epoch,
            "new-recovery-native-" + sid, 8,
            "d6-new-probe-" + sid,
            True, True, True, True, True,
        ) for sid in plan.roster
    )
    idle = LlamaSlotIdleReceipt(
        "synthetic-single-backend", 0, 1, False, "synthetic GET /slots idle",
    )
    boot = Stage28ForkPaperEpoch(
        plan.generation_id, plan.source_world_id, plan.source_branch_id,
        plan.declared_world_tick, plan.fork_branch_id,
        plan.source_committed_sha256,
        world.paper_session_id, "d6-fork-boot",
        world.epoch, world.world_tick,
        "paper-main-thread:p0d:d6-fork-boot:nonce:sha256:" + "a" * 64,
        1001,
        tuple(sorted(dict(plan.old_native_sessions).values())),
    )
    links = tuple(
        Stage28NativePaperBodyLink(
            self_id=p.self_id,
            native_session_id=p.native_session_id,
            native_probe_ref=p.observation_ref,
            native_world_time_tick=p.observed_world_tick,
            paper_session_id=world.paper_session_id,
            tick_boot_id=boot.paper_boot_id,
            presence_boot_id="independent-d6-boot",
            paper_observed_tick=world.world_tick,
            paper_tick_source_ref=boot.paper_tick_source_ref,
            paper_log_sha256="b" * 64,
            paper_actor_uuid="d6-actor-" + p.self_id,
        ) for p in logins
    )
    return world, logins, idle, boot, links


def _d6_loaded_online(tmp_path):
    (_, contexts, old_tasks, _, _, generation, fork, receipt,
     digest) = _actual_cut_and_restore(tmp_path)
    recovered = prepare_recovered_a_b_resident_owners(
        generation, fork, expected_world_id="world-A",
        expected_source_branch_id="source",
        expected_committed_sha256=digest,
        expected_fork_branch_id=receipt["fork_branch_id"],
    )
    world, logins, idle, boot, links = _d6_new_world_sources(recovered.plan)
    for sid in ("A", "B"):
        native = "new-recovery-native-" + sid
        recovered.cognitive_work.bind_login(
            self_id=sid, native_session_id=native,
            world_epoch=world.epoch, world_tick=8,
        )
        probe = _synthetic_native_probe(self_id=sid, native=native, tick=8)
        recovered.owners[sid].accept_rejoined_worldbody(
            probe, request_id=probe.request_id,
        )
    return recovered, contexts, old_tasks, world, logins, idle, boot, links


def test_d6_b_real_fresh_l1_gate_precedes_new_exploration_reconsideration(tmp_path):
    (recovered, contexts, old_tasks, world, logins,
     idle, boot, links) = _d6_loaded_online(tmp_path)
    admitted = inspect_d6_new_exploration_reevaluation(
        recovered, world=world, logins=logins, idle=idle, boot=boot, links=links,
    )
    assert admitted.eligibility.l1_reevaluation_eligible is True
    assert admitted.eligibility.source_and_new_ticks_comparable is False
    assert admitted.old_l1_decision_reusable is False
    assert admitted.l2_model_call_authorized is False
    assert admitted.action_issue_authorized is False
    assert tuple(x.self_id for x in admitted.questions) == ("A", "B")
    for q in admitted.questions:
        sid = q.self_id
        assert q.native_session_id == "new-recovery-native-" + sid
        assert q.active_question_refs == ("question:ridge" if sid == "A"
                                          else "question:forest",)
        assert q.prior_l2_attempt_refs == (old_tasks[sid].attempt_ref,)
        assert q.prior_l2_reissue_authorized is False
        current = setup(sid, with_target=False, with_preset=False)
        current["owner"] = recovered.owners[sid].intent
        # A NEW bounded CPU-driven L1 decision, still no model/physical call:
        fresh = build(current, owner_revision=5)
        selected = choose(current, fresh, "ESCALATE_L2")
        assert selected.status == "ESCALATE_L2"
        owner = recovered.owners[sid]
        epoch, native, world_epoch = recovered.cognitive_work.current_scope(sid)
        assert reserve_resident_l2(
            owner, recovered.cognitive_work,
            scope=ResidentD4Scope(
                sid, current["scope"].world_session_id,
                epoch, native, world_epoch,
                len(owner.intent.events), owner.intent.last_at_ns,
            ),
            round_=fresh, selection=selected,
            owner_provenance=OWNER,
        ) is None
        assert owner.retained.exploration_continuity.attempts[0].phase is (
            AttemptPhase.RESERVED
        )


@pytest.mark.parametrize("failure", [
    "busy-gpu", "old-native", "missing-b", "stale-gpu",
    "foreign-paper", "no-original-probe", "wrong-request-id",
])
def test_d6_b_fresh_l1_admission_rejects_stale_native_paper_gpu(
    tmp_path, failure,
):
    (recovered, contexts, old_tasks, world, logins,
     idle, boot, links) = _d6_loaded_online(tmp_path)
    if failure == "busy-gpu":
        idle = replace(idle, is_processing=True)
    elif failure == "old-native":
        logins = (
            replace(logins[0], native_session_id="native-old-A"),
            logins[1],
        )
    elif failure == "missing-b":
        logins = (logins[0],)
    elif failure == "stale-gpu":
        logins = (replace(logins[0], stale_gpu_fenced=False), logins[1])
    elif failure == "foreign-paper":
        world = replace(world, paper_session_id="paper-forged")
    elif failure == "no-original-probe":
        recovered.owners["A"].current_worldbody_observation = None
    else:
        recovered.owners["B"].current_worldbody_observation = (
            _synthetic_native_probe(
                self_id="wrong", native="new-recovery-native-B", tick=8,
            )
        )
    with pytest.raises(D6FreshReconsiderationHold):
        inspect_d6_new_exploration_reevaluation(
            recovered, world=world, logins=logins, idle=idle,
            boot=boot, links=links,
        )
    assert recovered.physical.active_action_ids == ()
    assert all(
        recovered.owners[sid].retained.exploration_continuity.attempts[0].phase
        is AttemptPhase.RESERVED
        for sid in ("A", "B")
    )


def test_d6_b_fresh_l1_rejects_all_online_without_native_proof(tmp_path):
    (_, _, _, _, _, generation, fork, receipt, digest) = _actual_cut_and_restore(
        tmp_path
    )
    recovered = prepare_recovered_a_b_resident_owners(
        generation, fork, expected_world_id="world-A",
        expected_source_branch_id="source",
        expected_committed_sha256=digest,
        expected_fork_branch_id=receipt["fork_branch_id"],
    )
    world, logins, idle, boot, links = _d6_new_world_sources(recovered.plan)
    # Dataclasses bearing 'verified' flags are not proof that the actual
    # resident has even rejoined. All Self remain OFFLINE here.
    with pytest.raises(D6FreshReconsiderationHold):
        inspect_d6_new_exploration_reevaluation(
            recovered, world=world, logins=logins, idle=idle,
            boot=boot, links=links,
        )
    assert recovered.physical.all_residents_offline
