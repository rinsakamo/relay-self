"""C Lane Stage27/28 read-only original-owner integration seam (#839).

The physical/checkpoint modules are deliberately NOT vendored into #993's
unmerged #840 stack. Runtime imports mean this bridge HOLDS until the original
Stage27/28 code is present in an integration branch. No WAL, Action, Skill,
Intent, Memory or World file is ever mutated by these adapters.
"""
from __future__ import annotations

import math
from pathlib import Path

from relay_self.action import ActionLifecycle, ActionState
from relay_self.cognitive_learning_contract import (
    BeforePrediction,
    EvidenceOrigin,
    OutcomeAssessment,
)
from relay_self.cognitive_learning_owner_adapter import (
    BoundedSkillExperience,
    BoundedSkillRead,
    C1AdmissionError,
    TargetRead,
    WalActionRead,
    WalDisposition,
    WorldBodyRead,
    assemble_bounded_skill_experience,
    propose_existing_memory,
)
from relay_self.common_io import Clock, ClockStamp, ScopeRef
from relay_self.intent import IntentCommitment
from relay_self.persistent_cognition import Memory, PersistentCognition
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution


def _original_stage27_types():
    # Import only when the original *unmerged* Stage27 owner is present.
    try:
        from adapters.mineflayer.python_protocol import MineflayerObservation
        from relay_self.physical_action_journal import (
            PhysicalActionJournal,
            PhysicalJournalError,
            PhysicalJournalUnresolved,
        )
        from relay_self.skill_invocation import SkillInvocation
        from relay_self.target_contract import (
            TargetBodyObservation,
            TargetConditionStatus,
            evaluate_target,
        )
    except ImportError as exc:
        raise C1AdmissionError(
            "STAGE27_DEPENDENCY_NOT_MERGED: cannot authenticate original WAL"
        ) from exc
    return (
        MineflayerObservation, PhysicalActionJournal, PhysicalJournalError,
        PhysicalJournalUnresolved, SkillInvocation, TargetBodyObservation,
        TargetConditionStatus, evaluate_target,
    )


def _native_probe(probe: object, scope: ScopeRef, original_type: type) -> None:
    if (
        not isinstance(probe, original_type)
        or probe.kind != "probe" or not probe.request_id
        or probe.session_id != scope.world_session_id
        or probe.provenance.source != "mineflayer"
        or probe.provenance.reference != f"{probe.session_id}:{probe.seq}"
        or probe.snapshot.time is None
    ):
        raise C1AdmissionError("foreign/stale/unqualified original native probe")


def _position_matches(original: object, persisted: object) -> bool:
    return (
        type(persisted) is dict
        and set(persisted) == {"x", "y", "z"}
        and all(type(persisted[k]) in (float, int) for k in ("x", "y", "z"))
        and all(
            math.isfinite(persisted[key])
            and abs(getattr(original, key) - persisted[key]) <= 1e-6
            for key in ("x", "y", "z")
        )
    )


