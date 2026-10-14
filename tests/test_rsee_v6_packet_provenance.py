"""R standalone native V6 clock packet independent source/byte review gates."""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy

import pytest

from experiments.standard_env.v6_packet_provenance import (
    S_BLOBS,
    S_CANDIDATE_HEAD,
    V6PacketRejected,
    main,
    review_native_original,
    review_s_clock_source,
)

SESSION = "s-v6-original-review"


def _native_rows():
    return [
        {
            "type": "adapter_started", "session_id": SESSION, "seq": 0,
            "mineflayer_version": "4.39.0",
            "config": {
                "host": "127.0.0.1", "port": 25565, "username": "RelaySelf",
                "version": "1.21.8",
            },
        },
        {
            "type": "native_clock_packet", "session_id": SESSION, "seq": 1,
            "source": "minecraft_1_21_8_clientbound_update_time",
            "observation_precision": "SERVER_UPDATE_TIME_PACKET_SAMPLE_ONLY",
            "world_age_ticks": "100", "world_day_time_raw_ticks": "14560",
            "tick_day_time": True, "host_monotonic_ns": "1000000000",
            "command_effect_tick_attested": False,
        },
        {
            "type": "native_clock_packet", "session_id": SESSION, "seq": 2,
            "source": "minecraft_1_21_8_clientbound_update_time",
            "observation_precision": "SERVER_UPDATE_TIME_PACKET_SAMPLE_ONLY",
            "world_age_ticks": "121", "world_day_time_raw_ticks": "-23",
            "tick_day_time": False, "host_monotonic_ns": "2000000000",
            "command_effect_tick_attested": False,
        },
        {"type": "shutdown_ack", "session_id": SESSION, "seq": 3},
        {"type": "connection_end", "session_id": SESSION, "seq": 4},
    ]


def _original(tmp_path, rows=None):
    path = tmp_path / "native-v6-original.jsonl"
    lines = rows if rows is not None else _native_rows()
    source = "".join(json.dumps(x, sort_keys=True) + "\n" for x in lines).encode()
    path.write_bytes(source)
    return path, hashlib.sha256(source).hexdigest()


def test_r_v6_native_packet_plan_has_no_qualifications(capsys):
    assert main([]) == 0
    v = json.loads(capsys.readouterr().out)
    assert v["classification"] == "RSEE_V6_NATIVE_PACKET_READONLY_PLAN"
    assert v["pin_candidate_s_head"] == S_CANDIDATE_HEAD
    assert v["physical_execution_authorized"] is False


def test_r_v6_native_original_checks_bytes_but_not_command_effect(tmp_path):
    path, sha = _original(tmp_path)
    v = review_native_original(
        path, expected_sha256=sha, expected_session=SESSION,
    )
    assert v["classification"] == "RSEE_V6_PACKET_BYTES_MATCH_REVIEW_ONLY"
    assert v["native_rows"] == 5 and v["native_packet_age_samples"] == 2
    assert v["sampled_world_age_delta"] == 21
    assert v["first_age_sample_ticks"] == 100
    assert v["last_age_sample_ticks"] == 121
    assert v["first_packet_host_ns"] == 1000000000
    assert v["last_packet_host_ns"] == 2000000000
    assert v["native_original_bytes_sha256_match"] is True
    assert v["server_packet_payload_provenance_independently_attested"] is False
    assert v["exact_console_summon_effect_age_attested"] is False
    assert v["matched_world_time_across_arms"] is False
    assert v["physical_execution_authorized"] is False


@pytest.mark.parametrize("mutation", [
    lambda x: x[1].update(source="synthetic_oracle"),
    lambda x: x[1].update(world_age_ticks=100),
    lambda x: x[1].update(world_age_ticks="0100"),
    lambda x: x[1].update(world_age_ticks="-1"),
    lambda x: x[1].update(world_day_time_raw_ticks=str(2**63)),
    lambda x: x[1].update(host_monotonic_ns="0"),
    lambda x: x[1].update(tick_day_time=1),
    lambda x: x[1].update(command_effect_tick_attested=True),
    lambda x: x[1].update(observation_precision="EXACT_SUMMON_TICK"),
    lambda x: x[1].update(unexpected=1),
    lambda x: x[2].update(world_age_ticks="99"),
    lambda x: x[2].update(host_monotonic_ns="1"),
    lambda x: x[2].update(seq=1),
    lambda x: x[2].update(session_id="foreign"),
    lambda x: x[0].update(mineflayer_version="4.38.0"),
    lambda x: x[0]["config"].update(version="1.21.7"),
    lambda x: x[3].update(type="effect_result"),
    lambda x: x.pop(),
    lambda x: x.insert(2, deepcopy(x[1])),
])
def test_r_v6_native_packet_fail_closed_negative_source(tmp_path, mutation):
    rows = _native_rows()
    mutation(rows)
    path, sha = _original(tmp_path, rows)
    with pytest.raises(V6PacketRejected):
        review_native_original(path, expected_sha256=sha, expected_session=SESSION)


def test_r_v6_independent_sha_and_session_are_not_taken_from_report(tmp_path):
    path, sha = _original(tmp_path)
    with pytest.raises(V6PacketRejected, match="SHA256"):
        review_native_original(path, expected_sha256="0" * 64, expected_session=SESSION)
    with pytest.raises(V6PacketRejected):
        review_native_original(path, expected_sha256=sha, expected_session="foreign")
    with pytest.raises(V6PacketRejected):
        review_native_original(path, expected_sha256="bad", expected_session=SESSION)
    alias = tmp_path / "alias.jsonl"
    alias.symlink_to(path)
    with pytest.raises(V6PacketRejected):
        review_native_original(alias, expected_sha256=sha, expected_session=SESSION)


def test_r_v6_original_rejects_duplicate_json_key_with_matching_bytes(tmp_path):
    path, _ = _original(tmp_path)
    original = path.read_text()
    altered = original.replace(
        '"world_age_ticks": "100",', '"world_age_ticks": "100", "world_age_ticks": "200",',
    )
    assert original != altered
    path.write_text(altered)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(V6PacketRejected, match="duplicate"):
        review_native_original(path, expected_sha256=sha, expected_session=SESSION)


def test_r_v6_pinned_candidate_source_rejects_nonexistent_and_wrong_git(tmp_path):
    assert len(S_BLOBS) == 4
    with pytest.raises(V6PacketRejected):
        review_s_clock_source(tmp_path / "missing")
    with pytest.raises(V6PacketRejected):
        review_s_clock_source(tmp_path)
    assert main(["--s-checkout", str(tmp_path)]) == 2
