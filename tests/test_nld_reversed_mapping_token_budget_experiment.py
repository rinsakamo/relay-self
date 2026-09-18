from experiments.nld_reversed_mapping_token_budget import (
    TOKEN_BUDGETS,
    build_budget_cases,
    build_budget_schedule,
    dry_run_payload,
    parsed_destination,
    summarize_budget_isolation,
)
from experiments.nld_tri_mode import parse_decision


def test_parse_decision_exposes_source_without_changing_label_semantics() -> None:
    explicit = parse_decision("Decision: B. Alternative A was considered.")
    assert explicit.label == "B"
    assert explicit.source == "explicit"
    assert explicit.explicit_label == "B"
    assert explicit.fallback_label == "A"

    fallback = parse_decision("I considered A, then choose C.")
    assert fallback.label == "C"
    assert fallback.source == "fallback"
    assert fallback.explicit_label is None
    assert fallback.fallback_label == "C"

    none = parse_decision("no bounded label")
    assert none.label is None
    assert none.source == "none"


def test_budget_cases_keep_only_reversed_mapping_cells() -> None:
    cases = {case.case_id: case for case in build_budget_cases()}

    assert set(cases) == {
        "reversed_cave_open",
        "reversed_ridge_open",
    }
    assert cases["reversed_cave_open"].expected_label == "B"
    assert cases["reversed_cave_open"].feasible_destination == "cave"
    assert cases["reversed_ridge_open"].expected_label == "A"
    assert cases["reversed_ridge_open"].feasible_destination == "ridge"

    for case in cases.values():
        assert case.label_to_destination == {
            "A": "ridge",
            "B": "cave",
            "C": "DEFER",
        }


def test_schedule_balances_case_budget_mode_and_positions() -> None:
    schedule = build_budget_schedule()
    assert TOKEN_BUDGETS == (32, 64)
    assert len(schedule) == 72

    for case in build_budget_cases():
        for max_new_tokens in TOKEN_BUDGETS:
            subject = [
                row
                for row in schedule
                if row["case_id"] == case.case_id
                and row["max_new_tokens"] == max_new_tokens
            ]
            assert len(subject) == 18
            for mode in ("ar", "dlm", "linear_spec"):
                rows = [row for row in subject if row["mode"] == mode]
                assert len(rows) == 6
                for position in (1, 2, 3):
                    assert sum(
                        row["ordinal_position"] == position for row in rows
                    ) == 2


def test_parsed_destination_uses_reversed_mapping() -> None:
    case = build_budget_cases()[0]
    assert parsed_destination(case, "A") == "ridge"
    assert parsed_destination(case, "B") == "cave"
    assert parsed_destination(case, "C") == "DEFER"
    assert parsed_destination(case, None) == "INVALID"


def test_summary_preserves_parse_and_termination_evidence() -> None:
    case = build_budget_cases()[0]
    observations = []
    for position, source in enumerate(
        ("explicit", "fallback", "none"),
        start=1,
    ):
        label = "B" if source != "none" else None
        observations.append(
            {
                "case_id": case.case_id,
                "max_new_tokens": 32,
                "mode": "linear_spec",
                "ordinal_position": position,
                "elapsed_seconds": 0.1 * position,
                "nfe": 10,
                "generated_token_count": 32,
                "tokens_per_forward": 3.2,
                "parsed_label": label,
                "parsed_destination": (
                    parsed_destination(case, label)
                ),
                "decision_correct": label == case.expected_label,
                "parse_source": source,
                "explicit_label": "B" if source == "explicit" else None,
                "fallback_label": "B" if source == "fallback" else None,
                "eos_reached": source == "explicit",
                "reached_or_exceeded_effective_max_new_tokens": (
                    source != "explicit"
                ),
                "cuda_peak_allocated_bytes": 100,
            }
        )

    summary = summarize_budget_isolation(observations)
    row = summary[case.case_id]["budgets"]["32"]["modes"]["linear_spec"]

    assert row["parse_sources"] == {
        "explicit": 1,
        "fallback": 1,
        "none": 1,
    }
    assert row["observed_destinations"] == {
        "INVALID": 1,
        "cave": 2,
    }
    assert row["eos_reached"] == {"false": 2, "true": 1}
    assert row["token_cap_proxy"] == {"false": 1, "true": 2}


def test_dry_run_records_two_output_budgets_and_six_warmups() -> None:
    payload = dry_run_payload(
        model_id="example/nld",
        max_thinking_tokens=32,
        seed=1,
        dtype="bf16",
    )

    assert payload["evidence_class"] == (
        "reversed mapping token-budget plan only"
    )
    assert payload["token_budgets"] == [32, 64]
    assert payload["measured_observation_count"] == 72
    assert payload["observations_per_case_budget_mode_cell"] == 6
    assert len(payload["warmup_subjects"]) == 6
