"""Replay prior actual real-World Paper stdout without claiming new World B.

Original is the sealed immutable World-success source from route A. We
reconstruct only a *byte prefix* ending at the 8th input callback, which
could have been read while Paper was alive, then audit its byte identity
against the final exact Paper original. Not a real next L0 native epoch.
"""
from __future__ import annotations

import json
from pathlib import Path

from adapters.mineflayer.l23_paper_s7_settling import _paper_rows
from adapters.mineflayer.m02_paper_dev.s50_live_paper_window import (
    capture_s50_live_paper_window,
    verify_s50_live_window_against_final_paper,
)

ORIGINAL = Path("docs/evidence/selfbody-postworld-epoch-20261031/run1")


def test_archived_world_a_original_supports_b_paper_only_prefix_source():
    original = (ORIGINAL / "server.log").read_bytes()
    report = json.loads((ORIGINAL / "s49-report.json").read_bytes())
    assert report["status"] == "PASS"
    assert report["selfbody_postworld_internal_epoch"]["classification"] == (
        "DEV_POSTWORLD_INTERNAL_EPOCH_PRIOR_EXPERIENCE_READ_PASS"
    )
    session_id = report["session_id"]
    action_id = report["actual_native_actions"][0]["action"]
    marker = f"{action_id}-{session_id}"
    assert action_id.startswith("s49-native-move-")
    # End at the last complete original 8th INPUT_TICK line; never synthesize
    # a Node trace footer, Paper event or extra native probe.
    lines = original.splitlines(keepends=True)
    prefix_end = next(
        i + 1 for i, line in enumerate(lines)
        if b"S50_DEV_INPUT_TICK " in line
        and b"index=8 " in line
        and marker.encode() in line
    )
    prefix = b"".join(lines[:prefix_end])
    assert prefix.endswith(b"\n")
    inputs = _paper_rows(prefix, "S50_DEV_INPUT_TICK ")
    assert len(inputs) == 8
    world = inputs[0]["world"]
    subject = inputs[0]["subject_uuid"]
    witness = capture_s50_live_paper_window(
        prefix, session_id=session_id, action_id=action_id,
        world=world, subject_uuid=subject,
    )
    assert tuple(t.world_tick for t in witness.ticks) == tuple(range(253, 261))
    assert witness.prior_motion_summary()[
        "motion_with_last_reported_input_off_ticks"
    ] == (253, 254, 255)
    assert witness.node_trace_complete is False
    assert witness.final_source_verified is False
    assert verify_s50_live_window_against_final_paper(witness, original)
