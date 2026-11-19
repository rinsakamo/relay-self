"""D Lane D9: genuine original B resident L1 -> D Question/L2 before typed cut.

The only GPU submit path is ResidentLlamaInferenceLane (original B owner).
A received choice can be DEFER/UNRESOLVED; NEVER fabricate ESCALATE_L2.
The native observation is a real current owned Mineflayer probe in production.
Unit fixtures are synthetic and cannot qualify real Paper/Gemma source evidence.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from adapters.mineflayer.python_protocol import MineflayerObservation
from relay_self.cognitive_minimal_dev import (
    PatternKind,
    Predicate,
    WorldPercept,
    resolve_l1_choice,
)
from relay_self.common_io import Clock, ClockStamp, CommonEnvelope, ScopeRef
from relay_self.exploration_checkpoint_bridge_dev import (
    ResidentD4Scope,
    reserve_resident_l2,
    retain_resident_question,
)
from relay_self.exploration_goal_dev import (
    ExplorationBasis,
    ExplorationDisposition,
    ExplorationEvidence,
    NeedReadout,
    form_exploration_round,
    propose_exploration_need,
)
from relay_self.innate_schema import (
    SchemaActivation,
    SchemaMode,
    SchemaModuleSpec,
    SchemaSnapshot,
)
from relay_self.persistent_cognition import load_persistent_cognition
from relay_self.physical_action_journal import PhysicalActionJournal
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    CognitionMode,
    ProviderDecision,
    RelayEngineAttempt,
    RelayEngineResult,
)
from relay_self.resident_cognitive_work_owner_dev import ResidentCognitiveWorkOwner
from relay_self.resident_llama_inference_lane_dev import ResidentLlamaInferenceLane
from relay_self.three_self_present import (
    EpistemicStatus,
    project_present_frame,
    project_three_self,
)


class D9OriginalL1Hold(RuntimeError):
    """Original Owner/current native/real L1 result not qualified: no cut grant."""


@dataclass(frozen=True, slots=True)
class D9OriginalRound:
    scope: ResidentD4Scope
    question_ref: str
    round_: object
    native_source_ref: str
    probe_request_id: str
    model_work_ref: str
    source_body_only: bool = True
    physical_action_issue_authorized: bool = False


@dataclass(frozen=True, slots=True)
class D9OriginalL1Outcome:
    self_id: str
    old_native_session_id: str
    question_ref: str
    native_probe_request_id: str
    l1_request_id: str
    work_ref: str
    backend_ref: str
    model_status: str
    model_choice_id: str | None
    selected_status: str
    attempted_l2_ref: str | None
    requested_prompt_tokens: int | None
    completion_tokens: int | None
    finish_reason: str | None
    l1_model_invoked: bool = True
    l2_model_invoked: bool = False
    physical_action_issue_authorized: bool = False


def _original_scope(
    owner, resident: ResidentCognitiveWorkOwner, probe: MineflayerObservation,
    world_session_id: str,
) -> ResidentD4Scope:
    from relay_self.checkpointed_cognitive_runtime_dev import CheckpointedCognitiveOwner

    if (
        not isinstance(owner, CheckpointedCognitiveOwner)
        or not isinstance(resident, ResidentCognitiveWorkOwner)
        or not isinstance(probe, MineflayerObservation)
        or probe.kind != "probe" or not probe.request_id
        or type(world_session_id) is not str or not world_session_id
    ):
        raise D9OriginalL1Hold("original owner/native typed probe required")
    with resident.lock:
        try:
            epoch, native, world_epoch = resident.current_scope(owner.self_id)
        except RuntimeError as exc:
            raise D9OriginalL1Hold("Self is not original B resident ONLINE") from exc
        original = owner.current_worldbody_observation
        if (
            resident.owners.get(owner.self_id) is not owner
            or owner.cohort is not resident
            or owner.fresh_native_observation_required
            or original is not probe
            or probe.session_id != native
            or owner.native_session_id != native
            or probe.snapshot.time is None
            or owner.last_observed_tick != (
                probe.snapshot.time.day * 24000
                + probe.snapshot.time.time_of_day
            )
            or owner.files.cognition_file.is_symlink()
            or not owner.files.cognition_file.is_file()
            or load_persistent_cognition(owner.files.cognition_file) != owner.retained
        ):
            raise D9OriginalL1Hold("original current WorldBody/Owner source stale")
        PhysicalActionJournal.restore(
            owner.files.physical_wal_file, self_id=owner.self_id,
        ).require_clear()
        return ResidentD4Scope(
            owner.self_id, world_session_id, epoch, native, world_epoch,
            len(owner.intent.events), owner.intent.last_at_ns,
        )


def form_d9_native_exploration_round(
    owner, resident: ResidentCognitiveWorkOwner,
    probe: MineflayerObservation, *,
    world_session_id: str,
) -> D9OriginalRound:
    """Question from what current probe does NOT cover; no invented target.

    The initial exploration predicate must be installed in the original B
    owner's innate registry BEFORE entering the real World. No injection
    of patterns or Presets into a running Self is permitted.
    """
    scope = _original_scope(owner, resident, probe, world_session_id)
    registry = owner.pattern_registry
    if not any(
        p.schema_id == "exploration" and p.kind is PatternKind.GOAL
        and p.predicate is Predicate.EXPLORE
        for p in registry.patterns
    ):
        raise D9OriginalL1Hold(
            "original Self innate exploration Schema was not installed"
        )
    digest = hashlib.sha256(json.dumps({
        "self_id": owner.self_id,
        "native_session_id": probe.session_id,
        "request_id": probe.request_id,
        "source": [probe.provenance.source, probe.provenance.reference],
    }, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    # A Question about beyond this probe's finite coverage is an UNKNOWN,
    # not a factual claim that a particular item or destination exists.
    question = "question:unobserved-world:" + owner.self_id + ":" + digest[:24]
    source_revs = (
        "native:" + probe.session_id,
        "probe:" + probe.request_id,
    )
    world_scope = ScopeRef(owner.self_id, world_session_id)
    native_identity = Provenance("innate-schema", "cognitive-v0.1")
    schema = SchemaSnapshot(owner.self_id, registry.revision, (
        SchemaActivation(
            SchemaModuleSpec(
                "exploratory", 1, frozenset({SchemaMode.FULL}),
                ("EXPLORATION_NEED",), (), native_identity,
            ), SchemaMode.FULL,
        ),
    ))
    three_self = project_three_self(
        retained=owner.retained, scope=world_scope,
        epoch_ref="owner-epoch:" + str(scope.cognition_epoch),
        source_revision_refs=source_revs,
    )
    provisional = project_present_frame(
        three_self=three_self, snapshot=schema,
        current_registry_revision=schema.revision,
        current_source_revision_refs=source_revs, frame_revision=1,
        active_question_refs=(question,),
    )
    origin = probe.provenance
    envelope = CommonEnvelope(
        event_id="signal:exploration:" + digest,
        kind="COGNITIVE_SIGNAL",
        scope=world_scope,
        occurred_at=ClockStamp(Clock.WORLD_TICK, owner.last_observed_tick),
        provenance=origin, source_refs=(origin,),
    )
    food = probe.snapshot.food
    pressure = 0.0 if food is None else max(
        0.0, min(1.0, (20.0 - float(food)) / 20.0)
    )
    need = propose_exploration_need(
        present=provisional, snapshot=schema, schema_id="exploratory",
        evidence=(ExplorationEvidence(
            ExplorationBasis.OPEN_QUESTION, question,
            EpistemicStatus.UNKNOWN,
        ),),
        other_needs=(NeedReadout("food:observed", pressure),),
        disposition=ExplorationDisposition(),
        signal_envelope=envelope,
        current_registry_revision=schema.revision,
        current_source_revision_refs=source_revs,
    )
    if need is None:
        raise D9OriginalL1Hold("original Schema produced no exploration Need")
    present = project_present_frame(
        three_self=three_self, snapshot=schema,
        current_registry_revision=schema.revision,
        current_source_revision_refs=source_revs, frame_revision=2,
        active_question_refs=(question,), signals=(need.signal,),
    )
    # No made-up destination and no physical allowed skill. Even a real
    # L1 result here is a choice between actual ESCALATE_L2 and DEFER.
    percept = WorldPercept(
        world_scope, origin, probe.seq,
        hunger=int(food) if food is not None and float(food).is_integer() else None,
        fatigue_high=None, targets=(),
        exploration_need=True,
        threat_cue=any(x.name == "zombie" for x in probe.snapshot.nearby_entities),
    )
    round_ = form_exploration_round(
        present=present, need=need, snapshot=schema, percept=percept,
        registry=registry, intent_owner=owner.intent,
        owner_revision=len(owner.intent.events),
        allowed_skills=frozenset(), definitions={},
        epoch=scope.cognition_epoch,
    )
    if (
        tuple((num, label) for num, label in round_.l1.numbered)
        != (("1", "ESCALATE_L2"), ("2", "DEFER"))
        or not round_.proposals
        or round_.proposals[0].route != "NEEDS_L2"
    ):
        raise D9OriginalL1Hold(
            "original cognitive Schema failed to form unresolved Goal and bounded L1"
        )
    return D9OriginalRound(
        scope, question, round_, origin.reference, probe.request_id,
        "d9-explore:" + digest,
    )


async def run_d9_original_bounded_l1(
    owner, resident: ResidentCognitiveWorkOwner,
    lane: ResidentLlamaInferenceLane,
    probe: MineflayerObservation, *,
    world_session_id: str,
    timeout_s: float = 60.0,
) -> D9OriginalL1Outcome:
    """Use actual owner-only GPU submission, never a caller-supplied choice.

    Returns after original D4 owner persisted Question and, only if the
    actual backend selected ESCALATE_L2, a pre-GPU-L2 RESERVED journal.
    This does not call L2, infer a Target, or issue a physical Action.
    """
    if not isinstance(lane, ResidentLlamaInferenceLane) or lane.cognitive_work is not resident:
        raise D9OriginalL1Hold("original resident GPU lane required")
    roundup = form_d9_native_exploration_round(
        owner, resident, probe, world_session_id=world_session_id,
    )
    owner_provenance = Provenance(
        "original-self-owner", "d9:" + owner.self_id,
    )
    retain_resident_question(
        owner, resident, scope=roundup.scope,
        present=roundup.round_.present,
        question_ref=roundup.question_ref,
        owner_provenance=owner_provenance,
    )
    ticket = lane.submit(
        owner.self_id, work_ref=roundup.model_work_ref,
        request=roundup.round_.l1.request, mode=CognitionMode.BOUNDED,
    )
    actual = await lane.await_result(ticket, timeout_s=timeout_s)
    if not isinstance(actual, ProviderDecision):
        raise D9OriginalL1Hold("actual BOUNDED provider result type required")
    current = _original_scope(owner, resident, probe, world_session_id)
    if (
        current != roundup.scope
        or ticket.self_epoch != current.cognition_epoch
        or ticket.native_session_id != current.native_session_id
        or ticket.world_epoch != current.world_epoch
        or ticket.request_id != roundup.round_.l1.request.request_id
        or ticket.mode is not CognitionMode.BOUNDED
    ):
        raise D9OriginalL1Hold("original L1 returned after Self/World/Intent changed")
    normalized = RelayEngineResult(
        status=actual.status, choice_id=actual.choice_id,
        attempts=(RelayEngineAttempt(
            CognitionMode.BOUNDED, actual.status,
            actual.choice_id, actual.reason,
            call_facts=actual.call_facts,
        ),),
        think_allowed=False,
    )
    selection = resolve_l1_choice(
        roundup.round_.l1, normalized, current_frame=roundup.round_.frame,
        intent_owner=owner.intent, available_skills=frozenset(),
    )
    attempt = None
    if selection.status == "ESCALATE_L2":
        attempt = reserve_resident_l2(
            owner, resident, scope=roundup.scope,
            round_=roundup.round_, selection=selection,
            owner_provenance=owner_provenance,
        )
    return D9OriginalL1Outcome(
        owner.self_id, current.native_session_id,
        roundup.question_ref, roundup.probe_request_id,
        roundup.round_.l1.request.request_id,
        roundup.model_work_ref, ticket.backend_ref,
        actual.status.value, actual.choice_id, selection.status,
        None if attempt is None else attempt.attempt_ref,
        actual.call_facts.prompt_tokens,
        actual.call_facts.completion_tokens,
        actual.call_facts.finish_reason,
    )
