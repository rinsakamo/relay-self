"""Protocol sub-effect is an original S49 Action *effect*, not an Action."""
import json

import pytest

from adapters.mineflayer.python_protocol import (
    MineflayerAdapterProtocolError, encode_g44_gait_transition_dev,
)


def test_g44_typed_parent_and_transition_id():
    data=json.loads(encode_g44_gait_transition_dev(
        "goal-demo-step-2",transition_index=1,from_mode="RUN",to_mode="JOG",
    ))
    assert data["action_id"]=="goal-demo-step-2-g44-1-jog"
    assert data["parent_action_id"]=="goal-demo-step-2"
    assert data["effect"]=="g44_gait_transition_dev"


@pytest.mark.parametrize("args",[
    ("foreign",1,"RUN","JOG"),
    ("goal-demo",2,"RUN","JOG"),
    ("goal-demo",1,"JOG","WALK"),
    ("goal-demo",True,"RUN","JOG"),
    ("goal-demo",2,"WALK","RUN"),
])
def test_g44_protocol_fails_closed(args):
    with pytest.raises(MineflayerAdapterProtocolError,match="G4.4"):
        encode_g44_gait_transition_dev(
            args[0],transition_index=args[1],
            from_mode=args[2],to_mode=args[3],
        )
