"""Offline native OS fixture log ↔ W3 receipt ↔ W4 epoch negative gates."""
from __future__ import annotations

import asyncio
import hashlib
import json
import os

import pytest

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_os_process_receipt_dev import (
    review_s49_os_process_receipt_dev,
)
from adapters.mineflayer.s49_paper_backward_wait_dev import (
    BEGIN,
    TICK,
    project_s49_backward_paper_dev,
)
from adapters.mineflayer.s49_w4_epoch_source_dev import (
    review_s49_w4_read_epoch_dev,
)
from test_s49_paper_custody_dev import PLAYER
from test_s49_w4_epoch_source_dev import local_read_epoch, setup

PID = 19042
START = "736211"


def make_os_log(tmp_path, w3, *, observer=False):
    receipt_path = w3 / "w3-node-stdout-receipt.json"
    data = receipt_path.read_bytes()
    receipt = json.loads(data)
    envelope = {
        "test": "tests/test_s49_native_os_custody.py::local_fixture",
        "python": "3.12.3",
        "utc": "2026-10-25T07:00:00+00:00",
    }

    def row(event, **fields):
        return {"event": event, **envelope, **fields}

    rows = [
        row("spawn", pid=PID, starttime=START, parent_pid=1500,
            argv=["/usr/bin/node", "inert.js"],
            proc_stat=f"{PID} (node) S " + " ".join(["0"] * 18)
            + f" {START} 0 0"),
        row("wait_enter", pid=PID, starttime=START),
        row("wait_return", pid=PID, starttime=START, result=0,
            returncode=0, proc_absent=True),
        row("final_process", pid=PID, starttime=START,
            returncode=0, proc_absent=True),
        row("w3_receipt", path=str(receipt_path),
            sha256=hashlib.sha256(data).hexdigest(), content=receipt),
    ]
    if observer:
        rows.insert(1, row("independent_observer_ack",
                           pid=PID, starttime=START))
    path = tmp_path / "native-os-events.jsonl"
    write_rows(path, rows)
    return path, rows


def write_rows(path, rows):
    path.write_bytes(b"".join(
        (json.dumps(row, sort_keys=True) + "\n").encode("utf-8")
        for row in rows
    ))


def scene(monkeypatch, tmp_path):
    capture, w3, cursor, archive, producer = setup(monkeypatch, tmp_path)
    epoch = review_s49_w4_read_epoch_dev(
        capture, producer, local_read_epoch(capture),
    )
    log, rows = make_os_log(tmp_path, w3)
    return capture, w3, cursor, archive, producer, epoch, log, rows


def review(w3, producer, epoch, log):
    return review_s49_os_process_receipt_dev(
        native_os_log=log, w3_root=w3,
        producer_review=producer, w4_epoch_review=epoch,
    )


def test_local_os_pid_starttime_reap_w3_receipt_consistent_but_untrusted(
    monkeypatch, tmp_path,
):
    _capture, w3, _cursor, _archive, producer, epoch, log, _rows = (
        scene(monkeypatch, tmp_path)
    )
    out = review(w3, producer, epoch, log)
    assert out["status"] == "OS_EVENT_LOG_AND_W3_RECEIPT_SHAPE_ONLY"
    assert out["os_recorded_pid"] == PID
    assert out["os_recorded_proc_starttime"] == START
    assert out["w3_stdout_sha256"] == producer["w3_stdout_sha256"]
    assert out["w4_local_epoch"] == epoch["local_read_epoch"]
    assert out["os_event_log_sha256"] == hashlib.sha256(log.read_bytes()).hexdigest()
    assert out["os_observer_identity_independently_authenticated"] is False
    assert out["os_process_identity_attested"] is False
    assert out["original_s49_owner_process_to_w3_bound"] is False
    assert out["cross_source_issuer_epoch_attested"] is False
    assert out["clear_caused_paper_back_off"] == "NOT_ATTESTED"
    assert out["source_bound_tick"] is None
    assert out["wait_interval_ref"] is None
    assert out["wait_ticks_admitted"] == 0
    assert out["p1_fatigue_recovered"] == 0.0
    assert out["qualification_go"] is False


