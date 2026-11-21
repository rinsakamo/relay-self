from experiments.nld_easy_permutation_isolation import (
    build_isolation_cases,
    build_isolation_schedule,
    dry_run_payload,
    parsed_destination,
    summarize_isolation,
)


def test_cases_form_expected_two_by_two_surface() -> None:
    cases = {case.case_id: case for case in build_isolation_cases()}

    assert cases["cave_open_a_cave"].expected_label == "A"
    assert cases["cave_open_a_ridge"].expected_label == "B"
    assert cases["ridge_open_a_cave"].expected_label == "B"
    assert cases["ridge_open_a_ridge"].expected_label == "A"

    assert cases["cave_open_a_cave"].feasible_destination == "cave"
    assert cases["cave_open_a_ridge"].feasible_destination == "cave"
    assert cases["ridge_open_a_cave"].feasible_destination == "ridge"
    assert cases["ridge_open_a_ridge"].feasible_destination == "ridge"


def test_parsed_destination_uses_cell_mapping() -> None:
    cases = {case.case_id: case for case in build_isolation_cases()}

    assert parsed_destination(cases["cave_open_a_cave"], "A") == "cave"
    assert parsed_destination(cases["cave_open_a_ridge"], "A") == "ridge"
    assert parsed_destination(cases["cave_open_a_ridge"], "B") == "cave"
    assert parsed_destination(cases["ridge_open_a_cave"], "C") == "DEFER"
    assert parsed_destination(cases["ridge_open_a_cave"], None) == "INVALID"


def test_schedule_balances_each_cell_mode_across_positions() -> None:
    schedule = build_isolation_schedule()

    assert len(schedule) == 72

    for case in build_isolation_cases():
        case_rows = [
            row for row in schedule if row["case_id"] == case.case_id
        ]
        assert len(case_rows) == 18

        for mode in ("ar", "dlm", "linear_spec"):
            rows = [
                row for row in case_rows if row["mode"] == mode
            ]
            assert len(rows) == 6
            for position in (1, 2, 3):
                assert sum(
                    row["ordinal_position"] == position for row in rows
                ) == 2


def test_summary_keeps_label_and_destination_distributions() -> None:
    case = build_isolation_cases()[1]
    observations = []
    for position, label in enumerate(("A", "B", "B"), start=1):
        observations.append(
            {
                "case_id": case.case_id,
                "mode": "ar",
                "ordinal_position": position,
                "elapsed_seconds": 0.1 * position,
                "nfe": 3,
                "generated_token_count": 3,
                "tokens_per_forward": 1.0,
                "parsed_label": label,
                "parsed_destination": parsed_destination(case, label),
                "decision_correct": label == case.expected_label,
                "cuda_peak_allocated_bytes": 100,
            }
        )

    summary = summarize_isolation(observations)
    ar = summary[case.case_id]["modes"]["ar"]

    assert ar["observed_labels"] == {"A": 1, "B": 2}
    assert ar["observed_destinations"] == {"cave": 2, "ridge": 1}
    assert ar["correct_count"] == 2


def test_dry_run_records_fixed_display_order_scope() -> None:
    payload = dry_run_payload(
        model_id="example/nld",
        max_new_tokens=32,
        max_thinking_tokens=32,
        seed=1,
        dtype="bf16",
    )

    assert payload["evidence_class"] == "easy permutation isolation plan only"
    assert payload["measured_observation_count"] == 72
    assert payload["observations_per_case_mode_cell"] == 6
    assert payload["warmup_modes"] == ["ar", "dlm", "linear_spec"]
    assert any(
        "display order remains fixed" in statement
        for statement in payload["non_claims"]
    )
