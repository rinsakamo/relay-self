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
