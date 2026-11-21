from pathlib import Path

from experiments.gemma_flee_artifact_reuse_transaction import (
    _experiment_command,
)


def test_experiment_command_uses_no_bytecode_and_protocol_output() -> None:
    command = _experiment_command(
        endpoint="http://127.0.0.1:1234/v1/chat/completions",
        model="gemma-local",
        timeout=60.0,
        output_path=Path("/tmp/result.json"),
        run=True,
        protocol_failure_output_path=Path("/tmp/protocol-failure.json"),
    )

    assert command[1:4] == [
        "-B",
        "-m",
        "experiments.gemma_flee_artifact_reuse",
    ]
    assert "--run" in command
    flag_index = command.index("--protocol-failure-output")
    assert command[flag_index + 1] == "/tmp/protocol-failure.json"


def test_canonical_launcher_owns_source_layout_import_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    launcher = (
        repo_root
        / "experiments"
        / "run_gemma_flee_artifact_reuse_transaction.sh"
    ).read_text(encoding="utf-8")

    assert (
        'SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"'
        in launcher
    )
    assert 'REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"' in launcher
    assert (
        'export PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"'
        in launcher
    )
    assert (
        "exec python3 -B -m "
        'experiments.gemma_flee_artifact_reuse_transaction "$@"'
        in launcher
    )
