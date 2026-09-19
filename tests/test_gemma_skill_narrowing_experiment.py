from experiments.gemma_skill_narrowing import (
    BROAD_DISTRACTORS,
    CASES,
    build_request,
    build_schedule,
    dry_run_payload,
)


def test_schedule_balances_broad_and_narrow() -> None:
    rows = build_schedule()
    assert len(rows) == 48

    for case in CASES:
        case_rows = [
            row for row in rows if row["case_id"] == case.case_id
        ]
        assert len(case_rows) == 12
        for condition in ("broad", "narrow"):
            condition_rows = [
                row
                for row in case_rows
                if row["condition"] == condition
            ]
            assert len(condition_rows) == 6
            assert {
                row["order_index"] for row in condition_rows
            } == {0, 1}


def test_narrowing_changes_only_context_surface() -> None:
    case = CASES[0]
    broad = build_request(case, condition="broad")
    narrow = build_request(case, condition="narrow")

    assert broad.request_id == narrow.request_id
    assert broad.instruction == narrow.instruction
    assert broad.intent_id == narrow.intent_id
    assert broad.focus == narrow.focus
    assert broad.choices == narrow.choices
    assert len(narrow.context) == 6
    assert len(broad.context) == 6 + len(BROAD_DISTRACTORS)
    assert broad.context[:6] == narrow.context


def test_dry_run_records_expected_matrix() -> None:
    payload = dry_run_payload()
    assert payload["measured_episode_count"] == 48
    assert payload["observations_per_case_condition"] == 6
    assert payload["broad_distractor_count"] == len(BROAD_DISTRACTORS)
