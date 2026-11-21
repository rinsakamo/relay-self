from pathlib import Path

from experiments.nld_adequate_cost_surface_transaction import build_command


def test_build_command_keeps_qualified_runtime(tmp_path: Path) -> None:
    command = build_command(
        model_id="example/nld",
        output_path=tmp_path / "result.json",
        run=True,
    )
    assert "--run" in command
    assert command[command.index("--dtype") + 1] == "bf16"
    assert command[command.index("--seed") + 1] == "1"
