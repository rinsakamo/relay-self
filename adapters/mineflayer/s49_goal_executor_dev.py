"""DEV L0 goal path through the SAME S49 normal Action supervisor/S15/S16.

The legacy S14 admission is zombie-specific. This new explicit goal-specific
DEV admission is independently authorized; it does not pretend to be a
zombie-derived S12/S13 plan or imply production certification.
"""
from __future__ import annotations

import math
import os
from collections.abc import Awaitable, Callable
from dataclasses import replace

from adapters.mineflayer.action_outcome import interpret_world_consequence
from adapters.mineflayer.execution import (
    MOVE_FORWARD_SNEAK_DEV_REF,
    MOVE_FORWARD_SPRINT_DEV_REF,
    build_mineflayer_command,
    execute_mineflayer_command,
)
from adapters.mineflayer.normal_action import (
    NormalActionAuthorization,
    NormalActionReceipt,
    NormalActionRejected,
    NormalActionStage,
    NormalSessionActionExecutor,
)
from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import (
    MineflayerEffectResult,
    MineflayerObservation,
)
from adapters.mineflayer.s49_goal_t2_boundary_dev import GoalT2ActionBoundaryDev
from relay_self.action import ActionState
from relay_self.action_outcome import (
    ActionOutcomeDisposition,
    record_interpreted_action_outcome,
)
from relay_self.execution_binding import (
    BoundExecutionCandidate,
    ExecutionBinding,
    start_and_propose_bound_execution,
)
from relay_self.goal_detour_dev import L1DetourPlanDev
from relay_self.goal_grid_search_dev import L1GridRoutePlanDev
from relay_self.goal_navigation import (
    GoalDecisionKind,
    L0GoalDecision,
    L1GoalDirective,
)
from relay_self.provenance import Provenance


