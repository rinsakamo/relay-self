"""Owner-local llama-server subprocess lifecycle tests: NO real GGUF/GPU/World."""
from __future__ import annotations

import hashlib
import json
import os
import socket
import stat
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from adapters.mineflayer import self_owned_llama as owned
from adapters.mineflayer.self_demo import CONFIRM


SCRIPT = """#!/usr/bin/env python3
import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
p=argparse.ArgumentParser()
p.add_argument('--alias',required=True)
p.add_argument('--port',type=int,required=True)
args,_=p.parse_known_args()
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  if self.path=='/health':
   b=b'{"status":"ok"}'
  elif self.path=='/v1/models':
   b=json.dumps({"data":[{"id":args.alias}]}).encode()
  else:
   self.send_response(404);self.end_headers();return
  self.send_response(200);self.send_header('Content-Length',str(len(b)))
  self.end_headers();self.wfile.write(b)
 def log_message(self,*a):pass
HTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
"""


def _port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _args(tmp_path, *, alias="fake-self-model", port=None):
    work = tmp_path / "evidence"
    work.mkdir()
    binary = tmp_path / "llama-server"
    binary.write_text(SCRIPT, encoding="utf-8")
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    gguf = tmp_path / "model.gguf"
    gguf.write_bytes(b"TEST_MOCK_ONLY_NOT_A_REAL_GGUF")
    digest = hashlib.sha256(gguf.read_bytes()).hexdigest()
    return (
        ["--run-disposable", "--confirm", CONFIRM,
         "--output-dir", str(work),
         "--llama-server", str(binary), "--gguf", str(gguf),
         "--gguf-sha256", digest,
         "--model-alias", alias, "--model-port", str(port or _port()),
         "--ready-timeout", "2", "--model-timeout", "1"],
        work,
    )


def _toolchain(monkeypatch):
    import shutil

    real = shutil.which
    monkeypatch.setattr(
        shutil, "which",
        lambda x: "/ci/fake/" + x if x in ("java", "node") else real(x),
    )


def test_owned_localhost_model_spawn_once_reuses_original_world_cli_and_stops(
    tmp_path, monkeypatch,
):
    _toolchain(monkeypatch)
    args, work = _args(tmp_path)
    calls = []
    def fake_self_cli(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(owned.subprocess, "run", fake_self_cli)
    assert owned.main(args) == 0
    assert len(calls) == 1
    cmd, options = calls[0]
    assert cmd[1:3] == ["-m", "adapters.mineflayer.self_demo"]
    assert "--live-think" in cmd
    assert "--confirm" in cmd and CONFIRM in cmd
    assert "src" in options["env"]["PYTHONPATH"]
    result = json.loads((work / owned.REPORT_NAME).read_text())
    assert result["model_process_launched"] is True
    assert result["loopback_health_and_alias_checked"] is True
    assert result["self_demo_exit"] == 0
    assert result["owned_process_waited"] is True
    assert result["stop_ack"] is False
    assert result["gpu_release_verified"] is False
    assert result["backend_model_identity_attested"] is False
    assert result["physical_minecraft_outcome_attested_by_wrapper"] is False
    assert (work / owned.LOG_NAME).is_file()
    assert not owned._ready(int(args[args.index("--model-port")+1]), "fake-self-model")


@pytest.mark.parametrize("variant", [
    "no_consent", "wrong_sha", "occupied_port", "output_collision",
    "symlink_model", "model_alias_injection", "invalid_gpu", "wrong_model_suffix",
])
def test_preflight_blocks_without_model_or_minecraft_side_effects(
    tmp_path, monkeypatch, variant, capsys,
):
    _toolchain(monkeypatch)
    args, work = _args(tmp_path)
    if variant == "no_consent":
        args[args.index("--confirm")+1] = "NO_PERMISSION"
    elif variant == "wrong_sha":
        args[args.index("--gguf-sha256")+1] = "0" * 64
    elif variant == "output_collision":
        (work / "previous-run").write_text("KEEP")
    elif variant == "model_alias_injection":
        args[args.index("--model-alias")+1] = "../model;rm -rf"
    elif variant == "invalid_gpu":
        args.extend(["--gpu-layers", "500"])
    elif variant == "wrong_model_suffix":
        gguf = Path(args[args.index("--gguf")+1])
        renamed = gguf.with_suffix(".bin")
        gguf.rename(renamed)
        args[args.index("--gguf")+1] = str(renamed)
    elif variant == "symlink_model":
        gguf = Path(args[args.index("--gguf")+1])
        sym = gguf.with_name("link.gguf")
        sym.symlink_to(gguf)
        args[args.index("--gguf")+1] = str(sym)
    elif variant == "occupied_port":
        port = int(args[args.index("--model-port")+1])
        blocker = socket.socket()
        blocker.bind(("127.0.0.1", port))
    try:
        assert owned.main(args) == 2
        assert "BLOCKED" in capsys.readouterr().out
        assert not (work / owned.REPORT_NAME).exists()
        assert not (work / owned.LOG_NAME).exists()
    finally:
        if variant == "occupied_port":
            blocker.close()


def test_owned_child_exits_before_readiness_never_launches_world(
    tmp_path, monkeypatch,
):
    _toolchain(monkeypatch)
    args, work = _args(tmp_path)
    binary = Path(args[args.index("--llama-server")+1])
    binary.write_text("#!/usr/bin/env python3\nimport sys\nsys.exit(3)\n")
    invoked = []
    monkeypatch.setattr(
        owned.subprocess, "run",
        lambda *a, **k: invoked.append("WORLD") or SimpleNamespace(returncode=0),
    )
    assert owned.main(args) == 1
    assert not invoked
    saved = json.loads((work / owned.REPORT_NAME).read_text())
    assert saved["status"] == "MODEL_EARLY_EXIT"
    assert saved["minecraft_launch_attempted"] is False
    assert saved["owned_process_waited"] is True


def test_existing_loopback_alias_mismatch_never_executes_game(
    tmp_path, monkeypatch,
):
    _toolchain(monkeypatch)
    args, work = _args(tmp_path)
    binary = Path(args[args.index("--llama-server")+1])
    binary.write_text(SCRIPT.replace(
        'args.alias', '"WRONG_ALIAS"'
    ), encoding="utf-8")
    calls = []
    monkeypatch.setattr(
        owned.subprocess, "run",
        lambda *a, **k: calls.append(a) or SimpleNamespace(returncode=0),
    )
    args[args.index("--ready-timeout")+1] = "1"
    assert owned.main(args) == 1
    assert not calls
    saved = json.loads((work / owned.REPORT_NAME).read_text())
    assert saved["status"] == "MODEL_READINESS_TIMEOUT"
    assert saved["minecraft_launch_attempted"] is False


def test_owned_llama_wrapper_is_not_an_action_or_habit_authority():
    content = Path(owned.__file__).read_text()
    assert "adapters.mineflayer.self_demo" in content
    for forbidden in (
        "ActionSupervisor(", "commit_learning_update(",
        "commit_test_quorum_habit(", "execute_mineflayer_command(",
        "killall(", "pkill(", "os.system(", "shell=True",
        "backend_stop_ack=True", "gpu_release_verified=True",
    ):
        assert forbidden not in content


def test_helper_defensive_model_file_type_and_process_group(monkeypatch, tmp_path):
    with pytest.raises(owned.OwnedModelRejected):
        owned._regular(tmp_path)
    monkeypatch.setattr(os, "getpgid", lambda _: 999)
    proc = SimpleNamespace(pid=123, poll=lambda: None)
    with pytest.raises(owned.OwnedModelRejected):
        owned._stop_only_owned(proc)
