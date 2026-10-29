"""G4.6 T1u extension schema is opt-in and strict without weakening v0."""
import pytest

from adapters.mineflayer.t1f_protocol import validate_result


def _base():
    # Valid ADMITTED original sample with no invented native effect.
    b="00000000-0000-0000-0000-000000000001"
    return {
        "snapshot":{
            "version":1,"boot":b,"world":b,"player":b,
            "index":1,"tick":11,"world_tick":11,
            "paper_ns":1,"challenge":"a"*32+":1","x":0.0,
            "y":64.0,"z":0.0,"health":20.0,"food":20,
            "input":0,"threats_complete":True,"threats":[],
            "basal_ticks":11,"basal_exhaustion":0.0,
            "motion_blocks":0.0,"motion_exhaustion":0.0,
            "gait_dev":{
                "sneaking":False,"sprinting":True,
                "speed_base":0.1,"speed_value":0.13,"speed_modifiers":1,
            },
        },
        "status":"ADMITTED","reason":"OK",
        "assessment":"NO_KNOWN_URGENT_SIGNAL",
        "latest_confirmed_tick":11,"received_ns":"11000",
        "evaluation_start_ns":"11000","evaluation_completed_ns":"11500",
        "age_upper_ns":"1500","age_lower_ns":"500",
        "paper_to_node_exact_ns":None,"cache_mismatch":False,
        "qualification":False,"tps_admission_granted":False,
        "challenge_sent_ns":"10000",
        "control":{"phase":"MOVING","since_ns":"9000","generation":1},
        "applied_controls_dev":{
            "forward":True,"back":False,"left":False,"right":False,
            "jump":False,"sneak":False,"sprint":True,
        },
        "g46_motor_boundary_dev":{
            "action_id":"goal-a-step-2","effect_id":"goal-a-step-2",
            "requested_mode":"SPRINT_INPUT","transition_index":0,
            "control_generation":1,"control_phase":"MOVING",
        },
    }


def test_g46_valid_original_s49_node_boundary_extension():
    validate_result(_base())


@pytest.mark.parametrize("alter",[
    {"control_generation":2},{"control_phase":"CLEARED"},
    {"effect_id":"foreign"},{"transition_index":2},
    {"requested_mode":"WALK"},{"action_id":None},
])
def test_g46_schema_fails_closed_on_foreign_or_misaligned_mode(alter):
    sample=_base()
    sample["g46_motor_boundary_dev"].update(alter)
    with pytest.raises(ValueError,match="G4.6"):
        validate_result(sample)


def test_g46_original_schema_still_passes_without_optional_boundary():
    sample=_base()
    del sample["g46_motor_boundary_dev"]
    validate_result(sample)

@pytest.mark.parametrize("mode", ["JOG", "WALK"])
def test_g48_original_ordinary_t1u_schema_requires_scoped_marker(mode):
    sample=_base()
    sample["g46_motor_boundary_dev"].update({
        "requested_mode":mode,"transition_index":0,
        "g48_ordinary_action_dev":True,
    })
    validate_result(sample)
    sample["g46_motor_boundary_dev"].pop("g48_ordinary_action_dev")
    with pytest.raises(ValueError, match="G4.6"):
        validate_result(sample)


@pytest.mark.parametrize("bad", [
    {"g48_ordinary_action_dev": False},
    {"effect_id":"goal-fake"},
    {"transition_index":1},
    {"requested_mode":"SPRINT_INPUT"},
    {"control_phase":"CLEARED"},
])
def test_g48_schema_rejects_wrong_original_ordinary_epoch(bad):
    sample=_base()
    sample["g46_motor_boundary_dev"].update({
        "requested_mode":"JOG","transition_index":0,
        "g48_ordinary_action_dev":True,
    })
    sample["g46_motor_boundary_dev"].update(bad)
    with pytest.raises(ValueError, match="G4.[68]"):
        validate_result(sample)
