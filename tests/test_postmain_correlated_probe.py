"""S29: exact cross-language correlated probe ID and bounded sequential receipts."""
from __future__ import annotations

import asyncio
import json
from collections import deque
from dataclasses import replace
from pathlib import Path

import pytest

import test_mineflayer_process_session as process_fixture
import test_postmain_explicit_probe as s28
import test_postmain_source_native_world as s27
from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import (
    MineflayerAdapterProtocolError,
    MineflayerObservation,
    MineflayerStreamDecoder,
    encode_observe,
    parse_mineflayer_line,
)
from relay_self.correlated_probe import (
    CorrelatedProbeGrant,
    CorrelatedProbeReceipt,
    InvalidCorrelatedProbe,
    request_correlated_post_action_probe,
)
from relay_self.explicit_probe import ExclusiveProbeCursor
from relay_self.postfailure_cognition import run_explicit_postfailure_epoch

ROOT = Path(__file__).resolve().parents[1]
REQUEST1 = "s29-probe:one.1"
REQUEST2 = "s29-probe:two.2"


class CorrelatedSession(s28.ProbeSession):
    def __init__(self, parent, frames=(), *, mode="normal"):
        super().__init__(parent, frames, mode=mode)
        self.sent_ids: list[str | None] = []

    async def send_observe(self, request_id: str | None = None):
        self.sent_ids.append(request_id)
        await super().send_observe()


def _subject(*, distance=0.2, request_id=REQUEST1, seq=5, mode="normal"):
    data, failed, inputs, args, earlier = s28._subject(
        distance=distance, seq=seq, mode=mode,
    )
    message = replace(args["observation"], request_id=request_id)
    adapter = CorrelatedSession(args["consequence"], (message,), mode=mode)
    grant = CorrelatedProbeGrant(
        authority=earlier["authority"], request_id=request_id,
    )
    kwargs = {
        "adapter": adapter,
        "cursor": earlier["cursor"],
        "grant": grant,
        "supervisor": data["supervisor"],
        "action": args["action"],
        "consequence": args["consequence"],
        "observed_at_ns": 65,
        "inspected_at_ns": 67,
        "max_age_ns": 5,
        "timeout_s": 0.05,
        "max_frames": 4,
    }
    return data, failed, inputs, args, kwargs


def _run(kwargs, **changes):
    return asyncio.run(request_correlated_post_action_probe(**{**kwargs, **changes}))


def _response_wire(message):
    raw = json.loads(s27._wire_message(message))
    if message.request_id is not None:
        raw["request_id"] = message.request_id
    return json.dumps(raw)


def test_node_python_correlated_shape_and_legacy_observe_are_both_valid():
    assert json.loads(encode_observe()) == {"type": "observe"}
    assert json.loads(encode_observe(REQUEST1)) == {
        "type": "observe", "request_id": REQUEST1,
    }
    _, _, _, args, _kwargs = _subject()
    original = args["observation"]
    raw = _response_wire(replace(original, request_id=REQUEST1))
    decoded = parse_mineflayer_line(raw)
    assert isinstance(decoded, MineflayerObservation)
    assert decoded.request_id == REQUEST1
    assert decoded.provenance.reference == f"{s27.s23.SESSION3}:5"
    legacy = parse_mineflayer_line(s27._wire_message(original))
    assert isinstance(legacy, MineflayerObservation)
    assert legacy.request_id is None

    decoder = MineflayerStreamDecoder()
    decoder.decode(json.dumps({
        "type": "adapter_started", "session_id": original.session_id, "seq": 0,
        "mineflayer_version": s27.MINEFLAYER_VERSION,
        "config": {
            "host": "127.0.0.1", "port": 25565,
            "username": "RelaySelf", "version": None,
        },
    }))
    parent = args["consequence"]
    for previous in (
        parent.before_observation, parent.dispatch_receipt,
        parent.cleanup_receipt, parent.after_observation,
    ):
        decoder.decode(s27._wire_message(previous))
    assert decoder.decode(raw).request_id == REQUEST1
    with pytest.raises(MineflayerAdapterProtocolError):
        decoder.decode(raw)