def assemble_stage27_c1_from_canonical_wal(
    *,
    cognition: PersistentCognition,
    intent: IntentCommitment,
    skill: SkillExecution,
    actions: tuple[ActionLifecycle, ...],
    journal_path: Path,
    original_wal_sha256: str,
    selected_invocation: object,
    before_probe: object,
    after_probe: object,
    world_id: str,
    world_epoch: int,
    selected_provenance: Provenance,
    before_prediction: BeforePrediction | None = None,
) -> BoundedSkillExperience | None:
    """Only the original Stage27 journal verifier may authenticate a WAL.

    Restores the ORIGINAL fsynced canonical WAL twice, without clearing it.
    TargetContract is evaluated using the actual final native position, never
    a fabricated physical outcome. UNKNOWN/WAL PREPARED/active Skill => HOLD.
    No physical effect, model, checkpoint or Memory adoption occurs.
    """
    if (
        not isinstance(cognition, PersistentCognition)
        or not isinstance(intent, IntentCommitment)
        or not isinstance(skill, SkillExecution)
        or not isinstance(actions, tuple)
        or not all(isinstance(a, ActionLifecycle) for a in actions)
        or not isinstance(journal_path, Path)
        or not isinstance(selected_provenance, Provenance)
        or type(world_id) is not str or not world_id
        or type(world_epoch) is not int or world_epoch < 0
        or type(original_wal_sha256) is not str
        or len(original_wal_sha256) != 64
    ):
        raise C1AdmissionError("typed original owner, epoch and journal references required")
    (
        NativeProbe, Journal, JournalError, JournalUnresolved, Invocation,
        BodyObservation, TargetStatus, evaluate_target,
    ) = _original_stage27_types()
    if not isinstance(selected_invocation, Invocation):
        raise C1AdmissionError("original bound L1 SkillInvocation required")
    invocation = selected_invocation
    scope = invocation.scope
    if (
        not isinstance(scope, ScopeRef) or not scope.world_session_id
        or cognition.identity.self_id != scope.self_id
        or skill.intent_id not in (e.intent_id for e in intent.events)
        or invocation.skill_id != skill.skill_id
        or invocation.target.contract is None
        or invocation.target.ref != invocation.target.contract.target_ref
        or invocation.goal_id != invocation.target.contract.goal_id
        or invocation.parameter_preset_ref is None
        or not skill.is_current_snapshot
    ):
        raise C1AdmissionError("original Invocation/owner/Target scope changed")
    _native_probe(before_probe, scope, NativeProbe)
    _native_probe(after_probe, scope, NativeProbe)
    if before_probe.seq >= after_probe.seq:
        raise C1AdmissionError("native observation sequence did not advance")
    if not skill.is_terminal:
        return None
    try:
        journal = Journal.restore(journal_path, self_id=scope.self_id)
        if journal.unresolved:
            return None  # PREPARED_UNRESOLVED: no C1 success, no automatic replay
        journal.require_clear()
        if journal.digest != original_wal_sha256:
            raise C1AdmissionError("original WAL digest differs from attestable source")
        rows = journal.records
    except JournalUnresolved:
        return None
    except JournalError as exc:
        raise C1AdmissionError("original physical WAL refused readback") from exc
    if (
        not rows or len(rows) != len(actions)
        or {row["action_id"] for row in rows} != {a.action_id for a in actions}
        or len({a.action_id for a in actions}) != len(actions)
    ):
        raise C1AdmissionError("exact original child Action/WAL cohort required")
    by_action_id = {a.action_id: a for a in actions}
    wal = []
    for idx, row in enumerate(rows):
        action = by_action_id[row["action_id"]]
        if (
            row["capability"] != "MOVE_PLACE"
            or row["session_id"] != scope.world_session_id
            or row["skill_execution_id"] != skill.execution_id
            or row["intent_id"] != skill.intent_id
            or row["invocation_ref"] != invocation.invocation_ref
            or row["preset_ref"] != invocation.parameter_preset_ref
            or row["target_ref"] != invocation.target.ref
            or row["target_contract_ref"] != invocation.target.contract.contract_ref
            or row["source_ref"] != f"{scope.world_session_id}:{row['probe_seq']}"
            or action.state is not ActionState.OUTCOME
            or not action.is_current_snapshot
            or row["status"] not in (
                "NATIVE_PLACE_MOVE_SETTLED",
                "NATIVE_PLACE_MOVE_NO_PROGRESS",
                "NATIVE_PLACE_MOVE_OVERSHOOT",
            )
            or idx and row["probe_seq"] <= rows[idx - 1]["after_seq"]
        ):
            raise C1AdmissionError("canonical native/action/invocation lineage mismatch")
        wal.append(WalActionRead(
            action_id=action.action_id,
            scope=scope, world_id=world_id,
            disposition=WalDisposition.TERMINAL_OUTCOME,
            wal_ref=Provenance("canonical-physical-wal", f"{original_wal_sha256}:{action.action_id}"),
            digest_sha256=original_wal_sha256,
        ))
    if (
        rows[0]["probe_seq"] != before_probe.seq
        or rows[0]["probe_request_id"] != before_probe.request_id
        or rows[-1]["after_seq"] != after_probe.seq
        or not _position_matches(before_probe.snapshot.position, rows[0]["started_position"])
        or not _position_matches(after_probe.snapshot.position, rows[-1]["settled_position"])
        or not _position_matches(invocation.target.contract.anchor, rows[-1]["target_position"])
    ):
        raise C1AdmissionError("original native positions/probes do not match canonical WAL")

    # Stage28 warns: Mineflayer day clock is NOT the Paper process tick.
    def clock(probe: object) -> ClockStamp:
        t = probe.snapshot.time
        return ClockStamp(Clock.WORLD_TICK, t.day * 24000 + t.time_of_day)

    before = WorldBodyRead(
        scope=scope, world_id=world_id, epoch=world_epoch, source_seq=before_probe.seq,
        clock=clock(before_probe), source_refs=(before_probe.provenance,),
        origin=EvidenceOrigin.WORLD_BODY_OBSERVED,
    )
    after = WorldBodyRead(
        scope=scope, world_id=world_id, epoch=world_epoch, source_seq=after_probe.seq,
        clock=clock(after_probe), source_refs=(after_probe.provenance,),
        origin=before.origin,
    )
    assessment = evaluate_target(
        invocation.target.contract,
        BodyObservation(
            scope=scope, seq=after_probe.seq, provenance=after_probe.provenance,
            position=after_probe.snapshot.position,
        ),
    )
    # A native geometrical condition is NOT an independently proven Goal.
    # The C1 field explicitly means Target condition, not Intent completion.
    target_outcome = (
        OutcomeAssessment.SUCCESS
        if assessment.status is TargetStatus.CONDITION_OBSERVED
        else OutcomeAssessment.UNKNOWN if assessment.status is TargetStatus.UNKNOWN
        else OutcomeAssessment.PARTIAL
    )
    target = (
        TargetRead(OutcomeAssessment.UNKNOWN)
        if target_outcome is OutcomeAssessment.UNKNOWN else TargetRead(
            target_outcome,
            check_ref=Provenance("target-contract", assessment.contract_ref),
            observed_after_ref=after_probe.provenance,
        )
    )
    readout = BoundedSkillRead(
        cognition=cognition, intent=intent, skill=skill,
        actions=tuple(by_action_id[row["action_id"]] for row in rows),
        wal=tuple(wal), scope=scope, world_id=world_id,
        goal_ref=invocation.goal_id, target_ref=invocation.target.ref,
        preset_ref=invocation.parameter_preset_ref,
        bound_selection_ref=selected_provenance,
        before=before, after=after, target=target,
        before_prediction=before_prediction,
    )
    # Re-read the original on-disk journal to fence a concurrent physical writer.
    try:
        reread = Journal.restore(journal_path, self_id=scope.self_id)
    except JournalError as exc:
        raise C1AdmissionError("original WAL changed during C1 read") from exc
    if reread.digest != original_wal_sha256 or reread.records != rows:
        raise C1AdmissionError("original WAL changed during C1 read")
    return assemble_bounded_skill_experience(readout)


