from experiments.nld_native_path_trajectory import dry_run_payload


def test_dry_run_counts() -> None:
    plan = dry_run_payload()
    assert plan["physical_measured_calls"] == 72
    assert plan["focus_observations"] == 18
