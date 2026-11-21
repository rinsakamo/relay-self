"""I4a DEV: fresh current-Owner L1 choice -> S2 Owner-only handoff.

Separate from Stage26's immutable *restored* snapshot demo. No physical
action, Stage27h resumption, WAL mutation, checkpoint or C1 promotion.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

from adapters.mineflayer.python_protocol import MineflayerObservation, MineflayerPosition
from relay_self.checkpointed_cognitive_runtime_dev import (
    CheckpointedCognitiveOwner,
    LiveCognitionCheckpointError,
)
from relay_self.cognitive_minimal_dev import (
    L1Round,
    Option,
    Target,
    WorldPercept,
    assemble_l1_select,
    cpu_schema_epoch,
    resolve_l1_choice,
)
from relay_self.common_io import ScopeRef
from relay_self.i_lane_i4a_live_wal_anchor_dev import (
    I4ALiveAnchorHold,
    LiveS2Readiness,
    qualify_live_s2_readiness,
    verify_live_wal_history_anchor,
)
from relay_self.initial_skill_ir import initial_skill_definitions
from relay_self.intent import IntentCommitment
from relay_self.p0d_stage27_owned_move_intent_dev import Stage27OwnedMoveIntent
from relay_self.physical_issue_admission_dev import (
    PhysicalIssueAdmission,
    PhysicalIssueFenceError,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    CognitionMode,
    DecisionStatus,
    ProviderDecision,
    RelayEngine,
)
from relay_self.resident_llama_inference_lane_dev import (
    ResidentInferenceTicket,
    ResidentLlamaInferenceLane,
)
from relay_self.skill import SkillState
from relay_self.skill_invocation import SkillDefinition
from relay_self.target_contract import (
    ArrivalCondition,
    ReferenceFrame,
    TargetContract,
    TargetKind,
)


class I4ANextHandoffHold(RuntimeError):
    """No current qualified choice/Owner/physical scope for next SkillRun."""


@dataclass(frozen=True, slots=True, eq=False)
class I4ANextPrepared:
    owner: CheckpointedCognitiveOwner
    physical: PhysicalIssueAdmission
    lane: ResidentLlamaInferenceLane
    readiness: LiveS2Readiness
    first_probe: MineflayerObservation
    round: L1Round
    target: Target
    definition: SkillDefinition


@dataclass(frozen=True, slots=True, eq=False)
class I4ANextWitness:
    prepared: I4ANextPrepared
    ticket: ResidentInferenceTicket
    decision: ProviderDecision
    after_probe: MineflayerObservation
    request_sha256: str
    response_sha256: str
    request_path: str
    response_path: str
    action_issue_authorized: bool = False


def _state_unchanged(prepared: I4ANextPrepared) -> None:
    owner = prepared.owner
    snap = prepared.readiness
    if (
        getattr(owner, "_i4a_next_prepared", None) is not prepared
        or owner.retained != snap.retained
        or owner.pattern_registry != snap.registry
        or tuple(sorted(owner.skills.items())) != snap.skills
        or owner.intent.events != snap.intent_events
        or owner.intent.current_intent is not None
        or owner.intent.pending_reconsideration is not None
        or any(skill.state is SkillState.STARTED for skill in owner.skills.values())
        or owner.fresh_native_observation_required
    ):
        raise I4ANextHandoffHold("S2 owner state changed after candidate creation")


def _original_source(prepared: I4ANextPrepared) -> None:
    try:
        verify_live_wal_history_anchor(
            prepared.owner, physical=prepared.physical,
            lane=prepared.lane, anchor=prepared.readiness.anchor,
        )
        _state_unchanged(prepared)
    except I4ALiveAnchorHold as exc:
        raise I4ANextHandoffHold("S1 authenticated prefix not current") from exc


def prepare_live_s2_l1(
    owner: CheckpointedCognitiveOwner,
    *,
    physical: PhysicalIssueAdmission,
    lane: ResidentLlamaInferenceLane,
    readiness: LiveS2Readiness,
    first_probe: MineflayerObservation,
) -> I4ANextPrepared:
    """Build current-memory/registry numbered L1 choice from fresh Native."""
    if (
        not isinstance(readiness, LiveS2Readiness)
        or not isinstance(first_probe, MineflayerObservation)
        or owner.cohort is None
        or not isinstance(physical, PhysicalIssueAdmission)
        or not isinstance(lane, ResidentLlamaInferenceLane)
    ):
        raise I4ANextHandoffHold("valid current Owner source required")
    with owner.cohort.lock:
        again = qualify_live_s2_readiness(
            owner, physical=physical, lane=lane,
            anchor=readiness.anchor, first_probe=first_probe,
        )
        if (
            again != readiness
            and (
                again.self_id != readiness.self_id
                or again.native_session_id != readiness.native_session_id
                or again.world_epoch != readiness.world_epoch
                or again.request_id != readiness.request_id
                or again.probe_seq != readiness.probe_seq
                or again.wal_sha256 != readiness.wal_sha256
                or again.retained != readiness.retained
                or again.registry != readiness.registry
                or again.skills != readiness.skills
                or again.intent_events != readiness.intent_events
            )
        ):
            raise I4ANextHandoffHold("S2 preflight changed before L1")
        if getattr(owner, "_i4a_next_prepared", None) is not None:
            raise I4ANextHandoffHold("already prepared next live Owner task")
        definition = next(d for d in initial_skill_definitions() if d.skill_id == "MOVE")
        scope = ScopeRef(owner.self_id, first_probe.session_id)
        target_ref = f"destination:i4a-s2-{owner.self_id}-{first_probe.seq}"
        pos = first_probe.snapshot.position
        contract = TargetContract(
            scope=scope, goal_id="EXPLORE_WORLD",
            target_ref=target_ref, kind=TargetKind.PLACE,
            reference_frame=ReferenceFrame.WORLD,
            provenance=first_probe.provenance,
            condition=ArrivalCondition(0.0, 0.6, 1.0),
            bound_seq=first_probe.seq,
            anchor=MineflayerPosition(pos.x + 1.0, pos.y, pos.z),
        )
        target = Target(
            target_ref, "DESTINATION", first_probe.provenance,
            first_probe.session_id, first_probe.seq, arrival_contract=contract,
        )
        frame = cpu_schema_epoch(
            WorldPercept(
                scope, first_probe.provenance, first_probe.seq,
                hunger=int(first_probe.snapshot.food), fatigue_high=False,
                targets=(target,), exploration_need=True,
            ), owner.pattern_registry,
            allowed_skills=frozenset({("MOVE", 1)}),
            epoch=first_probe.seq,
            skill_definitions={("MOVE", 1): definition},
            use_registered_presets=True,
        )
        if (
            len(frame.options) != 1
            or not isinstance(frame.options[0], Option)
            or frame.options[0].invocation is None
            or frame.options[0].invocation.parameter_preset_ref is None
        ):
            raise I4ANextHandoffHold("current Owner lacks bounded MOVE option")
        round_ = assemble_l1_select(frame, intent_owner=IntentCommitment())
        if tuple(x.choice_id for x in round_.request.choices) != ("1", "2", "3"):
            raise I4ANextHandoffHold("current Owner L1 choices unqualified")
        round_ = replace(
            round_, request=replace(
                round_.request,
                request_id=(
                    f"i4a-s2-l1-{owner.self_id}-{first_probe.session_id}-"
                    f"{first_probe.seq}-{readiness.wal_sha256[:12]}"
                ),
            ),
        )
        prepared = I4ANextPrepared(
            owner, physical, lane, readiness, first_probe,
            round_, target, definition,
        )
        owner._i4a_next_prepared = prepared
        return prepared


def submit_live_s2_l1(prepared: I4ANextPrepared) -> ResidentInferenceTicket:
    if not isinstance(prepared, I4ANextPrepared):
        raise I4ANextHandoffHold("original current Owner L1 task required")
    with prepared.owner.cohort.lock:
        _original_source(prepared)
        return prepared.lane.submit(
            prepared.owner.self_id,
            work_ref=prepared.round.request.request_id,
            request=prepared.round.request,
            mode=CognitionMode.BOUNDED,
        )


async def finish_live_s2_l1(
    prepared: I4ANextPrepared,
    *,
    ticket: ResidentInferenceTicket,
    post_model_probe,
) -> I4ANextWitness:
    """Only return a source-bound witness. Caller adopts probe via original Owner."""
    if (
        not isinstance(prepared, I4ANextPrepared)
        or not isinstance(ticket, ResidentInferenceTicket)
        or ticket.self_id != prepared.owner.self_id
        or ticket.request_id != prepared.round.request.request_id
        or ticket.work_ref != prepared.round.request.request_id
        or ticket.mode is not CognitionMode.BOUNDED
        or ticket.native_session_id != prepared.readiness.native_session_id
        or ticket.world_epoch != prepared.readiness.world_epoch
        or not callable(post_model_probe)
    ):
        raise I4ANextHandoffHold("foreign/old L1 S2 ticket")
    decision = await prepared.lane.await_result(ticket)
    raw = prepared.lane.provider.stage26_raw_receipt(ticket.request_id)
    after = await post_model_probe()
    first = prepared.first_probe
    if (
        not isinstance(decision, ProviderDecision)
        or decision.call_facts.finish_reason != "stop"
        or decision.call_facts.prompt_tokens is None
        or decision.call_facts.completion_tokens is None
        or decision.call_facts.total_tokens is None
        or decision.call_facts.total_tokens
        != decision.call_facts.prompt_tokens
        + decision.call_facts.completion_tokens
        or not isinstance(after, MineflayerObservation)
        or after.kind != "probe" or not after.request_id
        or after.request_id == first.request_id
        or after.session_id != first.session_id
        or after.seq <= first.seq or after.snapshot.health <= 0
        or after.snapshot.time is None or after.snapshot.oxygen_level == 0
        or after.provenance.source != "mineflayer"
        or after.provenance.reference != f"{after.session_id}:{after.seq}"
        or math.dist(
            (first.snapshot.position.x, first.snapshot.position.y,
             first.snapshot.position.z),
            (after.snapshot.position.x, after.snapshot.position.y,
             after.snapshot.position.z),
        ) > 0.25
    ):
        raise I4ANextHandoffHold("post-L1 fresh Native/model source unavailable")
    with prepared.owner.cohort.lock:
        _original_source(prepared)
        if prepared.lane.result(ticket) != decision:
            raise I4ANextHandoffHold("S2 decision changed after model")
        frame = cpu_schema_epoch(
            WorldPercept(
                prepared.round.frame.scope, after.provenance, after.seq,
                hunger=int(after.snapshot.food), fatigue_high=False,
                targets=(prepared.target,), exploration_need=True,
            ), prepared.owner.pattern_registry,
            allowed_skills=frozenset({("MOVE", 1)}), epoch=after.seq,
            skill_definitions={("MOVE", 1): prepared.definition},
            use_registered_presets=True,
        )
        answer = RelayEngine(lambda request, *, mode: decision)(
            prepared.round.request,
        )
        selection = resolve_l1_choice(
            prepared.round, answer, current_frame=frame,
            intent_owner=IntentCommitment(),
            available_skills=frozenset({("MOVE", 1)}),
        )
        if (
            decision.status is not DecisionStatus.RESOLVED
            or decision.choice_id != "1"
            or selection.status != "READY"
        ):
            raise I4ANextHandoffHold("real L1 did not choose current bounded MOVE")
        return I4ANextWitness(
            prepared, ticket, decision, after,
            raw.request_sha256, raw.response_sha256,
            raw.request_path, raw.response_path,
        )


def begin_live_s2_owner_handoff(
    witness: I4ANextWitness, *,
    at_ns: int, provenance: Provenance,
) -> Stage27OwnedMoveIntent:
    """One original Owner Intent/Skill transition; no physical Action authority."""
    if (
        not isinstance(witness, I4ANextWitness)
        or not isinstance(at_ns, int) or at_ns <= 0
        or not isinstance(provenance, Provenance)
        or witness.action_issue_authorized
    ):
        raise I4ANextHandoffHold("explicit original S2 handoff parameters required")
    prepared = witness.prepared
    owner, physical, lane = prepared.owner, prepared.physical, prepared.lane
    if owner.cohort is None:
        raise I4ANextHandoffHold("original Owner no longer in cohort")
    with owner.cohort.lock:
        _original_source(prepared)
        after = witness.after_probe
        if (
            getattr(owner, "current_worldbody_observation", None) is not after
            or after.session_id != owner.native_session_id
            or witness.ticket.request_id != prepared.round.request.request_id
            or witness.ticket.native_session_id != owner.native_session_id
            or witness.ticket.world_epoch != prepared.readiness.world_epoch
            or witness.decision.status is not DecisionStatus.RESOLVED
            or witness.decision.choice_id != "1"
            or lane.result(witness.ticket) != witness.decision
        ):
            raise I4ANextHandoffHold("post-L1 CURRENT/choice no longer owned by Self")
        raw = lane.provider.stage26_raw_receipt(witness.ticket.request_id)
        if (
            raw.request_sha256 != witness.request_sha256
            or raw.response_sha256 != witness.response_sha256
            or raw.request_path != witness.request_path
            or raw.response_path != witness.response_path
        ):
            raise I4ANextHandoffHold("new model HTTP source changed before handoff")
        try:
            with physical.quiescent_wal_history_window(
                self_id=owner.self_id,
                native_session_id=owner.native_session_id,
            ):
                _original_source(prepared)
                option = prepared.round.frame.options[0]
                assert option.invocation is not None
                intent_id = "stage27-intent-" + witness.ticket.request_id
                skill_id = "stage27-skill-" + witness.ticket.request_id
                if skill_id in owner.skills:
                    raise I4ANextHandoffHold("duplicate S2 Skill ID")
                owner.commit_intent(
                    intent_id, option.goal_id, at_ns, provenance,
                )
                owner.start_skill(
                    skill_id, option.skill_id, at_ns + 1, provenance,
                )
                owner._i4a_next_prepared = None
        except (PhysicalIssueFenceError, LiveCognitionCheckpointError) as exc:
            raise I4ANextHandoffHold("original S2 atomic handoff refused") from exc
    return Stage27OwnedMoveIntent(
        owner.self_id, witness.ticket.native_session_id,
        witness.ticket.world_epoch, witness.ticket.request_id, "1", after.seq,
        intent_id, skill_id, option.invocation.invocation_ref,
        option.invocation.parameter_preset_ref or "",
        option.target_ref, option.target_kind,
    )
