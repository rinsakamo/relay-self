"""Prepare ONE fresh L-lane physical World and attest its owned process tree.

This is an operator-side helper, NOT a World or Gemma simulator. A preflight
report without raw SHA readback cannot unlock the capture namespace. The new
World budget is consumed only by 'run', never by 'prepare'. No retries.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from tools.l_mp11_gemma_structured_preflight import verify_preflight_report

READY = "l-next-world-capture-ready.json"
STARTED = "l-next-world-attempt-started.json"
EXITED = "l-next-world-runner-exit.json"
SNAPSHOTS = "l-next-world-owned-processes.jsonl"
RUNNER_LOG = "l-next-world-runner-original.log"


class NextWorldGateRejected(ValueError):
    """New World preparation/provenance/budget is incomplete."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_directory(path: Path, *, must_exist: bool) -> None:
    if not isinstance(path, Path) or not path.is_absolute():
        raise NextWorldGateRejected("all trial paths must be absolute")
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise NextWorldGateRejected("symlink directory/ancestor is prohibited")
    if must_exist and not path.is_dir():
        raise NextWorldGateRejected("original evidence root does not exist")
    if not must_exist and path.exists():
        raise NextWorldGateRejected("new capture namespace was already used")


def _git_head(repo: Path) -> str:
    if not repo.is_dir() or not (repo / ".git").exists():
        # A linked worktree may have a .git file; do not assume a directory.
        if not (repo / ".git").is_file():
            raise NextWorldGateRejected("clean local Git worktree required")
    head = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        text=True, stderr=subprocess.PIPE,
    ).strip()
    dirty = subprocess.check_output(
        ["git", "-C", str(repo), "status", "--porcelain"],
        text=True, stderr=subprocess.PIPE,
    ).strip()
    if dirty:
        raise NextWorldGateRejected("local execution worktree must be clean")
    return head


def prepare_trial(
    evidence_root: Path, repo: Path, preflight_report: Path, *,
    expected_head: str, endpoint: str, model: str,
    b1_contract_v2: bool = False,
) -> dict:
    """Create fresh/empty W3 capture directory only before any Java launch."""
    _safe_directory(evidence_root, must_exist=True)
    _safe_directory(repo, must_exist=True)
    if (len(expected_head) != 40
            or any(c not in "0123456789abcdef" for c in expected_head)
            or _git_head(repo) != expected_head):
        raise NextWorldGateRejected("exact execution HEAD mismatch")
    if not isinstance(preflight_report, Path):
        raise NextWorldGateRejected("original preflight report path required")
    _safe_directory(preflight_report.parent, must_exist=True)
    if not preflight_report.is_file() or preflight_report.is_symlink():
        raise NextWorldGateRejected("original Gemma preflight must be a regular file")
    if not preflight_report.is_relative_to(evidence_root):
        raise NextWorldGateRejected("new evidence root must own this preflight")
    # Schema, model alias, thinking-off and saved raw request/response SHA are
    # independently checked, NOT trusted from report status text alone.
    verified = verify_preflight_report(
        preflight_report, endpoint=endpoint, model=model,
        b1_contract_v2=b1_contract_v2,
    )
    if verified.get("execution_head") != expected_head:
        raise NextWorldGateRejected("probe execution HEAD differs from this trial")
    world = evidence_root / "world"
    capture = world / "native-stdout"
    _safe_directory(world, must_exist=False)
    _safe_directory(capture, must_exist=False)
    if any((evidence_root / p).exists() for p in (READY, STARTED, EXITED)):
        raise NextWorldGateRejected("new trial marker already exists")
    # W3 constructor requires a pre-existing empty absolute capture root.
    # Fail closed if an intermediate path was left from a previous attempt.
    world.mkdir(mode=0o700)
    capture.mkdir(mode=0o700)
    result = {
        "classification": "CAPTURE_READY_ONLY_NOT_WORLD_STARTED",
        "expected_head": expected_head,
        "capture_root": str(capture),
        "preflight_report": str(preflight_report),
        "preflight_sha256": sha256(preflight_report),
        "endpoint": endpoint,
        "model": model,
        "preflight_status": verified["status"],
        "b1_contract_v2": b1_contract_v2,
        "worlds_allowed": 1,
        "retries_allowed": 0,
        "h1_h2_calls_allowed": 2,
        "original_s49_actions_allowed": 3,
        "actual_worlds_started": 0,
        "actual_llm_world_calls": 0,
        "actual_body_actions": 0,
        "gguf_process_identity_verified_by_this_helper": False,
    }
    target = evidence_root / READY
    with target.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    return result


