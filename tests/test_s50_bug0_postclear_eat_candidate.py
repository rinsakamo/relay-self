"""Offline S50 original-reader reuse for Bug-0 EAT; no World or Action."""

import hashlib
from dataclasses import replace

import pytest

import test_s50_input_witness_source as inputs
import test_s50_p1_wait as wait
from adapters.mineflayer.m02_paper_dev.s50_bug0_postclear_eat_candidate import (
    ACTIVITY_OBSERVED,
    QUIET_CANDIDATE,
    S50Bug0PostClearRejected,
    review_s50_bug0_postclear_candidate,
)

START = 40


def source(*, moving_tick=0, new_event_tick=0, sprint_tick=0):
    # Reuse both existing S50 test fixtures, not a parallel low-level
    # Paper log parser or a fabricated authenticated STOP grant.
    w = wait.fixture().replace(
        "marker_id=action-session", "marker_id=" + inputs.MARKER,
    ).replace("world=world", "world=" + inputs.WORLD)
    if sprint_tick:
        lines = w.splitlines()
        lines[sprint_tick] = lines[sprint_tick].replace(
            "sprint=false", "sprint=true",
        )
        w = "\n".join(lines)
    packet = inputs.fixture(
        moving_tick=moving_tick, new_event_tick=new_event_tick,
    ).decode("utf-8")
    for index in range(1, 9):
        packet = packet.replace(
            f"tick={inputs.START + index} index={index}",
            f"tick={START + index} index={index}",
        )
    if new_event_tick:
        packet = packet.replace(
            f"last_input_event_tick={inputs.START + new_event_tick}",
            f"last_input_event_tick={START + new_event_tick}",
        )
    return (w + "\n" + packet).encode("utf-8")


def review(data, *, marker=inputs.MARKER, world=inputs.WORLD,
           subject=inputs.SUBJECT, begin=START, terminal="outcome"):
    return review_s50_bug0_postclear_candidate(
        data, marker_id=marker, world=world, subject_uuid=subject,
        wait_begin_tick=begin, source_action_terminal=terminal,
    )


def test_two_existing_s50_samplers_join_but_never_prove_stop_or_authorize_eat():
    original = source()
    row = review(original)
    assert row.first_tick == 41 and row.last_tick == 48
    assert row.paper_original_sha256 == hashlib.sha256(original).hexdigest()
    assert row.sample_status == QUIET_CANDIDATE
    assert row.sampled_input_active_ticks == ()
    assert row.sampled_body_activity_ticks == ()
    assert row.input_event_count_final == 0
    assert row.effective_s15_clear_tick == "NOT_ATTESTED"
    assert row.complete_tick_input_coverage is False
    assert row.source_authenticated_independently is False
    assert row.physically_stopped_proven is False
    assert row.eat_action_authorized is False
    assert row.p1_wait_ticks_admitted == 0
    assert row.learning_updates == 0


@pytest.mark.parametrize("case", ["input_on", "input_event", "sprint"])
def test_mismatched_activity_is_reported_as_no_wait_and_never_grants(case):
    raw = (
        source(moving_tick=3) if case == "input_on" else
        source(new_event_tick=3) if case == "input_event" else
        source(sprint_tick=3)
    )
    row = review(raw)
    assert row.sample_status == ACTIVITY_OBSERVED
    assert (
        row.sampled_input_active_ticks
        or row.sampled_body_activity_ticks
        or row.input_event_count_final
    )
    assert not row.physically_stopped_proven
    assert not row.eat_action_authorized
    assert row.p1_wait_ticks_admitted == 0


@pytest.mark.parametrize("fault", [
    "wrong_marker", "wrong_world", "wrong_subject", "wrong_tick",
    "gapped_wait", "duplicated_input", "truncated_input", "false_clear",
    "wrong_coverage", "foreign_tick", "bad_utf8", "no_action",
    "source_overflow", "duplicate_wait", "foreign_subject_argument",
])
def test_no_unsafe_source_join_on_missing_or_cross_session_paper(fault):
    raw = source()
    marker = inputs.MARKER
    world = inputs.WORLD
    subject = inputs.SUBJECT
    begin = START
    terminal = "outcome"
    if fault == "wrong_marker":
        raw = raw.replace(f"marker_id={marker}".encode(), b"marker_id=foreign", 1)
    elif fault == "wrong_world":
        raw = raw.replace(f"world={world}".encode(), b"world=foreign", 1)
    elif fault == "wrong_subject":
        raw = raw.replace(f"subject_uuid={subject}".encode(), b"subject_uuid=foreign", 1)
    elif fault == "wrong_tick":
        begin += 1
    elif fault == "gapped_wait":
        raw = raw.replace(b"tick=43 index=3", b"tick=44 index=3", 1)
    elif fault == "duplicated_input":
        raw += raw.splitlines(keepends=True)[-1]
    elif fault == "truncated_input":
        raw = b"\n".join(raw.splitlines()[:-1]) + b"\n"
    elif fault == "false_clear":
        raw = raw.replace(
            b"effective_s15_clear_tick=NOT_ATTESTED",
            b"effective_s15_clear_tick=252", 1,
        )
    elif fault == "wrong_coverage":
        raw = raw.replace(
            b"coverage=LAST_REPORTED_INPUT_CALLBACK_SAMPLE_ONLY",
            b"coverage=FULL_TICK_ATTESTED", 1,
        )
    elif fault == "foreign_tick":
        raw = raw.replace(b"tick=44 index=4", b"tick=99 index=4", 1)
    elif fault == "bad_utf8":
        raw = b"\xff" + raw
    elif fault == "no_action":
        terminal = "unknown"
    elif fault == "source_overflow":
        raw = b"x" * (16_000_000 + 1)
    elif fault == "duplicate_wait":
        raw += (wait.fixture().splitlines()[-1] + "\n").encode()
    elif fault == "foreign_subject_argument":
        subject = "different-subject"
    with pytest.raises(S50Bug0PostClearRejected):
        review(raw, marker=marker, world=world,
               subject=subject, begin=begin, terminal=terminal)


@pytest.mark.parametrize("field,value", [
    ("physically_stopped_proven", True),
    ("eat_action_authorized", True),
    ("complete_tick_input_coverage", True),
    ("p1_wait_ticks_admitted", 8),
])
def test_join_does_not_offer_mutable_authority_even_if_caller_edits_copy(
    field, value,
):
    row = review(source())
    forged = replace(row, **{field: value})
    assert forged is not row
    # No S49/S51/P1 API accepts this readback as an Action grant.
    # It is NOT a signed or attested capability; reject use by convention.
    assert row.eat_action_authorized is False
    assert row.physically_stopped_proven is False
