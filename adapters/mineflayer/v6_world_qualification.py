"""S #537 one disposable engineering World; no V trial or Self Action.

Default is stopped-byte preparation. --confirm authorizes only this dedicated
one-shot entry point; external human authorization is still required. The
exclusive grant file is retained even after errors. Never retry a child start.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from adapters.mineflayer.b0_rsee import B0RSEEInputs, verify_b0_rsee
from adapters.mineflayer.python_protocol import (
    MineflayerLaunchConfig,
    MineflayerObservation,
    MineflayerStreamDecoder,
    encode_observe,
    encode_shutdown,
)
from adapters.mineflayer.s31a_real_server_ci import _write_config
from adapters.mineflayer.v6_atomic_fixture import proposed_datapack_files
from adapters.mineflayer.v6_original_capture import PHASES, V6OriginalCapture
from adapters.mineflayer.v6_start_marker import proposed_start_pack

CONFIRM = "V6-ENGINEERING-WORLD-ONCE-NO-SCIENCE"
R_HEAD = "49592916c141bdcc58b373efeb7f3130351ed641"
START_HEAD = "2aaff0b921bcbd47a61d563b52d502596f896924"
FOOD_HEAD = "37f9365d3d16c9bda440ca9a9c8a10be6a32f1fc"
# The actual 1.21.8 server reply is "Running function <namespace:id>".
# It acknowledges command dispatch, NEVER the scoreboard side effects.
INSTALL_DISPATCH_REPLIES = (
    r"\bRunning function relayself_v6:install(?:\s|$)",
    r"\bRunning function relayself_v6_start:install(?:\s|$)",
)


class QualificationBlocked(ValueError):
    """Missing authority or a failed one-shot terminal; never recover by replay."""


def need(ok: bool, why: str) -> None:
    if not ok:
        raise QualificationBlocked(why)


def saved(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8") as out:
        json.dump(value, out, sort_keys=True, indent=2)
        out.write("\n")


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          capture_output=True, text=True, timeout=15).stdout.strip()


def clean(root: Path, head: str) -> None:
    need(root.is_absolute() and root.resolve() == root, "canonical checkout required")
    need(git(root, "rev-parse", "HEAD") == head, "exact checkout HEAD missing")
    need(not git(root, "status", "--porcelain", "--untracked-files=all"),
         "dirty checkout")


def remote_ci(number: int, head: str) -> dict:
    p = subprocess.run([
        "gh", "pr", "view", str(number), "--repo", "rinsakamo/relay-self",
        "--json", "headRefOid,statusCheckRollup",
    ], capture_output=True, text=True, check=True, timeout=30)
    result = json.loads(p.stdout)
    need(result["headRefOid"] == head, "remote PR head changed")
    checks = result["statusCheckRollup"]
    need(bool(checks) and all(c.get("status") == "COMPLETED"
                             and c.get("conclusion") == "SUCCESS" for c in checks),
         "all exact-head CI jobs must terminate SUCCESS")
    return result


def port_free() -> None:
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(("127.0.0.1", 25565))


def r_review(args: argparse.Namespace, clone: Path) -> dict:
    # Independent process imports only the pinned clean R checkout.
    code = """
import json,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from experiments.standard_env.v6_start_admission import review_staged_clone
v=list(map(Path,sys.argv[2:9]))
r=review_staged_clone(jar=v[0],golden=v[1],manifest=v[2],initial_evidence=v[3],
 staged_clone=v[4],s_start_checkout=v[5],s_food_checkout=v[6],slot=sys.argv[9],nonce=sys.argv[10])
print(json.dumps(r,sort_keys=True))
"""
    p = subprocess.run([sys.executable, "-I", "-B", "-c", code,
                        str(args.r_checkout), str(args.jar), str(args.golden),
                        str(args.manifest), str(args.initial_evidence), str(clone),
                        str(args.start_checkout), str(args.food_checkout),
                        args.slot, args.nonce],
                       capture_output=True, text=True, timeout=70, check=True)
    result = json.loads(p.stdout)
    need(result.get("classification") == "RSEE_V6_TWO_PACK_STOPPED_BYTES_REVIEW_ONLY"
         and result.get("added_pack_file_count") == 6
         and result.get("original_world_bytes_independently_read") is True,
         "independent R stopped-byte review incomplete")
    return result


def prepare(args: argparse.Namespace, report: dict) -> Path:
    root = Path(__file__).resolve().parents[2]
    clean(root, args.s_head)
    clean(args.r_checkout, R_HEAD)
    clean(args.start_checkout, START_HEAD)
    clean(args.food_checkout, FOOD_HEAD)
    report["s_ci"] = remote_ci(545, args.s_head)
    report["r_ci"] = remote_ci(610, R_HEAD)
    need(not args.grant.exists() and not args.grant.is_symlink(), "grant already consumed")
    need(args.grant.is_absolute() and args.grant.parent.is_dir(), "external grant path required")
    need(not any(os.environ.get(k) for k in ("NODE_OPTIONS", "JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS", "_JAVA_OPTIONS")),
         "runtime substitution environment forbidden")
    need(args.node.is_file() and os.access(args.node, os.X_OK), "Node executable unavailable")
    need(shutil.which("java") is not None, "Java executable unavailable")
    java = Path(shutil.which("java")).resolve()
    need('JAVA_VERSION="21.' in (java.parent.parent / "release").read_text(),
         "Java 21 runtime required before World launch")
    # Dependency import inspection is an offline Node probe, never a bridge
    # or World session. Import the actual graph before spending the grant.
    js = """
