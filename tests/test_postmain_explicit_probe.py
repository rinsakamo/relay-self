"""S28: single explicit Mineflayer observe/receive seam, no autonomous loop."""
from __future__ import annotations

import asyncio
import json
from collections import deque
from dataclasses import replace
from pathlib import Path

import pytest

import test_postmain_source_native_world as s27
from relay_self.action import ActionState
from relay_self.explicit_probe import (
    ExclusiveProbeCursor,
    ExplicitProbeAuthority,
    InvalidExplicitProbe,
    request_explicit_post_action_probe,
)
from relay_self.postfailure_cognition import run_explicit_postfailure_epoch
from relay_self.skill import SkillState

ROOT = Path(__file__).resolve().parents[1]


class ProbeSession:
    """Exclusive deterministic adapter transport double, not a live endpoint."""

    def __init__(self, parent, frames=(), *, mode="normal"):
        self.started = replace(
            s27.s23.s20.s19.FakeSession(()).started,
            session_id=parent.session_id,
        )
        self.frames = deque(frames)
        self.mode = mode
        self.sent = 0
        self.read = 0

    async def send_observe(self):
        self.sent += 1
        if self.mode == "send_error":
            raise RuntimeError("simulated send error")

    async def receive(self):
        self.read += 1
        if self.mode == "timeout" or not self.frames:
            await asyncio.sleep(1)
            raise RuntimeError("should time out first")
        return self.frames.popleft()


def _subject(*, distance=1.8, seq=5, messages=None, mode="normal"):
    data, failed, inputs, args = s27._fixture(distance_m=distance, seq=seq)
    parent = args["consequence"]
    adapter = ProbeSession(
        parent, frames=(args["observation"],) if messages is None else messages,
        mode=mode,
    )
    cursor = ExclusiveProbeCursor(
        session_id=parent.session_id,
        next_seq=parent.after_observation.seq + 1,
    )
    authority = ExplicitProbeAuthority(
        authority_id="s28-caller-probe-once",
        session_id=parent.session_id,
        parent_action_id=args["action"].action_id,
        target_entity_id=s27.ENTITY_ID,
        target_name="zombie",
        granted=True,
        provenance=s27.s23.p("s28-explicit-probe-lease"),
    )
    kwargs = {
        "adapter": adapter,
        "cursor": cursor,
        "authority": authority,
        "supervisor": data["supervisor"],
        "action": args["action"],
        "consequence": parent,
        "observed_at_ns": 65,
        "inspected_at_ns": 67,
        "max_age_ns": 5,
        "timeout_s": 0.05,
        "max_frames": 4,
    }
    return data, failed, inputs, args, kwargs


def _run(kwargs, **changes):
    return asyncio.run(
        request_explicit_post_action_probe(**{**kwargs, **changes})
    )


def test_single_explicit_observe_roundtrip_delivers_source_native_evidence_to_s24():
    for distance, choice, cm in ((0.2, "MOVE_AWAY", 20), (1.8, "WAIT", 180)):
        data, failed, inputs, args, kwargs = _subject(distance=distance)
        assert kwargs["adapter"].sent == 0
        assert data["supervisor"].open_actions == ()
        roundtrip = _run(kwargs)
        assert roundtrip.source_receipt.evidence.threat_clearance_cm == cm
        assert roundtrip.probe_seq == 5
        assert roundtrip.request_cursor_seq == 5
        assert roundtrip.received_count == 1
        assert roundtrip.authority_id == "s28-caller-probe-once"
        assert roundtrip.source_receipt.source.provenance.reference == f"{s27.s23.SESSION3}:5"
        assert kwargs["adapter"].sent == 1
        assert kwargs["adapter"].read == 1
        assert kwargs["cursor"].consumed is True
        assert data["supervisor"].last_at_ns == 60

        trace = run_explicit_postfailure_epoch(
            data["supervisor"], args["action"], args["consequence"],
            inputs["recovery_skill"], data["intent"], data["commit"].new_state,
            roundtrip.source_receipt.evidence,
            at_ns=70,
            provenance=s27.s23.p("s28-explicit-third-epoch"),
        )
        assert trace.selected_candidate == choice
        assert roundtrip.source_receipt.evidence.provenance in trace.source_provenance
        assert data["supervisor"].open_actions == ()
        assert failed.state is SkillState.FAILED
        assert inputs["recovery_skill"].state is SkillState.STARTED
        assert data["commit"].new_state.value == 4
        for action_id in (
            data["closed1"].action_id, s27.s23.s20.ACTION2,
            s27.s23.ACTION3,
        ):
            assert data["supervisor"].get(action_id).state is ActionState.OUTCOME

    document = json.loads(
        (ROOT / "docs/postmain-s28-observe-roundtrip.json").read_text(encoding="utf-8")
    )
    assert document["near"]["distance_cm"] == 20
    assert document["near"]["selection"] == "MOVE_AWAY"
    assert document["far"]["distance_cm"] == 180
    assert document["far"]["selection"] == "WAIT"


def test_contiguous_nonprobe_frame_can_precede_explicit_probe():
    data, _failed, _inputs, args, kwargs = _subject(seq=6)
    before_probe = replace(args["observation"], seq=5, kind="entities")
    kwargs["adapter"].frames = deque((before_probe, args["observation"]))
    receipt = _run(kwargs)
    assert receipt.received_count == 2
    assert receipt.probe_seq == 6
    assert receipt.source_receipt.source.kind == "probe"
    assert kwargs["adapter"].sent == 1
    assert kwargs["adapter"].read == 2
    assert data["supervisor"].open_actions == ()


