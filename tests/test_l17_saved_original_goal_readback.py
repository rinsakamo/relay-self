"""L17 saved S49 original readback: synthetic files only, no World activity."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict

import pytest

import test_l13_independent_goal_receipt as l13
import test_l16_s49_first_action_original_capture as l16
from adapters.mineflayer.l16_first_action_goal_originals import (
    inspect_l16_first_action_prefix,
)
from adapters.mineflayer.l17_saved_original_goal_readback import (
    audit_saved_l16_capture,
    main,
)


def saved_fixture(tmp_path):
    args = l16.fixture()
    sid, aid = args["session_id"], args["action_id"]
    ids = (f"l16:{sid}:{aid}:goal-1", f"l16:{sid}:{aid}:goal-2")
    rx = args["received_original"].splitlines(keepends=True)
    for index, request in ((-2, ids[0]), (-1, ids[1])):
        data = json.loads(rx[index])
        data["request_id"] = request
        rx[index] = l13.raw(data)
    args["received_original"] = b"".join(rx)
    tx = args["sent_original"].splitlines(keepends=True)
    for index, request in ((-2, ids[0]), (-1, ids[1])):
        data = json.loads(tx[index])
        data["request_id"] = request
        tx[index] = l13.raw(data)
    args["sent_original"] = b"".join(tx)
    from relay_self.l14_original_bridge_goal_window import _sha
    from test_l14_original_bridge_goal_window import _index

    args["s7_receipt"] = _index(
        args["received_original"], args["sent_original"],
    )
    args["first_probe_request_id"], args["second_probe_request_id"] = ids
    window = inspect_l16_first_action_prefix(**args)
    root = tmp_path / "fresh"
    root.mkdir()
    (root / "native_bridge_received_original.jsonl").write_bytes(
        args["received_original"],
    )
    (root / "native_bridge_sent_original.jsonl").write_bytes(
        args["sent_original"],
    )
    (root / "native_bridge_source_receipt.json").write_bytes(
        l13.raw(args["s7_receipt"]),
    )
    (root / "l16_pre_world_goal_plan.json").write_bytes(args["plan_original"])
    report = tmp_path / "s49-report.json"
    report.write_bytes(l13.raw({
        "session_id": sid,
        "actual_native_actions": [{"action": aid}],
        "l16_capture": {
            "status": "SOURCE_PREFIX_CAPTURED_UNQUALIFIED",
            "root": str(root),
            "s7_index": args["s7_receipt"],
            "window": asdict(window),
            "first_action_only": True,
            "later_session_actions_not_in_recorded_prefix": True,
            "real_l10_pairs": 0,
            "external_goal_owner_independent": False,
        },
    }))
    assert _sha(args["received_original"]) == window.received_sha256
    return root, report, args


def test_readonly_cli_audits_saved_original_no_external_goal(tmp_path, capsys):
    root, report, args = saved_fixture(tmp_path)
    files = [p for p in tmp_path.rglob("*") if p.is_file()]
    original = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    assert main(["--root", str(root), "--s49-report", str(report)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["classification"] == "waiting_for_independent_s16_goal_originals"
    assert result["l16_diagnostic_goal_status"] == "REACHED"
    assert result["received_sha256"] == args["s7_receipt"]["received_sha256"]
    assert result["independent_goal_original_present"] is False
    assert result["qualified_real_learning_pairs"] == 0
    assert result["s10_updates"] == result["s11_habit_grants"] == 0
    assert original == {
        p: hashlib.sha256(p.read_bytes()).hexdigest() for p in files
    }


@pytest.mark.parametrize("fault", [
    "received_changed", "sent_changed", "index_changed", "plan_changed",
    "report_goal_changed", "report_action_changed", "unsealed",
    "report_sha_changed", "report_missing", "source_missing",
    "root_symlink", "report_symlink", "foreign_report_session",
])
def test_bad_saved_original_or_report_rejected(tmp_path, fault):
    root, report, _ = saved_fixture(tmp_path)
    received = root / "native_bridge_received_original.jsonl"
    sent = root / "native_bridge_sent_original.jsonl"
    index = root / "native_bridge_source_receipt.json"
    plan = root / "l16_pre_world_goal_plan.json"
    if fault == "received_changed":
        received.write_bytes(received.read_bytes() + b'{"bad":true}\n')
    elif fault == "sent_changed":
        sent.write_bytes(sent.read_bytes() + b'{"type":"shutdown"}\n')
    elif fault == "index_changed":
        d = json.loads(index.read_bytes())
        d["received_sha256"] = "0"*64
        index.write_bytes(l13.raw(d))
    elif fault == "plan_changed":
        d = json.loads(plan.read_bytes())
        d["target_z"] += 1
        plan.write_bytes(l13.raw(d))
    elif fault == "source_missing":
        received.unlink()
    elif fault == "report_missing":
        report.unlink()
    elif fault == "root_symlink":
        link = tmp_path / "link-root"
        link.symlink_to(root, target_is_directory=True)
        root = link
    elif fault == "report_symlink":
        link = tmp_path / "link-report"
        link.symlink_to(report)
        report = link
    else:
        d = json.loads(report.read_bytes())
        if fault == "report_goal_changed":
            d["l16_capture"]["window"]["observed_goal_status"] = "NOT_REACHED"
        elif fault == "report_action_changed":
            d["actual_native_actions"][0]["action"] = "foreign"
        elif fault == "unsealed":
            d["l16_capture"]["status"] = "INCOMPLETE_NO_GOAL_LABEL"
        elif fault == "report_sha_changed":
            d["l16_capture"]["s7_index"]["received_sha256"] = "0"*64
        elif fault == "foreign_report_session":
            d["session_id"] = "foreign"
        report.write_bytes(l13.raw(d))
    with pytest.raises((ValueError, OSError, KeyError, TypeError)):
        audit_saved_l16_capture(root, report)


def test_default_cli_does_not_read_files(monkeypatch, capsys):
    from adapters.mineflayer import l17_saved_original_goal_readback as module

    def fail(*_args, **_kwargs):
        pytest.fail("default L17 CLI cannot access physical files")

    monkeypatch.setattr(module, "audit_saved_l16_capture", fail)
    assert main([]) == 0
    assert json.loads(capsys.readouterr().out)["world_reads"] == 0


def test_one_argument_cli_is_rejected_before_file_io(capsys, tmp_path):
    with pytest.raises(SystemExit) as error:
        main(["--root", str(tmp_path)])
    assert error.value.code == 2


def test_rejected_cli_has_no_training_output(tmp_path, capsys):
    root, report, _ = saved_fixture(tmp_path)
    (root / "native_bridge_sent_original.jsonl").write_bytes(b"tampered\n")
    assert main(["--root", str(root), "--s49-report", str(report)]) == 2
    result = json.loads(capsys.readouterr().err)
    assert result["classification"] == "L17_ORIGINAL_READBACK_BLOCKED"
    assert result["qualified_real_learning_pairs"] == 0
