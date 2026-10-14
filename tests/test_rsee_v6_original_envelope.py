"""R V6 prospective original envelope: synthetic-only control cases."""
import hashlib
import json
from copy import deepcopy

import pytest

from experiments.standard_env.v6_original_envelope import (
    ISSUER_PHASES,
    ORIGINAL_NAMES,
    SCHEMA,
    OriginalBundleRejected,
    main,
    plan,
    review_original_bundle,
)

SLOT = "WORLD_START_A"
NONCE = "0123456789abcdef0123456789abcdef"
SID = "synthetic-v6-not-a-server-session"


def _dump(rows):
    return b"".join(
        json.dumps(row, separators=(",", ":"), sort_keys=True).encode() + b"\n"
        for row in rows
    )


def _native():
    rows = [
        {
            "type": "adapter_started", "session_id": SID, "seq": 0,
            "mineflayer_version": "4.39.0", "config": {"version": "1.21.8"},
        },
        {
            "type": "observation", "session_id": SID, "seq": 1,
            "kind": "spawn", "source": "mineflayer",
        },
        {
            "type": "observation", "session_id": SID, "seq": 2,
            "kind": "probe", "request_id": "native-first-probe",
            "source": "mineflayer",
        },
    ]
    for i in (3, 4):
        rows.append({
            "type": "native_clock_packet", "session_id": SID, "seq": i,
            "source": "minecraft_1_21_8_clientbound_update_time",
            "observation_precision": "SERVER_UPDATE_TIME_PACKET_SAMPLE_ONLY",
            "world_age_ticks": str(200 + i),
            "world_day_time_raw_ticks": str(100 + i),
            "tick_day_time": True, "host_monotonic_ns": str(i * 10_000),
            "command_effect_tick_attested": False,
        })
    rows += [
        {"type": "shutdown_ack", "session_id": SID, "seq": 5},
        {"type": "connection_end", "session_id": SID, "seq": 6},
    ]
    return rows


def _issuer():
    return [
        {
            "seq": i, "session_id": SID, "phase": phase,
            "issuer_command": command, "host_monotonic_ns": 1000 + i * 100,
            "first_probe_native_seq": 2,
            "first_probe_request_id": "native-first-probe",
        }
        for i, (phase, command) in enumerate(ISSUER_PHASES)
    ]


def _root(tmp_path):
    root = tmp_path / "originals"
    root.mkdir()
    data = {
        ORIGINAL_NAMES[0]: (
            "server started\n"
            f"RELAYSELF_V6_TRIAL_START_{SLOT}_{NONCE}_NOT_ADMITTED\n"
            "some log output\n"
            "RELAYSELF_V6_FIRST_INVOCATION_SOURCE_NOT_ADMITTED\n"
        ).encode(),
        ORIGINAL_NAMES[1]: _dump(_issuer()),
        ORIGINAL_NAMES[2]: _dump(_native()),
    }
    for path, raw in data.items():
        (root / path).write_bytes(raw)
    return root, data


def _kwargs(raw):
    return {
        "expected_shas": {k: hashlib.sha256(v).hexdigest() for k, v in raw.items()},
        "session": SID, "slot": SLOT, "nonce": NONCE,
        "first_probe_seq": 2, "first_probe_request": "native-first-probe",
    }


