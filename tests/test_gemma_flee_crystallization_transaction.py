from pathlib import Path

from experiments.gemma_flee_crystallization_transaction import (
    _experiment_command,
)


def test_experiment_command_uses_no_bytecode_and_artifact_output() -> None:
    command = _experiment_command(
        endpoint="http://127.0.0.1:1234/v1/chat/completions",
        model="gemma-local",
        timeout=60.0,
        output_path=Path("/tmp/result.json"),
        artifact_output_path=Path("/tmp/artifact.json"),
        run=True,
    )

    assert command[1:4] == [
        "-B",
        "-m",
        "experiments.gemma_flee_crystallization",
    ]
    assert "--run" in command
    assert command[command.index("--artifact-output") + 1] == (
        "/tmp/artifact.json"
    )


def test_canonical_launcher_owns_source_layout_import_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    launcher = (
        repo_root
        / "experiments"
        / "run_gemma_flee_crystallization_transaction.sh"
    ).read_text(encoding="utf-8")

    assert 'SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"' in launcher
    assert 'REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"' in launcher
    assert 'export PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"' in launcher
    assert (
        'exec python3 -B -m '
        'experiments.gemma_flee_crystallization_transaction "$@"'
    ) in launcher


def test_experiment_command_writes_protocol_failure_artifact() -> None:
    command = _experiment_command(
        endpoint="http://127.0.0.1:1234/v1/chat/completions",
        model="gemma-local",
        timeout=60.0,
        output_path=Path("/tmp/result.json"),
        artifact_output_path=Path("/tmp/artifact.json"),
        run=True,
        protocol_failure_output_path=Path("/tmp/protocol-failure.json"),
    )

    flag_index = command.index("--protocol-failure-output")
    assert command[flag_index + 1] == "/tmp/protocol-failure.json"
