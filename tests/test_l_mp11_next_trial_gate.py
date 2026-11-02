"""New physical trial gate; deterministic fixtures, never actual Paper or Gemma."""
from __future__ import annotations

from pathlib import Path

import pytest

from tools import l_mp11_next_trial_gate as gate

HEAD = "a" * 40
ENDPOINT = "http://127.0.0.1:8080/v1/chat/completions"
MODEL = "relay-self-gemma4-12b-q4km"


def prepped(tmp_path, monkeypatch):
    root = tmp_path / "new-trial"
    root.mkdir()
    (root / "gemma-strict-wire-probe").mkdir()
    report = root / "gemma-strict-wire-probe" / "gemma-structured-preflight.json"
    report.write_text('{"synthetic":"probe"}')
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").write_text("gitdir: /does-not-matter")
    monkeypatch.setattr(gate, "_git_head", lambda p: HEAD)
    monkeypatch.setattr(gate, "verify_preflight_report", lambda *a, **kw: {
        "status": "REAL_GEMMA_WIRE_PROBE_PASS_UNATTESTED_WEIGHTS",
        "execution_head": HEAD,
    })
    return root, repo, report


def test_new_capture_root_is_built_before_java_and_empty(tmp_path, monkeypatch):
    root, repo, report = prepped(tmp_path, monkeypatch)
    readback = gate.prepare_trial(
        root, repo, report, expected_head=HEAD,
        endpoint=ENDPOINT, model=MODEL,
    )
    capture = root / "world" / "native-stdout"
    assert capture.is_dir()
    assert capture.is_absolute()
    assert list(capture.iterdir()) == []
    assert readback["actual_worlds_started"] == 0
    assert readback["retries_allowed"] == 0
    assert readback["preflight_sha256"] == gate.sha256(report)
    assert readback["classification"] == "CAPTURE_READY_ONLY_NOT_WORLD_STARTED"
    assert not (root / gate.STARTED).exists()
    with pytest.raises(gate.NextWorldGateRejected):
        gate.prepare_trial(
            root, repo, report, expected_head=HEAD, endpoint=ENDPOINT,
            model=MODEL,
        )


def test_absent_probe_or_mismatched_sha_or_dirty_capture_refuse(tmp_path, monkeypatch):
    root, repo, report = prepped(tmp_path, monkeypatch)
    with pytest.raises(gate.NextWorldGateRejected):
        gate.prepare_trial(
            root, repo, root / "gemma-strict-wire-probe" / "missing",
            expected_head=HEAD, endpoint=ENDPOINT, model=MODEL,
        )
    gate.prepare_trial(
        root, repo, report, expected_head=HEAD, endpoint=ENDPOINT, model=MODEL,
    )
    report.write_text('{"tampered":"after prepare"}')
    with pytest.raises(gate.NextWorldGateRejected, match="changed since"):
        gate.run_once(root, repo, expected_head=HEAD, command=[])
    report.write_text('{"synthetic":"probe"}')
    (root / "world/native-stdout/used.log").write_text("not empty")
    with pytest.raises(gate.NextWorldGateRejected, match="not empty"):
        gate.run_once(root, repo, expected_head=HEAD, command=[])


def test_capture_symlink_ancestor_and_wrong_head_are_fail_closed(tmp_path, monkeypatch):
    root, repo, report = prepped(tmp_path, monkeypatch)
    link = tmp_path / "link"
    link.symlink_to(root, target_is_directory=True)
    with pytest.raises(gate.NextWorldGateRejected, match="symlink"):
        gate.prepare_trial(
            link, repo, link / "gemma-strict-wire-probe" /
            "gemma-structured-preflight.json",
            expected_head=HEAD, endpoint=ENDPOINT, model=MODEL,
        )
    with pytest.raises(gate.NextWorldGateRejected, match="HEAD"):
        gate.prepare_trial(
            root, repo, report, expected_head="b" * 40,
            endpoint=ENDPOINT, model=MODEL,
        )
    assert not (root / "world").exists()


def fake_proc(proc_root: Path, pid: int, ppid: int, exe: str, start: int):
    p = proc_root / str(pid)
    p.mkdir()
    # Linux /proc stat fields start at index 3 after the closing ")"
    words = ["S", str(ppid)] + ["0"] * 17 + [str(start), "0", "0"]
    (p / "stat").write_text(f"{pid} (process with space) " + " ".join(words))
    (p / "cmdline").write_bytes(
        f"{exe}\x00-server\x00/absolute/paper-1.21.8.jar\x00".encode()
    )
    (p / "cwd").symlink_to("/absolute/world", target_is_directory=True)
    (p / "exe").symlink_to(exe)


