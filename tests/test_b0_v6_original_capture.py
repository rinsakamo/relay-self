"""Passive original-byte emitter: fake in-memory streams, NO World start."""
import asyncio
import json
from dataclasses import replace

import pytest

import test_b0_ground_foraging as ground
from adapters.mineflayer.v6_original_capture import (
    CAPTURE_SCHEMA,
    ISSUER_NAME,
    NATIVE_NAME,
    ORIGINAL_NAMES,
    PHASES,
    SERVER_NAME,
    V6CaptureRejected,
    V6OriginalCapture,
)

SLOT = "WORLD_START_A"
NONCE = "0123456789abcdef0123456789abcdef"
SID = "synthetic-v6-passive-capture"


def _probe():
    p = ground._ground()
    return replace(
        p, session_id=SID,
        snapshot=replace(
            p.snapshot, nearby_entities=(), inventory=(),
            nearby_entities_coverage=replace(
                p.snapshot.nearby_entities_coverage, candidate_count=0,
            ),
        ),
    )


def _line(row):
    return (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _populate(capture, probe):
    capture.on_native_stdout(_line({
        "type": "adapter_started", "session_id": SID, "seq": 0,
    }))
    # Genuine Mineflayer first *observation* is spawn; first correlated
    # L0 probe is after it. The current R synthetic envelope omits spawn.
    capture.on_native_stdout(_line({
        "type": "observation", "session_id": SID, "seq": 1,
        "kind": "spawn", "request_id": None,
    }))
    for phase, command in PHASES[:2]:
        capture.note_issuer_attempt(phase=phase, command=command)
    p = replace(probe, seq=2, request_id="v6-native-first-probe")
    capture.on_native_stdout(_line({
        "type": "observation", "session_id": SID, "seq": 2,
        "kind": "probe", "request_id": p.request_id,
    }))
    capture.note_first_native_probe(p)
    for phase, command in PHASES[3:]:
        capture.note_issuer_attempt(phase=phase, command=command)
    capture.on_server_stdout(b"vanilla server ready\n")
    capture.on_server_stdout(
        f"RELAYSELF_V6_TRIAL_START_{SLOT}_{NONCE}_NOT_ADMITTED\n".encode()
    )
    capture.on_server_stdout(b"RELAYSELF_V6_FIRST_INVOCATION_SOURCE_NOT_ADMITTED\n")
    for seq, age in ((3, 202), (4, 203)):
        capture.on_native_stdout(_line({
            "type": "native_clock_packet", "session_id": SID, "seq": seq,
            "world_age_ticks": str(age),
        }))
    capture.on_native_stdout(_line({
        "type": "shutdown_ack", "session_id": SID, "seq": 5,
    }))
    capture.on_native_stdout(_line({
        "type": "connection_end", "session_id": SID, "seq": 6,
    }))
    return p


def test_genuine_bytes_passive_capture_with_spawn_and_probe(tmp_path):
    original = V6OriginalCapture(
        tmp_path / "originals", session=SID, slot=SLOT, nonce=NONCE,
    )
    probe = _populate(original, _probe())
    result = original.close()
    assert result["schema"] == CAPTURE_SCHEMA
    assert result["issuer_phases_logged"] == 12
    assert result["first_l0_probe"] == {
        "seq": probe.seq, "request_id": probe.request_id,
    }
    assert result["classification"] == "S_V6_THREE_ORIGINAL_STREAMS_WRITTEN_SOURCE_ONLY"
    assert set(p.name for p in (tmp_path / "originals").iterdir()) == set(ORIGINAL_NAMES)
    for name in ORIGINAL_NAMES:
        raw = (tmp_path / "originals" / name).read_bytes()
        import hashlib
        assert result["sha256"][name] == hashlib.sha256(raw).hexdigest()
        assert result["sizes"][name] == len(raw)
    issuer = [
        json.loads(row) for row in (tmp_path / "originals" / ISSUER_NAME).read_text().splitlines()
    ]
    assert [j["phase"] for j in issuer] == [p for p, _ in PHASES]
    assert all(row["first_probe_native_seq"] == 2 for row in issuer)
    assert all(row["first_probe_request_id"] == probe.request_id for row in issuer)
    assert all(issuer[i]["host_monotonic_ns"] < issuer[i+1]["host_monotonic_ns"]
               for i in range(11))
    assert b'"kind":"spawn"' in (tmp_path / "originals" / NATIVE_NAME).read_bytes()
    assert b'"kind":"probe"' in (tmp_path / "originals" / NATIVE_NAME).read_bytes()
    assert result["claimant_sha_is_external_precommit"] is False
    assert not result["server_stdout_original_origin_r_attested"]
    assert not result["native_stop_ack_r_attested"]
    assert not result["physical_execution_authorized"]
    assert result["science_g3"] == "NO_GO"


def test_real_raw_bytes_not_normalized_or_fabricated(tmp_path):
    x = V6OriginalCapture(tmp_path / "originals", session=SID, slot=SLOT, nonce=NONCE)
    raw = b"[12:00 INFO]: ready\n"
    x.on_server_stdout(raw)
    x.on_native_stdout(_line({"type": "adapter_started", "session_id": SID, "seq": 0}))
    for bad in (b"bad\r\n", b"line-without-LF", b"", b"\n", b"\x00\n"):
        with pytest.raises(V6CaptureRejected):
            x.on_server_stdout(bad)
    with pytest.raises(V6CaptureRejected):
        x.on_native_stdout(b"not-json\n")
    x.close()
    assert (tmp_path / "originals" / SERVER_NAME).read_bytes() == raw
    assert (tmp_path / "originals" / NATIVE_NAME).read_bytes() == _line({
        "type": "adapter_started", "session_id": SID, "seq": 0,
    })


def test_rejects_duplicates_unknown_phases_and_no_issuer_forgery(tmp_path):
    cap = V6OriginalCapture(tmp_path / "originals", session=SID, slot=SLOT, nonce=NONCE)
    with pytest.raises(V6CaptureRejected):
        cap.note_issuer_attempt(phase="start_function", command=PHASES[3][1])
    with pytest.raises(V6CaptureRejected):
        cap.note_first_native_probe(_probe())
    cap.note_issuer_attempt(phase=PHASES[0][0], command=PHASES[0][1])
    with pytest.raises(V6CaptureRejected):
        cap.note_issuer_attempt(phase=PHASES[0][0], command=PHASES[0][1])
    partial = cap.close()
    assert partial["classification"] == "S_V6_ORIGINAL_STREAMS_PARTIAL_NOT_QUALIFIED"
    assert partial["issuer_phases_logged"] == 1
    assert (tmp_path / "originals" / ISSUER_NAME).read_bytes() == b""
    with pytest.raises(V6CaptureRejected):
        cap.close()
    with pytest.raises(V6CaptureRejected):
        V6OriginalCapture(tmp_path / "originals", session=SID, slot=SLOT, nonce=NONCE)


@pytest.mark.parametrize("frame", [
    {"type": "adapter_started", "session_id": "foreign", "seq": 0},
    {"type": "adapter_started", "session_id": SID, "seq": 1},
    {"type": "adapter_started", "session_id": SID, "seq": True},
])
def test_rejects_foreign_or_out_of_order_native_frame(tmp_path, frame):
    cap = V6OriginalCapture(tmp_path / "originals", session=SID, slot=SLOT, nonce=NONCE)
    with pytest.raises(V6CaptureRejected):
        cap.on_native_stdout(_line(frame))
    cap.close()
    assert (tmp_path / "originals" / NATIVE_NAME).read_bytes() == b""


@pytest.mark.parametrize("slot,nonce", [
    ("WORLD_START_X", NONCE),
    ("WORLD_START_A", "missing-nonce"),
    ("WORLD_START_A", NONCE.upper()),
])
def test_bad_world_or_nonce_rejected_before_creating_any_paths(tmp_path, slot, nonce):
    with pytest.raises(V6CaptureRejected):
        V6OriginalCapture(tmp_path / "originals", session=SID, slot=slot, nonce=nonce)
    assert list(tmp_path.iterdir()) == []


def test_native_first_probe_must_be_original_not_replacement(tmp_path):
    cap = V6OriginalCapture(tmp_path / "originals", session=SID, slot=SLOT, nonce=NONCE)
    cap.on_native_stdout(_line({"type": "adapter_started", "session_id": SID, "seq": 0}))
    for phase, command in PHASES[:2]:
        cap.note_issuer_attempt(phase=phase, command=command)
    p = replace(_probe(), seq=2, request_id="first")
    with pytest.raises(V6CaptureRejected):
        cap.note_first_native_probe(p)
    cap.close()


def test_module_import_and_init_never_open_process_or_action(tmp_path):
    cap = V6OriginalCapture(tmp_path / "originals", session=SID, slot=SLOT, nonce=NONCE)
    res = cap.close()
    assert res["issuer_phases_logged"] == 0
    assert res["physical_execution_authorized"] is False
    assert len(list((tmp_path / "originals").iterdir())) == 3
