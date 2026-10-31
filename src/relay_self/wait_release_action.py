"""S26: explicitly release an S25 MOVE_AWAY recheck into a new Action.

The S25 WAIT remains non-Action. This seam reconstructs a deterministic
route/admission from the fixed S24 scores and separately authorizes only
Action *proposal*. The existing ActionLifecycle and ActionSupervisor own the
later authorization, ISSUE and World outcome. No scheduler or new Skill owner.
"""
from __future__ import annotations

from dataclasses import dataclass

from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import UnknownSupervisedAction
from relay_self.execution_admission import (
    AdmissionDecisionStatus,
    AdmissionPolicy,
    ExecutionAdmissionCriterion,
    admit_control_candidate,
)
from relay_self.execution_binding import (
    ExecutionBinding,
    ExecutionBindingResult,
    resolve_execution_binding,
)
from relay_self.explicit_wait import (
    ExplicitWaitReevaluation,
    WaitAuthorityScope,
    WaitGateAuthority,
)
from relay_self.planning import (
    PlanCandidate,
    PlanFeature,
    PlanningCriterion,
    PlanningDirection,
    select_plan,
)
from relay_self.postfailure_cognition import PostFailureEpochTrace
from relay_self.provenance import Provenance
from relay_self.route_adjudication import (
    RouteCriterion,
    adjudicate_routes,
    control_candidate_from_route_decision,
)
from relay_self.skill import SkillState


class InvalidWaitReleaseAction(ValueError):
    """Reevaluation, caller release authority or execution identity invalid."""


@dataclass(frozen=True, slots=True)
class WaitReleaseActionAuthority:
    """Caller permission to propose only; not an Action authorization."""

    authority_id: str
    intent_id: str
    evidence_id: str
    action_id: str
    binding_id: str
    skill_execution_id: str
    granted: bool
    provenance: Provenance

    def __post_init__(self) -> None:
        for name in (
            "authority_id", "intent_id", "evidence_id", "action_id",
            "binding_id", "skill_execution_id",
        ):
            _name(name, getattr(self, name))
        if type(self.granted) is not bool:
            raise InvalidWaitReleaseAction("granted must be bool")
        _provenance(self.provenance)


@dataclass(frozen=True, slots=True)
class WaitReleaseActionTrace:
    wait_evidence_id: str
    fresh_evidence_id: str
    reevaluation_authority_id: str
    release_authority_id: str
    route_criterion_id: str
    admission_criterion_id: str
    selected_candidate: str
    binding_result: ExecutionBindingResult
    proposed_action: ActionLifecycle
    provenance: Provenance


