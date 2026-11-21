from experiments.gemma_skill_narrowing_transaction import (
    _experiment_command,
)


def test_experiment_command_uses_no_bytecode_and_expected_surface(tmp_path) -> None:
    command = _experiment_command(
        endpoint="http://127.0.0.1:1234/v1/chat/completions",
        model="gemma-local",
        timeout=60.0,
        output_path=tmp_path / "result.json",
        run=True,
    )

    assert command[1:4] == [
        "-B",
        "-m",
        "experiments.gemma_skill_narrowing",
    ]
    assert "--run" in command
    assert command[command.index("--model") + 1] == "gemma-local"