def read_proc_status(pid: int, proc_root: Path = Path("/proc")) -> dict | None:
    """Linux /proc/<pid>/stat: bind PID to parent AND kernel start ticks."""
    folder = proc_root / str(pid)
    try:
        stat = (folder / "stat").read_text()
        k = stat.rfind(")")
        if k < 1:
            return None
        words = stat[k+2:].split()
        # Fields: state=3, ppid=4, starttime=22.
        ppid = int(words[1])
        start_ticks = int(words[19])
        argv = (folder / "cmdline").read_bytes().split(b"\x00")
        args = [a.decode("utf-8", errors="replace") for a in argv if a]
        return {
            "pid": pid, "ppid": ppid, "start_ticks": start_ticks,
            "state": words[0], "argv": args,
            "cwd": os.readlink(folder / "cwd"),
            "exe": os.readlink(folder / "exe"),
        }
    except (OSError, IndexError, ValueError):
        return None


def owned_tree(root_pid: int, proc_root: Path = Path("/proc")) -> list[dict]:
    """Collect actual descendants; no guessed minecraft.jar argv substring."""
    if type(root_pid) is not int or root_pid < 1:
        raise NextWorldGateRejected("real spawned child PID required")
    processes = {}
    try:
        folders = list(proc_root.iterdir())
    except OSError:
        return []
    for folder in folders:
        if folder.name.isdigit():
            item = read_proc_status(int(folder.name), proc_root)
            if item is not None:
                processes[item["pid"]] = item
    if root_pid not in processes:
        return []
    identified = {root_pid}
    # Close transitive parent links. Reap/exit may happen between reads:
    # absence means UNATTESTED, never "no processes ever existed".
    for _ in range(16):
        new = identified | {
            pid for pid, item in processes.items()
            if item["ppid"] in identified
        }
        if len(new) == len(identified):
            break
        identified = new
    return [processes[p] for p in sorted(identified)]


