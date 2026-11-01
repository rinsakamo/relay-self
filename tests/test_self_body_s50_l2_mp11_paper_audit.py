"""MP11 synthetic multi-marker Paper transcript: structure only, never real World."""
from __future__ import annotations

import pytest

from adapters.mineflayer.self_body_s50_l2_mp11_paper_audit import (
    MP11PaperRejected,
    audit_multi_trial_paper,
)

WORLD = "original-constant-world-uuid"
SUBJECT = "subject-constant-uuid"
MARKERS = ("s49-native-move-11-session", "s49-native-move-18-session")


def segment(marker, surface, *, start):
    mode = "GRASS_BLOCK_5X5_READONLY" if surface == "GRASS_BLOCK" else "PACKED_ICE_5X5"
    rows = [
        f"M02_DEV_S50_PHASE marker_id={marker} world={WORLD} phase=PRE_FORWARD",
        (f"S50_DEV_SURFACE_LOCK marker_id={marker} world={WORLD} "
         f"subject_uuid={SUBJECT} status=REAL_PAPER_PRE_ACTION_SURFACE_LOCK "
         f"original_material=GRASS_BLOCK target_material={surface} mode={mode} "
         "blocks_verified=25 on_ground=true"),
        f"M02_DEV_S50_PHASE marker_id={marker} world={WORLD} phase=POST_CLEAR",
        f"S50_DEV_WAIT_BEGIN marker_id={marker} world={WORLD} tick={start-1}",
    ]
    for i in range(8):
        tick = start+i
        rows.extend([
            (f"S50_DEV_WAIT_TICK marker_id={marker} world={WORLD} tick={tick} "
             f"index={i+1} from_x=0.5 from_y=-60 from_z={-i*0.05} "
             f"x=0.5 y=-60 z={-(i+1)*0.05}"),
            (f"S50_DEV_INPUT_TICK marker_id={marker} world={WORLD} "
             f"subject_uuid={SUBJECT} tick={tick} index={i+1}"),
        ])
        if i:
            rows.append(
                f"S50_DEV_LOCAL_FORECAST_SCORE marker_id={marker} world={WORLD} "
                f"subject_uuid={SUBJECT} prior_tick={tick-1} target_tick={tick} "
                "ticket_sha256=aa"
            )
        if i < 7:
            rows.append(
                f"S50_DEV_LOCAL_FORECAST_FIXED marker_id={marker} world={WORLD} "
                f"subject_uuid={SUBJECT} prior_tick={tick} target_tick={tick+1} "
                "ticket_sha256=aa"
            )
    return rows


def original():
    lines = (
        segment(MARKERS[0], "GRASS_BLOCK", start=100)
        + segment(MARKERS[1], "PACKED_ICE", start=200)
    )
    return ("\n".join(lines)+"\n").encode()


def audit(data):
    return audit_multi_trial_paper(
        data, action_markers=MARKERS, world_uuid=WORLD,
        subject_uuid=SUBJECT, surfaces=("GRASS_BLOCK","PACKED_ICE"),
    )


def test_two_sequential_original_like_markers_one_paper_world_source_shape():
    output = audit(original())
    assert len(output) == 2
    assert output[0].world_uuid == output[1].world_uuid == WORLD
    assert output[0].wait_ticks == tuple(range(100,108))
    assert output[1].wait_ticks == tuple(range(200,208))
    assert output[0].wait_motion_m[0] == pytest.approx(.05)
    assert output[0].status == "ORIGINAL_PAPER_MARKER_SHAPE_ONLY_NO_NATIVE_S16_AUTHORITY"
    assert output[0].paper_sha256 == output[1].paper_sha256


@pytest.mark.parametrize("bad",[
    "world","subject","surface","missing_wait","missing_forecast",
    "foreign_marker","input_tick","time_overlap","nonfinite","marker_replay",
    "input_index","phase","out_of_order",
])
def test_foreign_replay_nonconsecutive_or_incomplete_source_rejected(bad):
    s=original().decode()
    if bad=="world":
        s=s.replace(f"world={WORLD}", "world=other-world",1)
    if bad=="subject":
        s=s.replace(f"subject_uuid={SUBJECT}", "subject_uuid=other",1)
    if bad=="surface":
        s=s.replace("target_material=PACKED_ICE","target_material=GRASS_BLOCK")
    if bad=="missing_wait":
        s=s.replace("S50_DEV_WAIT_TICK marker_id="+MARKERS[0],
                    "S50_DEV_MISSING_TICK marker_id="+MARKERS[0],1)
    if bad=="missing_forecast":
        s=s.replace("S50_DEV_LOCAL_FORECAST_FIXED marker_id="+MARKERS[0],
                    "S50_DEV_MISSING_FORECAST_FIXED marker_id="+MARKERS[0],1)
    if bad=="foreign_marker":
        s=s.replace("M02_DEV_S50_PHASE marker_id="+MARKERS[1],
                    "M02_DEV_S50_PHASE marker_id=foreign-action",1)
    if bad=="input_tick":
        s=s.replace("tick=101 index=2","tick=199 index=2",1)
    if bad=="time_overlap":
        s=s.replace("tick=200 index=1","tick=100 index=1",1)
    if bad=="nonfinite":
        s=s.replace("from_x=0.5","from_x=nan",1)
    if bad=="marker_replay":
        s=s.replace("marker_id="+MARKERS[1],"marker_id="+MARKERS[0])
    if bad=="input_index":
        s=s.replace("tick=100 index=1","tick=100 index=99",1)
    if bad=="phase":
        s=s.replace("phase=PRE_FORWARD","phase=POST_CLEAR",1)
    if bad=="out_of_order":
        line=s.splitlines()
        indices=[i for i,x in enumerate(line) if "S50_DEV_WAIT_TICK" in x]
        line[indices[0]],line[indices[1]]=line[indices[1]],line[indices[0]]
        s="\n".join(line)+"\n"
    with pytest.raises(MP11PaperRejected):
        audit(s.encode())


def test_one_marker_not_misrepresented_as_multi_action_experiment():
    source=("\n".join(segment(MARKERS[0],"GRASS_BLOCK",start=100))+"\n").encode()
    with pytest.raises(MP11PaperRejected):
        audit(source)
