from experiments.nld_bounded_difficulty_matrix import (
    build_matrix_cases,
    build_matrix_schedule,
    dry_run_payload,
    summarize_matrix,
)


def test_cases_preserve_expected_bounded_semantics() -> None:
    cases = {case.case_id: case for case in build_matrix_cases()}

    assert cases["easy_separable"].expected_label == "A"
    assert cases["coupled_constraints"].expected_label == "B"
    assert cases["incomplete_focus"].expected_label == "C"

    assert "Cave route open: UNKNOWN" in cases["incomplete_focus"].prompt
    assert "Do not invent missing World facts." in cases["incomplete_focus"].prompt
    assert "Energy available: 3" in cases["coupled_constraints"].prompt


def test_schedule_balances_each_case_mode_across_positions() -> None:
    schedule = build_matrix_schedule()

    assert len(schedule) == 54

    case_ids = (
        "easy_separable",
        "coupled_constraints",
        "incomplete_focus",
    )
    modes = ("ar", "dlm", "linear_spec")

    for case_id in case_ids:
        case_rows = [
            row for row in schedule if row["case_id"] == case_id
        ]
        assert len(case_rows) == 18

        for mode in modes:
            rows = [
                row for row in case_rows if row["mode"] == mode
            ]
            assert len(rows) == 6
            for position in (1, 2, 3):
                assert sum(
                    row["ordinal_position"] == position for row in rows
                ) == 2


def test_schedule_is_deterministic() -> None:
    assert build_matrix_schedule() == build_matrix_schedule()


def test_summary_preserves_wrong_and_invalid_outputs() -> None:
    observations = []
    for case_index, case in enumerate(build_matrix_cases(), start=1):
        for mode_index, mode in enumerate(
            ("ar", "dlm", "linear_spec"),
            start=1,
        ):
            for position in (1, 2, 3):
                parsed_label = case.expected_label
                decision_correct = True
                if (
                    case.case_id == "coupled_constraints"
                    and mode == "dlm"
                    and position == 1
                ):
                    parsed_label = "A"
                    decision_correct = False
                if (
                    case.case_id == "incomplete_focus"
                    and mode == "linear_spec"
                    and position == 2
                ):
                    parsed_label = None
                    decision_correct = False

                observations.append(
                    {
                        "case_id": case.case_id,
                        "mode": mode,
                        "ordinal_position": position,
                        "elapsed_seconds": float(
                            case_index * mode_index * position
                        ),
                        "nfe": mode_index,
                        "generated_token_count": 3,
                        "tokens_per_forward": 3 / mode_index,
                        "parsed_label": parsed_label,
                        "decision_correct": decision_correct,
                        "cuda_peak_allocated_bytes": 100 + mode_index,
                    }
                )

    summary = summarize_matrix(observations)

    coupled_dlm = summary["coupled_constraints"]["modes"]["dlm"]
    assert coupled_dlm["count"] == 3
    assert coupled_dlm["correct_count"] == 2
    assert coupled_dlm["observed_labels"] == {"A": 1, "B": 2}

    incomplete_linear = summary["incomplete_focus"]["modes"]["linear_spec"]
    assert incomplete_linear["correct_count"] == 2
    assert incomplete_linear["invalid_output_count"] == 1
    assert incomplete_linear["observed_labels"]["INVALID"] == 1


def test_dry_run_records_bounded_matrix_nonclaims() -> None:
    payload = dry_run_payload(
        model_id="example/nld",
        max_new_tokens=32,
        max_thinking_tokens=32,
        seed=1,
        dtype="bf16",
    )

    assert payload["evidence_class"] == "bounded difficulty matrix plan only"
    assert payload["measured_observation_count"] == 54
    assert payload["observations_per_case_mode_cell"] == 6
    assert payload["warmup_modes"] == ["ar", "dlm", "linear_spec"]
    assert payload["runtime"]["same_loaded_model"] is True
    assert any(
        "not treated as a validated cognition-depth budget" in statement
        for statement in payload["non_claims"]
    )
