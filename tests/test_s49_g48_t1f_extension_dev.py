"""G4.8 direct S49 Action Node gait metadata is strictly opt-in and typed."""
import pytest

from adapters.mineflayer.t1f_protocol import validate_result
from test_s49_g46_t1f_extension_dev import _base


@pytest.mark.parametrize("mode", ["JOG", "WALK"])
def test_g48_direct_original_action_boundary_requires_matched_node_controls(
    monkeypatch, mode,
):
    monkeypatch.setenv("S49_G48_DIRECT_ACTION_GENERATION_DEV_ONLY", "1")
    sample = _base()
    sample["snapshot"]["gait_dev"].update({
        "sprinting": False, "sneaking": mode == "WALK",
        "speed_base": 0.1, "speed_value": 0.1, "speed_modifiers": 0,
    })
    sample["applied_controls_dev"].update({
        "forward": True, "sprint": False, "sneak": mode == "WALK",
    })
    sample["g46_motor_boundary_dev"].update({
        "requested_mode": mode, "transition_index": 0,
        "effect_id": "goal-a-step-2",
    })
    validate_result(sample)
    sample["applied_controls_dev"]["sneak"] = not (mode == "WALK")
    with pytest.raises(ValueError, match="G4.8"):
        validate_result(sample)


@pytest.mark.parametrize("mode", ["JOG", "WALK"])
def test_g48_direct_mode_disabled_remains_g46_invalid(monkeypatch, mode):
    monkeypatch.delenv("S49_G48_DIRECT_ACTION_GENERATION_DEV_ONLY", raising=False)
    sample = _base()
    sample["applied_controls_dev"].update({
        "forward": True, "sprint": False, "sneak": mode == "WALK",
    })
    sample["g46_motor_boundary_dev"].update({
        "requested_mode": mode, "transition_index": 0,
    })
    with pytest.raises(ValueError, match="G4.6"):
        validate_result(sample)
