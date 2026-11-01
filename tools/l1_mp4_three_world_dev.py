"""One-shot, at-most-three independent MP4 physical DEV Worlds, GitHub runner.

The only Action executor is original self_body_s50_world_dev.py.
No retry of a World; a failed cleanup blocks further Worlds. Durable evidence
is saved outside the disposable World directory and uploaded by workflow.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from adapters.mineflayer.self_body_s50_l1_paper_dispatch import require_paper_gate_config
from adapters.mineflayer.l23_paper_live_assets import L23PaperAssets, verify_paper_assets

PAPER_SHA = "8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e"
CONFIRM = "MP4-THREE-DISPOSABLE-PAPER-WORLDS-DEV-ONLY"


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_exclusive(path: Path, object_value: object) -> None:
    with path.open("x", encoding="utf-8") as out:
        json.dump(object_value, out, indent=2, sort_keys=True)
        out.write("\n")
        out.flush()
        os.fsync(out.fileno())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def port_is_free() -> bool:
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        try:
            sock.bind(("127.0.0.1", 25565))
            return True
        except OSError:
            return False


def prepare_config(base_config: Path, output: Path) -> str:
    raw = base_config.read_text(encoding="utf-8")
    for key in ("dev-enabled", "s50-forecast-gate-dev"):
        old = f"{key}: false"
        if raw.count(old) != 1:
            raise ValueError(f"unexpected off/default config: {key}")
        raw = raw.replace(old, f"{key}: true")
    if "s50-tick-meter-dev:" in raw:
        raise ValueError("ambiguous default tick-meter profile")
    raw = raw.replace("dev-enabled: true", "dev-enabled: true\ns50-tick-meter-dev: true")
    with output.open("x", encoding="utf-8") as fd:
        fd.write(raw)
    digest = sha(output)
    require_paper_gate_config(output, digest)
    return digest


def original_report(out: Path) -> dict:
    raw = json.loads(out.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise RuntimeError("owner report is not an object")
    return raw


def review(run_dir: Path, process_rc: int, time_expired: bool) -> dict:
    report_path = run_dir / "s49-report.json"
    report = original_report(report_path) if report_path.is_file() else {}
    paper = (run_dir / "server.log").read_bytes() if (run_dir / "server.log").is_file() else b""
    lines = paper.decode("utf-8", "replace").split("\n")
    kinds = (
        "S50_DEV_FORECAST_ACCEPT", "S50_DEV_FORECAST_REJECT",
        "S50_DEV_FORECAST_TICK", "S50_DEV_WAIT_TICK",
    )
    counts = {x: sum(x + " marker_id=" in row for row in lines) for x in kinds}
    matched = sum(
        "S50_DEV_FORECAST_TICK marker_id=" in row
        and "status=MATCHED_PAPER_ACCEPTED_PRIOR_TICK" in row
        for row in lines
    )
    host_journal = run_dir / "prediction-original.jsonl"
    journal = (
        [json.loads(row) for row in host_journal.read_text().splitlines()]
        if host_journal.is_file() else []
    )
    kinds_host = ("PREDICTION_FIXED", "PAPER_COMMAND_QUEUED", "PAPER_CONSOLE_WRITE")
    host_counts = {
        x: sum(row.get("kind") == x for row in journal) for x in kinds_host
    }
    exits = {k: report.get(k) for k in ("status", "classification", "node_exit", "server_exit")}
    complete = (
        process_rc == 0 and not time_expired and
        report.get("status") == "PASS"
        and report.get("node_exit") == 0
        and report.get("server_exit") == 0
        and counts["S50_DEV_WAIT_TICK"] == 8
        and host_counts["PREDICTION_FIXED"] == 7
        and host_counts["PAPER_COMMAND_QUEUED"] == 7
        and (run_dir / "client-packet-original.jsonl").is_file()
    )
    return dict(
        original_owner_status=exits,
        launcher_returncode=process_rc,
        timed_out=time_expired,
        paper_counts=counts,
        accepted_and_callback_matched=matched,
        host_counts=host_counts,
        complete_dev_source_shape=complete,
        paper_console_accepted_physical_world_tick=matched > 0,
        maximum_claim="DEV_PAPER_SAME_SERVER_CALLBACK_ORDER_ONLY",
        goal="UNDETERMINED",
        qualification="NO_GO",
        science="NOT_RUN",
    )


def run() -> int:
    cli = argparse.ArgumentParser()
    cli.add_argument("--output", type=Path, required=True)
    cli.add_argument("--paper-jar", type=Path, required=True)
    cli.add_argument("--plugin-jar", type=Path, required=True)
    cli.add_argument("--node-runtime", type=Path, required=True)
    cli.add_argument("--config-default", type=Path, required=True)
    cli.add_argument("--worlds", type=int, required=True)
    cli.add_argument("--confirm", required=True)
    cli.add_argument("--preflight-only", action="store_true")
    args = cli.parse_args()
    if args.confirm != CONFIRM or args.worlds != 3 or not args.output.is_absolute():
        cli.error("MP4 lane requires 3 distinct disposable DEV Worlds and explicit confirmation")
    if args.output.exists() or args.output.is_symlink():
        cli.error("output must be new, not shared or prior evidence")
    if not args.node_runtime.is_absolute() or args.node_runtime.is_symlink():
        cli.error("physical absolute Node runtime required")
    node_pkg = json.loads((args.node_runtime / "node_modules/mineflayer/package.json").read_text())
    if node_pkg.get("version") != "4.39.0":
        cli.error("Mineflayer version mismatch")
    args.output.mkdir(parents=True)
    config_path = args.output / "mp4-paper-config.yml"
    config_sha = prepare_config(args.config_default, config_path)
    assets = L23PaperAssets(
        args.paper_jar, PAPER_SHA,
        args.plugin_jar, sha(args.plugin_jar),
        config_path, config_sha,
    )
    verify_paper_assets(assets)
    if not port_is_free():
        raise RuntimeError("port 25565 occupied before first World")
    write_exclusive(args.output / "preflight.json", dict(
        created_utc=utc(), worlds_authorized=3, physical_worlds_started=0,
        owner="S49-original", runtime="Paper 1.21.8 / Mineflayer 4.39.0",
        git_head=os.environ.get("GITHUB_SHA"), server_sha=PAPER_SHA,
        plugin_sha=assets.plugin_sha256, config_sha=assets.config_sha256,
        status="PREFLIGHT_OK_NO_WORLD",
    ))
    if args.preflight_only:
        print("MP4_THREE_WORLD_PREFLIGHT_PASS physical_worlds_started=0")
        return 0

    env = os.environ.copy()
    env.update(
        PYTHONPATH="src:tests:.", PYTHONDONTWRITEBYTECODE="1",
        S49_REAL_SERVER_CI="1",
        RELAYSELF_RSEE_NODE_RUNTIME_ROOT=str(args.node_runtime),
    )
    if env.get("NODE_OPTIONS"):
        raise RuntimeError("Node shims forbidden")
    results = []
    for i in range(1, 4):
        if not port_is_free():
            results.append(dict(world=i, status="ABORT_UNCLEAN_PORT"))
            break
        root = args.output / f"world{i}"
        root.mkdir()
        capture = root / "capture"
        capture.mkdir()
        env["RELAYSELF_S50_PACKET_WITNESS_DEV"] = str(
            root / "client-packet-original.jsonl"
        )
        argv = [
            sys.executable, "-m", "adapters.mineflayer.self_body_s50_world_dev",
            "--report", str(root / "s49-report.json"),
            "--server-log", str(root / "server.log"),
            "--l16-capture-root", str(capture),
            "--l16-goal-target-x", "0", "--l16-goal-target-z", "0",
            "--l16-goal-tolerance-m", "0.49", "--l16-goal-stability-m", "0.05",
            "--l16-confirm", "L16-S49-FIRST-ACTION-ORIGINAL-DEV",
            "--l22-settling-probes", "6",
            "--selfbody-live-next-epoch-dev",
            "--selfbody-l1-motion-shadow-dev",
            "--l1-prediction-journal", str(root / "prediction-original.jsonl"),
            "--l1-paper-forecast-gate-dev",
            "--l23-paper-server-jar", str(args.paper_jar),
            "--l23-paper-server-sha256", PAPER_SHA,
            "--l23-paper-plugin-jar", str(args.plugin_jar),
            "--l23-paper-plugin-sha256", assets.plugin_sha256,
            "--l23-paper-config", str(config_path),
            "--l23-paper-config-sha256", config_sha,
        ]
        write_exclusive(root / "WORLD_ATTEMPT_STARTED.json", dict(
            index=i, created_utc=utc(), grant="USER_MP4_LANE_CONTINUING_UP_TO_THREE_20261101",
            code_head=os.environ.get("GITHUB_SHA"), argv=argv,
            no_retry=True, no_learning=True,
        ))
        rc = 124
        expired = False
        with (root / "launcher.log").open("xb") as log:
            child = subprocess.Popen(
                argv, env=env, stdout=log, stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            try:
                rc = child.wait(timeout=240)
            except subprocess.TimeoutExpired:
                expired = True
                try:
                    os.killpg(child.pid, signal.SIGTERM)
                    child.wait(timeout=8)
                except (ProcessLookupError, subprocess.TimeoutExpired):
                    try:
                        os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    child.wait()
        data = review(root, rc, expired)
        data["world"] = i
        data["completed_utc"] = utc()
        data["port_rebind_after_cleanup"] = port_is_free()
        write_exclusive(root / "dev-readback.json", data)
        results.append(data)
        write_exclusive(args.output / f"cumulative-{i}.json", results)
        print("MP4_WORLD_RESULT=" + json.dumps(data, sort_keys=True), flush=True)
        # Only proceed when original host has stopped cleanly. No external PID killed.
        if not data["port_rebind_after_cleanup"] or not data["complete_dev_source_shape"]:
            break
    result = dict(
        end_utc=utc(),
        worlds_started=sum((args.output / f"world{i}/WORLD_ATTEMPT_STARTED.json").is_file()
                           for i in range(1, 4)),
        reports=results,
        global_status="DEV_3_WORLDS_COMPLETED" if len(results) == 3 and
                      all(x.get("complete_dev_source_shape") for x in results)
                      else "DEV_PARTIAL_OR_BLOCKED",
        grant="USER_LANE_CONTINUING",
        qualification="NO_GO", science="NOT_RUN", learning_updates=0,
    )
    write_exclusive(args.output / "summary.json", result)
    print("MP4_THREE_WORLD_SUMMARY=" + json.dumps(result, sort_keys=True))
    return 0 if result["global_status"] == "DEV_3_WORLDS_COMPLETED" else 1


if __name__ == "__main__":
    raise SystemExit(run())
