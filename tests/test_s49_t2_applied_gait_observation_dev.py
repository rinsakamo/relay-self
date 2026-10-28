"""G1 observed gait candidates, not authorized WALK/JOG/RUN/DASH or extra P1."""
import pytest

from adapters.mineflayer.python_protocol import MineflayerPaperSnapshot
from adapters.mineflayer.s49_t2_applied_gait_observation_dev import G1AppliedGaitObserverDev

SID = "one-native-session"
BOOT = "00000000-0000-0000-0000-000000000001"
WORLD = "00000000-0000-0000-0000-000000000002"
PLAYER = "00000000-0000-0000-0000-000000000003"


def _frame(monkeypatch, tick, *, x=0.0, blocks=0.0, controls=None,
           phase="MOVING", generation=1, sprint=False, sneak=False,
           mods=0, value=0.1, sid=SID):
    from adapters.mineflayer import t1f_protocol
    monkeypatch.setattr(t1f_protocol, "validate_result", lambda _: None)
    names=("forward", "back", "left", "right", "jump", "sneak", "sprint")
    controls = dict.fromkeys(names, False) if controls is None else controls
    return MineflayerPaperSnapshot(session_id=sid, seq=tick * 2, data={
        "status": "ADMITTED",
        "snapshot": {
            "boot": BOOT, "world": WORLD, "player": PLAYER,
            "world_tick": tick, "tick": tick, "index": tick,
            "x": x, "y": 65.0, "z": 0.0, "motion_blocks": blocks,
            "input": 0,
            "gait_dev": {
                "sprinting": sprint, "sneaking": sneak,
                "speed_base": 0.1, "speed_value": value,
                "speed_modifiers": mods,
            },
        },
        "control": {"phase": phase, "generation": generation},
        "applied_controls_dev": controls,
    })


def _controls(*active):
    names = ("forward", "back", "left", "right", "jump", "sneak", "sprint")
    return {n: n in active for n in names}


def test_initial_and_stable_original_forward_are_candidates_not_p1(monkeypatch):
    observer = G1AppliedGaitObserverDev(SID)
    observer.observe(_frame(monkeypatch, 1, controls=_controls("forward")), t2_activity=None)
    observer.observe(_frame(monkeypatch, 2, controls=_controls("forward"),
                            x=0.07, blocks=0.07), t2_activity="MOVE_OR_UNDETERMINED")
    assert [v.kind for v in observer.rows] == [
        "INITIAL_NO_INTERVAL", "STABLE_ORDINARY_FORWARD_CANDIDATE",
    ]
    assert observer.rows[-1].paper_motion_blocks_delta == pytest.approx(0.07)
    assert observer.rows[-1].full_tick_gait_attested is False
    assert observer.rows[-1].p1_transition_posted is False


def test_blocked_forward_is_not_walk_or_rest(monkeypatch):
    observer = G1AppliedGaitObserverDev(SID)
    for t in (1,2):
        observer.observe(_frame(monkeypatch, t, controls=_controls("forward")),t2_activity=None)
    assert observer.rows[-1].kind == "BLOCKED_OR_STALLED_CONTROL_UNDETERMINED"


def test_sprint_requires_both_server_and_client_fact(monkeypatch):
    observer = G1AppliedGaitObserverDev(SID)
    for t,x in [(1,0.0),(2,0.12)]:
        observer.observe(_frame(monkeypatch, t, controls=_controls("forward","sprint"),
                                x=x,blocks=x,sprint=True,mods=1,value=0.13),
                         t2_activity="MOVE_OR_UNDETERMINED")
    assert observer.rows[-1].kind == "STABLE_SPRINT_FORWARD_CANDIDATE"
    assert observer.rows[-1].full_tick_gait_attested is False


def test_sprint_command_but_server_not_sprint_stays_undetermined(monkeypatch):
    observer = G1AppliedGaitObserverDev(SID)
    for t,x in [(1,0.0),(2,0.12)]:
        observer.observe(_frame(monkeypatch, t, controls=_controls("forward","sprint"),
                                x=x,blocks=x,sprint=False,mods=0,value=0.1),
                         t2_activity=None)
    assert observer.rows[-1].kind == "MOVING_MODE_UNDETERMINED"


def test_source_transition_never_fabricates_stable_gait(monkeypatch):
    observer = G1AppliedGaitObserverDev(SID)
    observer.observe(_frame(monkeypatch, 1, controls=_controls("forward")),t2_activity=None)
    observer.observe(_frame(monkeypatch, 2, controls=_controls(),phase="CLEARED",
                            generation=2,x=0.04,blocks=0.04),t2_activity=None)
    observer.observe(_frame(monkeypatch, 3, controls=_controls(),phase="CLEARED",
                            generation=2,x=0.04,blocks=0.04),t2_activity="WAIT_DEV")
    assert [r.kind for r in observer.rows] == [
        "INITIAL_NO_INTERVAL", "TRANSITION_OR_UNDETERMINED",
        "STABLE_PHYSICAL_IDLE_CANDIDATE",
    ]
    assert observer.rows[-1].t2_activity == "WAIT_DEV"
    assert not observer.rows[-1].p1_transition_posted


def test_missing_gait_source_latches_without_minting_mode(monkeypatch):
    observer=G1AppliedGaitObserverDev(SID)
    frame=_frame(monkeypatch,1)
    frame.data["snapshot"].pop("gait_dev")
    with pytest.raises(ValueError,match="G1_ORIGINAL_PAPER_GAIT_FACTS_MISSING"):
        observer.observe(frame,t2_activity=None)
    assert observer.failed and observer.rows==[]


def test_source_gap_and_foreign_session_latch(monkeypatch):
    observer=G1AppliedGaitObserverDev(SID)
    observer.observe(_frame(monkeypatch,1),t2_activity=None)
    with pytest.raises(ValueError,match="G1_PAPER_INTERVAL_DISCONTINUOUS"):
        observer.observe(_frame(monkeypatch,3),t2_activity=None)
    assert observer.failed and len(observer.rows)==1
    foreign=G1AppliedGaitObserverDev(SID)
    with pytest.raises(ValueError,match="G1_SOURCE_NOT_ADMITTED"):
        foreign.observe(_frame(monkeypatch,1,sid="other-session"),t2_activity=None)


def test_physical_idle_candidate_is_not_R_qualified_wait(monkeypatch):
    observer=G1AppliedGaitObserverDev(SID)
    for t in (1,2):
        observer.observe(_frame(monkeypatch,t,controls=_controls(),phase="CLEARED"),
                         t2_activity="WAIT_DEV")
    assert observer.rows[-1].kind=="STABLE_PHYSICAL_IDLE_CANDIDATE"
    assert not observer.rows[-1].full_tick_gait_attested
    assert not observer.rows[-1].m0_extra_charge_posted
