"""T1m sidecar join: each source stays in its own clock domain."""
from copy import deepcopy

from adapters.mineflayer.t1m_timing_join_dev import analyze_t1m_timing


def originals(*, status="ADMITTED"):
    challenge = "a" * 32 + ":1"
    java = [
        f"INFO T1M_DEV_JVM_CHALLENGE_RX challenge={challenge} jvm_rel_ns=100",
        f"INFO T1M_DEV_JVM_CALLBACK index=1 challenge={challenge}"
        " world_tick=201 rx_to_callback_ns=2000000"
        " callback_to_send_return_ns=300000 jvm_rel_ns=2300100 qualification=false",
    ]
    node = [
        dict(kind="challenge_write_return", challenge=challenge,
             node_sent_ns="100000000", node_write_return_ns="100010000",
             event_loop_delay_window_max_ns=12000000),
        dict(kind="snapshot_callback", challenge=challenge, index=1,
             server_tick=101, world_tick=201, node_received_ns="150000000",
             node_complete_ns="150100000", age_upper_ns="50100000",
             status=status, reason="CAUSAL_AGE_UPPER_BOUND_MET" if status == "ADMITTED"
             else "CAUSAL_AGE_UPPER_BOUND_EXCEEDED",
             event_loop_delay_window_max_ns=9000000),
    ]
    native = [dict(
        type="paper_snapshot", seq=2, session_id="s", data=dict(
            status=status, reason=node[1]["reason"],
            received_ns="150000000", evaluation_completed_ns="150100000",
            age_upper_ns="50100000",
            snapshot=dict(index=1, challenge=challenge, world_tick=201,
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