const {createRequire}=require('node:module');
const r=createRequire(process.argv[1]+'/package.json');
r('mineflayer');r('minecraft-protocol');
console.log(JSON.stringify({node:process.versions.node,mineflayer:r('mineflayer/package.json').version,
 protocol:r.resolve('minecraft-protocol')}));
"""
    probe = subprocess.run([str(args.node), "-e", js, str(args.node_root)],
                           capture_output=True, text=True, check=True, timeout=20)
    report["offline_node_import_probe"] = json.loads(probe.stdout)
    need(int(report["offline_node_import_probe"]["node"].split(".")[0]) >= 22
         and report["offline_node_import_probe"]["mineflayer"] == "4.39.0",
         "Node/Mineflayer runtime incompatible")
    port_free()
    inputs = B0RSEEInputs(args.golden_checkout, args.jar, args.golden,
                          args.manifest, args.initial_evidence, args.node_root, True)
    report["golden_before"] = verify_b0_rsee(inputs)
    run = args.output / "disposable"
    run.mkdir()
    clone = run / "s31a-ephemeral"
    shutil.copytree(args.golden, clone)
    # Verify original bytes before staging; fixed producers remain untouched.
    verify_b0_rsee(inputs, snapshot_copy=clone)
    packs = {f"datapacks/relayself_v6_atomic/{k}": v
             for k, v in proposed_datapack_files().items()}
    packs.update({f"datapacks/relayself_v6_start_v1/{k}": v
                  for k, v in proposed_start_pack(args.slot, args.nonce).items()})
    need(len(packs) == 6, "both exact three-file packs required")
    for relative, raw in packs.items():
        p = clone / relative
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("xb") as out:
            out.write(raw)
    _write_config(run)
    with (run / "server.properties").open("a") as out:
        out.write("level-seed=575\n")
    report["stopped_clone_r_review"] = r_review(args, clone)
    report["pack_sha256"] = {k: hashlib.sha256(v).hexdigest() for k, v in packs.items()}
    report["config_sha256"] = hashlib.sha256((run / "server.properties").read_bytes()).hexdigest()
    saved(args.output / "prejava.json", report)
    return run


class OwnedStreams:
    """One owner, exact stdout bytes and bounded consumers; no command retry."""
    def __init__(self, capture: V6OriginalCapture, root: Path):
        self.capture = capture
        self.root = root
        self.server = None
        self.node = None
        self.tasks: list[asyncio.Task] = []
        self.server_lines: list[str] = []
        self.native: asyncio.Queue = asyncio.Queue(maxsize=8192)
        self.decoder = MineflayerStreamDecoder()
        self.console = (root / "server_stdin_original.bin").open("xb")
        self.node_stdin = (root / "node_stdin_original.jsonl").open("xb")
        self.clock_count = 0
        self.stop_ack = False

    async def server_reader(self) -> None:
        assert self.server is not None and self.server.stdout is not None
        while raw := await self.server.stdout.readline():
            self.capture.on_server_stdout(raw)
            self.server_lines.append(raw.decode("utf-8"))

    async def native_reader(self) -> None:
        assert self.node is not None and self.node.stdout is not None
        while raw := await self.node.stdout.readline():
            self.capture.on_native_stdout(raw)
            message = self.decoder.decode(raw.decode("utf-8"))
            row = json.loads(raw)
            if row["type"] == "native_clock_packet":
                self.clock_count += 1
            if row["type"] == "shutdown_ack":
                self.stop_ack = True
            await self.native.put(message)

    def check_readers(self) -> None:
        for task in self.tasks:
            if task.done():
                task.result()  # preserve first stream exception

    async def wait_log(self, pattern: str, start: int = 0, timeout: float = 15) -> str:
        deadline = time.monotonic() + timeout
        cursor = start
        while time.monotonic() < deadline:
            self.check_readers()
            for line in self.server_lines[cursor:]:
                # Dispatch alone is not a datapack effect: fail on explicit
                # Minecraft parser or command errors before accepting a reply.
                if re.search(
                    r"Unknown function|Unknown command|Failed to load|"
                    r"Couldn't load|Error loading", line,
                    re.IGNORECASE,
                ):
                    raise QualificationBlocked(
                        "original server error before readback: " + line.strip()
                    )
                if re.search(pattern, line):
                    return line
            cursor = len(self.server_lines)
            need(self.server is not None and self.server.returncode is None,
                 "server ended before readback")
            await asyncio.sleep(.05)
        raise QualificationBlocked("server original readback timeout: " + pattern)

    async def issue(self, phase: str, command: str, pattern: str) -> str:
        need((phase, command) in PHASES, "nonqualification command forbidden")
        self.capture.note_issuer_attempt(phase=phase, command=command)
        assert self.server is not None and self.server.stdin is not None
        raw = (command + "\n").encode()
        self.console.write(raw)
        self.console.flush()
        start = len(self.server_lines)
        self.server.stdin.write(raw)
        await self.server.stdin.drain()
        return await self.wait_log(pattern, start)

    async def node_send(self, raw: str) -> None:
        need(json.loads(raw).get("type") in ("observe", "shutdown"),
             "Self Action forbidden in engineering qualification")
        assert self.node is not None and self.node.stdin is not None
        self.node_stdin.write(raw.encode())
        self.node_stdin.flush()
        self.node.stdin.write(raw.encode())
        await self.node.stdin.drain()

    async def next_native(self, predicate, timeout: float = 30):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.check_readers()
            try:
                msg = await asyncio.wait_for(self.native.get(), timeout=.25)
            except TimeoutError:
                continue
            if predicate(msg):
                return msg
        raise QualificationBlocked("native observation timeout")

    async def probe(self, request: str) -> MineflayerObservation:
        await self.node_send(encode_observe(request))
        return await self.next_native(lambda m: isinstance(m, MineflayerObservation)
                                      and m.kind == "probe" and m.request_id == request)

    async def cleanup(self, report: dict) -> None:
        # No replacement start. Emergency termination is cleanup, not a retry.
        for name, process in (("node", self.node), ("java", self.server)):
            if process is None:
                continue
            if process.returncode is None:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), 8)
                except TimeoutError:
                    process.kill()
                    await process.wait()
            report[name + "_exit"] = process.returncode
            try:
                os.kill(process.pid, 0)
                report[name + "_pid_gone"] = False
            except ProcessLookupError:
                report[name + "_pid_gone"] = True
        for task in self.tasks:
            try:
                await asyncio.wait_for(task, 5)
            except Exception as exc:
                report.setdefault("stream_errors", []).append(type(exc).__name__ + ": " + str(exc))
        self.console.close()
        self.node_stdin.close()
        report["native_stop_ack"] = self.stop_ack
        try:
            port_free()
            report["port_rebind"] = True
        except OSError:
            report["port_rebind"] = False


async def execute(args: argparse.Namespace, run: Path, report: dict) -> None:
    capture = V6OriginalCapture(args.output / "originals", slot=args.slot, nonce=args.nonce)
    owner = OwnedStreams(capture, args.output)
    try:
        # Claim persistent grant BEFORE the unique Java create call. Retain it
        # on an uncertain spawn error rather than guessing permission remains.
        with args.grant.open("x") as out:
            out.write(json.dumps({"output": str(args.output), "s_head": args.s_head}) + "\n")
            out.flush()
            os.fsync(out.fileno())
        report["grant_consumed_conservatively"] = True
        report["java_launch_calls"] = 1
        owner.server = await asyncio.create_subprocess_exec(
            "java", "-Xms512M", "-Xmx1536M", "-jar", str(args.jar), "nogui",
            cwd=run, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT)
        report["java_started"] = True
        report["java_pid"] = owner.server.pid
        owner.tasks.append(asyncio.create_task(owner.server_reader()))
        await owner.wait_log(r"Done \(.*For help", timeout=190)
        need(not any(re.search(r"Failed to load|Couldn't load|Unknown function|Error loading", line)
                     for line in owner.server_lines), "datapack parser/load failure")
        env = dict(os.environ, RELAYSELF_RSEE_NODE_RUNTIME_ROOT=str(args.node_root),
                   RELAYSELF_V6_NATIVE_CLOCK_V1="1")
        config = MineflayerLaunchConfig(version="1.21.8")
        owner.node = await asyncio.create_subprocess_exec(
            *config.argv(Path(__file__).with_name("bridge.mjs"), node_executable=str(args.node)),
            env=env, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=(args.output / "node_stderr_original.log").open("xb"))
        report["node_pid"] = owner.node.pid
        owner.tasks.append(asyncio.create_task(owner.native_reader()))
        await owner.next_native(lambda m: isinstance(m, MineflayerObservation) and m.kind == "spawn", 75)
        # Actual Minecraft 1.21.8 console output reports "Running function
        # <id>", NOT "Executed N command". This is a dispatch witness only:
        # the subsequent original scoreboard readbacks remain mandatory.
        await owner.issue(*PHASES[0], INSTALL_DISPATCH_REPLIES[0])
        await owner.issue(*PHASES[1], INSTALL_DISPATCH_REPLIES[1])
        first = await owner.probe("v6-qualification-first-item-free")
        capture.note_first_native_probe(first)
        await owner.issue(*PHASES[3], "RELAYSELF_V6_TRIAL_START_" + args.slot + "_" + args.nonce + "_NOT_ADMITTED")
        scores = {}
        for i in (4, 5):
            player = PHASES[i][1].split()[3]
            line = await owner.issue(*PHASES[i], re.escape(player) + r" has (-?\d+) \[rs_v6_tick\]")
            scores[player] = int(re.search(re.escape(player) + r" has (-?\d+)", line)[1])
        need(scores["#start_attempt"] == 1, "start attempt != 1")
        # Fixed engineering opportunity: immediate after start score readbacks.
        # No M0 ticks or V scientific arm policy are instantiated.
        await owner.issue(*PHASES[6], "RELAYSELF_V6_FIRST_INVOCATION_SOURCE_NOT_ADMITTED")
        for i in (7, 8, 9, 10):
            player = PHASES[i][1].split()[3]
            line = await owner.issue(*PHASES[i], re.escape(player) + r" has (-?\d+) \[rs_v6_tick\]")
            scores[player] = int(re.search(re.escape(player) + r" has (-?\d+)", line)[1])
        report["scores"] = scores
        need(scores["#attempt"] == scores["#ok"] == 1
             and 0 <= scores["#start_gametime"] <= scores["#before"] == scores["#after"] <= 2**31-1,
             "invalid/overflow/nonatomic server scores")
        # One separate native observation after allowing entity replication.
        await asyncio.sleep(2)
        food = await owner.probe("v6-qualification-after-food")
        need(any(e.name == "item" for e in food.snapshot.nearby_entities), "native food entity missing")
        need(owner.clock_count > 0, "native update_time sample missing")
        report["candidate_elapsed_server_ticks"] = scores["#before"] - scores["#start_gametime"]
        await owner.node_send(encode_shutdown())
        await asyncio.wait_for(owner.node.wait(), 10)
        await asyncio.wait_for(owner.tasks[1], 5)
        need(owner.stop_ack and owner.node.returncode == 0, "native STOP ACK/exit missing")
        await owner.issue(*PHASES[11], "Stopping server")
        await asyncio.wait_for(owner.server.wait(), 30)
        await asyncio.wait_for(owner.tasks[0], 5)
        need(owner.server.returncode == 0, "Java did not exit cleanly")
        report["status"] = "ENGINEERING_CAPTURE_COMPLETED_R_REVIEW_REQUIRED"
    finally:
        await owner.cleanup(report)
        report["capture"] = capture.close()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "grant", "r-checkout", "start-checkout", "food-checkout",
                 "golden-checkout", "jar", "golden", "manifest", "initial-evidence", "node-root", "node"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--s-head", required=True)
    p.add_argument("--slot", default="WORLD_START_A")
    p.add_argument("--nonce", required=True)
    p.add_argument("--confirm", choices=(CONFIRM,))
    args = p.parse_args(argv)
    need(args.output.is_absolute() and not args.output.exists() and not args.output.is_symlink(), "fresh external output required")
    args.output.mkdir(mode=0o700)
    report = {"classification": "PREWORLD_BLOCKED", "java_started": False,
              "java_launch_calls": 0, "grant_consumed_conservatively": False,
              "science_g3": "NO_GO", "production": "NO_GO", "v6_trials": 0,
              "self_action_count": 0, "m_credit_count": 0, "s_head": args.s_head}
    rc = 2
    try:
        run = prepare(args, report)
        if args.confirm is None:
            report["classification"] = "STOPPED_CLONE_PREPARED_NOT_RUN"
            rc = 0
        else:
            asyncio.run(execute(args, run, report))
            need(report.get("native_stop_ack") and report.get("java_pid_gone")
                 and report.get("node_pid_gone") and report.get("port_rebind")
                 and not report.get("stream_errors"), "cleanup incomplete")
            report["classification"] = "ENGINEERING_WORLD_CAPTURE_ONLY_NOT_SCIENCE"
            rc = 0
    except Exception as exc:
        report["error"] = type(exc).__name__ + ": " + str(exc)
        if report["grant_consumed_conservatively"]:
            report["classification"] = "WORLD_QUALIFICATION_FAILED_GRANT_CONSUMED_NO_RETRY"
    finally:
        saved(args.output / "report.json", report)
    print(json.dumps(report, sort_keys=True))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
