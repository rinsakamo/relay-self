"""T1l Node-clock causal age diagnosis and raw Paper continuity controls."""
from adapters.mineflayer.t1l_source_diagnostic_dev import (
    analyze_paper_records, AGE_LIMIT_NS,
)


def paper(i, *, seq=None, status="ADMITTED", age_ms=120,
          recv_to_complete_ms=15, source="s", reason="CAUSAL_AGE_UPPER_BOUND_MET",
          world="world"):
    # Every duration is within one synthetic Node monotonic clock domain.
    challenge = 1_000_000_000 + i * 200_000_000
    completed = challenge + int(age_ms * 1e6)
    received = completed - int(recv_to_complete_ms * 1e6)
    start = received + 1_000_000
    return {
        "type": "paper_snapshot", "session_id": source, "seq": seq or i * 3,
        "data": {
            "snapshot": {
                "index": i, "tick": 100 + i, "world_tick": 1000 + i,
                "boot": "boot", "world": world, "player": "player",
            },
            "status": status, "reason": reason,
            "challenge_sent_ns": str(challenge),
            "received_ns": str(received),
            "evaluation_start_ns": str(start),
            "evaluation_completed_ns": str(completed),
            "age_upper_ns": str(completed - challenge),
            "age_lower_ns": str(completed - received),
        },
    }


def test_breakdown_is_node_clock_not_paper_one_way_latency():
    records = [paper(1, age_ms=120), paper(2, age_ms=140)]
    audit = analyze_paper_records(records, session_id="s")
    assert audit["source_continuous"]
    assert audit["paper_frames"] == 2
    assert audit["statuses"] == {"ADMITTED": 2}
    assert audit["maxima_ms"]["causal_upper_ms"] == 140
    assert audit["maxima_ms"]["challenge_to_receive_ms"] == 125
    assert audit["maxima_ms"]["receive_to_complete_ms"] == 15
    assert audit["maxima_ms"]["node_queue_ms"] == 1
    assert audit["maxima_ms"]["node_evaluation_ms"] == 14
    assert audit["over_150ms"] == []
    assert not audit["one_way_latency_known"]
    assert not audit["qualification"]


def test_refusal_at_150ms_keeps_original_classification_and_components():
    accepted = paper(1, age_ms=120)
    stale = paper(2, status="STALE", age_ms=191.281,
                  reason="CAUSAL_AGE_UPPER_BOUND_EXCEEDED")
    audit = analyze_paper_records([accepted, stale])
    assert audit["statuses"] == {"ADMITTED": 1, "STALE": 1}
    assert audit["source_continuous"]
    assert audit["over_150ms"][0]["causal_upper_ms"] == 191.281
    assert audit["over_150ms"][0]["status"] == "STALE"
    assert audit["age_limit_ms_unchanged"] == AGE_LIMIT_NS // 1_000_000


def test_false_admitted_over_age_bound_is_a_violation_not_a_pass():
    audit = analyze_paper_records([paper(1, age_ms=150, status="ADMITTED")])
    assert not audit["source_continuous"]
    assert "false_admitted_over_age_limit" in audit["source_violations"]


def test_foreign_source_duplicate_seq_and_missing_paper_tick_fail_closed():
    bad = paper(3, seq=1, source="foreign")
    audit = analyze_paper_records([paper(1, seq=9), bad], session_id="s")
    assert not audit["source_continuous"]
    assert "foreign_session" in audit["source_violations"]
    assert "source_seq_reordered_or_duplicate" in audit["source_violations"]
    assert "paper_index_or_worldtick_gap" in audit["source_violations"]


def test_invalid_node_clock_order_refuses_analysis():
    bad = paper(1)
    bad["data"]["evaluation_start_ns"] = str(int(bad["data"]["received_ns"]) - 1)
    audit = analyze_paper_records([bad])
    assert not audit["source_continuous"]
    assert "node_clock_order_or_lower_bound" in audit["source_violations"]


def test_native_effect_frames_between_paper_samples_are_not_seq_gaps():
    audit = analyze_paper_records([
        paper(1, seq=3),
        {"type": "effect_result", "seq": 4, "session_id": "s"},
        paper(2, seq=5),
    ])
    assert audit["source_continuous"]
    assert audit["paper_frames"] == 2


def test_missing_challenge_cannot_be_accepted_without_causal_bound():
    bad = paper(1, status="ADMITTED")
    bad["data"]["challenge_sent_ns"] = None
    bad["data"]["age_upper_ns"] = None
    audit = analyze_paper_records([bad])
    assert "false_admitted_over_age_limit" in audit["source_violations"]


def test_challenge_index_never_exceeds_existing_v1_protocol_limit():
    bad = paper(2401)
    audit = analyze_paper_records([bad])
    assert not audit["source_continuous"]
    assert "challenge_index_out_of_bounds" in audit["source_violations"]