def test_process_session_sends_new_wire_request_id_without_changing_old_default():
    process = process_fixture.FakeProcess([])
    session = MineflayerProcessSession(process)
    async def scenario():
        await session.send_observe()
        await session.send_observe(REQUEST1)
    asyncio.run(scenario())
    assert [json.loads(x) for x in process.stdin.writes] == [
        {"type": "observe"},
        {"type": "observe", "request_id": REQUEST1},
    ]


@pytest.mark.parametrize("invalid", [
    "", "with spaces", "日本語", "../?", "a" * 129, "comma,id", 2, True, [],
])
def test_request_id_validation_matches_node_strict_ascii_surface(invalid):
    with pytest.raises((MineflayerAdapterProtocolError, InvalidCorrelatedProbe)):
        encode_observe(invalid)
    _, _, _, _args, kwargs = _subject()
    with pytest.raises((MineflayerAdapterProtocolError, InvalidCorrelatedProbe)):
        CorrelatedProbeGrant(kwargs["grant"].authority, invalid)


def test_correlated_grant_requires_id_despite_legacy_optional_encoder():
    _, _, _, _, kwargs = _subject()
    assert json.loads(encode_observe(None)) == {"type": "observe"}
    with pytest.raises(InvalidCorrelatedProbe):
        CorrelatedProbeGrant(kwargs["grant"].authority, None)


@pytest.mark.parametrize("invalid", [
    None, 8, True, "space id", "", "日本語", "a" * 129,
])
def test_present_but_invalid_observation_request_id_rejected(invalid):
    _, _, _, args, _kwargs = _subject()
    wire = json.loads(_response_wire(replace(args["observation"], request_id=REQUEST1)))
    wire["request_id"] = invalid
    with pytest.raises(MineflayerAdapterProtocolError):
        parse_mineflayer_line(json.dumps(wire))


def test_correlated_id_is_not_permitted_on_unsolicited_nonprobe_observation():
    _, _, _, args, _kwargs = _subject()
    with pytest.raises(MineflayerAdapterProtocolError):
        replace(args["observation"], kind="entities", request_id=REQUEST1)
    payload = json.loads(
        _response_wire(replace(args["observation"], request_id=REQUEST1))
    )
    payload["kind"] = "entities"
    with pytest.raises(MineflayerAdapterProtocolError):
        parse_mineflayer_line(json.dumps(payload))


def test_correlated_response_is_accepted_and_feeds_s24_decision():
    for dist, expected, cm in ((0.2, "MOVE_AWAY", 20), (1.8, "WAIT", 180)):
        data, failed, inputs, args, kwargs = _subject(distance=dist)
        receipt = _run(kwargs)
        assert isinstance(receipt, CorrelatedProbeReceipt)
        assert receipt.authority_id == kwargs["grant"].authority.authority_id
        assert receipt.request_id == receipt.acknowledged_request_id == REQUEST1
        assert receipt.request_cursor_seq == 5
        assert receipt.probe_seq == 5 and receipt.next_cursor_seq == 6
        assert receipt.source_receipt.source.request_id == REQUEST1
        assert receipt.source_receipt.evidence.threat_clearance_cm == cm
        assert kwargs["adapter"].sent_ids == [REQUEST1]
        assert kwargs["adapter"].sent == 1
        assert kwargs["cursor"].consumed
        assert data["supervisor"].open_actions == ()
        trace = run_explicit_postfailure_epoch(
            data["supervisor"], args["action"], args["consequence"],
            inputs["recovery_skill"], data["intent"], data["commit"].new_state,
            receipt.source_receipt.evidence,
            at_ns=70, provenance=s27.s23.p("s29-caller-invoked-cognition"),
        )
        assert trace.selected_candidate == expected
        assert receipt.source_receipt.evidence.provenance in trace.source_provenance
        assert data["commit"].new_state.value == 4
        assert inputs["recovery_skill"].is_current_snapshot
        assert failed.is_terminal
        assert data["supervisor"].open_actions == ()

    doc = json.loads((ROOT / "docs/postmain-s29-correlated-trace.json").read_text())
    assert doc["near"]["request_id"] == REQUEST1
    assert doc["near"]["selected"] == "MOVE_AWAY"
    assert doc["far"]["selected"] == "WAIT"


