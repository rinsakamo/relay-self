"""DEV-only one-run Paper observer negatives, without Minecraft or P1 grant."""
from __future__ import annotations

import asyncio
import json

import pytest

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_paper_backward_wait_dev import (
    project_s49_backward_paper_dev,
)
from adapters.mineflayer.s49_paper_transcript_dev import (
    review_s49_paper_transcript_dev,
)
from test_s49_paper_backward_wait_dev import raw_paper, run, typed_owner

RUN_ID = "12345678-1234-4234-8234-123456789abc"
FOREIGN = "22345678-1234-4234-8234-123456789abc"
PLAYER = "32345678-1234-4234-8234-123456789abc"


def transcript(capture, run_id=RUN_ID):
    ex = capture._executor
    action, session = capture.projection.action_id, ex.session_id
    world = ex._wait_fence._world
    subject = (
        f"S49_OBSERVER_SUBJECT action_id={action} session_id={session}"
        f" player_uuid={PLAYER} world={world} run_id={run_id}"
        " clear_ack=UNATTESTED_CONSOLE_CLAIM\n"
    )
    paper = "".join(
        line.rstrip("\n") + f" run_id={run_id}\n"
        for line in raw_paper(capture).splitlines(keepends=True)
    )
    complete = (
        f"S49_OBSERVER_COMPLETE action_id={action} session_id={session}"
        f" player_uuid={PLAYER} world={world} run_id={run_id}"
        " last_tick=78 samples=8 authority=NONE p1_recovery=NONE\n"
    )
    return subject + paper + complete


def review(capture, paper, *, player=PLAYER):
    return review_s49_paper_transcript_dev(
        capture, paper, expected_player_uuid=player,
    )


def test_one_run_with_original_s16_is_correlation_not_proof(monkeypatch):
    capture = typed_owner(monkeypatch)
    outcome = review(capture, transcript(capture))
    assert outcome["status"] == "ONE_RUN_TRANSCRIPT_SHAPE_ONLY"
    assert outcome["observer_run_id"] == RUN_ID
    assert outcome["sample_count"] == 8
    assert (outcome["first_tick"], outcome["last_tick"]) == (71, 78)
    assert outcome["typed_s16_sha256"] == capture.projection.evidence_sha256
    assert outcome["source_authentication"] == "UNATTESTED_PAPER_LOG_TEXT"
    assert outcome["server_effective_control_release"] == "NOT_ATTESTED"
    assert outcome["whole_tick_self_inactivity"] == "NOT_ATTESTED"
    assert outcome["source_bound_tick"] is None
    assert outcome["wait_interval_ref"] is None
    assert outcome["wait_ticks_admitted"] == 0
    assert outcome["p1_fatigue_recovered"] == 0.0
    assert capture._executor.wait_phase == "NEW"


@pytest.mark.parametrize("mutation", [
    "session", "action", "world", "player", "expected_player",
    "missing_subject", "duplicate_subject", "missing_complete",
    "duplicate_complete", "restart", "missing_tick", "duplicate_tick",
    "different_run_tick", "bad_run_id", "last_tick", "abort",
    "false_clear", "false_authority", "false_recovery", "bad_sample_count",
    "old_s50", "old_nine_line_only",
])
def test_foreign_or_replayed_observer_run_rejected(monkeypatch, mutation):
    capture = typed_owner(monkeypatch)
    original = transcript(capture)
    rows = original.splitlines(keepends=True)
    player = PLAYER
    if mutation == "session":
        original = original.replace(
            "session_id=" + capture.projection.session_id, "session_id=foreign", 1
        )
    elif mutation == "action":
        original = original.replace(
            "action_id=" + capture.projection.action_id, "action_id=foreign", 1
        )
    elif mutation == "world":
        original = original.replace("world=paper-dev-world-s49", "world=foreign", 1)
    elif mutation == "player":
        original = original.replace("player_uuid=" + PLAYER,
                                    "player_uuid=" + FOREIGN, 1)
    elif mutation == "expected_player":
        player = FOREIGN
    elif mutation == "missing_subject":
        original = "".join(rows[1:])
    elif mutation == "duplicate_subject":
        original = rows[0] + original
    elif mutation == "missing_complete":
        original = "".join(rows[:-1])
    elif mutation == "duplicate_complete":
        original += rows[-1]
    elif mutation == "restart":
        original += transcript(capture, FOREIGN)
    elif mutation == "missing_tick":
        original = "".join(row for row in rows if "index=4 " not in row)
    elif mutation == "duplicate_tick":
        original = "".join(rows[:3] + [rows[2]] + rows[3:])
    elif mutation == "different_run_tick":
        original = original.replace("run_id=" + RUN_ID,
                                    "run_id=" + FOREIGN, 2)
    elif mutation == "bad_run_id":
        original = original.replace("run_id=" + RUN_ID, "run_id=invalid", 1)
    elif mutation == "last_tick":
        original = original.replace("last_tick=78", "last_tick=79")
    elif mutation == "abort":
        original += "S49_DEV_BACK_WAIT_ABORT reason=PLUGIN_DISABLED\n"
    elif mutation == "false_clear":
        original = original.replace("UNATTESTED_CONSOLE_CLAIM", "ATTESTED", 1)
    elif mutation == "false_authority":
        original = original.replace("authority=NONE", "authority=GRANTED")
    elif mutation == "false_recovery":
        original = original.replace("p1_recovery=NONE", "p1_recovery=YES")
    elif mutation == "bad_sample_count":
        original = original.replace("samples=8", "samples=9")
    elif mutation == "old_s50":
        original = original.replace("S49_DEV_BACK_WAIT_TICK", "S50_PAPER_TICK")
    else:
        original = raw_paper(capture)
    with pytest.raises(BoundaryRejected):
        review(capture, original, player=player)


