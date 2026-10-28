"""L2/L1 goal contract and independent observation-driven L0 motion loop.

A DEV operator can supply an L2 proposal and L1 policy decision. This does
not pretend to have called L2 or trained L1. It never issues physical Actions:
only the existing S49 Action supervisor may issue a chosen L0 motor step.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from adapters.mineflayer.python_protocol import MineflayerObservation
from relay_self.provenance import Provenance


class GoalControlRejected(ValueError):
    pass


class GoalPurpose(str, Enum):
    APPROACH = "approach"
    INTERACT = "interact"
    ESCAPE = "escape"


class GoalDecisionKind(str, Enum):
    MOVE = "MOVE"
    WAIT_VERIFY = "WAIT_VERIFY"
    REACHED = "REACHED"
    INTERRUPT = "INTERRUPT"
    NEEDS_REPLAN = "NEEDS_REPLAN"


@dataclass(frozen=True, slots=True)
class L2GoalProposal:
    goal_id: str
    intent_id: str
    session_id: str
    target_x: float
    target_z: float
    purpose: GoalPurpose
    minimum_tolerance_m: float
    maximum_tolerance_m: float
    danger_interrupt_m: float
    provenance: Provenance

    def __post_init__(self) -> None:
        if (
            not all(isinstance(s,str) and s for s in (
                self.goal_id,self.intent_id,self.session_id
            ))
            or not isinstance(self.purpose,GoalPurpose)
            or not isinstance(self.provenance,Provenance)
            or self.provenance.source=="mineflayer"
            or any(type(v) not in (int,float) or not math.isfinite(v) for v in (
                self.target_x,self.target_z,self.minimum_tolerance_m,
                self.maximum_tolerance_m,self.danger_interrupt_m
            ))
            or not 0.05 <= self.minimum_tolerance_m <= self.maximum_tolerance_m <= 1.0
            or not 1.0 <= self.danger_interrupt_m <= 4.0
        ):
            raise GoalControlRejected("L2 target requires bounded authenticated intent")


@dataclass(frozen=True, slots=True)
class L1GoalDirective:
    proposal: L2GoalProposal
    tolerance_m: float
    max_actions: int
    max_observations: int
    provenance: Provenance

    def __post_init__(self) -> None:
        if (
            not isinstance(self.proposal,L2GoalProposal)
            or type(self.tolerance_m) is not float
            or not math.isfinite(self.tolerance_m)
            or not self.proposal.minimum_tolerance_m
                <= self.tolerance_m <= self.proposal.maximum_tolerance_m
            or type(self.max_actions) is not int
            or not 1 <= self.max_actions <= 8
            or type(self.max_observations) is not int
            or not self.max_actions+2 <= self.max_observations <= 24
            or not isinstance(self.provenance,Provenance)
            or self.provenance.source=="mineflayer"
            or self.provenance==self.proposal.provenance
        ):
            raise GoalControlRejected("L1 tolerance/capacity needs independent bounded decision")


def compile_l1_goal_dev(
    proposal:L2GoalProposal, *, current_x:float,current_z:float,
    provenance:Provenance,
) -> L1GoalDirective:
    """Deterministic explicit L1-style policy, not an actual LLM invocation."""
    if not isinstance(proposal,L2GoalProposal) or any(
        type(v) not in (int,float) or not math.isfinite(v)
        for v in (current_x,current_z)
    ):
        raise GoalControlRejected("missing original World basis for L1 tolerance")
    distance=math.hypot(proposal.target_x-current_x,proposal.target_z-current_z)
    if not 0.3 <= distance <= 7.0:
        raise GoalControlRejected("goal too near or far for DEV direct L0")
    ratio={
        GoalPurpose.APPROACH:0.14,
        GoalPurpose.INTERACT:0.07,
        GoalPurpose.ESCAPE:0.22,
    }[proposal.purpose]
    tolerance=float(max(
        proposal.minimum_tolerance_m,
        min(proposal.maximum_tolerance_m,distance*ratio),
    ))
    return L1GoalDirective(
        proposal=proposal,tolerance_m=tolerance,max_actions=6,
        max_observations=18,provenance=provenance,
    )


@dataclass(frozen=True, slots=True)
class L0GoalDecision:
    kind: GoalDecisionKind
    source_seq: int
    x: float
    z: float
    goal_error_m: float
    forward_remaining_m: float
    cross_track_m: float
    input_duration_s: float | None
    reason: str


class ObservedGoalL0:
    """Single goal owner; fresh probes alone advance the motor loop.

    No zombie event is needed to continue. A nearby threat may INTERRUPT.
    Only a fresh settling observation can validate REACHED after WAIT_VERIFY.
    """
    def __init__(
        self,directive:L1GoalDirective,*,start_x:float,start_z:float,
        forward_x:float=0.0,forward_z:float=1.0,
    ):
        if not isinstance(directive,L1GoalDirective) or any(
            type(v) not in (float,int) or not math.isfinite(v)
            for v in (start_x,start_z,forward_x,forward_z)
        ) or not math.isclose(math.hypot(forward_x,forward_z),1,abs_tol=1e-9):
            raise GoalControlRejected("L0 needs actual World basis and unit heading")
        self.directive=directive
        self.start=(float(start_x),float(start_z))
        self.forward=(float(forward_x),float(forward_z))
        self.last_seq=-1
        self.observations=0
        self.actions=0
        self.last_error:float|None=None
        self.nonprogress=0
        self.pending_settle:tuple[float,float]|None=None
        self.closed=False

    def decide(self,probe:MineflayerObservation) -> L0GoalDecision:
        g=self.directive.proposal
        if (
            self.closed
            or not isinstance(probe,MineflayerObservation)
            or probe.session_id!=g.session_id
            or probe.kind!="probe"
            or not probe.request_id
            or probe.provenance.source!="mineflayer"
            or probe.seq<=self.last_seq
            or probe.snapshot.nearby_entities_coverage.truncated
            or self.observations >= self.directive.max_observations
        ):
            raise GoalControlRejected("L0 refuses stale, foreign or exhausted World probe")
        pos=probe.snapshot.position
        dx=g.target_x-pos.x
        dz=g.target_z-pos.z
        fx,fz=self.forward
        forward=dx*fx+dz*fz
        cross=dx*fz-dz*fx
        error=math.hypot(dx,dz)
        self.observations+=1
        self.last_seq=probe.seq
        threat=any(
            e.name=="zombie" and e.distance<g.danger_interrupt_m
            for e in probe.snapshot.nearby_entities
        )
        def result(kind,reason,duration=None):
            return L0GoalDecision(kind,probe.seq,pos.x,pos.z,error,forward,cross,
                                  duration,reason)
        if threat:
            self.closed=True
            return result(GoalDecisionKind.INTERRUPT,"OBSERVED_NEAR_THREAT")
        if self.pending_settle is not None:
            previous=self.pending_settle
            self.pending_settle=None
            if error<=self.directive.tolerance_m and math.hypot(
                pos.x-previous[0],pos.z-previous[1]
            )<=0.08:
                self.closed=True
                return result(GoalDecisionKind.REACHED,"STABLE_NATIVE_XZ_WITHIN_TOLERANCE")
        if error<=self.directive.tolerance_m:
            self.pending_settle=(pos.x,pos.z)
            return result(GoalDecisionKind.WAIT_VERIFY,"WITHIN_TOLERANCE_VERIFY_SETTLE")
        if forward<=0 or abs(cross)>0.30:
            self.closed=True
            return result(GoalDecisionKind.NEEDS_REPLAN,"GOAL_PASSED_OR_LATERAL")
        if self.actions>=self.directive.max_actions:
            self.closed=True
            return result(GoalDecisionKind.NEEDS_REPLAN,"MOTOR_ACTION_BUDGET")
        if self.last_error is not None:
            self.nonprogress=(
                self.nonprogress+1 if error>self.last_error-0.02 else 0
            )
        if self.nonprogress>=2:
            self.closed=True
            return result(GoalDecisionKind.NEEDS_REPLAN,"NONPROGRESS_WORLD")
        self.last_error=error
        # Input is purposely bounded, and World observes its actual response.
        duration=float(max(0.10,min(0.35,forward/4.3*0.60)))
        return result(GoalDecisionKind.MOVE,"OBSERVED_GOAL_DISTANCE",duration)

    def admitted(self,decision:L0GoalDecision)->None:
        if (
            not isinstance(decision,L0GoalDecision)
            or decision.kind is not GoalDecisionKind.MOVE
            or decision.source_seq!=self.last_seq
            or self.closed
            or self.actions>=self.directive.max_actions
        ):
            raise GoalControlRejected("no original L0 source for next Action")
        self.actions+=1