def propose_for_stage28_original_owner(
    experience: BoundedSkillExperience,
    *,
    recovered_owner: object,
    verified_world_id: str,
    new_native_probe: object,
    integration_provenance: Provenance,
) -> Memory | None:
    """Return Memory proposal ONLY; Stage28's original Self decides adoption.

    A new session never retroactively authenticates the historical Stage27
    World observation. The verified World ID must match the historical source.
    The independently verified Stage28 cohort/fork and fresh probe are owned
    by Stage28; this check is an additional fail-closed readout, not a grant.
    """
    try:
        from adapters.mineflayer.python_protocol import MineflayerObservation
        from relay_self.checkpointed_cognitive_runtime_dev import CheckpointedCognitiveOwner
    except ImportError as exc:
        raise C1AdmissionError(
            "STAGE28_DEPENDENCY_NOT_MERGED: no recovered original Owner"
        ) from exc
    if not isinstance(experience, BoundedSkillExperience) or not isinstance(
        recovered_owner, CheckpointedCognitiveOwner
    ) or not isinstance(integration_provenance, Provenance):
        raise C1AdmissionError("original restored Owner and C1 experience required")
    owner = recovered_owner
    if (
        owner.self_id != experience.scope.self_id
        or verified_world_id != experience.world_id
        or owner.cohort is None
        or owner.fresh_native_observation_required
        or owner.current_worldbody_observation is None
        or not isinstance(new_native_probe, MineflayerObservation)
        or owner.current_worldbody_observation != new_native_probe
        or new_native_probe.kind != "probe" or not new_native_probe.request_id
        or new_native_probe.session_id != owner.native_session_id
        or new_native_probe.provenance.source != "mineflayer"
        or new_native_probe.provenance.reference
        != f"{owner.native_session_id}:{new_native_probe.seq}"
        or owner.native_session_id == experience.scope.world_session_id
        or new_native_probe.snapshot.time is None
    ):
        raise C1AdmissionError("Stage28 restored owner/fresh source/world unqualified")
    return propose_existing_memory(
        owner.retained, experience,
        integration_provenance=integration_provenance,
    )
