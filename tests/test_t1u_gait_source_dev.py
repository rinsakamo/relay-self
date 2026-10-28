"""Original-source witness rejection is distinct from the gait mathematics."""
import copy

import pytest

from adapters.mineflayer.python_protocol import MineflayerPaperSnapshot
from adapters.mineflayer.t1u_gait_source_dev import applied_gait_source_dev
from adapters.mineflayer.t2_tick_accounting import TickAccounting
from test_t1f_t2_dev import frame


def witness(i, **kwargs):
    f = frame(i, **kwargs)
    d = copy.deepcopy(f.data)
    d["applied_controls_dev"] = {k: bool(d["snapshot"]["input"] & 2) and k == "back"
        for k in ("forward", "back", "left", "right", "jump", "sneak", "sprint")}
    d["snapshot"]["gait_dev"] = dict(sneaking=False, sprinting=False,
        speed_base=.10000000149, speed_value=.10000000149, speed_modifiers=0)
    return MineflayerPaperSnapshot(f.session_id, f.seq, d)


def test_native_facts_certify_only_stable_ordinary_back_jog():
    a = witness(1, control="MOVING", bits=2, x=.1)
    b = witness(2, control="MOVING", bits=2, x=.3)
    g = applied_gait_source_dev(b, a, False)
    assert (g.gait, g.direction, g.world_tick) == ("JOG", "back", 202)
    owner = TickAccounting(a.session_id, gait_source=applied_gait_source_dev)
    owner.observe(a)
    owner.observe(b)
    assert owner.rows[0]["gait_evidence"]["paper_gait_dev"] == b.data["snapshot"]["gait_dev"]
    assert owner.fatigue.world_tick == 202


@pytest.mark.parametrize("kind", ["missing", "sneak", "sprint", "boost", "edge",
                                  "residual", "idle", "foreign", "gap", "blocked", "missing_controls", "wrong_controls"])
def test_unsupported_or_unproven_source_never_earns_a_gait(kind):
    a = witness(1, control="MOVING", bits=2, x=.1)
    b = witness(2, control="MOVING", bits=2, x=.3)
    d = copy.deepcopy(b.data)
    if kind == "missing_controls":
        d.pop("applied_controls_dev")
    elif kind == "wrong_controls":
        d["applied_controls_dev"]["sneak"] = True
    elif kind == "missing":
        d["snapshot"].pop("gait_dev")
    elif kind in ("sneak", "sprint"):
        d["snapshot"]["gait_dev"]["sneaking" if kind == "sneak" else "sprinting"] = True
    elif kind == "boost":
        d["snapshot"]["gait_dev"].update(speed_modifiers=1, speed_value=.15)
    elif kind == "edge":
        a = witness(1, bits=0, x=.1)
    elif kind in ("residual", "idle"):
        d["snapshot"]["input"] = 0
        d["control"]["phase"] = "CLEARED"
        if kind == "idle":
            d["snapshot"].update(x=.1, motion_blocks=.1)
    elif kind == "foreign":
        d["snapshot"]["boot"] = "22222222-2222-2222-2222-222222222222"
    elif kind == "gap":
        d["snapshot"]["world_tick"] += 1
    elif kind == "blocked":
        d["snapshot"].update(x=.1, motion_blocks=.1)
    b = MineflayerPaperSnapshot(b.session_id, b.seq, d)
    with pytest.raises(ValueError, match="NATIVE_GAIT_NOT_ATTESTED"):
        applied_gait_source_dev(b, a, False)


def test_initial_idle_latches_without_free_recovery_or_action():
    owner = TickAccounting("test-session", gait_source=applied_gait_source_dev)
    owner.observe(witness(1))
    before = owner.fatigue
    with pytest.raises(ValueError, match="NATIVE_GAIT_NOT_ATTESTED"):
        owner.observe(witness(2))
    assert owner.failed and owner.fatigue == before and owner.energy.body.tick == 0
    assert owner.gait_refusal["classification"] == "UNDETERMINED"
    assert owner.gait_refusal["p1_updated"] is False
    with pytest.raises(ValueError):
        owner.begin("forbidden")


def test_causal_wait_recovers_same_single_state():
    owner = TickAccounting("test-session", gait_source=applied_gait_source_dev)
    owner.observe(witness(1))
    owner.clear_seq = owner.terminal_seq = 1
    owner.observe(witness(2))
    assert owner.rows[0]["applied_gait"] == "WAIT"
    assert owner.fatigue.world_tick == 202


@pytest.mark.parametrize("change", [
    lambda g: g.update(sneaking="false"),
    lambda g: g.update(speed_value=float("nan")),
    lambda g: g.update(speed_modifiers=-1),
    lambda g: g.update(extra=True),
    lambda g: g.pop("sprinting"),
])
def test_protocol_rejects_corrupt_passive_witness(change):
    from adapters.mineflayer.python_protocol import MineflayerAdapterProtocolError
    f = witness(1)
    d = copy.deepcopy(f.data)
    change(d["snapshot"]["gait_dev"])
    with pytest.raises(MineflayerAdapterProtocolError):
        MineflayerPaperSnapshot(f.session_id, f.seq, d)


def test_node_applied_controls_plus_paper_motion_when_input_packet_absent():
    a = witness(1, control="MOVING", bits=2, x=.1)
    b = witness(2, control="MOVING", bits=2, x=.3)
    for f in (a, b):
        f.data["snapshot"]["input"] = 0
    g = applied_gait_source_dev(b, a, False)
    assert g.gait == "JOG" and g.direction == "back"


@pytest.mark.parametrize("change", [
    lambda c: c.update(back="true"),
    lambda c: c.pop("sprint"),
    lambda c: c.update(extra=False),
])
def test_applied_control_wire_is_exact_and_boolean(change):
    from adapters.mineflayer.python_protocol import MineflayerAdapterProtocolError
    f = witness(1)
    d = copy.deepcopy(f.data)
    change(d["applied_controls_dev"])
    with pytest.raises(MineflayerAdapterProtocolError):
        MineflayerPaperSnapshot(f.session_id, f.seq, d)
