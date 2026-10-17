"""Standalone R synthetic adversarial coverage of S50 native tick writer."""
import pytest

from experiments.standard_env import s50_tick_chord_original_audit as audit

MARKER = "s50-A-session-B"
WORLD = "world-dev-uuid"


def specimen(*, rate=.01, edits=None):
    """Seven source tick chords, and six genuine quiet samples after clear."""
    edits = edits or {}
    lines = []
    for name, time in (("PRE_FORWARD", 100), ("POST_FORWARD", 101),
                       ("PRE_CLEAR", 103), ("POST_CLEAR", 104)):
        lines.append(f"M02_DEV_S50_PHASE phase={name} marker_id={MARKER} "
                     f"world={WORLD} world_full_time={time} "
                     "x=0.5 y=65 z=0.5")
    lines.append(f"S50_DEV_TICK_METER_ARM marker_id={MARKER} world={WORLD} "
                 "world_full_time=100 x=0.5 y=65 z=0.5")
    walked=charged=0.
    pose=.5
    for i in range(1, 14):
        distance = .125 if i <= 6 else 0.0
        next_pose = pose + distance
        walked+=distance
        charged+=distance*rate
        tick = 100+i
        lines.append(
            f"S50_DEV_TICK_MOTION id={i} marker_id={MARKER} world={WORLD} "
            f"world_full_time={tick} from_x={pose} from_y=65 from_z=0.5 "
            f"to_x={next_pose} to_y=65 to_z=0.5 blocks={distance} "
            f"billed={distance*rate} cumulative_blocks={walked} "
            f"cumulative_billed={charged} write_before=1.0 "
            f"write_target={1+distance*rate} write_after={1+distance*rate}"
        )
        lines.append(
            f"S50_DEV_TICK marker_id={MARKER} world={WORLD} tick={tick} "
            f"x={next_pose} y=65 z=0.5 packets=1 blocks=0.75 billed=0.0 "
            f"tick_meter_blocks={walked} tick_meter_billed={charged}"
        )
        pose=next_pose
    lines.append(
        f"M02_DEV_MOTION id=1 marker_id={MARKER} world={WORLD} "
        "blocks=0.7 billed=0 cumulative_billed=0")
    text="\n".join(lines)+"\n"
    for old,new in edits.items():
        assert old in text
        text=text.replace(old,new,1)
    return text.encode()


@pytest.mark.parametrize("arm,rate", [
    ("BASE_ON",.01),("SHAM_ON",.01),("BASAL_ZERO",.01),
    ("WALK_ZERO",0),("BOTH_ZERO",0),
])
def test_original_tick_chord_is_observation_not_science(arm,rate):
    x=audit.review_paper_source(specimen(rate=rate),arm,MARKER)
    assert x["native_tick_rows"]==13
    assert x["source_tick_chord_blocks_lower_bound"]==pytest.approx(.75)
    assert x["walk_native_exhaustion_setter_input"]==pytest.approx(rate*.75)
    assert x["source_walk_exhaustion_per_chord_block"]==pytest.approx(rate)
    assert not x["event_native_double_billing"]
    assert x["bounded_quiet_window_observed"]
    assert not x["continuous_subtick_path_attested"]
    assert not x["engineering_qualified"]
    assert not x["science_go"]


@pytest.mark.parametrize("edit,reason", [
    ({"id=2 marker_id=":"id=1 marker_id="},"tick writer"),
    ({"world_full_time=102 from_x":"world_full_time=101 from_x"},"tick writer"),
    ({"from_x=0.625":"from_x=0.6"},"pose"),
    ({"billed=0.00125":"billed=0.0002"},"billed"),
    ({"cumulative_blocks=0.75":"cumulative_blocks=0.7"},"cumulative"),
    ({"write_after=1.00125":"write_after=1.04"},"setter"),
    ({"M02_DEV_MOTION id=1":"M02_DEV_MOTION id=2"},"double billing"),
    ({"blocks=0.7 billed=0":"blocks=0.7 billed=0.001"},"double billing"),
    ({"phase=PRE_CLEAR":"phase=POST_FORWARD"},"phase"),
    ({"tick=109":"tick=108"},"tick snapshot"),
])
def test_source_corruption_rejected(edit,reason):
    with pytest.raises(audit.InvalidSource,match=reason):
        audit.review_paper_source(specimen(edits=edit),"BASE_ON",MARKER)


def test_foreign_marker_missing_tick_or_zero_rate_forgery():
    with pytest.raises(audit.InvalidSource):
        audit.review_paper_source(specimen(),"BASE_ON","other-session")
    with pytest.raises(audit.InvalidSource):
        audit.review_paper_source(specimen(rate=.01),"BOTH_ZERO",MARKER)
    with pytest.raises(audit.InvalidSource):
        audit.review_paper_source(b"\x00","BASE_ON",MARKER)