def test_two_distinct_requests_in_same_session_bind_to_their_own_reply_ids():
    data, _failed, _inputs, args, kwargs = _subject()
    first_msg = kwargs["adapter"].frames[0]
    origin = first_msg.snapshot.position
    entity = first_msg.snapshot.nearby_entities[0]
    far_entity = replace(
        entity, distance=1.8,
        position=replace(entity.position, x=origin.x + 1.8),
    )
    second_msg = replace(
        first_msg, seq=6, request_id=REQUEST2,
        snapshot=replace(
            first_msg.snapshot, nearby_entities=(far_entity,),
        ),
    )
    adapter = CorrelatedSession(
        args["consequence"], frames=(first_msg, second_msg),
    )
    kwargs["adapter"] = adapter
    first = _run(kwargs)
    second_kwargs = {
        **kwargs,
        "cursor": ExclusiveProbeCursor(
            session_id=args["consequence"].session_id,
            next_seq=first.next_cursor_seq,
        ),
        "grant": CorrelatedProbeGrant(kwargs["grant"].authority, REQUEST2),
        "previous_receipt": first,
        "observed_at_ns": 66,
        "inspected_at_ns": 68,
    }
    second = _run(second_kwargs)
    assert [first.request_id, second.request_id] == [REQUEST1, REQUEST2]
    assert [first.probe_seq, second.probe_seq] == [5, 6]
    assert [first.source_receipt.evidence.threat_clearance_cm,
            second.source_receipt.evidence.threat_clearance_cm] == [20, 180]
    assert adapter.sent_ids == [REQUEST1, REQUEST2]
    assert first.next_cursor_seq == 6 and second.next_cursor_seq == 7
    assert data["supervisor"].open_actions == ()


def test_contiguous_unrequested_entity_event_before_matched_probe():
    data, _, _, args, kwargs = _subject(seq=6)
    desired = kwargs["adapter"].frames[0]
    event = replace(desired, seq=5, kind="entities", request_id=None)
    kwargs["adapter"].frames = deque((event, desired))
    receipt = _run(kwargs)
    assert receipt.received_count == 2
    assert receipt.probe_seq == 6
    assert receipt.request_id == REQUEST1
    assert data["supervisor"].open_actions == ()


@pytest.mark.parametrize("variant", [
    "missing_id", "wrong_id", "previous_id", "wrong_session",
    "old_seq", "gap_seq", "untyped_frame", "absent_target",
    "nonprobe_exhaustion", "timeout", "send_error",
])
def test_bad_or_uncorrelated_reply_rejects_and_consumes_cursor(variant):
    data, _, _, args, kwargs = _subject()
    message = kwargs["adapter"].frames[0]
    if variant == "missing_id":
        kwargs["adapter"].frames = deque((replace(message, request_id=None),))
    elif variant == "wrong_id":
        kwargs["adapter"].frames = deque((replace(message, request_id=REQUEST2),))
    elif variant == "previous_id":
        kwargs["adapter"].frames = deque((replace(message, request_id="old-request"),))
    elif variant == "wrong_session":
        kwargs["adapter"].frames = deque((replace(message, session_id="different-session"),))
    elif variant == "old_seq":
        kwargs["adapter"].frames = deque((replace(message, seq=4),))
    elif variant == "gap_seq":
        kwargs["adapter"].frames = deque((replace(message, seq=6),))
    elif variant == "untyped_frame":
        kwargs["adapter"].frames = deque(({"type": "observation"},))
    elif variant == "absent_target":
        empty = replace(
            message.snapshot, nearby_entities=(),
            nearby_entities_coverage=replace(
                message.snapshot.nearby_entities_coverage, candidate_count=0,
            ),
        )
        kwargs["adapter"].frames = deque((replace(message, snapshot=empty),))
    elif variant == "nonprobe_exhaustion":
        kwargs["adapter"].frames = deque((replace(message, seq=5, kind="entities", request_id=None),))
        kwargs["max_frames"] = 1
    else:
        kwargs["adapter"].mode = variant
    with pytest.raises((InvalidCorrelatedProbe, ValueError, RuntimeError)):
        _run(kwargs)
    assert kwargs["cursor"].consumed is True
    assert kwargs["adapter"].sent_ids == [REQUEST1]
    assert data["supervisor"].open_actions == ()