def propose_explicit_wait_release_action(
    reevaluation: ExplicitWaitReevaluation,
    reevaluation_authority: WaitGateAuthority | None,
    release_authority: WaitReleaseActionAuthority | None,
    binding: ExecutionBinding,
    *,
    at_ns: int,
    provenance: Provenance,
) -> WaitReleaseActionTrace:
    """Explicit S25 WAIT -> MOVE_AWAY recheck -> S13/S14 -> Action PROPOSED.

    Do not treat this function as the source of later Action authorization.
    """
    _time(at_ns)
    _provenance(provenance)
    if not isinstance(reevaluation, ExplicitWaitReevaluation):
        raise InvalidWaitReleaseAction("requires S25 typed reevaluation")
    if not isinstance(binding, ExecutionBinding):
        raise InvalidWaitReleaseAction("requires separate typed S14 binding")
    gate = reevaluation.original
    if not isinstance(reevaluation.result, PostFailureEpochTrace):
        raise InvalidWaitReleaseAction("requires S24 typed fresh cognition")
    current_intent = gate.intent.current_intent
    if current_intent is None or gate.intent.pending_reconsideration is not None:
        raise InvalidWaitReleaseAction("Current Intent not active")
    if gate.intent.events != gate.intent_events:
        raise InvalidWaitReleaseAction("Intent changed since WAIT acknowledgement")
    if not gate.recovery_skill.is_current_snapshot or gate.recovery_skill.state is not SkillState.STARTED:
        raise InvalidWaitReleaseAction("recovery Skill no longer current STARTED")
    if not gate.action3.is_current_snapshot or gate.action3.state is not ActionState.OUTCOME:
        raise InvalidWaitReleaseAction("prior Action3 no longer terminal")
    if gate.supervisor.get(gate.action3.action_id) is not gate.action3:
        raise InvalidWaitReleaseAction("Action3 is not current supervised lifecycle")
    if gate.supervisor.open_actions:
        raise InvalidWaitReleaseAction("cannot release WAIT while another Action is open")
    if not (
        gate.action3.skill_execution_id == gate.recovery_skill.execution_id
        and gate.recovery_skill.intent_id == current_intent.intent_id
        and gate.action3.intent_id == current_intent.intent_id
        and gate.retained_snapshot.revision == 1
        and gate.retained_snapshot.value == 4
        and gate.trace.retained_revision == 1
    ):
        raise InvalidWaitReleaseAction("Skill/Intent/retained lineage does not match")
    old = gate.trace.world_evidence
    new = reevaluation.new_evidence
    fresh = reevaluation.result
    if (
        gate.trace.selected_candidate != "WAIT"
        or gate.trace.admission_status is not AdmissionDecisionStatus.ADMITTED
        or gate.trace.wait_score != 4
        or gate.trace.move_score != 7
        or reevaluation.original.trace.world_evidence != old
        or new == old
        or new.evidence_id == old.evidence_id
        or new.provenance == old.provenance
        or new.action_id != gate.action3.action_id
        or new.binding_id != old.binding_id
        or new.session_id != old.session_id
        or new.consequence_provenance != old.consequence_provenance
        or fresh.world_evidence != new
        or fresh.world_evidence.provenance not in fresh.source_provenance
        or fresh.retained_revision != 1
        or fresh.admission_status is not AdmissionDecisionStatus.ADMITTED
        or fresh.selected_candidate != "MOVE_AWAY"
        or fresh.epoch.cognition_requested
        or fresh.epoch.timed_out_actions
        or fresh.stage_ids != gate.trace.stage_ids
    ):
        raise InvalidWaitReleaseAction("S25 fresh MOVE_AWAY result is not exact")
    expected_wait = 8 if new.threat_clearance_cm <= 100 else 4
    if (
        fresh.wait_score != expected_wait
        or fresh.move_score != 7
        or fresh.wait_score <= fresh.move_score
        or new.observed_at_ns <= gate.armed_at_ns
        or new.observed_at_ns > gate.expires_at_ns
        or at_ns < new.observed_at_ns
        or at_ns > gate.expires_at_ns
    ):
        raise InvalidWaitReleaseAction("fixed S24 comparator/freshness mismatch")
    if gate.supervisor.last_at_ns is not None and at_ns < gate.supervisor.last_at_ns:
        raise InvalidWaitReleaseAction("proposal predates latest supervisor decision")
    if not isinstance(reevaluation_authority, WaitGateAuthority):
        raise InvalidWaitReleaseAction("separate S25 reevaluation authority required")
    if (
        not reevaluation_authority.granted
        or reevaluation_authority.scope is not WaitAuthorityScope.REEVALUATE
        or reevaluation_authority.authority_id != reevaluation.reevaluation_authority_id
        or reevaluation_authority.authority_id == gate.acknowledgement_authority_id
        or reevaluation_authority.intent_id != current_intent.intent_id
        or reevaluation_authority.evidence_id != new.evidence_id
    ):
        raise InvalidWaitReleaseAction("reevaluation caller authority mismatch")
    if not isinstance(release_authority, WaitReleaseActionAuthority) or not release_authority.granted:
        raise InvalidWaitReleaseAction("caller release proposal authority required")
    if (
        release_authority.authority_id in (
            gate.acknowledgement_authority_id,
            reevaluation_authority.authority_id,
        )
        or release_authority.intent_id != current_intent.intent_id
        or release_authority.evidence_id != new.evidence_id
        or release_authority.action_id != binding.action_id
        or release_authority.binding_id != binding.binding_id
        or release_authority.skill_execution_id != gate.recovery_skill.execution_id
    ):
        raise InvalidWaitReleaseAction("release authority not scoped to this Action")
    if (
        binding.action_id == gate.action3.action_id
        or binding.skill_execution_id != gate.recovery_skill.execution_id
        or binding.skill_ref != gate.recovery_skill.skill_id
        or binding.required_intent_id != current_intent.intent_id
        or binding.candidate_ref != "MOVE_AWAY"
        or binding.action_ref != "MOVE_BACKWARD"
    ):
        raise InvalidWaitReleaseAction("S14 binding is not exact MOVE_AWAY mapping")
    try:
        gate.supervisor.get(binding.action_id)
    except UnknownSupervisedAction:
        pass
    else:
        raise InvalidWaitReleaseAction("Action ID already supervised")

    # Reconstruct a new S12 orientation from the *same* fixed S24 scorer and
    # new evidence. Do not mislabel this as S24 exposing its PlanSelection.
    candidates = (
        PlanCandidate(
            "WAIT", (PlanFeature("comparison_score", expected_wait),),
            provenance=new.provenance,
            source_refs=(f"post-wait:{new.evidence_id}",),
            source_provenance=(new.provenance,),
        ),
        PlanCandidate(
            "MOVE_AWAY", (PlanFeature("comparison_score", 7),),
            provenance=new.provenance,
            source_refs=(f"post-wait:{new.evidence_id}",),
            source_provenance=(new.provenance,),
        ),
    )
    selection = select_plan(
        candidates,
        PlanningCriterion(
            "s26-recheck-scorer", "comparison_score",
            PlanningDirection.MINIMIZE,
        ),
    )
    if selection.selected is None or selection.selected.candidate_id != fresh.selected_candidate:
        raise InvalidWaitReleaseAction("S26 route re-derivation contradicts S25")
    route = adjudicate_routes(
        selection, None,
        RouteCriterion("s26-post-wait-route", allow_single_source=True),
        provenance=provenance,
    )
    control = control_candidate_from_route_decision(route)
    if control is None or control.candidate_ref != "MOVE_AWAY":
        raise InvalidWaitReleaseAction("no executable MOVE_AWAY S12 route")
    criterion = ExecutionAdmissionCriterion(
        "s26-explicit-release-admission",
        AdmissionPolicy.CURRENT_INTENT_ALLOW_LIST,
        current_intent.intent_id,
        ("MOVE_AWAY",),
    )
    admission = admit_control_candidate(
        control, route, gate.intent, criterion,
        provenance=Provenance("s26-explicit-release", new.evidence_id),
    )
    if admission.status is not AdmissionDecisionStatus.ADMITTED:
        raise InvalidWaitReleaseAction("new S13 admission not ADMITTED")
    bound = resolve_execution_binding(
        admission, control, route, gate.intent, criterion, binding,
        provenance=provenance,
    )
    if bound.candidate_ref != fresh.selected_candidate:
        raise InvalidWaitReleaseAction("S14 binding differs from recheck selection")
    proposed = ActionLifecycle.propose(
        binding.action_id, skill_execution=gate.recovery_skill,
        intent_commitment=gate.intent, at_ns=at_ns, provenance=provenance,
    )
    result = ExecutionBindingResult(
        binding_id=binding.binding_id, candidate_ref=binding.candidate_ref,
        intent_id=bound.intent_id,
        skill_execution_id=gate.recovery_skill.execution_id,
        skill_ref=gate.recovery_skill.skill_id,
        action_id=proposed.action_id, action_ref=binding.action_ref,
        skill_state=gate.recovery_skill.state,
        action_state=proposed.state, provenance=provenance,
    )
    return WaitReleaseActionTrace(
        wait_evidence_id=old.evidence_id, fresh_evidence_id=new.evidence_id,
        reevaluation_authority_id=reevaluation_authority.authority_id,
        release_authority_id=release_authority.authority_id,
        route_criterion_id=route.criterion.criterion_id,
        admission_criterion_id=criterion.criterion_id,
        selected_candidate=bound.candidate_ref,
        binding_result=result, proposed_action=proposed,
        provenance=provenance,
    )


def _name(name: str, value: object) -> None:
    if not isinstance(value, str) or not value or value != value.strip() or any(c.isspace() for c in value):
        raise InvalidWaitReleaseAction(f"{name} must be a structured identifier")


def _time(value: object) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise InvalidWaitReleaseAction("time must be non-negative integer")


def _provenance(value: object) -> None:
    if not isinstance(value, Provenance):
        raise InvalidWaitReleaseAction("provenance must be typed")