class S49GoalExecutorDev(NormalSessionActionExecutor):
    """One goal, one inherited original supervisor, bounded Action tokens."""

    def __init__(self,session_id, intent):
        if os.environ.get("S49_L0_GOAL_LOOP_DEV_ONLY")!="1":
            raise NormalActionRejected("goal executor needs explicit DEV gate")
        super().__init__(session_id,intent,dev_forward_motor=True)
        self._goal_id: str|None=None
        self._previous_probe_seq=-1
        self._phase_action_count=0
        self._route_plan: L1DetourPlanDev | L1GridRoutePlanDev | None=None
        self._route_stage=-1
        self._t2_boundary_dev: GoalT2ActionBoundaryDev | None = None

    def bind_t2_owner_dev(self, owner) -> GoalT2ActionBoundaryDev:
        """Optional existing T2 owner; no second motor/reader/P1 is created."""
        if (
            os.environ.get("S49_L1_T2_BOUNDARY_DEV_ONLY") != "1"
            or self._t2_boundary_dev is not None
            or self._count != 0
            or self.supervisor.open_actions
        ):
            raise NormalActionRejected("T2 owner binding must precede first S49 goal Action")
        handoff = GoalT2ActionBoundaryDev(owner, session_id=self.session_id)
        self._t2_boundary_dev = handoff
        return handoff

    def adopt_waypoint_dev(
        self, plan:L1DetourPlanDev|L1GridRoutePlanDev, stage_index:int, *,
        last_closed_action_id:str, latest_native_seq:int,
    )->None:
        """Rebind SAME original Action owner only after a closed previous stage.

        Stage zero must originate from native UNKNOWN, never an untrusted
        retry of its original physical Action. Later stages need previously
        committed route order and completed earlier waypoint.
        """
        if (
            os.environ.get("S49_L1_WAYPOINT_DEV_ONLY")!="1"
            or not isinstance(plan,(L1DetourPlanDev,L1GridRoutePlanDev))
            or (isinstance(plan,L1GridRoutePlanDev) and
                os.environ.get("S49_L1_GRID_SEARCH_DEV_ONLY")!="1")
            or plan.parent.session_id!=self.session_id
            or plan.parent.intent_id!=(
                self.intent.current_intent.intent_id
                if self.intent.current_intent else None
            )
            or type(stage_index) is not int
            or not 0<=stage_index<len(plan.stages)
            or not isinstance(last_closed_action_id,str)
            or not last_closed_action_id
            or type(latest_native_seq) is not int
            or latest_native_seq<=self._previous_probe_seq
            or self.supervisor.open_actions
            or self._count<1
        ):
            raise NormalActionRejected("original Action still open or invalid L1 waypoint")
        prior=self.supervisor.get(last_closed_action_id)
        if prior.action_id!=last_closed_action_id:
            raise NormalActionRejected("foreign closed route Action")
        if stage_index==0 and self._route_plan is None:
            if (
                prior.state is not ActionState.UNKNOWN
                or not isinstance(plan,L1GridRoutePlanDev)
                   and not isinstance(plan,L1DetourPlanDev)
                or plan.source_action_id!=last_closed_action_id
                or latest_native_seq<plan.source_s16_seq
            ):
                raise NormalActionRejected("first L1 route needs closed original UNKNOWN")
        elif stage_index==0:
            previous=self._route_plan
            if (
                os.environ.get("S49_L1_GRID_REFRESH_DEV_ONLY")!="1"
                or not isinstance(previous,L1GridRoutePlanDev)
                or not isinstance(plan,L1GridRoutePlanDev)
                or previous.parent!=plan.parent
                or plan.route_id!=previous.route_id
                or plan.revision!=previous.revision+1
                or plan.reason!="NATIVE_GRID_REFRESH_AFTER_SETTLED_WAYPOINT"
                or plan.source_voxel_seq<=previous.source_voxel_seq
                or plan.source_s16_seq<=previous.source_voxel_seq
                or plan.source_action_id!=last_closed_action_id
                or latest_native_seq<=plan.source_voxel_seq
                or prior.state is not ActionState.OUTCOME
                or self._goal_id is None
                or last_closed_action_id
                   !=f"goal-{self._goal_id}-step-{self._count}"
            ):
                raise NormalActionRejected("unsettled/stale/foreign native route revision")
        elif (
            prior.state is not ActionState.OUTCOME
            or self._route_plan!=plan
            or self._route_stage!=stage_index-1
        ):
            raise NormalActionRejected("replan cannot reissue unresolved native motor")
        self._route_plan=plan
        self._route_stage=stage_index
        self._goal_id=plan.subgoal(stage_index).goal_id
        self._phase_action_count=0


    async def execute_goal_step(
        self,session:MineflayerProcessSession,*,directive:L1GoalDirective,
        decision:L0GoalDecision,probe:MineflayerObservation,
        propose:NormalActionAuthorization,issue:NormalActionAuthorization,
        on_effect_ack_dev: (
            Callable[[str,MineflayerEffectResult],Awaitable[None]]|None
        )=None,
        on_live_probe_dev:Callable[[MineflayerObservation],bool]|None=None,
        look_yaw_dev:float|None=None,
        on_look_ack_dev:Callable[[MineflayerEffectResult],None]|None=None,
        g2_sprint_first_dev:bool=False,
        g2_sneak_prefix_dev:bool=False,
    )->NormalActionReceipt:
        goal=directive.proposal if isinstance(directive,L1GoalDirective) else None
        if type(g2_sneak_prefix_dev) is not bool or (
            g2_sneak_prefix_dev and (
                g2_sprint_first_dev
                or os.environ.get("S49_GOAL_G2_SNEAK_DEV_ONLY")!="1"
                or os.environ.get("S49_L1_G1_OBSERVATION_DEV_ONLY")!="1"
                or self._count>=3
                or look_yaw_dev is not None
                or on_live_probe_dev is not None
            )
        ):
            raise NormalActionRejected(
                "G2 sneak requires first three original S49 Actions, gated and non-rotating"
            )
        if type(g2_sprint_first_dev) is not bool or (
            g2_sprint_first_dev and (
                os.environ.get("S49_GOAL_G2_SPRINT_FIRST_DEV_ONLY")!="1"
                or os.environ.get("S49_SPRINT_MOTOR_DEV_ONLY")!="1"
                or os.environ.get("S49_L1_G1_OBSERVATION_DEV_ONLY")!="1"
                or self._count!=0
                or look_yaw_dev is not None
                or on_live_probe_dev is not None
            )
        ):
            raise NormalActionRejected("G2 sprint requires first original S49 Action, gated and non-rotating")
        if (
            (on_live_probe_dev is not None or on_effect_ack_dev is not None)
            and (
                os.environ.get("S49_L0_INFLIGHT_PREEMPT_DEV_ONLY")!="1"
                or not callable(on_live_probe_dev)
                or not callable(on_effect_ack_dev)
            )
        ):
            raise NormalActionRejected("in-flight DEV callbacks need both explicit owners")
        if (
            (look_yaw_dev is not None or on_look_ack_dev is not None)
            and (
                os.environ.get("S49_L0_TURN_DEV_ONLY")!="1"
                or type(look_yaw_dev) is not float
                or not math.isfinite(look_yaw_dev)
                or not callable(on_look_ack_dev)
            )
        ):
            raise NormalActionRejected("unbound original S49 goal LOOK DEV")
        if (
            os.environ.get("S49_L0_GOAL_LOOP_DEV_ONLY")!="1"
            or not isinstance(session,MineflayerProcessSession)
            or session.started.session_id!=self.session_id
            or session.process_returncode is not None
            or not isinstance(decision,L0GoalDecision)
            or decision.kind is not GoalDecisionKind.MOVE
            or not isinstance(probe,MineflayerObservation)
            or probe.session_id!=self.session_id or probe.kind!="probe"
            or not probe.request_id or probe.provenance.source!="mineflayer"
            or probe.snapshot.nearby_entities_coverage.truncated
            or probe.seq<=self._previous_probe_seq
            or decision.source_seq!=probe.seq
            or goal is None or goal.session_id!=self.session_id
            or goal.intent_id!=(self.intent.current_intent.intent_id
                                if self.intent.current_intent else None)
            or self.intent.pending_reconsideration is not None
            or self._phase_action_count>=directive.max_actions
            or self.supervisor.open_actions
            or (self._t2_boundary_dev is not None and self._t2_boundary_dev.latched)
            or type(decision.input_duration_s) is not float
            or not math.isfinite(decision.input_duration_s)
            or not 0.10<=decision.input_duration_s<=0.35
            or abs(decision.x-probe.snapshot.position.x)>1e-9
            or abs(decision.z-probe.snapshot.position.z)>1e-9
            or (self._goal_id is not None and self._goal_id!=goal.goal_id)
        ):
            raise NormalActionRejected("goal Action lacks original live L0 admission")
        action_id=f"goal-{goal.goal_id}-step-{self._count+1}"
        for g in (propose,issue):
            if (
                not isinstance(g,NormalActionAuthorization)
                or not g.granted or g.session_id!=self.session_id
                or g.intent_id!=goal.intent_id
                or g.action_id!=action_id
                or g.event_seq!=probe.seq or g.probe_seq!=probe.seq
                or g.entity_id!=0
                or g.provenance.source=="mineflayer"
            ):
                raise NormalActionRejected("independent goal step grants required")
        if (
            propose.stage is not NormalActionStage.PROPOSE
            or issue.stage is not NormalActionStage.ISSUE
            or propose.authority_id==issue.authority_id
            or propose.provenance==issue.provenance
            or action_id in self._dispatched
        ):
            raise NormalActionRejected("goal proposal and issue must be separate")
        self._goal_id=goal.goal_id
        self._previous_probe_seq=probe.seq
        t=100+10*self._count
        origin=Provenance("normal-action-runtime",f"{self.session_id}:goal:{t}")
        gait_requested_action_ref=(
            MOVE_FORWARD_SNEAK_DEV_REF if g2_sneak_prefix_dev else
            MOVE_FORWARD_SPRINT_DEV_REF if g2_sprint_first_dev else "MOVE_FORWARD"
        )
        binding=ExecutionBinding(
            binding_id=f"goal-binding-{self._count+1}",
            candidate_ref="GOAL_APPROACH",
            required_intent_id=goal.intent_id,
            skill_execution_id=f"goal-skill-{self._count+1}",
            skill_ref=(
                "goal-forward-sneak-dev" if g2_sneak_prefix_dev
                else "goal-forward-sprint-dev" if g2_sprint_first_dev
                else "goal-forward-walk"
            ),action_id=action_id,
            action_ref=gait_requested_action_ref,
            provenance=directive.provenance,
        )
        # Explicit provisional DEV goal admission. Not legacy zombie S14 route.
        bound=BoundExecutionCandidate(
            binding=binding,candidate_ref="GOAL_APPROACH",
            intent_id=goal.intent_id,
            admission_criterion_id="l1-goal-step-dev-admission",
            route_criterion_id="l1-goal-direct-forward-only",
            control_criterion_id="l0-observed-position-dev",
            admission_provenance=propose.provenance,
            control_provenance=goal.provenance,
            route_provenance=directive.provenance,provenance=origin,
        )
        _,proposed,result=start_and_propose_bound_execution(
            bound,self.intent,at_ns=t,provenance=origin,
        )
        authorized=proposed.authorize(
            at_ns=t+1,provenance=propose.provenance,authority=propose.authority_id,
        )
        issued=self.supervisor.issue(
            authorized,at_ns=t+2,deadline_ns=t+100,provenance=issue.provenance,
        )
        command=replace(
            build_mineflayer_command(issued,result),
            duration_s=decision.input_duration_s,
        )
        # Existing T2 owner observes the original issued Action boundary.
        # A refused handoff consumes the S49 issuance as UNKNOWN without IO.
        if self._t2_boundary_dev is not None:
            try:
                self._t2_boundary_dev.before_issue(
                    command.action_id, probe_seq=probe.seq,
                )
            except BaseException:
                if self.supervisor.get(issued.action_id).state is ActionState.ISSUED:
                    self.supervisor.mark_unknown(
                        issued.action_id, at_ns=t+3, provenance=origin,
                    )
                raise
        # Consumed BEFORE external IO. No automatic retry after unknown.
        self._dispatched.add(command.action_id)
        self._count+=1
        self._phase_action_count+=1
        try:
            consequence=await execute_mineflayer_command(
                session,command,timeout_s=9,provenance=origin,
                on_effect_ack_dev=on_effect_ack_dev,
                on_live_probe_dev=on_live_probe_dev,
                look_yaw_dev=look_yaw_dev,
                on_look_ack_dev=on_look_ack_dev,
            )
            interpretation=interpret_world_consequence(
                issued,result,consequence,provenance=origin,
            )
            if interpretation.disposition is not ActionOutcomeDisposition.OUTCOME:
                terminal=self.supervisor.mark_unknown(
                    issued.action_id,at_ns=t+3,provenance=origin,
                )
            else:
                terminal=record_interpreted_action_outcome(
                    self.supervisor,interpretation,at_ns=t+3,
                )
            receipt = NormalActionReceipt(terminal,consequence,probe.provenance)
            if self._t2_boundary_dev is not None:
                self._t2_boundary_dev.after_terminal(receipt)
            return receipt
        except BaseException:
            if self._t2_boundary_dev is not None:
                self._t2_boundary_dev.latch()
            if self.supervisor.get(issued.action_id).state is ActionState.ISSUED:
                self.supervisor.mark_unknown(
                    issued.action_id,at_ns=t+3,provenance=origin,
                )
            raise