def test_self_declared_observer_ack_still_cannot_sign_original_issuer(
    monkeypatch, tmp_path,
):
    _capture, w3, _cursor, _archive, producer, epoch, log, _rows = (
        scene(monkeypatch, tmp_path)
    )
    log.unlink()
    make_os_log(tmp_path, w3, observer=True)
    out = review(w3, producer, epoch, log)
    assert out["os_observer_ack_in_local_log"] is True
    assert out["os_observer_identity_independently_authenticated"] is False
    assert out["os_process_identity_attested"] is False


@pytest.mark.parametrize("case", (
    "wrong_pid", "pid_as_bool", "wrong_start", "foreign_proc_stat",
    "proc_stat_wrong_start", "wrong_parent", "no_argv",
    "wait_return_missing", "final_missing", "receipt_missing",
    "duplicate_spawn", "duplicate_wait", "reordered_reap",
    "abnormal_exit", "unreaped", "wait_wrong_result", "wait_bool",
    "foreign_receipt_path", "foreign_receipt_hash", "forged_receipt",
    "different_w3_session", "forged_w3_source", "epoch_foreign_action",
    "epoch_fake_os_identity", "mixed_test", "bad_utc", "truncated_line",
    "extra_unknown_event", "symlink", "hardlink", "relative",
    "receipt_tampered", "w3_raw_tampered", "observer_wrong_start",
))
def test_bad_native_os_log_and_false_epoch_authority_rejected(
    monkeypatch, tmp_path, case,
):
    _capture, w3, _cursor, _archive, producer, epoch, log, rows = (
        scene(monkeypatch, tmp_path)
    )
    if case == "wrong_pid":
        rows[2]["pid"] += 1
    elif case == "pid_as_bool":
        rows[0]["pid"] = True
    elif case == "wrong_start":
        rows[3]["starttime"] = "736212"
    elif case == "foreign_proc_stat":
        rows[0]["proc_stat"] = rows[0]["proc_stat"].replace(
            f"{PID} (", "9999 (", 1,
        )
    elif case == "proc_stat_wrong_start":
        rows[0]["proc_stat"] = rows[0]["proc_stat"].replace(START, "736212")
    elif case == "wrong_parent":
        rows[0]["parent_pid"] = 0
    elif case == "no_argv":
        rows[0]["argv"] = []
    elif case == "wait_return_missing":
        rows.pop(2)
    elif case == "final_missing":
        rows.pop(3)
    elif case == "receipt_missing":
        rows.pop()
    elif case == "duplicate_spawn":
        rows.insert(1, dict(rows[0]))
    elif case == "duplicate_wait":
        rows.insert(3, dict(rows[2]))
    elif case == "reordered_reap":
        rows[2], rows[3] = rows[3], rows[2]
    elif case == "abnormal_exit":
        rows[2]["returncode"] = -9
    elif case == "unreaped":
        rows[3]["proc_absent"] = False
    elif case == "wait_wrong_result":
        rows[2]["result"] = 1
    elif case == "wait_bool":
        rows[2]["result"] = True
    elif case == "foreign_receipt_path":
        rows[-1]["path"] = "/tmp/foreign/w3-node-stdout-receipt.json"
    elif case == "foreign_receipt_hash":
        rows[-1]["sha256"] = "f" * 64
    elif case == "forged_receipt":
        rows[-1]["content"] = {"schema": "self_attested"}
    elif case == "different_w3_session":
        producer = {**producer, "session_id": "foreign"}
    elif case == "forged_w3_source":
        producer = {**producer, "raw_native_tcp_attested": True}
    elif case == "epoch_foreign_action":
        epoch = {**epoch, "action_id": "wrong"}
    elif case == "epoch_fake_os_identity":
        epoch = {**epoch, "os_process_identity_attested": True}
    elif case == "mixed_test":
        rows[2]["test"] = "unrelated"
    elif case == "bad_utc":
        rows[0]["utc"] = "2026-10-25T07:00:00"
    elif case == "truncated_line":
        log.write_bytes(log.read_bytes()[:-1])
    elif case == "extra_unknown_event":
        rows.insert(1, {**rows[0], "event": "os_auth_granted"})
    elif case == "symlink":
        alias = tmp_path / "native-os-alias.log"
        alias.symlink_to(log)
        log = alias
    elif case == "hardlink":
        os.link(log, tmp_path / "native-hardlink.log")
    elif case == "relative":
        log = type(log)("native-os-events.jsonl")
    elif case == "receipt_tampered":
        (w3 / "w3-node-stdout-receipt.json").write_bytes(b"{}\n")
    elif case == "w3_raw_tampered":
        (w3 / "w3-node-stdout.raw.jsonl").write_bytes(b"{}\n")
    elif case == "observer_wrong_start":
        rows.insert(1, {**rows[0], "event": "independent_observer_ack",
                        "starttime": "wrong"})
    if case not in ("truncated_line", "symlink", "hardlink", "relative",
                    "receipt_tampered", "w3_raw_tampered"):
        write_rows(log, rows)
    with pytest.raises(BoundaryRejected):
        review(w3, producer, epoch, log)


