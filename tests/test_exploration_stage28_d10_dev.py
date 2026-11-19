"""D Lane D10: entirely SYNTHETIC raw source and hostile-seal tests.

No live Paper, Node, Gemma, GPU or original real World are created. Source
integrity checks that pass on these fakes are NOT real DEV attestation.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import pytest

from adapters.mineflayer.process_session import MineflayerProcessSession
from experiments.stage28_d10_seal_original_dev import (
    D10SealHold,
    seal_d10_stopped_original,
)
from relay_self.exploration_d10_original_source_audit_dev import (
    D10OriginalAuditHold,
    _native_raw,
    audit_d10_original_d9_source,
)
from relay_self.exploration_d8_owned_source_dev import (
    D8OwnedSourcePins,
    D8PinnedSourceHold,
    inspect_d8_original_source,
    load_d8_pins,
)
from test_exploration_stage28_d7_dev import _fixture
from test_mineflayer_adapter import observation_line


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _raw_native_sources(tmp_path: Path):
    receipts = {}
    expected = {}
    for index, name in enumerate(("A0", "A1", "B0"), 1):
        native = "native-d10-test-" + name
        request = "probe-d10-" + name
        value = json.loads(observation_line(
            session_id=native, seq=1, kind="probe",
        ))
        value["request_id"] = request
        payload = (json.dumps(value) + "\n").encode()
        path = tmp_path / ("D10-original-native-" + name + ".jsonl")
        path.write_bytes(payload)
        receipts[name] = {
            "session_id": native, "pid": 100 + index,
            "source_name": path.name,
            "sha256": _sha(payload), "bytes": len(payload),
        }
        expected[name] = (native, request)
    return receipts, expected


def test_d10_original_b_native_adapter_has_actual_effect_gate_and_raw_api():
    assert callable(MineflayerProcessSession.install_effect_admission)
    assert callable(MineflayerProcessSession.start_raw_source_audit)
    assert callable(MineflayerProcessSession.finish_raw_source_audit)
    assert isinstance(MineflayerProcessSession.owned_child_pid, property)


def test_d10_three_original_native_sessions_raw_sha_and_current_probes(tmp_path):
    receipts, expected = _raw_native_sources(tmp_path)
    actual = _native_raw(
        tmp_path,
        {"d10_original_native_sources": receipts},
        native_ids={k: v[0] for k, v in expected.items()},
        request_ids={k: v[1] for k, v in expected.items()},
    )
    assert actual == tuple(
        (name, receipts[name]["sha256"]) for name in ("A0", "A1", "B0")
    )


@pytest.mark.parametrize("malice", [
    "foreign-native", "bad-sha", "wrong-probe", "same-pid",
    "duplicate-seq", "missing-A1", "symlink-B0", "effect",
])
def test_d10_original_native_hostile_source_refuses(malice, tmp_path):
    receipts, expected = _raw_native_sources(tmp_path)
    ids = {k: v[0] for k, v in expected.items()}
    requests = {k: v[1] for k, v in expected.items()}
    a0 = tmp_path / "D10-original-native-A0.jsonl"
    b0 = tmp_path / "D10-original-native-B0.jsonl"
    if malice == "foreign-native":
        ids["B0"] = "not-original-B"
    elif malice == "bad-sha":
        a0.write_bytes(a0.read_bytes() + b"\n")
    elif malice == "wrong-probe":
        requests["B0"] = "foreign-request-id"
    elif malice == "same-pid":
        receipts["A1"]["pid"] = receipts["A0"]["pid"]
    elif malice == "duplicate-seq":
        a0.write_bytes(a0.read_bytes() * 2)
        receipts["A0"]["sha256"] = _sha(a0.read_bytes())
        receipts["A0"]["bytes"] = a0.stat().st_size
    elif malice == "missing-A1":
        del receipts["A1"]
    elif malice == "symlink-B0":
        b0.unlink()
        b0.symlink_to(a0)
    else:
        obj = json.loads(a0.read_text())
        obj["type"] = "effect_result"
        obj.pop("snapshot", None)
        a0.write_text(json.dumps(obj) + "\n")
        receipts["A0"]["sha256"] = _sha(a0.read_bytes())
        receipts["A0"]["bytes"] = a0.stat().st_size
    with pytest.raises((D10OriginalAuditHold, ValueError, TypeError)):
        _native_raw(
            tmp_path, {"d10_original_native_sources": receipts},
            native_ids=ids, request_ids=requests,
        )


def test_d10_seal_refuses_pre_world_incomplete_source_without_manifest(tmp_path):
    gen, _, _, pins = _fixture(tmp_path / "world-candidate")
    root = tmp_path / "synthetic-evidence"
    root.mkdir()
    dest = root / "typed-world-self-generations" / gen.name
    dest.parent.mkdir()
    shutil.copytree(gen, dest)
    with pytest.raises(D10SealHold, match="report"):
        seal_d10_stopped_original(
            root, dest,
            expected_world_id=pins["expected_world_id"],
            expected_source_branch_id=pins["expected_source_branch_id"],
        )
    assert not (root / "SHA256SUMS").exists()
    assert not (root.parent / "d10-independent-audit.json").exists()


def test_d10_d8_legacy_source_manifest_backward_compatible_but_no_auto_d9(
    tmp_path, monkeypatch,
):
    gen, restored, _, expected = _fixture(tmp_path)
    base = {
        "generation_id": gen.name,
        "world_id": expected["expected_world_id"],
        "source_branch_id": expected["expected_source_branch_id"],
        "fork_branch_id": expected["expected_fork_branch_id"],
        "committed_sha256": expected["expected_committed_sha256"],
        "stage28b_evidence_sha256": "a" * 64,
        "stage28b_evidence_files": 42,
    }
    path = tmp_path / "pins.json"
    path.write_text(json.dumps(base))
    assert load_d8_pins(path).d10_source_audit_sha256 is None
    with pytest.raises(D8PinnedSourceHold):
        D8OwnedSourcePins(**{
            **base, "d10_source_audit_sha256": "definitely-not-sha",
        })
    path.write_text(json.dumps({
        **base, "d10_source_audit_sha256": "b" * 64,
    }))
    pins = load_d8_pins(path)

    checked = []
    def frozen_historical(*a, **kwargs):
        checked.append(kwargs["expected_report_classification"])
        return SimpleNamespace(
            historical_native_sessions=("native-old-A", "native-old-B"),
        )
    monkeypatch.setattr(
        "relay_self.stage28c2b_historical_native_sessions_dev."
        "inspect_original_stage28b_native_sessions", frozen_historical,
    )
    with pytest.raises(D8PinnedSourceHold, match="historical"):
        inspect_d8_original_source(
            gen, restored, tmp_path / "synthetic-history", pins=pins,
        )
    assert checked == [
        "REAL_D9_SOURCE_A_B_TYPED_CUT_CAPTURED_INDEPENDENT_AUDIT_PENDING"
    ]
    assert not (tmp_path / "d10-independent-audit.json").exists()
    # Old B-only source path has its old strict classification, not D9.
    pins = D8OwnedSourcePins(**base)
    _, old = inspect_d8_original_source(
        gen, restored, tmp_path / "synthetic-history", pins=pins,
    )
    assert old.historical_native_sessions == (
        "native-old-A", "native-old-B",
    )
    assert checked[-1] == "REAL_PAPER_TWO_SELF_TYPED_STOPPED_WORLD_CUT_DEV"


def test_d10_no_missing_report_or_old_world_can_be_audited(tmp_path):
    gen, _, _, pins = _fixture(tmp_path)
    with pytest.raises(D10OriginalAuditHold):
        audit_d10_original_d9_source(
            tmp_path / "no-evidence", gen,
            expected_manifest_sha256="b" * 64, expected_files=3,
            expected_world_id=pins["expected_world_id"],
            expected_source_branch_id=pins["expected_source_branch_id"],
            expected_committed_sha256=pins["expected_committed_sha256"],
        )
    assert not (tmp_path / "d10-independent-audit.json").exists()


def test_d10_audit_wire_format_roundtrip_has_no_authority():
    from relay_self.exploration_d10_original_source_audit_dev import (
        D10OriginalAuditReceipt,
    )

    synthetic = D10OriginalAuditReceipt(
        "a" * 64, 1, "b" * 64, "g-000000000000",
        "test-world-not-uuid", "test-branch",
        "c" * 64, "native-A0", "native-A1", "native-B0",
        (("A0", "d" * 64), ("A1", "e" * 64), ("B0", "f" * 64)),
        "1" * 64, "2" * 64, "test-boot-not-uuid",
        "3" * 64, "4" * 64, "5" * 64,
        "1", "test-original-l1",
        (("A", ("question:unknown",)), ("B", ("question:unknown-B",))),
        (("A", ()), ("B", ("prior-reservation",))),
    )
    wire = json.loads(json.dumps(asdict(synthetic)))
    assert wire["original_l2_replay_authorized"] is False
    assert wire["original_action_replay_authorized"] is False
    assert wire["original_real_world_execution_attested"] is False
    assert wire["independent_source_classification"] == (
        "D10_ORIGINAL_BYTES_CORRELATED_DEV"
    )
