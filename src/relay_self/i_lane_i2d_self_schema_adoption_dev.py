"""I2d DEV: actual original shared L2 proposal -> shared L1 Self choice -> Owner.

No caller-supplied "accepted=True", no fabricated exploration Pattern, no
second Owner/GPU scheduler and no physical Skill/Target. The only installable
learned Pattern is an unbound EXPLORE_WORLD Goal proposed by an OPEN L2 result
and explicitly selected by a later separate BOUNDED L1 model result.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass, field

from relay_self.common_io import ScopeRef
from relay_self.cognitive_minimal_dev import (
    Origin,
    PatternKind,
    Predicate,
    SchemaPattern,
    accept_learned_pattern,
    parse_l2_pattern_proposal,
)
from relay_self.i_lane_i2_original_exploration_handoff_dev import (
    I2OriginalGoalHandoff,
    prepare_i2_original_goal_handoff,
    verify_i2_original_goal_handoff,
)
from relay_self.innate_schema import (
    SchemaActivation,
    SchemaMode,
    SchemaModuleSpec,
    SchemaSnapshot,
    check_schema_eligibility,
)
from relay_self.persistent_cognition import (
    load_persistent_cognition,
    save_persistent_cognition,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    BoundedChoice,
    BoundedChoiceRequest,
    CognitionDatum,
    CognitionMode,
    DecisionStatus,
    OpenCognitionRequest,
    ProviderDecision,
    ProviderExpression,
    RelayEngine,
)
from relay_self.resident_llama_inference_lane_dev import (
    ResidentInferenceTicket,
    ResidentLlamaInferenceLane,
)


class I2dOriginalHold(RuntimeError):
    """No authenticated/current Self-led exploration adoption path."""


@dataclass(slots=True, eq=False)
class I2dL2ProposalWork:
    handoff: I2OriginalGoalHandoff
    request: OpenCognitionRequest
    ticket: ResidentInferenceTicket
    request_sha256: str
    consumed: bool = field(default=False, init=False)


@dataclass(slots=True, eq=False)
class I2dL1AcceptanceWork:
    proposed: I2dL2ProposalWork
    pattern: SchemaPattern
    request: BoundedChoiceRequest
    ticket: ResidentInferenceTicket
    request_sha256: str
    consumed: bool = field(default=False, init=False)


@dataclass(frozen=True, slots=True)
class I2dSelfAdoptionResult:
    self_id: str
    l2_ticket: ResidentInferenceTicket
    l1_ticket: ResidentInferenceTicket
    outcome: str
    pattern_registry_revision: int
    goal_unresolved: bool = True
    question_adopted: bool = False
    intent_committed: bool = False
    physical_action_authorized: bool = False


def _fingerprint(x: object) -> str:
    return hashlib.sha256(repr(x).encode("utf-8")).hexdigest()


def _current(*, bridge, lane, boot, world, links,
             handoff: I2OriginalGoalHandoff) -> None:
    if (type(handoff) is not I2OriginalGoalHandoff
            or not isinstance(lane, ResidentLlamaInferenceLane)
            or bridge.inference_lane is not lane
            or bridge.cognitive_work is not lane.cognitive_work
            or not bridge.physical.observation_only
            or bridge.physical.active_action_ids
            or lane.uncertain
            or handoff.status != "NO_QUALIFIED_EXPLORATION_GOAL"
            or handoff.goal_candidates
            or handoff.need_signal_ref or handoff.question_candidate_ref
            or handoff.model_invoked or handoff.goal_adopted
            or handoff.question_adopted or handoff.intent_committed
            or handoff.action_issue_authorized):
        raise I2dOriginalHold("unqualified original no-exploration shared lane")
    try:
        owner = bridge.owners[handoff.self_id]
        resident = bridge.cognitive_work
        schema = resident.present_schema(handoff.self_id)
        if (owner.cohort is not resident
                or owner.retained.pattern_registry != owner.pattern_registry
                or owner.pattern_registry.revision != handoff.registry_revision
                or schema.modules
                or owner.supervisor.open_actions
                or owner.intent.current_intent is not None
                or load_persistent_cognition(owner.files.cognition_file) != owner.retained):
            raise I2dOriginalHold("original persisted Owner/Registry/Intent is stale")
        verify_i2_original_goal_handoff(
            bridge=bridge, boot=boot, world=world, links=links,
            handoff=handoff, i2b_read_attached_lane=True,
        )
    except (ValueError, KeyError, RuntimeError, AttributeError, OSError) as exc:
        raise I2dOriginalHold("original I2/Native/Paper/Schema source stale") from exc


def _ticket_valid(lane, ticket, *, handoff, request, mode, work_ref):
    return (
        type(ticket) is ResidentInferenceTicket
        and ticket.self_id == handoff.self_id
        and ticket.native_session_id == handoff.native_session_id
        and ticket.self_epoch == handoff.resident_epoch
        and ticket.backend_ref == lane.backend_ref
        and ticket.mode is mode
        and ticket.work_ref == work_ref
        and ticket.request_id == request.request_id
        and not ticket.action_issue_authorized
    )


def _job_result(lane, ticket, expected_mode):
    try:
        with lane._lock:
            job = lane._require_current_job(ticket)
            if (job.result_adopted or ticket.mode is not expected_mode
                    or job.future is None or not job.future.done()
                    or not job.terminal_slot_idle):
                raise I2dOriginalHold("replayed or incomplete original model ticket")
            return lane.result(ticket)
    except (ValueError, RuntimeError, KeyError) as exc:
        raise I2dOriginalHold("original model ticket/result is stale") from exc


def _only_unbound_exploration(pattern):
    if (
        type(pattern) is not SchemaPattern
        or pattern.origin is not Origin.LEARNED
        or pattern.schema_id != "exploration"
        or pattern.kind is not PatternKind.GOAL
        or pattern.predicate is not Predicate.EXPLORE
        or pattern.goal_id != "EXPLORE_WORLD"
        or pattern.version != 1
        or any(value is not None for value in (
            pattern.skill_id, pattern.skill_version, pattern.target_kind
        ))
    ):
        raise I2dOriginalHold("L2 proposal is not an unbound exploration Goal")


def submit_i2d_original_l2(
    *, bridge, boot, world, links, self_id: str,
    lane: ResidentLlamaInferenceLane,
) -> I2dL2ProposalWork:
    """Original B/E source first; one OPEN ticket on attached shared lane."""
    with lane.cognitive_work.lock:
        handoff = prepare_i2_original_goal_handoff(
            bridge=bridge, boot=boot, world=world, links=links, self_id=self_id,
            i2b_read_attached_lane=True,
        )
        _current(bridge=bridge, lane=lane, boot=boot, world=world,
                 links=links, handoff=handoff)
        request = OpenCognitionRequest(
            request_id="i2d-l2:" + handoff.bounded_request.request_id,
            instruction=(
                "Consider whether to propose a *new nonmotor* learned exploration "
                "Need/Goal. You may decline by returning no valid JSON. If proposing, "
                "return exactly one JSON object with keys pattern_id, version, "
                "schema_id, kind, predicate, goal_id, skill_id, skill_version, "
                "target_kind. Permitted proposal only: pattern_id is a unique "
                "nonempty string; version=1; schema_id='exploration'; kind='GOAL'; "
                "predicate='EXPLORE'; goal_id='EXPLORE_WORLD'; skill_id=null, "
                "skill_version=null, target_kind=null. This grants NO MOVE/Action. "
                "The separate Self L1 acceptance vote remains necessary."
            ),
            intent_id=handoff.bounded_request.intent_id,
            focus="LEARN_NONMOTOR_EXPLORATION_PATTERN",
            context=(
                *handoff.bounded_request.context,
                CognitionDatum.from_value(
                    "i2d_source_binding",
                    {"material_sha256": handoff.material_sha256,
                     "request_sha256": _fingerprint(handoff.bounded_request)},
                    bridge.owners[self_id].retained.identity.provenance,
                ),
            ),
            identity_context=handoff.bounded_request.identity_context,
        )
        try:
            lane.require_world_idle()
            _current(bridge=bridge, lane=lane, boot=boot, world=world,
                     links=links, handoff=handoff)
            ticket = lane.submit(
                self_id, work_ref=request.request_id, request=request,
                mode=CognitionMode.OPEN,
            )
        except (ValueError, RuntimeError, OSError) as exc:
            raise I2dOriginalHold("original shared L2 cannot be submitted") from exc
        if not _ticket_valid(
            lane, ticket, handoff=handoff, request=request,
            mode=CognitionMode.OPEN, work_ref=request.request_id,
        ):
            raise I2dOriginalHold("original L2 ticket not source-bound")
        return I2dL2ProposalWork(handoff, request, ticket, _fingerprint(request))


def submit_i2d_original_l1_acceptance(
    *, bridge, boot, world, links, proposed: I2dL2ProposalWork,
    lane: ResidentLlamaInferenceLane,
) -> I2dL1AcceptanceWork:
    """Actual L2 expression -> a separate Self L1 ACCEPT/DEFER choice."""
    if type(proposed) is not I2dL2ProposalWork or proposed.consumed:
        raise I2dOriginalHold("one original L2 proposal ticket required")
    with lane.cognitive_work.lock:
        h = proposed.handoff
        _current(bridge=bridge, lane=lane, boot=boot, world=world,
                 links=links, handoff=h)
        if (proposed.request_sha256 != _fingerprint(proposed.request)
                or not _ticket_valid(
            lane, proposed.ticket, handoff=h, request=proposed.request,
            mode=CognitionMode.OPEN, work_ref=proposed.request.request_id,
        )):
            raise I2dOriginalHold("foreign or tampered L2 proposal request")
        result = _job_result(lane, proposed.ticket, CognitionMode.OPEN)
        if type(result) is not ProviderExpression:
            raise I2dOriginalHold("L2 produced no actual expression")
        try:
            pattern = parse_l2_pattern_proposal(
                result.text, model_provenance=result.provenance,
            )
            _only_unbound_exploration(pattern)
            accept_learned_pattern(
                bridge.owners[h.self_id].pattern_registry, pattern,
                accepted_by_self=True,
                expected_revision=h.registry_revision,
                allowed_skills=frozenset(),
            )
        except (ValueError, TypeError) as exc:
            raise I2dOriginalHold("L2 proposal not eligible even as candidate") from exc
        request = BoundedChoiceRequest(
            request_id="i2d-l1:" + h.bounded_request.request_id,
            instruction=(
                "Choose exactly one numbered option to decide whether Self "
                "accepts the L2-proposed unbound exploration Goal. "
                "Do not infer any Target, Skill, movement or action permission. "
                "Choose 2 to defer. Return only the choice number."
            ),
            intent_id=h.bounded_request.intent_id,
            focus="SELF_ACCEPT_LEARNED_EXPLORATION_SCHEMA",
            choices=(
                BoundedChoice("1", "ACCEPT_UNBOUND_EXPLORATION_SCHEMA"),
                BoundedChoice("2", "DEFER"),
            ),
            context=(
                *proposed.request.context,
                CognitionDatum.from_value(
                    "i2d_model_proposal",
                    {"pattern": json.loads(result.text),
                     "model_provenance": result.provenance.reference,
                     "l2_ticket": repr(proposed.ticket),
                     "l2_request_sha256": _fingerprint(proposed.request)},
                    result.provenance,
                ),
            ),
            identity_context=proposed.request.identity_context,
            think_allowed=False,
        )
        try:
            lane.require_world_idle()
            _current(bridge=bridge, lane=lane, boot=boot, world=world,
                     links=links, handoff=h)
            ticket = lane.submit(
                h.self_id, work_ref=request.request_id, request=request,
                mode=CognitionMode.BOUNDED,
            )
        except (ValueError, RuntimeError, OSError) as exc:
            raise I2dOriginalHold("original shared L1 vote not submitted") from exc
        if not _ticket_valid(
            lane, ticket, handoff=h, request=request,
            mode=CognitionMode.BOUNDED, work_ref=request.request_id,
        ):
            raise I2dOriginalHold("foreign or tampered Self acceptance ticket")
        proposed.consumed = True
        return I2dL1AcceptanceWork(proposed, pattern, request, ticket, _fingerprint(request))


def finish_i2d_self_adoption(
    *, bridge, boot, world, links, accepted: I2dL1AcceptanceWork,
    lane: ResidentLlamaInferenceLane,
) -> I2dSelfAdoptionResult:
    """Single original Owner publication, only after actual L2+L1 results.

    Persistence readback failure fences this Self and leaves no live published
    cognition; no retry and no inferred successful commit.
    """
    if type(accepted) is not I2dL1AcceptanceWork or accepted.consumed:
        raise I2dOriginalHold("one unused original Self acceptance request required")
    with lane.cognitive_work.lock, lane._lock:
        proposed = accepted.proposed
        h = proposed.handoff
        _current(bridge=bridge, lane=lane, boot=boot, world=world,
                 links=links, handoff=h)
        if (not proposed.consumed
                or proposed.request_sha256 != _fingerprint(proposed.request)
                or accepted.request_sha256 != _fingerprint(accepted.request)
                or not _ticket_valid(
                    lane, proposed.ticket, handoff=h, request=proposed.request,
                    mode=CognitionMode.OPEN, work_ref=proposed.request.request_id,
                )
                or not _ticket_valid(
                    lane, accepted.ticket, handoff=h, request=accepted.request,
                    mode=CognitionMode.BOUNDED, work_ref=accepted.request.request_id,
                )):
            raise I2dOriginalHold("original L2/L1 request/ticket source mismatch")
        l2result = _job_result(lane, proposed.ticket, CognitionMode.OPEN)
        if type(l2result) is not ProviderExpression:
            raise I2dOriginalHold("original L2 result lost")
        try:
            pattern = parse_l2_pattern_proposal(
                l2result.text, model_provenance=l2result.provenance,
            )
        except (TypeError, ValueError) as exc:
            raise I2dOriginalHold("L2 candidate altered after Self vote") from exc
        if pattern != accepted.pattern:
            raise I2dOriginalHold("L2 candidate altered after Self vote")
        l1result = _job_result(lane, accepted.ticket, CognitionMode.BOUNDED)
        if type(l1result) is not ProviderDecision:
            raise I2dOriginalHold("original L1 result unavailable")
        decision = RelayEngine(lambda request, *, mode: l1result)(accepted.request)
        selection = (
            decision.choice_id if decision.status is DecisionStatus.RESOLVED
            else None
        )
        if selection not in (None, "1", "2"):
            raise I2dOriginalHold("noncanonical model choice")
        owner = bridge.owners[h.self_id]
        if selection != "1":
            accepted.consumed = True
            lane._require_current_job(proposed.ticket).result_adopted = True
            lane._require_current_job(accepted.ticket).result_adopted = True
            return I2dSelfAdoptionResult(
                h.self_id, proposed.ticket, accepted.ticket,
                "DEFER" if selection == "2" else "UNRESOLVED",
                owner.pattern_registry.revision,
            )
        _only_unbound_exploration(pattern)
        registry = accept_learned_pattern(
            owner.pattern_registry, pattern, accepted_by_self=True,
            expected_revision=h.registry_revision, allowed_skills=frozenset(),
        )
        activation = SchemaActivation(
            SchemaModuleSpec(
                "exploratory", 1, frozenset({SchemaMode.FULL}),
                ("QUESTION_CANDIDATE", "EXPLORATION_NEED"), (),
                Provenance("original-self-accepted-l2-l1",
                           accepted.ticket.request_id),
            ),
            SchemaMode.FULL,
        )
        snapshot = SchemaSnapshot(h.self_id, registry.revision, (activation,))
        if not check_schema_eligibility(
            snapshot, scope=ScopeRef(h.self_id, None),
            schema_id="exploratory", requested_mode=SchemaMode.FULL,
            current_registry_revision=registry.revision,
        ).allowed:
            raise I2dOriginalHold("Self-accepted Schema mode ineligible")
        owner._eligible()
        new_cognition = owner.retained.retain_schema_registry(
            registry, expected_revision=h.registry_revision,
        )
        # In-memory owner publication occurs ONLY after durable readback;
        # a failure during the on-disk replacement fences future cognition.
        try:
            save_persistent_cognition(owner.files.cognition_file, new_cognition)
            if load_persistent_cognition(owner.files.cognition_file) != new_cognition:
                raise I2dOriginalHold("original cognition write/readback mismatch")
        except (ValueError, RuntimeError, OSError) as exc:
            lane.cognitive_work.fence_self(h.self_id)
            lane.fence_self(h.self_id)
            raise I2dOriginalHold(
                "original cognition persistence uncertain; Self fenced"
            ) from exc
        owner.retained = new_cognition
        owner.pattern_registry = registry
        lane.cognitive_work._present_schemas[h.self_id] = (snapshot, registry)
        lane._require_current_job(proposed.ticket).result_adopted = True
        lane._require_current_job(accepted.ticket).result_adopted = True
        accepted.consumed = True
        return I2dSelfAdoptionResult(
            h.self_id, proposed.ticket, accepted.ticket,
            "SELF_ACCEPTED_NONMOTOR_EXPLORATION_SCHEMA",
            registry.revision,
        )


async def run_i2d_self_adoption(
    *, bridge, boot, world, links, self_id: str,
    lane: ResidentLlamaInferenceLane, timeout_s: float = 60.0,
) -> I2dSelfAdoptionResult:
    """At most one OPEN and one BOUNDED inference, no automatic retries."""
    l2 = submit_i2d_original_l2(
        bridge=bridge, boot=boot, world=world, links=links,
        self_id=self_id, lane=lane,
    )
    try:
        await lane.await_result(l2.ticket, timeout_s=timeout_s)
    except (RuntimeError, ValueError, TimeoutError) as exc:
        raise I2dOriginalHold("original L2 not terminal; no retry") from exc
    l1 = submit_i2d_original_l1_acceptance(
        bridge=bridge, boot=boot, world=world, links=links,
        proposed=l2, lane=lane,
    )
    try:
        await lane.await_result(l1.ticket, timeout_s=timeout_s)
    except (RuntimeError, ValueError, TimeoutError) as exc:
        raise I2dOriginalHold("original Self L1 not terminal; no retry") from exc
    return finish_i2d_self_adoption(
        bridge=bridge, boot=boot, world=world, links=links,
        accepted=l1, lane=lane,
    )