def test_actual_proc_ppid_tree_includes_absolute_jar_without_argv_alias(tmp_path):
    fake_proc(tmp_path, 101, 1, "/usr/bin/python3", 100)
    fake_proc(tmp_path, 102, 101, "/opt/java21/bin/java", 103)
    fake_proc(tmp_path, 103, 101, "/opt/node22/bin/node", 104)
    fake_proc(tmp_path, 104, 102, "/bin/sh", 105)
    fake_proc(tmp_path, 105, 5, "/opt/java21/bin/java", 106)
    tree = gate.owned_tree(101, proc_root=tmp_path)
    assert [p["pid"] for p in tree] == [101, 102, 103, 104]
    assert tree[1]["start_ticks"] == 103
    assert tree[1]["exe"] == "/opt/java21/bin/java"
    assert tree[1]["cwd"] == "/absolute/world"
    assert "/absolute/paper-1.21.8.jar" in tree[1]["argv"]


def test_missing_root_process_is_unattested_not_no_processes(tmp_path):
    fake_proc(tmp_path, 8, 1, "/usr/bin/java", 102)
    assert gate.owned_tree(99, proc_root=tmp_path) == []
    assert gate.read_proc_status(99, proc_root=tmp_path) is None


def physical_command(root):
    capture = root / "world" / "native-stdout"
    return [
        "/opt/.venv/bin/python", "-B", "-m",
        "adapters.mineflayer.s49_normal_session_real_ci",
        "--mp11-three-actions-dev", "--l-mp11-live-prefix-dev",
        "--l-mp11-paper-eof-dev", "--l-mp11-evidence-ids-dev",
        "--raw-capture-root", str(capture),
        "--l-mp11-gemma-preflight-report",
        str(root / "gemma-strict-wire-probe" / "gemma-structured-preflight.json"),
        "--l-mp11-live-l2-endpoint", ENDPOINT,
        "--l-mp11-live-l2-model", MODEL,
    ]


def test_single_world_budget_consumed_and_exact_owned_java_identity(
    tmp_path, monkeypatch,
):
    root, repo, report = prepped(tmp_path, monkeypatch)
    gate.prepare_trial(
        root, repo, report, expected_head=HEAD, endpoint=ENDPOINT, model=MODEL,
    )
    names = [
        "S49_REAL_SERVER_CI", "MP11_S49_THREE_ACTION_DEV",
        "MP11_G3_PAPER_THREE_WINDOWS_DEV", "L_MP11_LIVE_PREFIX_DEV",
        "L_MP11_LIVE_L2_DEV", "L_MP11_EVIDENCE_IDS_DEV",
        "L_MP11_GEMMA_STRICT_SCHEMA_DEV", "L_MP11_PAPER_EOF_DEV",
    ]
    for name in names:
        monkeypatch.setenv(name, "1")

    class FakeProcess:
        pid = 991
        count = 0

        def poll(self):
            self.count += 1
            return None if self.count == 1 else 0

        def wait(self):
            return 0

    calls = []
    monkeypatch.setattr(
        gate.subprocess, "Popen",
        lambda argv, **kwargs: (calls.append((argv, kwargs)), FakeProcess())[1],
    )
    monkeypatch.setattr(
        gate, "owned_tree",
        lambda pid: [
            {"pid": 991, "ppid": 10, "exe": "/usr/bin/python3"},
            {"pid": 992, "ppid": 991, "exe": "/opt/java21/bin/java"},
            {"pid": 993, "ppid": 991, "exe": "/opt/node22/bin/node"},
        ],
    )
    monkeypatch.setattr(gate.time, "sleep", lambda _: None)
    result = gate.run_once(
        root, repo, expected_head=HEAD, command=physical_command(root),
    )
    assert result["returncode"] == 0
    assert result["owned_java_pid_attested"]
    assert result["owned_node_pid_attested"]
    assert result["world_qualified"] is False
    assert result["snapshots"] == 2
    assert len(calls) == 1
    assert (root / gate.STARTED).exists()
    assert (root / gate.EXITED).exists()
    assert len((root / gate.SNAPSHOTS).read_text().splitlines()) == 2
    with pytest.raises(gate.NextWorldGateRejected, match="spent World budget"):
        gate.run_once(
            root, repo, expected_head=HEAD, command=physical_command(root),
        )
    assert len(calls) == 1


