"""S13 original-shape nonissued bridge interval and negative source tests."""
from __future__ import annotations

import json

import pytest

from adapters.mineflayer.normal_action import NormalSessionActionExecutor
from adapters.mineflayer.python_protocol import encode_observe, encode_shutdown
from adapters.mineflayer.self_s13_wait_interval import (
    S13NonissuanceRejected,
    review_nonissued_wait_interval,
)
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from test_mineflayer_process_session import observation_line, started_line


def _owner():
    intent = IntentCommitment()
    intent.commit(
        "escape-threat", objective="observe threat",
        at_ns=1, provenance=Provenance("s13-test", "owner"),
    )
    return NormalSessionActionExecutor("session-1", intent)


def _streams():
    source = json.loads(observation_line())
    def observation(seq, kind, tick, *, probe_id=None):
        item = {
            **source,
            "seq": seq,
            "kind": kind,
            "snapshot": {
                **source["snapshot"],
                "time": {
                    "time_of_day": tick, "day": 2, "is_day": False,
                },
                "nearby_entities": [{
                    "entity_id": 2, "name": "zombie", "entity_type": "zombie",
                    "distance": 5, "position": {"x": 4, "y": 64, "z": 2},
                }],
                "nearby_entities_coverage": {
                    **source["snapshot"]["nearby_entities_coverage"],
                    "candidate_count": 1,
                },
            },
        }
        if probe_id is not None:
            item["request_id"] = probe_id
        return item
    messages = [
        json.loads(started_line()),
        observation(1, "spawn", 13000),
        observation(2, "probe", 13001, probe_id="s13-before"),
        observation(3, "time", 13010),
        observation(4, "probe", 13021, probe_id="s13-after"),
        {"type": "shutdown_ack", "session_id": "session-1", "seq": 5},
    ]
    original_in = b"".join(
        (json.dumps(x, separators=(",", ":")) + "\n").encode() for x in messages
    )
    original_out = (
        encode_observe("s13-before") +
        encode_observe("s13-after") +
        encode_shutdown()
    ).encode()
    return messages, original_in, original_out


def _run(*, received=None, sent=None, owner=None, **kwargs):
    _, native_in, native_out = _streams()
    return review_nonissued_wait_interval(
        received_original=native_in if received is None else received,
        sent_original=native_out if sent is None else sent,
        owner=_owner() if owner is None else owner,
        expected_session_id="session-1", expected_target_id=2,
        **kwargs,
    )


def test_nonissued_wait_is_world_interval_not_s16_action_outcome():
    _, received, sent = _streams()
    a = _run(received=received, sent=sent)
    assert a.classification == "S13_ORIGINAL_SHAPED_NONISSUED_WORLD_INTERVAL_REVIEW_ONLY"
    assert a.elapsed_world_ticks == 20
    assert a.pre_seq == 2 and a.post_seq == 4
    assert a.target_entity_id == 2
    assert a.sent_observes == 2 and a.sent_effects == 0
    assert a.health_before == a.health_after == 12
    assert not a.s16_action_receipt_created
    assert not a.external_goal_attested
    assert not a.world_goal_success_claimed
    assert not a.independently_authenticated_minecraft_tcp
    assert not a.external_actor_silence_proven
    assert not a.action_authority and not a.science_qualified
    assert a.new_physical_runs == 0
    assert (received, sent) == _streams()[1:]


@pytest.mark.parametrize("case", [
    "sent_effect", "sent_extra", "sent_truncated", "sent_duplicate",
    "received_gap", "received_duplicate", "received_foreign",
    "received_malformed", "received_truncated", "received_error",
    "received_effect", "received_death", "received_no_ack",
    "probe_request_swap", "probe_missing", "probe_truncated",
    "zombie_disappears", "foreign_target", "same_tick",
    "reverse_tick", "too_long", "owner_issued", "owner_dispatched",
    "owner_supervised", "bad_expected", "trailing_garbage",
])
def test_fail_closed_when_nonissuance_or_bounded_interval_not_proven(case):
    messages, native_in, native_out = _streams()
    owner = _owner()
    if case == "sent_effect":
        native_out = native_out.replace(
            encode_shutdown().encode(),
            b'{"type":"effect","action_id":"forged","effect":"attack_entity","entity_id":2}\n'
            + encode_shutdown().encode(),
        )
    elif case == "sent_extra":
        native_out += encode_observe("extra").encode()
    elif case == "sent_truncated":
        native_out = native_out[:-1]
    elif case == "sent_duplicate":
        native_out = (
            encode_observe("s13-before")
            + encode_observe("s13-before")
            + encode_shutdown()
        ).encode()
    elif case == "received_gap":
        messages[3]["seq"] = 9
    elif case == "received_duplicate":
        messages[4]["seq"] = 3
    elif case == "received_foreign":
        messages[4]["session_id"] = "foreign"
    elif case == "received_malformed":
        native_in += b'{not-json}\n'
    elif case == "received_truncated":
        native_in = native_in[:-1]
    elif case == "received_error":
        messages[3] = {
            "type": "command_error", "session_id": "session-1",
            "seq": 3, "message": "stale",
        }
    elif case == "received_effect":
        messages[3] = {
            "type": "effect_result", "session_id": "session-1",
            "seq": 3, "action_id": "action", "effect": "set_control",
            "result": "applied", "error": None,
        }
    elif case == "received_death":
        messages[3]["kind"] = "death"
    elif case == "received_no_ack":
        messages.pop()
    elif case == "probe_request_swap":
        messages[4]["request_id"] = "s13-before"
    elif case == "probe_missing":
        messages[4]["kind"] = "time"
        del messages[4]["request_id"]
    elif case == "probe_truncated":
        cov = messages[4]["snapshot"]["nearby_entities_coverage"]
        cov.update({"truncated": True, "candidate_count": 17})
        messages[4]["snapshot"]["nearby_entities"] = [
            {**messages[4]["snapshot"]["nearby_entities"][0], "entity_id": i}
            for i in range(16)
        ]
    elif case == "zombie_disappears":
        messages[4]["snapshot"]["nearby_entities"] = []
        messages[4]["snapshot"]["nearby_entities_coverage"]["candidate_count"] = 0
    elif case == "foreign_target":
        messages[4]["snapshot"]["nearby_entities"][0]["entity_id"] = 9
    elif case == "same_tick":
        messages[4]["snapshot"]["time"]["time_of_day"] = 13001
    elif case == "reverse_tick":
        messages[4]["snapshot"]["time"]["time_of_day"] = 12999
    elif case == "too_long":
        messages[4]["snapshot"]["time"]["time_of_day"] = 15000
    elif case == "owner_issued":
        owner._count = 1
    elif case == "owner_dispatched":
        owner._dispatched.add("action")
    elif case == "owner_supervised":
        owner.supervisor._lifecycles["forged"] = object()
    elif case == "bad_expected":
        with pytest.raises(S13NonissuanceRejected):
            _run(expected_target_id=-1)
        return
    elif case == "trailing_garbage":
        native_out += b'{"type":"nope"}\n'
    if case.startswith("received_") or case in {
        "probe_request_swap", "probe_missing", "probe_truncated",
        "zombie_disappears", "foreign_target", "same_tick",
        "reverse_tick", "too_long",
    }:
        if case not in {"received_malformed", "received_truncated"}:
            native_in = b"".join(
                (json.dumps(x, separators=(",", ":")) + "\n").encode()
                for x in messages
            )
    with pytest.raises((S13NonissuanceRejected, ValueError, TypeError)):
        _run(received=native_in, sent=native_out, owner=owner)
