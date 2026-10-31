"""S50 DEV-only input readback: synthetic Paper rows, never real idle proof."""
from __future__ import annotations

from pathlib import Path

import pytest

from adapters.mineflayer.m02_paper_dev.s50_input_witness_source import (
    S50InputWitnessRejected,
    review_s50_input_samples,
)

MARKER = "s49-native-move-18-session"
WORLD = "paper-world"
SUBJECT = "paper-subject"
START = 249
ROOT = Path(__file__).resolve().parents[1]
JAVA = ROOT / (
    "adapters/mineflayer/m02_paper_dev/src/main/java/"
    "io/github/rinsakamo/relaymetabolism/RelayMetabolismPlugin.java"
)
CONFIG = ROOT / "adapters/mineflayer/m02_paper_dev/src/main/resources/config.yml"


def fixture(*, moving_tick: int = 0, new_event_tick: int = 0) -> bytes:
    rows = []
    for index in range(1, 9):
        tick = START + index
        new_event = new_event_tick != 0 and index >= new_event_tick
        fields = {
            "marker_id": MARKER, "world": WORLD, "subject_uuid": SUBJECT,
            "tick": tick, "index": index,
            "input_events": int(new_event),
            "last_input_event_tick": START + new_event_tick if new_event else -1,
            "event_overflow": "false",
            "forward": "true" if index == moving_tick else "false",
            "backward": "false", "left": "false", "right": "false",
            "jump": "false", "sneak": "false", "sprint": "false",
            "coverage": "LAST_REPORTED_INPUT_CALLBACK_SAMPLE_ONLY",
            "effective_s15_clear_tick": "NOT_ATTESTED",
        }
        rows.append("[INFO] S50_DEV_INPUT_TICK " + " ".join(
            f"{k}={v}" for k, v in fields.items()
        ).replace("event_overflow=False", "event_overflow=false"))
    return ("\n".join(rows) + "\n").encode()


def review(original):
    return review_s50_input_samples(
        original, marker_id=MARKER, world=WORLD,
        subject_uuid=SUBJECT, start_tick=START,
    )


def test_quiet_sampled_input_never_becomes_complete_physical_idle():
    witness = review(fixture())
    assert witness.first_tick == 250 and witness.last_tick == 257
    assert witness.sampled_input_active_ticks == ()
    assert witness.input_event_count_final == 0
    assert not witness.input_event_observed
    assert witness.effective_client_clear_tick == "NOT_ATTESTED"
    assert not witness.entire_tick_input_idle
    assert not witness.physical_stability_verified
    assert not witness.goal_admitted
    assert witness.p1_wait_ticks_admitted == witness.l10_episodes_admitted == 0


def test_nonzero_input_and_update_are_diagnostic_not_action_authority():
    witness = review(fixture(moving_tick=3, new_event_tick=3))
    assert witness.sampled_input_active_ticks == (252,)
    assert witness.input_event_count_final == 1
    assert witness.input_event_observed
    assert not witness.entire_tick_input_idle
    assert witness.effective_client_clear_tick == "NOT_ATTESTED"


@pytest.mark.parametrize("fault", [
    "truncated", "duplicate", "gap", "wrong_world", "wrong_marker",
    "wrong_subject", "negative_events", "regressed_events",
    "future_event", "unknown_flag", "overflow", "wrong_coverage",
    "false_clear", "duplicate_field", "reversed",
])
def test_incomplete_foreign_or_unauthorized_source_is_rejected(fault):
    raw = fixture(new_event_tick=3)
    rows = raw.splitlines(keepends=True)
    if fault == "truncated":
        raw = b"".join(rows[:-1])
    elif fault == "duplicate":
        raw += rows[-1]
    elif fault == "gap":
        raw = raw.replace(b"tick=253 index=4", b"tick=255 index=4")
    elif fault == "wrong_world":
        raw = raw.replace(b"world=paper-world", b"world=wrong", 1)
    elif fault == "wrong_marker":
        raw = raw.replace(f"marker_id={MARKER}".encode(), b"marker_id=wrong", 1)
    elif fault == "wrong_subject":
        raw = raw.replace(b"subject_uuid=paper-subject", b"subject_uuid=wrong", 1)
    elif fault == "negative_events":
        raw = raw.replace(b"input_events=1", b"input_events=-2", 1)
    elif fault == "regressed_events":
        raw = raw.replace(b"tick=254 index=5 input_events=1",
                          b"tick=254 index=5 input_events=0", 1)
    elif fault == "future_event":
        raw = raw.replace(b"last_input_event_tick=252",
                          b"last_input_event_tick=999", 1)
    elif fault == "unknown_flag":
        raw = raw.replace(b"forward=false", b"forward=unknown", 1)
    elif fault == "overflow":
        raw = raw.replace(b"event_overflow=false", b"event_overflow=true", 1)
    elif fault == "wrong_coverage":
        raw = raw.replace(b"LAST_REPORTED_INPUT_CALLBACK_SAMPLE_ONLY",
                          b"ENTIRE_TICK_INPUT_IDLE", 1)
    elif fault == "false_clear":
        raw = raw.replace(b"effective_s15_clear_tick=NOT_ATTESTED",
                          b"effective_s15_clear_tick=252", 1)
    elif fault == "duplicate_field":
        raw = raw.replace(b"index=1 ", b"index=1 index=1 ", 1)
    elif fault == "reversed":
        rows[1], rows[2] = rows[2], rows[1]
        raw = b"".join(rows)
    with pytest.raises(S50InputWitnessRejected):
        review(raw)


def test_java_source_is_gated_observation_not_alternative_actuator():
    source = JAVA.read_text()
    config = CONFIG.read_text()
    assert "s50-input-witness-dev: false" in config
    assert "getCurrentInput()" in source
    assert "onS50InputUpdate(PlayerInputEvent event)" in source
    assert "S50_DEV_INPUT_TICK marker_id=" in source
    assert "S50_DEV_INPUT_EVENT marker_id=" in source
    assert "S50_DEV_INPUT_OVERFLOW marker_id=" in source
    assert "effective_s15_clear_tick=NOT_ATTESTED" in source
    assert "coverage=LAST_REPORTED_INPUT_CALLBACK_SAMPLE_ONLY" in source
