from experiments.nld_lexical_remapping_generalization import (
    FAMILIES,
    build_cases,
    build_schedule,
    dry_run_payload,
    parsed_destination,
)


def test_matrix_shape() -> None:
    assert [family.family_id for family in FAMILIES] == [
        "route",
        "color",
        "code",
    ]
    assert len(build_cases()) == 12
    assert len(build_schedule()) == 216


def test_each_family_has_balanced_expected_labels() -> None:
    for family in FAMILIES:
        cases = [
            case
            for case in build_cases()
            if case.family_id == family.family_id
        ]
        assert len(cases) == 4
        assert sorted(case.expected_label for case in cases) == [
            "A",
            "A",
            "B",
            "B",
        ]


def test_schedule_balances_mode_and_ordinal_position() -> None:
    for case in build_cases():
        rows = [
            row
            for row in build_schedule()
            if row["case_id"] == case.case_id
        ]
        assert len(rows) == 18
        for mode in ("ar", "dlm", "linear_spec"):
            mode_rows = [
                row for row in rows if row["mode"] == mode
            ]
            assert len(mode_rows) == 6
            for position in (1, 2, 3):
                assert sum(
                    row["ordinal_position"] == position
                    for row in mode_rows
                ) == 2


def test_mapping_projection_is_semantic() -> None:
    case = next(
        case
        for case in build_cases()
        if case.case_id == "color__entity1_open__a_entity2"
    )
    assert case.expected_label == "B"
    assert parsed_destination(case, "A") == "cobalt"
    assert parsed_destination(case, "B") == "amber"
    assert parsed_destination(case, None) == "INVALID"


def test_dry_run_records_complete_matrix() -> None:
    payload = dry_run_payload(
        model_id="example/nld",
        seed=1,
        dtype="bf16",
    )
    assert payload["measured_observation_count"] == 216
    assert payload["observations_per_case_mode_cell"] == 6
    assert len(payload["families"]) == 3
    assert len(payload["cases"]) == 12