def test_one_shot_cursor_reuse_rejected_before_second_send():
    data, _failed, _inputs, _args, kwargs = _subject()
    _run(kwargs)
    with pytest.raises(InvalidExplicitProbe):
        _run(kwargs)
    assert kwargs["adapter"].sent == 1
    assert kwargs["adapter"].read == 1
    assert data["supervisor"].open_actions == ()


@pytest.mark.parametrize(
    "field,variant",
    [
        ("cursor", "wrong_session"),
        ("cursor", "old_seq"),
        ("cursor", "future_seq"),
        ("cursor", "consumed"),
        ("authority", "missing"),
        ("authority", "denied"),
        ("authority", "wrong_session"),
        ("authority", "wrong_action"),
        ("action", "wrong_action"),
        ("consequence", "nonexecuted"),
        ("adapter", "different_started"),
        ("observed_at_ns", "before_terminal"),
        ("inspected_at_ns", "future_time"),
        ("inspected_at_ns", "too_old"),
        ("max_age_ns", "zero"),
        ("timeout_s", "zero_timeout"),
        ("max_frames", "too_many"),
    ],
)
def test_invalid_probe_preflight_does_not_send(field, variant):
    data, _failed, _inputs, _args, kwargs = _subject()
    source = kwargs[field]
    if variant == "wrong_session":
        source = replace(source, session_id="other-session")
    elif variant == "old_seq":
        source = replace(source, next_seq=4)
    elif variant == "future_seq":
        source = replace(source, next_seq=7)
    elif variant == "consumed":
        source = replace(source, consumed=True)
    elif variant == "missing":
        source = None
    elif variant == "denied":
        source = replace(source, granted=False)
    elif variant == "wrong_action" and field == "authority":
        source = replace(source, parent_action_id="some-other-action")
    elif variant == "wrong_action":
        source = data["closed1"]
    elif variant == "nonexecuted":
        source = replace(source, status=type(source.status).UNDETERMINED)
    elif variant == "different_started":
        source.started = replace(source.started, session_id="not-the-current-session")
    elif variant == "before_terminal":
        source = 60
    elif variant == "future_time":
        source = 64
    elif variant == "too_old":
        source = 71
    elif variant == "zero":
        source = 0
    elif variant == "zero_timeout":
        source = 0
    elif variant == "too_many":
        source = 17
    else:
        raise AssertionError(variant)
    with pytest.raises(InvalidExplicitProbe):
        _run(kwargs, **{field: source})
    assert kwargs["adapter"].sent == 0
    assert kwargs["cursor"].consumed is False
    assert data["supervisor"].open_actions == ()


@pytest.mark.parametrize(
    "variant",
    [
        "wrong_session", "replay_seq", "gap_seq", "untyped", "wrong_target",
        "nonprobe_only", "excess_nonprobes", "timeout", "send_error",
    ],
)
def test_bad_or_missing_response_consumes_one_shot_without_projection(variant):
    data, _failed, _inputs, args, kwargs = _subject()
    source = args["observation"]
    if variant == "wrong_session":
        kwargs["adapter"].frames = deque((replace(source, session_id="other-session"),))
    elif variant == "replay_seq":
        kwargs["adapter"].frames = deque((replace(source, seq=4),))
    elif variant == "gap_seq":
        kwargs["adapter"].frames = deque((replace(source, seq=6),))
    elif variant == "untyped":
        kwargs["adapter"].frames = deque(({"type": "observation", "seq": 5},))
    elif variant == "wrong_target":
        empty = replace(
            source.snapshot,
            nearby_entities=(),
            nearby_entities_coverage=replace(
                source.snapshot.nearby_entities_coverage, candidate_count=0
            ),
        )
        kwargs["adapter"].frames = deque((replace(source, snapshot=empty),))
    elif variant == "nonprobe_only":
        kwargs["adapter"].frames = deque((replace(source, kind="entities"),))
        kwargs["max_frames"] = 1
    elif variant == "excess_nonprobes":
        kwargs["adapter"].frames = deque(
            replace(source, kind="entities", seq=5 + i)
            for i in range(4)
        )
    elif variant in ("timeout", "send_error"):
        kwargs["adapter"].mode = variant
    else:
        raise AssertionError(variant)
    with pytest.raises((InvalidExplicitProbe, ValueError, RuntimeError)):
        _run(kwargs)
    assert kwargs["cursor"].consumed is True
    assert kwargs["adapter"].sent == 1
    assert data["supervisor"].open_actions == ()


def test_probe_does_not_imply_action_issue_or_autonomous_reentry():
    data, _failed, _inputs, _args, kwargs = _subject()
    previous_time = data["supervisor"].last_at_ns
    _run(kwargs)
    assert data["supervisor"].last_at_ns == previous_time == 60
    assert data["supervisor"].open_actions == ()
    assert data["supervisor"].advance(
        at_ns=67, provenance=s27.s23.p("s28-no-invisible-reentry"),
    ) == ()


def test_s28_receipt_preserves_protocol_limit():
    receipt = json.loads(
        (ROOT / "docs/postmain-s28-receipt.json").read_text(encoding="utf-8")
    )
    assert receipt["base_head"] == "f40c690cf7df005be4a69fe1cd57bb0d29c1070a"
    assert receipt["classification"] == "SERIALIZED_EXPLICIT_MINEFLAYER_PROBE_ROUNDTRIP_QUALIFIED"
    assert receipt["wire_request_id_available"] is False
    assert receipt["causal_request_response_proven"] is False
    assert receipt["live_minecraft"] == "NOT_RUN"
    assert receipt["automatic_epoch_reentry"] is False