def _callbacks(paper: str) -> str:
    return "\n".join(
        row for row in paper.splitlines()
        if row.startswith((BEGIN, TICK))
    ) + "\n"


def test_owner_report_receives_unprivileged_os_review_before_wait_arm(
    monkeypatch, tmp_path,
):
    capture, w3, cursor, archive, _producer, _epoch, log, _rows = (
        scene(monkeypatch, tmp_path)
    )
    paper = archive.paper_log_bytes.decode()
    dest = tmp_path / "original-owner-os-review.json"
    report = asyncio.run(project_s49_backward_paper_dev(
        capture, _callbacks(paper), output_path=dest,
        observer_transcript=paper, expected_player_uuid=PLAYER,
        require_preaction_edge=True, custody_archive=archive,
        w3_original_root=w3, paper_collector_cursor=cursor,
        w4_read_audit=local_read_epoch(capture),
        os_native_event_log=log,
    ))
    assert report == json.loads(dest.read_text())
    assert report["status"] == "SAME_ACTION_PAPER_SHAPE_ONLY"
    assert report["os_process_receipt_review"]["status"] == (
        "OS_EVENT_LOG_AND_W3_RECEIPT_SHAPE_ONLY"
    )
    assert report["os_process_receipt_review"]["os_process_identity_attested"] is False
    assert report["source_bound_tick"] is None
    assert report["wait_interval_ref"] is None
    assert report["wait_ticks_admitted"] == 0
    assert report["p1_fatigue_recovered"] == 0.0


@pytest.mark.parametrize("case", ("no_w4", "bad_log", "no_w3"))
def test_owner_fails_closed_if_os_gate_incomplete(
    monkeypatch, tmp_path, case,
):
    capture, w3, cursor, archive, _producer, _epoch, log, _rows = (
        scene(monkeypatch, tmp_path)
    )
    if case == "bad_log":
        log.write_bytes(log.read_bytes()[:-1])
    dest = tmp_path / "bad-original-owner-os.json"
    paper = archive.paper_log_bytes.decode()
    with pytest.raises(BoundaryRejected):
        asyncio.run(project_s49_backward_paper_dev(
            capture, _callbacks(paper), output_path=dest,
            observer_transcript=paper, expected_player_uuid=PLAYER,
            require_preaction_edge=True, custody_archive=archive,
            w3_original_root=None if case == "no_w3" else w3,
            paper_collector_cursor=None if case == "no_w3" else cursor,
            w4_read_audit=None if case == "no_w4" else local_read_epoch(capture),
            os_native_event_log=log,
        ))
    assert json.loads(dest.read_text())["status"] == "REJECTED_NOT_QUALIFIED"
    assert capture._executor.wait_phase == "NEW"
