from experiments.nld_adequate_cost_surface import (
    build_cost_cases,
    build_schedule,
    dry_run_payload,
)


def test_cost_surface_uses_color_family_only() -> None:
    cases = build_cost_cases()
    assert len(cases) == 4
    assert all(case.family_id == "color" for case in cases)


def test_cost_surface_schedule_is_balanced() -> None:
    schedule = build_schedule()
    assert len(schedule) == 72

    for case in build_cost_cases():
        rows = [
            row for row in schedule if row["case_id"] == case.case_id
        ]
        assert len(rows) == 18
        for mode in ("ar", "dlm", "linear_spec"):
            mode_rows = [row for row in rows if row["mode"] == mode]
            assert len(mode_rows) == 6
            for position in (1, 2, 3):
                assert sum(
                    row["ordinal_position"] == position
                    for row in mode_rows
                ) == 2


def test_dry_run_records_matched_subject() -> None:
    payload = dry_run_payload(
        model_id="example/nld",
        seed=1,
        dtype="bf16",
    )
    assert payload["measured_observation_count"] == 72
    assert payload["observations_per_case_mode_cell"] == 6
    assert len(payload["cases"]) == 4