def test_preflight_action_flags_and_missing_capture_refuse_without_spending(
    tmp_path, monkeypatch,
):
    root, repo, report = prepped(tmp_path, monkeypatch)
    gate.prepare_trial(
        root, repo, report, expected_head=HEAD, endpoint=ENDPOINT, model=MODEL,
    )
    flags = [
        "S49_REAL_SERVER_CI", "MP11_S49_THREE_ACTION_DEV",
        "MP11_G3_PAPER_THREE_WINDOWS_DEV", "L_MP11_LIVE_PREFIX_DEV",
        "L_MP11_LIVE_L2_DEV", "L_MP11_EVIDENCE_IDS_DEV",
        "L_MP11_GEMMA_STRICT_SCHEMA_DEV", "L_MP11_PAPER_EOF_DEV",
    ]
    for flag in flags:
        monkeypatch.setenv(flag, "1")
    bad = physical_command(root)
    bad[bad.index("--raw-capture-root")+1] = "/tmp/missing"
    with pytest.raises(gate.NextWorldGateRejected):
        gate.run_once(root, repo, expected_head=HEAD, command=bad)
    monkeypatch.delenv("L_MP11_GEMMA_STRICT_SCHEMA_DEV")
    with pytest.raises(gate.NextWorldGateRejected):
        gate.run_once(
            root, repo, expected_head=HEAD, command=physical_command(root),
        )
    assert not (root / gate.STARTED).exists()



def test_symlinked_preflight_file_is_rejected_before_capture(tmp_path, monkeypatch):
    root, repo, report = prepped(tmp_path, monkeypatch)
    raw = report.with_name("raw-preflight.json")
    report.rename(raw)
    report.symlink_to(raw)
    with pytest.raises(gate.NextWorldGateRejected, match="regular file"):
        gate.prepare_trial(
            root, repo, report, expected_head=HEAD, endpoint=ENDPOINT,
            model=MODEL,
        )
    assert not (root / "world").exists()


def test_wrapper_interrupt_signals_only_its_new_process_group(
    tmp_path, monkeypatch,
):
    root, repo, report = prepped(tmp_path, monkeypatch)
    gate.prepare_trial(
        root, repo, report, expected_head=HEAD, endpoint=ENDPOINT, model=MODEL,
    )
    flags = [
        "S49_REAL_SERVER_CI", "MP11_S49_THREE_ACTION_DEV",
        "MP11_G3_PAPER_THREE_WINDOWS_DEV", "L_MP11_LIVE_PREFIX_DEV",
        "L_MP11_LIVE_L2_DEV", "L_MP11_EVIDENCE_IDS_DEV",
        "L_MP11_GEMMA_STRICT_SCHEMA_DEV", "L_MP11_PAPER_EOF_DEV",
    ]
    for flag in flags:
        monkeypatch.setenv(flag, "1")

    class Owned:
        pid = 997

        def poll(self):
            return None

        def wait(self, timeout=None):
            assert timeout == 5
            return -15

    def spawn(args, **kwargs):
        assert kwargs["start_new_session"] is True
        return Owned()

    seen = []
    monkeypatch.setattr(gate.subprocess, "Popen", spawn)
    monkeypatch.setattr(
        gate, "owned_tree",
        lambda pid: (_ for _ in ()).throw(KeyboardInterrupt("operator stop")),
    )
    monkeypatch.setattr(gate.os, "killpg", lambda pid, sig: seen.append((pid, sig)))
    with pytest.raises(KeyboardInterrupt):
        gate.run_once(root, repo, expected_head=HEAD, command=physical_command(root))
    assert seen == [(997, gate.signal.SIGTERM)]
    status = (root / gate.EXITED).read_text()
    assert '"wrapper_owned_process_group_terminated": true' in status
    assert '"world_qualified": false' in status
    assert (root / gate.STARTED).exists()


def test_probe_from_other_execution_head_rejected(tmp_path, monkeypatch):
    root, repo, report = prepped(tmp_path, monkeypatch)
    monkeypatch.setattr(gate, "verify_preflight_report", lambda *a, **kw: {
        "status": "REAL_GEMMA_WIRE_PROBE_PASS_UNATTESTED_WEIGHTS",
        "execution_head": "b" * 40,
    })
    with pytest.raises(gate.NextWorldGateRejected, match="probe execution HEAD"):
        gate.prepare_trial(root, repo, report, expected_head=HEAD,
                           endpoint=ENDPOINT, model=MODEL)
    assert not (root / "world").exists()


@pytest.mark.parametrize("action", ["prepare", "run"])
def test_documented_cli_options_after_action(tmp_path, monkeypatch, action):
    import sys
    calls = []
    monkeypatch.setattr(sys, "argv", ["gate", action, "--evidence-root", str(tmp_path),
                        "--repo", str(tmp_path), "--expected-head", HEAD] + (
        ["--preflight-report", str(tmp_path / "probe"), "--endpoint", ENDPOINT,
         "--model", MODEL] if action == "prepare" else ["--", "/python", "-B", "-m", "owner"]))
    monkeypatch.setattr(gate, "prepare_trial", lambda *a, **kw: calls.append(kw) or {})
    monkeypatch.setattr(gate, "run_once", lambda *a, **kw: calls.append(kw) or {})
    assert gate.main() == 0
    assert calls[0]["expected_head"] == HEAD
    if action == "run":
        assert calls[0]["command"] == ["/python", "-B", "-m", "owner"]