def run_once(
    evidence_root: Path, repo: Path, *,
    expected_head: str, command: list[str], sample_seconds: float = 0.10,
) -> dict:
    """Consume exactly one physical World budget and record actual ancestry."""
    _safe_directory(evidence_root, must_exist=True)
    if _git_head(repo) != expected_head:
        raise NextWorldGateRejected("HEAD changed after capture preparation")
    ready_path = evidence_root / READY
    if (not ready_path.is_file() or ready_path.is_symlink()
            or (evidence_root / STARTED).exists()):
        raise NextWorldGateRejected("missing pre-Java preparation or spent World budget")
    ready = json.loads(ready_path.read_text())
    capture = evidence_root / "world" / "native-stdout"
    _safe_directory(capture, must_exist=True)
    if (
        ready.get("expected_head") != expected_head
        or ready.get("capture_root") != str(capture)
        or any(capture.iterdir())
        or ready.get("retries_allowed") != 0
        or ready.get("worlds_allowed") != 1
    ):
        raise NextWorldGateRejected("original W3 capture path not empty/attested")
    probe = Path(ready["preflight_report"])
    if probe.is_symlink():
        raise NextWorldGateRejected("preflight symlink changed after preparation")
    verified = verify_preflight_report(
        probe, endpoint=ready["endpoint"], model=ready["model"],
        b1_contract_v2=ready.get("b1_contract_v2", False),
    )
    if verified.get("execution_head") != expected_head:
        raise NextWorldGateRejected("probe execution HEAD differs from this trial")
    if sha256(probe) != ready["preflight_sha256"]:
        raise NextWorldGateRejected("preflight bytes changed since preparation")
    if not command or command[0].startswith("-") or any(
        "\x00" in a for a in command
    ):
        raise NextWorldGateRejected("explicit argv required, no shell")
    # Ensure the one-run original S49 CLI uses the prevalidated original inputs.
    required = {
        "--raw-capture-root": str(capture),
        "--l-mp11-gemma-preflight-report": str(probe),
        "--l-mp11-live-l2-endpoint": ready["endpoint"],
        "--l-mp11-live-l2-model": ready["model"],
    }
    for opt, val in required.items():
        if command.count(opt) != 1:
            raise NextWorldGateRejected(f"exact one {opt} required")
        index = command.index(opt)
        if index + 1 >= len(command) or command[index+1] != val:
            raise NextWorldGateRejected(f"wrong original argument for {opt}")
    for flag in (
        "--mp11-three-actions-dev", "--l-mp11-live-prefix-dev",
        "--l-mp11-paper-eof-dev", "--l-mp11-evidence-ids-dev",
    ):
        if command.count(flag) != 1:
            raise NextWorldGateRejected(f"missing required original scope {flag}")
    v2 = ready.get("b1_contract_v2", False)
    if type(v2) is not bool or (
        (command.count("--l-mp11-b1-contract-v2-dev") == 1) != v2
    ):
        raise NextWorldGateRejected("new World B1 contract must match preflight mode")
    if v2 and os.environ.get("L_MP11_B1_CONTRACT_V2_DEV") != "1":
        raise NextWorldGateRejected("missing explicit B1 V2 World opt-in")
    if (
        "-m" not in command
        or "adapters.mineflayer.s49_normal_session_real_ci" not in command
        or not 0.01 <= sample_seconds <= 1.0
    ):
        raise NextWorldGateRejected("real S49 runner and bounded sampling required")
    for var in (
        "S49_REAL_SERVER_CI", "MP11_S49_THREE_ACTION_DEV",
        "MP11_G3_PAPER_THREE_WINDOWS_DEV", "L_MP11_LIVE_PREFIX_DEV",
        "L_MP11_LIVE_L2_DEV", "L_MP11_EVIDENCE_IDS_DEV",
        "L_MP11_GEMMA_STRICT_SCHEMA_DEV", "L_MP11_PAPER_EOF_DEV",
    ):
        if os.environ.get(var) != "1":
            raise NextWorldGateRejected(f"missing explicit World scope {var}")
    started = {
        "classification": "NEW_INDEPENDENT_ONE_WORLD_BUDGET_CONSUMED",
        "head": expected_head,
        "argv": command,
        "ready_sha256": sha256(ready_path),
        "budget_consumed": True,
        "monotonic_start_ns": time.monotonic_ns(),
    }
    with (evidence_root / STARTED).open("x") as stream:
        json.dump(started, stream, sort_keys=True, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    result = {"returncode": None, "snapshots": 0, "java_owned": False,
              "node_owned": False, "world_qualified": False}
    proc = None
    with (evidence_root / RUNNER_LOG).open("xb") as output:
        with (evidence_root / SNAPSHOTS).open("x") as journal:
            try:
                proc = subprocess.Popen(
                    command, cwd=repo, stdout=output,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                started["runner_pid"] = proc.pid
                while True:
                    tree = owned_tree(proc.pid)
                    result["snapshots"] += 1
                    for child in tree:
                        if child["pid"] == proc.pid:
                            continue
                        exe = Path(child["exe"]).name
                        if exe == "java":
                            result["java_owned"] = True
                        if exe == "node":
                            result["node_owned"] = True
                    journal.write(json.dumps({
                        "monotonic_ns": time.monotonic_ns(),
                        "runner_pid": proc.pid,
                        "owned_processes": tree,
                    }, ensure_ascii=False) + "\n")
                    journal.flush()
                    if proc.poll() is not None:
                        break
                    time.sleep(sample_seconds)
                result["returncode"] = proc.wait()
            except BaseException as exc:
                result["launcher_error"] = f"{type(exc).__name__}: {exc}"
                # This wrapper owns only the new S49 child process group.
                # Never signal unrelated pre-existing model/server processes.
                if proc is not None and proc.poll() is None:
                    try:
                        os.killpg(proc.pid, signal.SIGTERM)
                        proc.wait(timeout=5)
                        result["wrapper_owned_process_group_terminated"] = True
                    except (OSError, subprocess.TimeoutExpired):
                        try:
                            os.killpg(proc.pid, signal.SIGKILL)
                            proc.wait(timeout=5)
                            result["wrapper_owned_process_group_killed"] = True
                        except (OSError, subprocess.TimeoutExpired):
                            result["wrapper_owned_process_group_unconfirmed"] = True
                raise
            finally:
                # A missing Java lineage remains UNATTESTED even if exit0.
                result["owned_java_pid_attested"] = result["java_owned"]
                result["owned_node_pid_attested"] = result["node_owned"]
                with (evidence_root / EXITED).open("x") as output_status:
                    json.dump(result, output_status, indent=2, sort_keys=True)
                    output_status.flush()
                    os.fsync(output_status.fileno())
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--preflight-report", type=Path)
    parser.add_argument("--endpoint")
    parser.add_argument("--model")
    parser.add_argument("--sample-seconds", type=float, default=0.25)
    parser.add_argument("--b1-contract-v2", action="store_true")
    argv = sys.argv[1:]
    separator = argv.index("--") if "--" in argv else len(argv)
    args = parser.parse_args(argv[:separator])
    args.original_runner = argv[separator + 1:]
    if args.action == "prepare":
        if args.original_runner or not args.preflight_report or not args.endpoint or not args.model:
            parser.error("prepare requires preflight original, endpoint, model, no runner")
        report = prepare_trial(
            args.evidence_root, args.repo, args.preflight_report,
            expected_head=args.expected_head,
            endpoint=args.endpoint, model=args.model,
            b1_contract_v2=args.b1_contract_v2,
        )
    else:
        command = args.original_runner
        if command and command[0] == "--":
            command = command[1:]
        report = run_once(
            args.evidence_root, args.repo, expected_head=args.expected_head,
            command=command, sample_seconds=args.sample_seconds,
        )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
