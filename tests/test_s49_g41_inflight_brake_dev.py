"""G4.1 source-qualified brake policy; never certify Goal reached."""
import pytest

from adapters.mineflayer.g41_inflight_brake_dev import decide_g41_inflight_brake_dev
from relay_self.goal_navigation import GoalPurpose, L1GoalDirective, L2GoalProposal
from relay_self.provenance import Provenance


def policy(z, *, mode="RUN", seq=13, previous=12, source="mineflayer",
           request="goal-g4-step-1-inflight-9", session="g41-session",
           truncated=False, danger=False):
    proposal=L2GoalProposal(
        "g4","intent","g41-session",0.,4.,GoalPurpose.APPROACH,
        .3,.55,1.5,Provenance("l2-g41","proposal"),
    )
    directive=L1GoalDirective(
        proposal,.55,6,18,Provenance("l1-g41","tolerance"),
    )
    return decide_g41_inflight_brake_dev(
        directive,action_id="goal-g4-step-1",mode=mode,
        session_id=session,source_seq=seq,request_id=request,
        source=source,x=0.,z=z,previous_seq=previous,
        truncated=truncated,danger_present=danger,
    )


@pytest.mark.parametrize("mode,z,brake",[
    ("DASH",1.,False),("RUN",2.6,True),("RUN",1.,False),
    ("JOG",3.25,True),("JOG",2.9,False),("WALK",3.5,True),
    ("WALK",3.2,False),
])
def test_g41_native_brake_advisory(mode,z,brake):
    result=policy(z,mode=mode)
    assert result.brake_requested is brake
    assert result.reached_attested is False
    assert result.actual_gait_attested is False
    assert result.source_seq==13


@pytest.mark.parametrize("bad",[
    {"previous":13},{"seq":10},{"source":"local"},
    {"session":"other"},{"truncated":True},{"danger":True},
    {"request":"foreign-inflight-9"},
])
def test_g41_foreign_stale_or_danger_fails_closed(bad):
    with pytest.raises(ValueError,match="G4.1 refuses"):
        policy(2.6,**bad)


def test_g41_inside_tolerance_is_not_goal_reached():
    result=policy(3.8,mode="WALK")
    assert result.brake_requested
    assert result.reason=="OBSERVED_TOLERANCE_BRAKE_FOR_SETTLE"
    assert result.reached_attested is False
