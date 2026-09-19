import os
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    ("relative_path", "help_text"),
    (
        (
            "adapters/mineflayer/run_live_qualification.sh",
            "Run the RelaySelf Mineflayer live qualification transaction.",
        ),
        (
            "adapters/llama_cpp/run_relay_engine_qualification.sh",
            "Qualify one real llama.cpp-backed RelayEngine bounded decision.",
        ),
    ),
)
def test_live_qualification_launchers_own_source_layout(
    tmp_path: Path,
    relative_path: str,
    help_text: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    launcher = repo_root / relative_path
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    completed = subprocess.run(
        ["bash", str(launcher), "--help"],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert help_text in completed.stdout
    assert "__pycache__" not in completed.stderr