def test_unmodified_nine_row_projection_remains_nonadmitting(
    monkeypatch, tmp_path,
):
    capture = typed_owner(monkeypatch)
    nine = "".join(
        line.rstrip("\n") + f" run_id={RUN_ID}\n"
        for line in raw_paper(capture).splitlines(keepends=True)
    )
    report = run(capture, nine, tmp_path / "legacy-shape.json")
    assert report["status"] == "SAME_ACTION_PAPER_SHAPE_ONLY"
    assert report["source_bound_tick"] is None
    assert report["wait_ticks_admitted"] == 0
    assert report["p1_fatigue_recovered"] == 0.0


def test_original_s16_tamper_and_cancel_fail_closed(monkeypatch):
    capture = typed_owner(monkeypatch)
    paper = transcript(capture)
    capture.projection.decoded_evidence["cleanup_receipt"]["result"] = "rejected"
    with pytest.raises(BoundaryRejected):
        review(capture, paper)
    other = typed_owner(monkeypatch)
    paper = transcript(other)
    other._state = "FAILED"
    with pytest.raises(BoundaryRejected):
        review(other, paper)


def test_prefixed_paper_lines_are_not_attested(monkeypatch):
    capture = typed_owner(monkeypatch)
    paper = "".join(
        "[Paper INFO] " + line
        for line in transcript(capture).splitlines(keepends=True)
    )
    result = review(capture, paper)
    assert result["status"] == "ONE_RUN_TRANSCRIPT_SHAPE_ONLY"
    assert result["source_authentication"] == "UNATTESTED_PAPER_LOG_TEXT"
    assert result["wait_interval_ref"] is None


def callback_slice(transcript_text):
    return "\n".join(transcript_text.splitlines()[1:-1]) + "\n"


def test_full_transcript_is_persisted_with_owner_wait_shape(
    monkeypatch, tmp_path,
):
    capture = typed_owner(monkeypatch)
    original = transcript(capture)
    result = asyncio.run(project_s49_backward_paper_dev(
        capture, callback_slice(original), output_path=tmp_path / "joined.json",
        observer_transcript=original, expected_player_uuid=PLAYER,
    ))
    saved = json.loads((tmp_path / "joined.json").read_text())
    assert saved == result
    assert saved["status"] == "SAME_ACTION_PAPER_SHAPE_ONLY"
    assert saved["observer_transcript_review"]["observer_run_id"] == RUN_ID
    assert saved["observer_transcript_review"]["sample_count"] == 8
    assert saved["observer_transcript_review"]["source_authentication"] == (
        "UNATTESTED_PAPER_LOG_TEXT"
    )
    assert capture._executor.wait_phase == "SEALED"
    assert saved["source_bound_tick"] is None
    assert saved["wait_interval_ref"] is None
    assert saved["wait_ticks_admitted"] == 0
    assert saved["p1_fatigue_recovered"] == 0.0


@pytest.mark.parametrize("mutation", ["different_tick", "wrong_player", "truncated"])
def test_full_transcript_and_callback_slice_must_agree(
    monkeypatch, tmp_path, mutation,
):
    capture = typed_owner(monkeypatch)
    original = transcript(capture)
    segment = callback_slice(original)
    player = PLAYER
    if mutation == "different_tick":
        segment = segment.replace("tick=74 index=4", "tick=75 index=4", 1)
    elif mutation == "wrong_player":
        player = FOREIGN
    else:
        original = original.replace("samples=8", "samples=7")
    destination = tmp_path / "rejected.json"
    with pytest.raises(BoundaryRejected):
        asyncio.run(project_s49_backward_paper_dev(
            capture, segment, output_path=destination,
            observer_transcript=original, expected_player_uuid=player,
        ))
    report = json.loads(destination.read_text())
    assert report["status"] == "REJECTED_NOT_QUALIFIED"
    assert report["source_bound_tick"] is None
    assert report["wait_interval_ref"] is None
    assert report["wait_ticks_admitted"] == 0
    assert report["p1_fatigue_recovered"] == 0.0
