"""Independent I1 Native/Paper/CPU provenance tests using synthetic raw bytes.

These do not start Paper, Mineflayer, GPU or a real Minecraft World.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import pytest

from adapters.mineflayer.python_protocol import MINEFLAYER_VERSION, parse_mineflayer_line
from experiments.i_lane_i1_independent_cpu_audit_dev import (
    I1IndependentAuditHold,
    _audit_i1_epochs,
)
from experiments.stage28c2b_independent_rejoin_audit_dev import (
    Stage28c2bIndependentAuditHold,
    independently_audit_recovered_real_rejoin,
)
from experiments.stage28c2b_real_recovered_rejoin_dev import _SOURCE_WORLD
from relay_self.cognitive_minimal_dev import initial_patterns
from relay_self.intent import IntentCommitment
from test_mineflayer_process_session import observation_line

_BOOT = "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb"
_ACTORS = {
    "A": "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa",
    "B": "cccccccc-cccc-4ccc-cccc-cccccccccccc",
}
_SESSION = "paper-owned-i1-audit"


def _line(row: dict) -> bytes:
    return (json.dumps(row, separators=(",", ":")) + "\n").encode()


def _native(sid: str, seq: int, req: str) -> tuple[dict, object]:
    row = json.loads(observation_line())
    row.update(type="observation", session_id="native-" + sid,
               seq=seq, kind="probe", request_id=req)
    row["snapshot"]["food"] = 6 if seq == 2 else 11
    decoded = parse_mineflayer_line(_line(row).decode())
    return row, decoded


def _fixture(tmp_path: Path):
    evidence, executable = tmp_path / "evidence", tmp_path / "world"
    evidence.mkdir()
    executable.mkdir()
    plugin = executable / "plugins" / "P0BRecorder" / "p0d-ticks" / "acks"
    plugin.mkdir(parents=True)
    paper = [
        f"P0D_RESIDENT_READY boot={_BOOT} source=PAPER_MAIN_THREAD version=1\n",
    ]
    for number, (sid, event) in enumerate((
        ("A", "JOIN"), ("B", "JOIN"), ("A", "PRESENT"), ("B", "PRESENT"),
    ), 4):
        paper.append(
            f"P0D_RESIDENT event={event} boot={_BOOT} tick={number} "
            f"world={_SOURCE_WORLD} actor={_ACTORS[sid]} name=Relay{sid} "
            "x=0 y=64 z=0 source=PAPER_MAIN_THREAD\n"
        )
    paper_refs = []
    for index, tick in enumerate((10, 20), start=1):
        nonce = f"i1-nonce-{index}"
        receipt = (
            f"boot_id={_BOOT}\n"
            f"nonce={nonce}\n"
            f"paper_tick={tick}\n"
            f"server_session_id={_SESSION}\n"
            "source=PAPER_MAIN_THREAD\n"
            f"world_uuid={_SOURCE_WORLD}\n"
        ).encode()
        (plugin / (nonce + ".ack")).write_bytes(receipt)
        ref = (
            f"paper-main-thread:p0d:{_BOOT}:{nonce}:sha256:"
            + hashlib.sha256(receipt).hexdigest()
        )
        paper.append(
            f"P0D_TICK_ACK nonce={nonce} boot={_BOOT} session={_SESSION} "
            f"world={_SOURCE_WORLD} tick={tick} source=PAPER_MAIN_THREAD\n"
        )
        prefix = "".join(paper).encode()
        paper_refs.append((ref, tick, hashlib.sha256(prefix).hexdigest()))
    frozen = "".join(paper).encode()
    (evidence / "prestop-paper-resident-owned.log").write_bytes(frozen)
    (evidence / (_SESSION + ".log")).write_bytes(
        frozen + b"Saved the game\nStopping server\n"
    )

    report = {
        "classification": "I1_ORIGINAL_CPU_SENSE_CAPTURED_INDEPENDENT_AUDIT_PENDING",
        "i1_original_cpu_sense_enabled": True,
        "i1_normal_continuous_native_observed": True,
        "real_gemma_post": 0,
        "real_action_issued": 0,
        "physical_action_issue_authorized": False,
        "fresh_l1_run": False,
        "paper_session_id": _SESSION,
        "paper_pid": 991,
        "paper_boot": {"paper_boot_id": _BOOT, "paper_pid": 991, "boot_tick": 3},
        "fresh_body_links": [
            {"self_id": sid, "paper_actor_uuid": _ACTORS[sid]}
            for sid in ("A", "B")
        ],
        "native_login_evidence": {},
        "owner_worldbody_observations": {},
        "raw_native_file_sha256": {},
        "i1_cpu_epochs": {
            "epochs": [], "per_self_counts": [["A", 2], ["B", 2]],
            "continuous_native_updates_observed": True,
            "model_invoked": False,
            "action_issue_authorized": False,
        },
    }
    owners = {
        sid: SimpleNamespace(pattern_registry=initial_patterns(),
                             intent=IntentCommitment())
        for sid in ("A", "B")
    }
    records = {}
    for sid in ("A", "B"):
        original, parsed_original = _native(sid, 1, "initial-" + sid)
        report["owner_worldbody_observations"][sid] = asdict(parsed_original)
        report["native_login_evidence"][sid] = {
            "native_session_id": "native-" + sid,
            "observation_ref": "initial-" + sid,
        }
        start = {
            "type": "adapter_started", "session_id": "native-" + sid,
            "seq": 0, "mineflayer_version": MINEFLAYER_VERSION,
            "config": {
                "host": "127.0.0.1", "port": 25565,
                "username": "Relay" + sid, "version": None,
            },
        }
        data = [_line(start), _line(original)]
        commands = [_line({"type": "observe", "request_id": "initial-" + sid})]
        for number, seq in enumerate((2, 3), start=1):
            req = f"i1-original-sense-{(number + 2 * int(sid == 'B')):032x}"
            source, obs = _native(sid, seq, req)
            data.append(_line(source))
            commands.append(_line({"type": "observe", "request_id": req}))
            ref, tick, digest = paper_refs[number - 1]
            rows = {
                "self_id": sid,
                "native_session_id": "native-" + sid,
                "native_seq": seq,
                "sense_revision": f"mineflayer:native-{sid}:{seq}",
                "native_request_id": req,
                "native_observation_ref": obs.provenance.reference,
                "paper_tick": tick,
                "paper_tick_source_ref": ref,
                "paper_log_sha256": digest,
                "paper_actor_uuid": _ACTORS[sid],
                "resident_epoch": 1,
                "source_revision_refs": [
                    f"native:native-{sid}:initial-{sid}:1:"
                    f"{parsed_original.provenance.reference}",
                    f"paper:{_SESSION}:{_BOOT}:{digest}:{ref}",
                    f"mineflayer:native-{sid}:{seq}",
                ],
                "schema_revision": 0,
                "goal_ids": ["HUNGER_RELIEF"],
                "l1_descriptions": ["ESCALATE_L2", "DEFER"],
                "inquiry_ref": None,
                "model_invoked": False,
                "action_issue_authorized": False,
            }
            records[(sid, number)] = rows
        raw = evidence / f"native-Relay{sid}-native-{sid}.jsonl"
        raw.write_bytes(b"".join(data))
        report["raw_native_file_sha256"]["Relay" + sid] = hashlib.sha256(
            raw.read_bytes()
        ).hexdigest()
        command_path = evidence / f"native-commands-Relay{sid}-native-{sid}.jsonl"
        command_path.write_bytes(b"".join(commands))
        report.setdefault("raw_native_command_file_sha256", {})["Relay" + sid] = (
            hashlib.sha256(command_path.read_bytes()).hexdigest()
        )
    report["i1_cpu_epochs"]["epochs"] = [
        records[(sid, round_)] for round_ in (1, 2) for sid in ("A", "B")
    ]
    return report, evidence, executable, owners


def test_independent_native_paper_cpu_replay_success_from_synthetic_sources(tmp_path):
    report, evidence, executable, owners = _fixture(tmp_path)
    verdict = _audit_i1_epochs(
        report=report, evidence=evidence, executable=executable,
        owners=owners,
    )
    assert verdict["classification"] == (
        "I1_ORIGINAL_A_B_NATIVE_PAPER_CPU_SOURCE_AUDITED_DEV"
    )
    assert verdict["native_observation_counts"] == [["A", 2], ["B", 2]]
    assert verdict["independent_paper_ack_per_epoch"]
    assert verdict["independent_cpu_replay"]
    assert verdict["real_action_issued"] == 0 and not verdict["qual_go"]


@pytest.mark.parametrize("tamper", [
    "false-count", "one-row", "wrong-order", "wrong-request",
    "duplicate-request", "foreign-self", "invented-sense-ref",
    "wrong-native-seq", "wrong-native-provenance", "forged-paper-hash",
    "wrong-paper-tick", "wrong-paper-ack", "paper-actor",
    "forged-goal", "forged-l1-options", "invented-exploration",
    "extra-native-probe", "changed-raw-snapshot", "stale-resident-epoch",
    "physical-authority", "model-invoked", "missing-command-log",
    "altered-command-id", "extra-physical-command", "command-sha-forgery",
])
def test_i1_independent_rejects_manifest_or_source_tampering(tmp_path, tamper):
    report, evidence, executable, owners = _fixture(tmp_path)
    rows = report["i1_cpu_epochs"]["epochs"]
    first, second = rows[0], rows[1]
    if tamper == "false-count":
        report["i1_cpu_epochs"]["per_self_counts"][0][1] = 1
    elif tamper == "one-row":
        rows.pop()
    elif tamper == "wrong-order":
        rows[0], rows[1] = rows[1], rows[0]
    elif tamper == "missing-command-log":
        (evidence / "native-commands-RelayA-native-A.jsonl").unlink()
    elif tamper in ("altered-command-id", "extra-physical-command", "command-sha-forgery"):
        path = evidence / "native-commands-RelayA-native-A.jsonl"
        if tamper == "command-sha-forgery":
            report["raw_native_command_file_sha256"]["RelayA"] = "f" * 64
        else:
            rows = [json.loads(line) for line in path.read_bytes().splitlines()]
            if tamper == "altered-command-id":
                rows[1]["request_id"] = "i1-original-sense-" + "a" * 32
            else:
                rows.insert(1, {"type": "effect", "effect": "attack_entity", "action_id": "forged"})
            path.write_bytes(b"".join(_line(row) for row in rows))
            report["raw_native_command_file_sha256"]["RelayA"] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    elif tamper == "wrong-request":
        first["native_request_id"] = "i1-original-sense-" + "f" * 32
    elif tamper == "duplicate-request":
        second["native_request_id"] = first["native_request_id"]
    elif tamper == "foreign-self":
        first["native_session_id"] = "native-B"
    elif tamper == "invented-sense-ref":
        first["sense_revision"] = "mineflayer:invented:2"
    elif tamper == "wrong-native-seq":
        first["native_seq"] += 1
    elif tamper == "wrong-native-provenance":
        first["native_observation_ref"] = "foreign"
    elif tamper == "forged-paper-hash":
        first["paper_log_sha256"] = "e" * 64
    elif tamper == "wrong-paper-tick":
        first["paper_tick"] += 1
    elif tamper == "wrong-paper-ack":
        first["paper_tick_source_ref"] = "wrong-Paper-ACK"
    elif tamper == "paper-actor":
        first["paper_actor_uuid"] = _ACTORS["B"]
    elif tamper == "forged-goal":
        first["goal_ids"] = ["DEFEND_SELF"]
    elif tamper == "forged-l1-options":
        first["l1_descriptions"] = ["ATTACK", "DEFER"]
    elif tamper == "invented-exploration":
        first["inquiry_ref"] = "invented-Question"
    elif tamper == "stale-resident-epoch":
        first["resident_epoch"] = 0
    elif tamper == "physical-authority":
        first["action_issue_authorized"] = True
    elif tamper == "model-invoked":
        first["model_invoked"] = True
    elif tamper in ("extra-native-probe", "changed-raw-snapshot"):
        raw = evidence / "native-RelayA-native-A.jsonl"
        lines = [json.loads(x) for x in raw.read_bytes().splitlines()]
        if tamper == "extra-native-probe":
            extra, _ = _native("A", 4, "i1-original-sense-" + "9" * 32)
            lines.append(extra)
        else:
            lines[2]["snapshot"]["food"] = 20
        raw.write_bytes(b"".join(_line(x) for x in lines))
        report["raw_native_file_sha256"]["RelayA"] = hashlib.sha256(
            raw.read_bytes()
        ).hexdigest()
    with pytest.raises((I1IndependentAuditHold, ValueError, TypeError)):
        _audit_i1_epochs(
            report=report, evidence=evidence, executable=executable,
            owners=owners,
        )


def test_legacy_stage28_auditor_refuses_to_promote_i1_report(tmp_path):
    result = tmp_path / "i1.json"
    result.write_text(json.dumps({
        "schema": 1,
        "classification": "I1_ORIGINAL_CPU_SENSE_CAPTURED_INDEPENDENT_AUDIT_PENDING",
        "i1_original_cpu_sense_enabled": True,
    }))
    with pytest.raises(Stage28c2bIndependentAuditHold):
        independently_audit_recovered_real_rejoin(
            result, generation=tmp_path, restored=tmp_path,
            stage28b_evidence=tmp_path, executable=tmp_path,
        )


def test_i1_independent_rejects_changed_paper_ack_file_even_with_valid_manifest(
    tmp_path,
):
    report, evidence, executable, owners = _fixture(tmp_path)
    ref = report["i1_cpu_epochs"]["epochs"][0]["paper_tick_source_ref"]
    nonce = ref.split(":")[-3]
    path = executable / "plugins" / "P0BRecorder" / "p0d-ticks" / "acks" / (
        nonce + ".ack"
    )
    assert path.is_file()
    path.write_bytes(path.read_bytes() + b"forged=1\\n")
    with pytest.raises(I1IndependentAuditHold, match="Paper ACK/prefix"):
        _audit_i1_epochs(
            report=report, evidence=evidence, executable=executable,
            owners=owners,
        )


def test_i1_base_auditor_cannot_claim_old_stage28_promotion(tmp_path, monkeypatch):
    from experiments import i_lane_i1_independent_cpu_audit_dev as audit

    captured = []

    def base(result_path, **kwargs):
        captured.append(kwargs)
        return {"classification": "REAL_RESTORED_WORLD_ORIGINAL_A_B_NATIVE_REJOIN_WORLDBODY_DEV"}

    monkeypatch.setattr(audit, "independently_audit_recovered_real_rejoin", base)
    with pytest.raises(I1IndependentAuditHold, match="base not qualified"):
        audit.independently_audit_i1_original_cpu(
            tmp_path / "no-source.json",
            generation=tmp_path, restored=tmp_path,
            stage28b_evidence=tmp_path, executable=tmp_path,
        )
    assert captured[0]["expected_i1_cpu_sense"] is True
    assert captured[0]["expected_gemma_posts"] == 0
