"""G4.4 strict in-flight staged observed gait policy."""
from dataclasses import replace

import pytest

from adapters.mineflayer.g44_intra_action_gait_dev import decide_g44_intra_action_gait_dev
from relay_self.goal_navigation import (
    GoalPurpose, L2GoalProposal, compile_l1_goal_dev,
)
from relay_self.provenance import Provenance


def directive():
    p=Provenance("dev-goal","g44")
    proposal=L2GoalProposal(
        goal_id="approach-demo",intent_id="approach-demo",
        session_id="session-g44",target_x=0.0,target_z=4.0,
        purpose=GoalPurpose.APPROACH,provenance=p,
    )
    return compile_l1_goal_dev(proposal, tolerance_m=0.55, provenance=p)


def eval_(mode,z,**changes):
    args={
        "action_id":"goal-approach-demo-step-2",
        "mode":mode,"session_id":"session-g44",
        "source_seq":100,"previous_seq":99,
        "request_id":"goal-approach-demo-step-2-inflight-101",
        "source":"mineflayer","x":0.0,"z":z,
        "truncated":False,"danger_present":False,
    }
    args.update(changes)
    return decide_g44_intra_action_gait_dev(directive(),**args)


def test_g44_stage_progression_and_never_attest_world_gait():
    assert eval_("RUN",1.0).target_mode is None
    assert eval_("RUN",2.0).target_mode=="JOG"
    assert eval_("JOG",2.0).target_mode is None
    assert eval_("JOG",2.1).target_mode=="WALK"
    assert eval_("WALK",3.6).target_mode=="CLEAR"
    assert not eval_("RUN",2.0).applied_attested
    assert not eval_("RUN",2.0).reached_attested


@pytest.mark.parametrize("change",[
    {"source_seq":99},{"session_id":"foreign"},
    {"source":"synthetic"},{"truncated":True},
    {"danger_present":True},{"x":float("nan")},
    {"request_id":"forged"},{"mode":"DASH"},
])
def test_g44_rejects_foreign_or_unsafe(change):
    with pytest.raises(ValueError,match="G4.4"):
        eval_("RUN",2.0,**change)