def test_same_caller_cursor_does_not_issue_second_request():
    _data, _, _, _args, kwargs = _subject()
    _run(kwargs)
    with pytest.raises(InvalidCorrelatedProbe):
        _run(kwargs)
    assert kwargs["adapter"].sent_ids == [REQUEST1]


@pytest.mark.parametrize("variant", [
    "missing_authority", "denied", "wrong_session", "wrong_parent",
    "stale_cursor", "wrong_cursor_seq", "wrong_outcome", "old_time",
])
def test_wrong_authority_or_parent_rejected_before_send(variant):
    data, _, _, _args, kwargs = _subject()
    grant = kwargs["grant"]
    if variant == "missing_authority":
        kwargs["grant"] = None
    elif variant == "denied":
        kwargs["grant"] = replace(grant, authority=replace(grant.authority, granted=False))
    elif variant == "wrong_session":
        kwargs["grant"] = replace(grant, authority=replace(grant.authority, session_id="another"))
    elif variant == "wrong_parent":
        kwargs["grant"] = replace(grant, authority=replace(grant.authority, parent_action_id="wrong"))
    elif variant == "stale_cursor":
        kwargs["cursor"] = replace(kwargs["cursor"], consumed=True)
    elif variant == "wrong_cursor_seq":
        kwargs["cursor"] = replace(kwargs["cursor"], next_seq=6)
    elif variant == "wrong_outcome":
        kwargs["action"] = data["closed1"]
    else:
        kwargs["observed_at_ns"] = 60
    with pytest.raises(InvalidCorrelatedProbe):
        _run(kwargs)
    assert kwargs["adapter"].sent_ids == []
    assert data["supervisor"].open_actions == ()


def test_previous_receipt_cannot_be_replayed_or_rebound_to_same_request_id():
    data, _, _, _args, kwargs = _subject()
    old = _run(kwargs)
    for new_grant in (
        CorrelatedProbeGrant(kwargs["grant"].authority, REQUEST1),
    ):
        cursor = ExclusiveProbeCursor(
            session_id=kwargs["consequence"].session_id,
            next_seq=old.next_cursor_seq,
        )
        with pytest.raises(InvalidCorrelatedProbe):
            _run({
                **kwargs, "cursor": cursor, "grant": new_grant,
                "previous_receipt": old,
            })
        assert cursor.consumed is False
    assert data["supervisor"].open_actions == ()


def test_receipt_maintains_bounded_protocol_claim():
    receipt = json.loads((ROOT / "docs/postmain-s29-receipt.json").read_text())
    assert receipt["base_head"] == "1485917e1ecef309c5d33bd50843baee19f7cfb2"
    assert receipt["classification"] == "PROTOCOL_CORRELATED_MINEFLAYER_PROBE_ROUNDTRIP_QUALIFIED"
    assert receipt["request_id_echo_required"] is True
    assert receipt["legacy_observe_preserved"] is True
    assert receipt["live_minecraft"] == "NOT_RUN"
    assert receipt["cryptographic_source_authentication"] is False
