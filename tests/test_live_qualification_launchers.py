import importlib
import socket
import subprocess
import urllib.request
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest

# Static source-layout identity and guarded argparse help are separate proofs.
# Shell cwd/PYTHONPATH setup, interpreter lookup and actual exec/argv forwarding
# are NOT exercised; end-to-end coverage awaits a separately authorized owner.
LAYOUT = (
    '#!/usr/bin/env bash\n'
    'set -euo pipefail\n\n'
    'SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"\n'
    'REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"\n'
    'export PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"\n\n'
    'cd "$REPO_ROOT"\n'
)
CASES = (
    (
        "adapters/mineflayer/run_live_qualification.sh",
        "adapters.mineflayer.qualify_live",
        "Run the RelaySelf Mineflayer live qualification transaction.",
    ),
    (
        "adapters/llama_cpp/run_relay_engine_qualification.sh",
        "adapters.llama_cpp.qualify_relay_engine",
        "Qualify one real llama.cpp-backed RelayEngine bounded decision.",
    ),
)


def _assert_identity(text, module_name):
    assert text == LAYOUT + f'exec python3 -B -m {module_name} "$@"\n'


@pytest.mark.parametrize(("relative_path", "module_name", "help_text"), CASES)
def test_live_qualification_static_layout_and_guarded_parser_help(
    relative_path, module_name, help_text, capsys,
):
    launcher = Path(__file__).resolve().parents[1] / relative_path
    _assert_identity(launcher.read_text(encoding="utf-8"), module_name)
    with ExitStack() as stack:
        guards = [stack.enter_context(patch.object(
            obj, name, side_effect=AssertionError(f"forbidden help operation: {name}"),
        )) for obj, name in (
            (subprocess, "Popen"), (subprocess, "run"),
            (socket, "socket"), (urllib.request, "urlopen"),
            (Path, "mkdir"), (Path, "write_text"), (Path, "write_bytes"),
        )]
        module = importlib.import_module(module_name)
        guards.append(stack.enter_context(patch.object(
            module, "run_live_qualification",
            side_effect=AssertionError("help attempted qualification"),
        )))
        # Direct parser only: no CLI subprocess, coroutine loop or live owner.
        with pytest.raises(SystemExit) as exited:
            module._parser().parse_args(["--help"])
        assert exited.value.code == 0
        assert help_text in capsys.readouterr().out
        for guard in guards:
            guard.assert_not_called()


@pytest.mark.parametrize(("relative_path", "module_name", "help_text"), CASES)
@pytest.mark.parametrize("mutation", [
    lambda text: text.replace(" -B ", " "),
    lambda text: text.replace(" -B ", " -b "),
    lambda text: text.replace('"$@"', "$*"),
    lambda text: text.replace("python3", "python"),
    lambda text: text.replace('cd "$REPO_ROOT"', 'cd /tmp'),
    lambda text: text.replace('$REPO_ROOT/src', '/tmp'),
    lambda text: text + "echo unexpected\n",
])
def test_live_launcher_identity_rejects_drift(relative_path, module_name, help_text, mutation):
    expected = LAYOUT + f'exec python3 -B -m {module_name} "$@"\n'
    with pytest.raises(AssertionError):
        _assert_identity(mutation(expected), module_name)
