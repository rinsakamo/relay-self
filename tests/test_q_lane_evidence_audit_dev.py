"""Q1 hostile evidence tests: synthetic sources, NEVER actual Paper/Native/Gemma."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from experiments.q_lane_evidence_audit_dev import (
    QEvidenceHold,
    build_untrusted_file_inventory,
    verify_evidence,
)

_HEAD = "a" * 40
_WORLD = "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb"
_BOOT = "cccccccc-cccc-4ccc-cccc-cccccccccccc"
def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _line(row: dict) -> bytes:
    return (json.dumps(row, sort_keys=True) + "\n").encode()


def _fixture(tmp_path: Path):
    root = tmp_path / "original"
    root.mkdir(parents=True)
    source = {
        "native_request_id": "observe-A-1",
        "native_seq": 7,
        "paper_nonce": "paper-A-nonce-1",
        "paper_tick": 23,
        "paper_boot_id": _BOOT,
        "paper_session_id": "owned-paper-1",
        "wal_action_id": "move-A-1",
        "wal_status": "NATIVE_MOVE_SETTLED",
        "question_ref": "question-A-1",
        "gpu_ticket_id": "ticket-A-1",
    }
    paper_line = (
        f"P0D_TICK_ACK nonce={source['paper_nonce']} boot={_BOOT} "
        f"session=owned-paper-1 world={_WORLD} tick=23 "
        "source=PAPER_MAIN_THREAD\n"
    ).encode()
    ack = (
        f"boot_id={_BOOT}\nnonce=paper-A-nonce-1\npaper_tick=23\n"
        f"server_session_id=owned-paper-1\nsource=PAPER_MAIN_THREAD\n"
        f"world_uuid={_WORLD}\n"
    ).encode()
    data = {
        "native_stdin": _line({"type": "observe", "request_id": "observe-A-1"}),
        "native_stdout": (
            _line({"type": "adapter_started", "session_id": "native-A-1", "seq": 0})
            + _line({
                "type": "observation", "session_id": "native-A-1", "seq": 7,
                "kind": "probe", "request_id": "observe-A-1",
            })
        ),
        "paper_log": b"Starting Paper\n" + paper_line,
        "paper_ack": ack,
        "wal": _line({
            "schema": 1, "self_id": "A", "actions": [
                {"action_id": "move-A-1", "status": "NATIVE_MOVE_SETTLED"},
            ],
        }),
        "checkpoint": _line({"generation": 4, "self_id": "A"}),
        "question_adopts": _line({
            "operation": "ADOPT", "self_id": "A", "question_ref": "question-A-1",
        }),
        "gpu_tickets": _line({
            "ticket_id": "ticket-A-1", "self_id": "A",
            "request_id": "observe-A-1", "consumed": True,
        }),
    }
    manifest = {
        "schema": 1, "head": _HEAD, "world_uuid": _WORLD,
        "owner_id": "original-owner-A", "self_id": "A",
        "native_session_id": "native-A-1", "checkpoint_generation": 4,
        "source": source,
        "files": [],
    }
    pins = {k: copy.deepcopy(v) for k, v in manifest.items() if k != "files"}
    pins["sha256"] = {}
    for role, raw in data.items():
        path = role + ".evidence"
        (root / path).write_bytes(raw)
        digest = _sha(raw)
        manifest["files"].append({
            "role": role, "path": path, "size": len(raw), "sha256": digest,
        })
        pins["sha256"][role] = digest
    return root, manifest, pins


def _change(root, manifest, pins, role, transform, *, repin=False):
    entry = next(x for x in manifest["files"] if x["role"] == role)
    path = root / entry["path"]
    data = transform(path.read_bytes())
    path.write_bytes(data)
    entry["sha256"] = _sha(data)
    entry["size"] = len(data)
    if repin:
        pins["sha256"][role] = _sha(data)


def test_q1_limited_read_only_consistency_not_real_attestation(tmp_path):
    root, manifest, pins = _fixture(tmp_path)
    before = {
        p.name: (p.read_bytes(), p.stat().st_mtime_ns)
        for p in root.iterdir()
    }
    result = verify_evidence(root, manifest, pins)
    assert result["classification"] == "Q1_EXTERNAL_PINS_AND_SOURCE_LINKS_CONSISTENT_DEV_ONLY"
    assert result["external_pin_origin_authenticated"] is False
    assert result["real_world_attested"] is False
    assert result["owner_checkpoint_semantics_attested"] is False
    assert result["qual_go"] is False and result["science_run"] is False
    assert before == {
        p.name: (p.read_bytes(), p.stat().st_mtime_ns)
        for p in root.iterdir()
    }


@pytest.mark.parametrize(("field", "replacement"), [
    ("head", "f" * 40), ("self_id", "B"), ("owner_id", "other-owner"),
    ("world_uuid", "other-world"), ("native_session_id", "native-A-old"),
    ("checkpoint_generation", 3),
])
def test_q1_foreign_scope_and_old_checkpoint_rejected(tmp_path, field, replacement):
    root, manifest, pins = _fixture(tmp_path)
    manifest[field] = replacement
    with pytest.raises(QEvidenceHold):
        verify_evidence(root, manifest, pins)


@pytest.mark.parametrize(("key", "value"), [
    ("native_request_id", "old-observe"), ("native_seq", 8),
    ("paper_nonce", "older-nonce"), ("paper_tick", 24),
    ("paper_session_id", "old-paper"), ("wal_action_id", "other-action"),
    ("gpu_ticket_id", "old-ticket"), ("question_ref", "other-question"),
])
def test_q1_independently_pinned_claims_reject_identity_edit(tmp_path, key, value):
    root, manifest, pins = _fixture(tmp_path)
    manifest["source"][key] = value
    with pytest.raises(QEvidenceHold):
        verify_evidence(root, manifest, pins)


@pytest.mark.parametrize(("role", "change"), [
    ("paper_log", lambda data: data + b"Saved the game\n"),
    ("paper_log", lambda data: data[:-2]),
    ("native_stdin", lambda data: data.replace(b"observe-A-1", b"observe-B-1")),
    ("checkpoint", lambda data: data.replace(b'"generation": 4', b'"generation": 5')),
    ("wal", lambda data: data.replace(b"move-A-1", b"move-B-1")),
])
def test_q1_rehashed_manifest_cannot_forge_independent_file_pin(tmp_path, role, change):
    root, manifest, pins = _fixture(tmp_path)
    _change(root, manifest, pins, role, change, repin=False)
    with pytest.raises(QEvidenceHold, match="pin"):
        verify_evidence(root, manifest, pins)


@pytest.mark.parametrize(("role", "change"), [
    ("paper_log", lambda data: data + data.split(b"Starting Paper\n")[1]),
    ("paper_log", lambda data: data.replace(b"P0D_TICK_ACK", b"P0D_TICK_XXX")),
    ("paper_log", lambda data: data[:-1]),
    ("paper_ack", lambda data: data.replace(b"paper_tick=23", b"paper_tick=24")),
    ("native_stdout", lambda data: data.replace(b"native-A-1", b"native-A-old")),
    ("native_stdout", lambda data: data.replace(b'"seq": 7', b'"seq": 9')),
    ("native_stdout", lambda data: data.replace(b"observe-A-1", b"observe-old")),
    ("wal", lambda data: data.replace(
        b"NATIVE_MOVE_SETTLED", b"PREPARED_UNRESOLVED",
    )),
    ("question_adopts", lambda data: data + data),
    ("gpu_tickets", lambda data: data + data),
])
def test_q1_source_failures_survive_repinning_all_file_hashes(tmp_path, role, change):
    """Intrinsic checks still HOLD if BOTH local digests are recalculated."""
    root, manifest, pins = _fixture(tmp_path)
    _change(root, manifest, pins, role, change, repin=True)
    with pytest.raises(QEvidenceHold):
        verify_evidence(root, manifest, pins)


def test_q1_other_self_evidence_swap_rejected(tmp_path):
    root, manifest, pins = _fixture(tmp_path)
    _change(
        root, manifest, pins, "wal",
        lambda data: data.replace(b'"self_id": "A"', b'"self_id": "B"'),
        repin=True,
    )
    with pytest.raises(QEvidenceHold, match="Self"):
        verify_evidence(root, manifest, pins)


def test_q1_missing_artifact_refused(tmp_path):
    root, manifest, pins = _fixture(tmp_path)
    (root / "paper_ack.evidence").unlink()
    with pytest.raises(QEvidenceHold, match="missing"):
        verify_evidence(root, manifest, pins)


def test_q1_exchanged_files_and_symlinks_refused(tmp_path):
    root, manifest, pins = _fixture(tmp_path)
    p1 = root / "paper_ack.evidence"
    p2 = root / "paper_log.evidence"
    first, second = p1.read_bytes(), p2.read_bytes()
    p1.write_bytes(second)
    p2.write_bytes(first)
    with pytest.raises(QEvidenceHold):
        verify_evidence(root, manifest, pins)
    p2.write_bytes(second)  # restore earlier role so symlink is the actual failure
    p1.unlink()
    p1.symlink_to(p2)
    with pytest.raises(QEvidenceHold, match="symlink"):
        verify_evidence(root, manifest, pins)


def test_q1_path_escape_and_missing_external_pin_fail_closed(tmp_path):
    root, manifest, pins = _fixture(tmp_path)
    manifest["files"][0]["path"] = "../escape"
    with pytest.raises(QEvidenceHold):
        verify_evidence(root, manifest, pins)
    root, manifest, pins = _fixture(tmp_path / "new")
    pins["sha256"].pop("wal")
    with pytest.raises(QEvidenceHold):
        verify_evidence(root, manifest, pins)


def test_q1_untrusted_manifest_file_inventory_is_read_only(tmp_path):
    root, manifest, pins = _fixture(tmp_path)
    before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in root.iterdir()}
    paths = {entry["role"]: entry["path"] for entry in manifest["files"]}
    entries = build_untrusted_file_inventory(root, paths)
    assert {entry["role"] for entry in entries} == set(pins["sha256"])
    assert {entry["sha256"] for entry in entries} == set(pins["sha256"].values())
    assert before == {
        p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in root.iterdir()
    }
    # Returning a local inventory is not authentication; a forged file with
    # recalculated hash still fails against independently supplied pins.
    _change(root, manifest, pins, "wal",
            lambda data: data.replace(b"move-A-1", b"move-X-1"))
    build_untrusted_file_inventory(root, paths)  # may index changed local bytes
    with pytest.raises(QEvidenceHold):
        verify_evidence(root, manifest, pins)


def test_q1_nested_original_source_is_read_only(tmp_path):
    root, manifest, pins = _fixture(tmp_path)
    path = root / "nested" / "more"
    path.mkdir(parents=True)
    (root / "wal.evidence").rename(path / "wal.evidence")
    entry = next(e for e in manifest["files"] if e["role"] == "wal")
    entry["path"] = "nested/more/wal.evidence"
    before = (path / "wal.evidence").read_bytes()
    assert verify_evidence(root, manifest, pins)["file_count"] == 8
    assert (path / "wal.evidence").read_bytes() == before


def test_q1_parent_symlink_fails_even_if_precheck_is_raced(tmp_path, monkeypatch):
    root, manifest, pins = _fixture(tmp_path)
    real = root / "real"
    real.mkdir()
    (root / "wal.evidence").rename(real / "wal.evidence")
    link = root / "substituted-dir"
    link.symlink_to(real, target_is_directory=True)
    entry = next(e for e in manifest["files"] if e["role"] == "wal")
    entry["path"] = "substituted-dir/wal.evidence"
    # Deliberately model a check/use race: the earlier symlink inspection
    # is bypassed, but per-ancestor O_NOFOLLOW still rejects the traversal.
    original = Path.is_symlink

    def missed_symlink(self):
        return False if self == link else original(self)

    monkeypatch.setattr(Path, "is_symlink", missed_symlink)
    before = (real / "wal.evidence").read_bytes()
    with pytest.raises(QEvidenceHold):
        verify_evidence(root, manifest, pins)
    assert (real / "wal.evidence").read_bytes() == before


def test_q1_rejects_fifo_without_blocking_or_writing(tmp_path):
    import os

    root, manifest, pins = _fixture(tmp_path)
    fifo = root / "paper_ack.evidence"
    fifo.unlink()
    os.mkfifo(fifo)
    with pytest.raises(QEvidenceHold):
        verify_evidence(root, manifest, pins)