def test_no_io_default_plan_is_prospective_no_source_producer(capsys):
    assert main([]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result == plan()
    assert result["schema"] == SCHEMA
    assert result["s_producer_for_this_bundle"] == "NOT_IMPLEMENTED"
    assert result["any_server_originals_read"] is False


def test_synthetic_positive_is_never_original_server_time_or_permission(tmp_path):
    root, raw = _root(tmp_path)
    result = review_original_bundle(root, **_kwargs(raw))
    assert result["classification"] == (
        "RSEE_V6_THREE_ORIGINAL_BYTES_AND_ORDER_REVIEW_ONLY"
    )
    assert result["native_rows"] == 7
    assert result["native_packet_age_samples"] == 2
    assert result["candidate_issuer_rows"] == len(ISSUER_PHASES)
    assert result["server_stdout_marker_order_consistent"] is True
    assert result["server_output_origin_authenticated"] is False
    assert result["original_server_score_readback_attested"] is False
    assert result["matched_12_arm_elapsed_world_tick_attested"] is False
    assert result["physical_execution_authorized"] is False
    assert result["science_g3"] == "NO_GO"


def test_sha_mismatch_missing_index_and_path_alias_refused(tmp_path):
    root, raw = _root(tmp_path)
    kw = _kwargs(raw)
    for name in ORIGINAL_NAMES:
        bad = deepcopy(kw)
        bad["expected_shas"][name] = "f" * 64
        with pytest.raises(OriginalBundleRejected, match="digest"):
            review_original_bundle(root, **bad)
    bad = deepcopy(kw)
    bad["expected_shas"].pop(ORIGINAL_NAMES[0])
    with pytest.raises(OriginalBundleRejected):
        review_original_bundle(root, **bad)
    (root / ORIGINAL_NAMES[0]).unlink()
    with pytest.raises((OriginalBundleRejected, ValueError)):
        review_original_bundle(root, **kw)


@pytest.mark.parametrize(("key", "value"), [
    ("slot", "WORLD_START_X"),
    ("nonce", "uppercaseNonce"),
    ("session", ""),
    ("session", "foreign-session"),
    ("first_probe_seq", True),
    ("first_probe_seq", 0),
    ("first_probe_seq", 5),
    ("first_probe_request", "foreign-probe"),
])
def test_foreign_scope_or_native_first_probe_is_rejected(tmp_path, key, value):
    root, raw = _root(tmp_path)
    kw = _kwargs(raw)
    kw[key] = value
    with pytest.raises(ValueError):
        review_original_bundle(root, **kw)


@pytest.mark.parametrize("change", [
    lambda rows: rows[0].update(phase="foreign"),
    lambda rows: rows[0].update(issuer_command="time set 0"),
    lambda rows: rows[4].update(issuer_command="summon minecraft:item ~ ~ ~"),
    lambda rows: rows[4].update(host_monotonic_ns=1),
    lambda rows: rows[4].update(session_id="foreign"),
    lambda rows: rows[4].update(first_probe_native_seq=9),
    lambda rows: rows[4].update(first_probe_request_id="forged"),
    lambda rows: rows[4].update(seq=2),
    lambda rows: rows[4].update(fabricated_original_attestation=True),
    lambda rows: rows.append(rows[-1]),
    lambda rows: rows.pop(),
])
def test_bounded_issuer_scope_negatives_even_with_recomputed_sha(tmp_path, change):
    root, raw = _root(tmp_path)
    rows = _issuer()
    change(rows)
    raw[ORIGINAL_NAMES[1]] = _dump(rows)
    (root / ORIGINAL_NAMES[1]).write_bytes(raw[ORIGINAL_NAMES[1]])
    with pytest.raises(ValueError):
        review_original_bundle(root, **_kwargs(raw))


@pytest.mark.parametrize("change", [
    lambda rows: rows[0].update(mineflayer_version="4.0.0"),
    lambda rows: rows[1].update(request_id="foreign"),
    lambda rows: rows[3].update(world_age_ticks="205"),
    lambda rows: rows[4].update(world_age_ticks="201"),
    lambda rows: rows[4].update(command_effect_tick_attested=True),
    lambda rows: rows[5].update(type="adapter_error"),
    lambda rows: rows.append({"type": "connection_end", "session_id": SID, "seq": 7}),
    lambda rows: rows.pop(),
])
def test_bounded_native_stream_negatives_even_with_recomputed_sha(tmp_path, change):
    root, raw = _root(tmp_path)
    rows = _native()
    change(rows)
    raw[ORIGINAL_NAMES[2]] = _dump(rows)
    (root / ORIGINAL_NAMES[2]).write_bytes(raw[ORIGINAL_NAMES[2]])
    with pytest.raises(ValueError):
        review_original_bundle(root, **_kwargs(raw))


@pytest.mark.parametrize("change", [
    lambda data: data.replace(b"RELAYSELF_V6_FIRST_INVOCATION_SOURCE_NOT_ADMITTED\n", b""),
    lambda data: data.replace(b"RELAYSELF_V6_FIRST_INVOCATION_SOURCE_NOT_ADMITTED\n",
                              b"RELAYSELF_V6_FIRST_INVOCATION_SOURCE_NOT_ADMITTED\n" * 2),
    lambda data: data.replace(b"server started\n", b"server started\r\n"),
    lambda data: data[:-1],
    lambda data: data.replace(b"RELAYSELF_V6_TRIAL_START_", b"UNRELATED_TRIAL_START_"),
])
def test_server_output_marker_scope_negatives_with_matching_claimant_sha(tmp_path, change):
    root, raw = _root(tmp_path)
    raw[ORIGINAL_NAMES[0]] = change(raw[ORIGINAL_NAMES[0]])
    (root / ORIGINAL_NAMES[0]).write_bytes(raw[ORIGINAL_NAMES[0]])
    with pytest.raises(ValueError):
        review_original_bundle(root, **_kwargs(raw))


def test_command_original_is_not_server_accepted_action(tmp_path):
    root, raw = _root(tmp_path)
    # This is a source-shaped prospective sample. It CANNOT prove that
    # S ever issued these commands, the server loaded either function,
    # privileged commands were excluded, or the scoreboard values were real.
    result = review_original_bundle(root, **_kwargs(raw))
    assert result["issuer_exclusivity_and_no_privileged_reset_attested"] is False
    assert result["true_start_or_summon_effect_tick_attested"] is False
    assert result["server_function_parser_or_load_attested"] is False


def test_missing_comparands_cli_blocks_without_creating_paths(tmp_path, capsys):
    assert main(["--root", str(tmp_path)]) == 2
    assert json.loads(capsys.readouterr().out)[
        "classification"
    ] == "RSEE_V6_ORIGINAL_BUNDLE_BLOCKED"
    assert sorted(tmp_path.iterdir()) == []


def test_rejects_extra_original_file_in_capture_root(tmp_path):
    root, raw = _root(tmp_path)
    (root / "unexpected.txt").write_text("extra")
    with pytest.raises(ValueError):
        review_original_bundle(root, **_kwargs(raw))
