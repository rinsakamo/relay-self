"""T1m sidecar join: each source stays in its own clock domain."""
from copy import deepcopy

from adapters.mineflayer.t1m_timing_join_dev import analyze_t1m_timing


def originals(*, status="ADMITTED"):
    challenge = "a" * 32 + ":1"
    java = [
        f"INFO T1M_DEV_JVM_CHALLENGE_RX challenge={challenge} jvm_rel_ns=100",
        f"INFO T1M_DEV_JVM_CALLBACK index=1 challenge={challenge}"
        " world_tick=201 server_tick=101 boot=b world=w player=p rx_to_callback_ns=2000000"
        " callback_to_send_return_ns=300000 jvm_rel_ns=2300100 qualification=false",
    ]
    node = [
        dict(kind="challenge_write_return", challenge=challenge,
             challenge_index=1, node_sent_ns="100000000", node_write_return_ns="100010000",
             event_loop_delay_window_max_ns=12000000),
        dict(kind="snapshot_callback", challenge=challenge, index=1,
             source_boot="b", source_world="w", source_player="p",
             server_tick=101, world_tick=201, node_received_ns="150000000",
             node_complete_ns="150100000", age_upper_ns="50100000",
             status=status, reason="CAUSAL_AGE_UPPER_BOUND_MET" if status == "ADMITTED"
             else "CAUSAL_AGE_UPPER_BOUND_EXCEEDED",
             event_loop_delay_window_max_ns=9000000),
    ]
    native = [dict(
        type="paper_snapshot", seq=2, session_id="s", data=dict(
            status=status, reason=node[1]["reason"],
            challenge_sent_ns="100000000", received_ns="150000000", evaluation_completed_ns="150100000",
            age_upper_ns="50100000",
            snapshot=dict(index=1, challenge=challenge, world_tick=201, tick=101,
                          boot="b", world="w", player="p"),
        ),
    )]
    return java, node, native


def test_same_challenge_index_join_preserves_two_independent_clock_domains():
    result = analyze_t1m_timing(*originals())
    assert result["matched_positive_jvm_samples"] == 1
    assert result["source_integrity_violations"] == []
    assert result["distributions_ms"]["node_a_ms"]["median"] == 50
    assert result["distributions_ms"]["jvm_rx_to_callback_ms"]["max"] == 2
    assert result["distributions_ms"]["jvm_callback_to_send_return_ms"]["max"] == .3
    assert result["distributions_ms"]["event_loop_delay_window_max_ms"]["max"] == 9
    assert not result["node_clock_comparable_to_jvm_clock"]
    assert not result["jvm_to_node_one_way_latency_known"]
    assert not result["event_loop_delay_correlated_to_exact_packet"]
    assert not result["qualification"]


def test_stale_native_remains_stale_without_promoting_outcome():
    java, node, native = originals(status="STALE")
    audit = analyze_t1m_timing(java, node, native)
    assert audit["source_statuses_original"] == {"STALE": 1}
    assert audit["matched_positive_jvm_samples"] == 1
    assert audit["qualification"] is False


def test_missing_correlated_jvm_sample_refuses_t1m_join():
    java, node, native = originals()
    audit = analyze_t1m_timing(java[:1], node, native)
    assert audit["matched_positive_jvm_samples"] == 0
    assert "missing_challenge_index_join" in audit["source_integrity_violations"]


def test_duplicate_jvm_callbacks_cannot_mint_two_matched_samples():
    java, node, native = originals()
    audit = analyze_t1m_timing(java + [java[1]], node, native)
    assert "duplicate_java_callback" in audit["source_integrity_violations"]
    assert audit["matched_positive_jvm_samples"] == 1


def test_duplicate_or_stale_challenge_issues_rejected():
    java, node, native = originals()
    audit = analyze_t1m_timing(java, [node[0], deepcopy(node[0]), node[1]], native)
    assert "duplicate_node_challenge_issue" in audit["source_integrity_violations"]


def test_source_id_or_timing_mismatch_refused():
    java, node, native = originals()
    node[1]["node_received_ns"] = "151000000"
    audit = analyze_t1m_timing(java, node, native)
    assert audit["matched_positive_jvm_samples"] == 0
    assert "cross_source_join_inconsistent" in audit["source_integrity_violations"]


def test_native_callback_worldtick_mismatch_refused():
    java, node, native = originals()
    native[0]["data"]["snapshot"]["world_tick"] = 202
    audit = analyze_t1m_timing(java, node, native)
    assert audit["matched_positive_jvm_samples"] == 0
    assert "cross_source_join_inconsistent" in audit["source_integrity_violations"]


def test_identity_index_status_and_extra_records_are_audited():
    for field, value in (("source_boot", "foreign"), ("world_tick", 999),
                         ("status", "STALE"), ("age_upper_ns", "1")):
        java, node, native = originals()
        node[1][field] = value
        result = analyze_t1m_timing(java, node, native)
        assert result["matched_positive_jvm_samples"] == 0
        assert result["source_integrity_violations"]
    java, node, native = originals()
    node[0]["challenge_index"] = 2
    assert analyze_t1m_timing(java, node, native)["source_integrity_violations"]
    java, node, native = originals()
    extra = deepcopy(node[1])
    extra["index"] = 2
    assert "unmatched_node_callback" in analyze_t1m_timing(
        java, node + [extra], native)["source_integrity_violations"]


def test_same_challenge_can_cover_consecutive_catchup_ticks():
    java, node, native = originals()
    j = java[1].replace("index=1", "index=2").replace("world_tick=201", "world_tick=202")
    j = j.replace("server_tick=101", "server_tick=102")
    n = deepcopy(node[1])
    n.update(index=2, world_tick=202, server_tick=102)
    r = deepcopy(native[0])
    r["seq"] += 1
    r["data"]["snapshot"].update(index=2, world_tick=202, tick=102)
    result = analyze_t1m_timing(java + [j], node + [n], native + [r])
    assert result["matched_positive_jvm_samples"] == 2
    assert result["source_integrity_violations"] == []


def test_post_evaluation_gap_is_not_misnamed_callback_wait():
    java, node, native = originals()
    event = deepcopy(node[0])
    event.update(challenge="a" * 32 + ":2", challenge_index=2,
                 node_sent_ns="417100000", node_write_return_ns="417200000",
                 timing_revision=2, previous_index=1, previous_complete_ns="150100000",
                 previous_emit_return_ns="151100000",
                 previous_diagnostic_start_ns="151100000",
                 previous_diagnostic_return_ns="416100000")
    result = analyze_t1m_timing(java, node + [event], native)
    assert result["source_integrity_violations"] == []
    stats = result["distributions_ms"]
    assert stats["post_eval_to_next_issue_ms"]["max"] == 267
    assert stats["diagnostic_hook_ms"]["max"] == 265
    assert stats["post_eval_emit_ms"]["max"] == 1
    event["previous_index"] = 2
    assert "invalid_post_evaluation_timing" in analyze_t1m_timing(
        java, node + [event], native)["source_integrity_violations"]
