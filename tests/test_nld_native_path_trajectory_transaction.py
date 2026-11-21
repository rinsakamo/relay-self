from pathlib import Path

from experiments.nld_native_path_trajectory_transaction import (
    build_analysis_command,
)


def test_analysis_command_supports_plan_and_input(tmp_path: Path) -> None:
    output = tmp_path / "out.json"

    plan = build_analysis_command(
        input_path=None,
        output_path=output,
    )
    assert "--input" not in plan

    actual = build_analysis_command(
        input_path=tmp_path / "raw.json",
        output_path=output,
    )
    assert "--input" in actual
