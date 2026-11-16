"""#904 Stage23b real report consistency and original stdout replay negative controls.

All streams in these tests are SYNTHETIC; test reenactment must not be
confused with recovery of missing Stage23a raw bytes.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import pytest

from adapters.mineflayer.process_session import (
    MineflayerProcessIOError,
    MineflayerProcessSession,
)
from adapters.mineflayer.python_protocol import (
    MineflayerEffectResult,
    MineflayerObservation,
)
from experiments.p0d_real_resident_presence_dev import (
    RealResidentPresenceRefusal,
    _adopt_verified_trial_report,
)
from relay_self.physical_issue_admission_dev import PhysicalIssueAdmission
from relay_self.resident_move_raw_audit_dev import (
    ResidentMoveRawAuditError,
    readback_owned_move_native_source,
)
from test_mineflayer_process_session import FakeProcess, observation_line, started_line
from test_p0d_resident_move_issuer_dev import ScriptedNative, _selected


def _raw_row(item):
    if isinstance(item, MineflayerEffectResult):
        return {"type": "effect_result", **asdict(item)}
    if isinstance(item, MineflayerObservation):
        return {"type": "observation", **asdict(item)}
    raise AssertionError("only original native effect/probe rows")


def _build_raw_original_stream(tmp_path):
    """Use original issuer/WAL; encode a LOCAL fixture, NOT native source proof."""
    args = _selected(tmp_path)
    gate = PhysicalIssueAdmission(
        {"A": "native-A"}, resident_mode=True, allow_resident_move=True,
    )
    native = ScriptedNative("native-A")
    native.gate = lambda sid, effect, action_id: gate.require_native_effect(
        self_id="A", native_session_id=sid, effect=effect, action_id=action_id,
    )

    async def run():
        return await gate.issue_move(native, **args)

    receipt = asyncio.run(run())
    stream = (
        args["current_probe"],
        receipt.start_ack,
        receipt.stop_ack,
        *receipt.all_stop_probes,
    )
    assert len(receipt.all_stop_probes) >= 3
    assert [v.seq for v in stream] == list(range(2, 2 + len(stream)))
    raw = tmp_path / "synthetic-stdout.jsonl"
    raw.write_bytes(
        b"".join(
            (json.dumps(_raw_row(row), sort_keys=True) + "\n").encode()
            for row in stream
        )
    )
    return raw, args, receipt


def test_original_move_raw_source_readback_all_settle_samples_and_wal(tmp_path):
    raw, args, receipt = _build_raw_original_stream(tmp_path)
    audit = readback_owned_move_native_source(
        raw_path=raw, journal_path=args["journal"].path, self_id="A",
        action_id=args["proposal"].binding.action_id,
        current_probe=args["current_probe"], receipt=receipt,
    )
    assert audit["source_sha256"] == hashlib.sha256(raw.read_bytes()).hexdigest()
    assert audit["native_start_ack"]["action_id"] == "move-A-start"
    assert audit["native_stop_ack"]["action_id"] == "move-A-stop"
    assert audit["canonical_wal_digest"] == receipt.journal_sha256
    assert len(audit["all_stop_probes"]) == len(receipt.all_stop_probes)
    assert all(
        set(row) == {"seq", "request_id", "tick", "position"}
        for row in audit["all_stop_probes"]
    )
    assert not audit["paper_action_id_causal_ticket"]


@pytest.mark.parametrize("fault", [
    "missing-last-probe", "forged-ack-action", "tampered-position",
    "foreign-session", "duplicate-ack", "missing-newline",
])
def test_original_move_raw_source_forgery_never_attests(tmp_path, fault):
    raw, args, receipt = _build_raw_original_stream(tmp_path)
    lines = [json.loads(x) for x in raw.read_text().splitlines()]
    if fault == "missing-last-probe":
        lines.pop()
    elif fault == "forged-ack-action":
        lines[1]["action_id"] = "other-parent-start"
    elif fault == "tampered-position":
        lines[-1]["snapshot"]["position"]["z"] += 0.4
    elif fault == "foreign-session":
        lines[-1]["session_id"] = "foreign-native"
    elif fault == "duplicate-ack":
        lines.insert(2, dict(lines[1]))
    data = "".join(json.dumps(x) + "\n" for x in lines).encode()
    if fault == "missing-newline":
        data = data.rstrip(b"\n")
    raw.write_bytes(data)
    with pytest.raises(ResidentMoveRawAuditError):
        readback_owned_move_native_source(
            raw_path=raw, journal_path=args["journal"].path, self_id="A",
            action_id="move-A", current_probe=args["current_probe"],
            receipt=receipt,
        )


def _sidecar(original_file: Path, digest: str) -> str:
    source_sha = hashlib.sha256(Path(original_file).read_bytes()).hexdigest()
    return json.dumps({
        "classification": "OWNED_NATIVE_MOVE_RAW_SOURCE_READBACK_DEV",
        "original_self_id": "B",
        "original_native_session": "native-B",
        "original_action_id": "original-move",
        "canonical_wal_digest": digest,
        "source_sha256": source_sha,
        "all_stop_probes": [{}, {}, {}],
        "native_start_ack": {"action_id": "original-move-start"},
        "native_stop_ack": {"action_id": "original-move-stop"},
        "paper_action_id_causal_ticket": False,
        "autonomous_l1_skill_selection": False,
    }, sort_keys=True) + "\n"


def test_real_report_true_is_derived_from_original_terminal_plus_raw_and_paper(tmp_path):
    raw = tmp_path / "raw.jsonl"
    raw.write_bytes(b"source-fixture\n")
    checked = tmp_path / "audit.json"
    checked.write_text(_sidecar(raw, "a" * 64))
    info = {
        "classification": "DEV_ORIGINAL_B_NATIVE_MOVE_SETTLED",
        "original_action_id": "original-move",
        "original_canonical_wal_sha256": "a" * 64,
        "b_native_session": "native-B",
        "autonomous_l1_skill_selection": False,
        "paper_action_causation": False,
        "independent_native_source": {
            "readback_classification": "OWNED_NATIVE_MOVE_RAW_SOURCE_READBACK_DEV",
            "all_settle_probes": 3,
            "raw_file": str(raw),
            "raw_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
            "readback_file": str(checked),
            "readback_sha256": hashlib.sha256(checked.read_bytes()).hexdigest(),
        },
    }
    trial = {
        "b_actual_physical_action": True,
        "b_physical_wal_outcome": True,
        "b_original_selected_move": info,
        "b_move_action_causality": False,
        "paper_player_continuity": "DEV_B_PAPER_MOVED_AFTER_A_LOGOUT",
        "world_only_generation": "source-qualified-world-gen",
        "world_only_new_session": "new-paper-session",
    }
    report = {
        "classification": "HOLD",
        "real_b_physical_action": None,
        "steps": [],
    }
    _adopt_verified_trial_report(
        report, trial, b_selected_move_dev=True, world_only=True,
    )
    assert report["real_b_physical_action"] is True
    assert report["real_b_physical_wal_outcome"] is True
    assert report["native_move_raw_source_attested"] is True
    assert report["steps"][0]["b_actual_physical_action"] is True
    assert report["classification"] == "REAL_PAPER_B_MOVE_CORRELATED_WORLD_ONLY_DEV"


@pytest.mark.parametrize("fault", [
    "nested_false", "missing_source", "raw_modified", "paper_presence_only",
    "world_missing", "unrequested_move",
])
def test_report_never_claims_real_b_move_on_unverified_or_conflicting_source(
    tmp_path, fault,
):
    raw = tmp_path / "raw"
    raw.write_bytes(b"correct-original-source")
    audit = tmp_path / "checked"
    audit.write_text(_sidecar(raw, "d" * 64))
    move = {
        "classification": "DEV_ORIGINAL_B_NATIVE_MOVE_SETTLED",
        "original_action_id": "original-move",
        "original_canonical_wal_sha256": "d" * 64,
        "b_native_session": "native-B",
        "autonomous_l1_skill_selection": False,
        "paper_action_causation": False,
        "independent_native_source": {
            "readback_classification": "OWNED_NATIVE_MOVE_RAW_SOURCE_READBACK_DEV",
            "all_settle_probes": 3,
            "raw_file": str(raw),
            "raw_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
            "readback_file": str(audit),
            "readback_sha256": hashlib.sha256(audit.read_bytes()).hexdigest(),
        },
    }
    trial = {
        "b_actual_physical_action": True,
        "b_physical_wal_outcome": True,
        "b_original_selected_move": move,
        "b_move_action_causality": False,
        "paper_player_continuity": "DEV_B_PAPER_MOVED_AFTER_A_LOGOUT",
        "world_only_generation": "committed-world",
        "world_only_new_session": "new-session",
    }
    if fault == "nested_false":
        trial["b_actual_physical_action"] = False
    elif fault == "missing_source":
        move["independent_native_source"] = None
    elif fault == "raw_modified":
        raw.write_bytes(b"posthoc-tamper")
    elif fault == "paper_presence_only":
        trial["paper_player_continuity"] = "DEV_B_PAPER_PRESENCE_AFTER_A_LOGOUT"
    elif fault == "world_missing":
        trial.pop("world_only_generation")
    report = {"classification": "HOLD", "real_b_physical_action": None, "steps": []}
    with pytest.raises(RealResidentPresenceRefusal):
        _adopt_verified_trial_report(
            report, trial, b_selected_move_dev=fault != "unrequested_move",
            world_only=True,
        )
    assert report == {
        "classification": "HOLD", "real_b_physical_action": None, "steps": [],
    }


def test_presence_only_report_remains_false_and_no_move_claim():
    report = {"classification": "HOLD", "real_b_physical_action": False, "steps": []}
    _adopt_verified_trial_report(
        report,
        {
            "b_actual_physical_action": False,
            "b_physical_wal_outcome": False,
            "b_original_selected_move": None,
        },
        b_selected_move_dev=False, world_only=False,
    )
    assert report["classification"] == "REAL_PAPER_RESIDENT_PRESENCE_DEV"
    assert report["real_b_physical_action"] is False
    assert not report["native_move_raw_source_attested"]


def test_exact_mineflayer_native_process_raw_source_bytes_fsynced_once(
    monkeypatch, tmp_path,
):
    proc = FakeProcess([started_line(), observation_line()])

    async def fake_launch(*_args, **_kwargs):
        return proc

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_launch)

    async def scenario():
        from adapters.mineflayer.python_protocol import MineflayerLaunchConfig

        session = await MineflayerProcessSession.launch(MineflayerLaunchConfig())
        raw = tmp_path / "original-owned-native.stdout.jsonl"
        session.start_raw_source_audit(raw)
        with pytest.raises(MineflayerProcessIOError, match="already used"):
            session.start_raw_source_audit(tmp_path / "other")
        entry = await session.receive()
        assert isinstance(entry, MineflayerObservation)
        session.finish_raw_source_audit()
        assert raw.read_bytes() == observation_line()
        with pytest.raises(MineflayerProcessIOError, match="not active"):
            session.finish_raw_source_audit()
        with pytest.raises(MineflayerProcessIOError, match="already used"):
            session.start_raw_source_audit(tmp_path / "late")

    asyncio.run(scenario())
