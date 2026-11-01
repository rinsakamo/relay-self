"""MP11 L live prefix read-only boundaries, using synthetic Paper text ONLY."""
from __future__ import annotations

import json
from dataclasses import replace

import pytest

from adapters.mineflayer.l_mp11_live_previous_action import (
    LivePriorLedger, LivePriorRejected,
)
from test_self_body_s50_l2_mp11_paper_audit import segment

WORLD = "original-constant-world-uuid"
SUBJECT = "subject-constant-uuid"
SESSION = "session"
ACTIONS = (
    "s49-native-move-11", "s49-native-move-18", "s49-native-move-26",
)
MARKERS = tuple(f"{name}-{SESSION}" for name in ACTIONS)


def snapshot(n: int = 1) -> bytes:
    text = []
    for i in range(n):
        text.extend(segment(MARKERS[i], "GRASS_BLOCK", start=100 + i*100))
    return ("\n".join(text) + "\n").encode()


def new_ledger() -> LivePriorLedger:
    return LivePriorLedger(session_id=SESSION, world_uuid=WORLD, subject_uuid=SUBJECT)


def accept(ledger: LivePriorLedger, n: int, *, raw: bytes | None = None):
    return ledger.accept_completed(
        snapshot(n) if raw is None else raw,
        action_id=ACTIONS[n-1], marker_id=MARKERS[n-1],
        native_s16_seq=25*n, native_outcome="S16_OUTCOME",
    )


def test_three_sequential_bounded_live_previous_action_sources():
    ledger = new_ledger()
    with pytest.raises(LivePriorRejected):
        ledger.model_request()
    for i in range(1, 4):
        w = accept(ledger, i)
        assert w.ordinal == i
        assert w.paper_wait_ticks == tuple(range(100+(i-1)*100,108+(i-1)*100))
        assert w.paper_wait_total_m == pytest.approx(.4)
        assert w.native_s16_seq == i*25
        assert w.source_status == "LIVE_PAPER_PREFIX_UNSEALED_S49_TYPED_S16_CLAIM"
        assert w.action_or_learning_authority is False
        assert w.original_paper_input_clear_tick_attested is False
        req = ledger.model_request()
        assert req.focus == "LIVE_PREVIOUS_S49_ACTION_SOURCE_L2_CONTEXT_ONLY"
        history = json.loads(req.context[1].value_json)
        assert len(history) == i
        assert [x["action_id"] for x in history] == list(ACTIONS[:i])
        assert len({x["paper_prefix_sha256"] for x in history}) == i
        limits = json.loads(req.context[0].value_json)
        assert limits["actual_l2_calls"] == 0
        assert limits["learning_admissions"] == 0
        assert limits["paper_original_verified_after_exit"] is False
    with pytest.raises(LivePriorRejected):
        accept(ledger, 3)


@pytest.mark.parametrize("bad", [
    "foreign_world", "foreign_subject", "wrong_surface",
    "missing_wait", "missing_score", "wrong_phase",
    "wrong_tick", "nonfinite", "early_future_marker",
    "incomplete_utf8", "partial_line", "extra_future",
])
def test_invalid_live_paper_source_never_admitted(bad):
    ledger = new_ledger()
    raw = snapshot(1)
    text = raw.decode()
    if bad == "foreign_world":
        text = text.replace(f"world={WORLD}", "world=wrong-world", 1)
    elif bad == "foreign_subject":
        text = text.replace(f"subject_uuid={SUBJECT}", "subject_uuid=foreign", 1)
    elif bad == "wrong_surface":
        text = text.replace("target_material=GRASS_BLOCK", "target_material=PACKED_ICE", 1)
    elif bad == "missing_wait":
        text = text.replace("S50_DEV_WAIT_TICK ", "NOT_A_WAIT_TICK ", 1)
    elif bad == "missing_score":
        text = text.replace("S50_DEV_LOCAL_FORECAST_SCORE ", "NOT_A_SCORE ", 1)
    elif bad == "wrong_phase":
        text = text.replace("phase=PRE_FORWARD", "phase=POST_CLEAR", 1)
    elif bad == "wrong_tick":
        text = text.replace("tick=101 index=2", "tick=111 index=2", 1)
    elif bad == "nonfinite":
        text = text.replace("from_x=0.5", "from_x=nan", 1)
    elif bad == "early_future_marker":
        text += f"M02_DEV_S50_PHASE marker_id={MARKERS[1]} world={WORLD} phase=PRE_FORWARD\n"
    elif bad == "extra_future":
        text += f"S50_DEV_WAIT_TICK marker_id={MARKERS[2]} world={WORLD} index=1 tick=900\n"
    if bad == "incomplete_utf8":
        raw = text.encode() + b"\xff\n"
    elif bad == "partial_line":
        raw = text.encode().rstrip(b"\n")
    else:
        raw = text.encode()
    with pytest.raises(LivePriorRejected):
        accept(ledger, 1, raw=raw)
    assert not ledger.history


@pytest.mark.parametrize("bad", [
    "wrong_action", "wrong_marker", "stale_s16", "unknown_s16",
    "partial_previous", "mutated_previous", "replay_action",
    "foreign_second_marker", "nonmonotonic_s16",
])
def test_second_trial_guard_and_owner_scope(bad):
    ledger = new_ledger()
    accept(ledger, 1)
    args = dict(action_id=ACTIONS[1],marker_id=MARKERS[1],
                native_s16_seq=50,native_outcome="S16_OUTCOME")
    raw = snapshot(2)
    if bad == "wrong_action":
        args["action_id"] = "foreign-action"
    elif bad == "wrong_marker":
        args["marker_id"] = MARKERS[0]
    elif bad == "stale_s16":
        args["native_s16_seq"] = 25
    elif bad == "unknown_s16":
        args["native_outcome"] = "S16_UNKNOWN"
    elif bad == "partial_previous":
        raw = snapshot(2)[len(snapshot(1)):]
    elif bad == "mutated_previous":
        raw = raw.replace(b"tick=100", b"tick=101", 1)
    elif bad == "replay_action":
        args["action_id"] = ACTIONS[0]
        args["marker_id"] = MARKERS[0]
    elif bad == "foreign_second_marker":
        raw = raw.replace(MARKERS[1].encode(), b"foreign-2")
    elif bad == "nonmonotonic_s16":
        args["native_s16_seq"] = 2
    with pytest.raises(LivePriorRejected):
        ledger.accept_completed(raw,**args)
    assert len(ledger.history) == 1


def test_observed_source_cannot_impersonate_original_attestation_or_action():
    ledger = new_ledger()
    source = accept(ledger, 1)
    # Data object modification has no authority over the append-only ledger.
    forged = replace(source, original_paper_input_clear_tick_attested=True,
                     action_or_learning_authority=True)
    assert forged != ledger.history[0]
    assert ledger.model_request().context[1].provenance.source == (
        "l.mp11.live.paper.prefix"
    )
    assert "paper_original_verified_after_exit" in (
        ledger.model_request().context[0].value_json
    )
