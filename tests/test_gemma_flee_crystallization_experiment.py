from experiments.gemma_flee_crystallization import (
    ARTIFACT_ALGORITHM,
    build_holdout_broad_request,
    build_holdout_schedule,
    dry_run_payload,
    filter_request,
)
from experiments.gemma_skill_narrowing import CASES, build_request


def test_dry_run_has_expected_training_and_holdout_shape() -> None:
    payload = dry_run_payload()
    assert payload["artifact_algorithm"] == ARTIFACT_ALGORITHM
    assert payload["candidate_key_count"] == 22
    assert payload["ordinary_training_episode_count"] == 4
    assert payload["maximum_ablation_episode_count"] == 88
    assert payload["holdout_measured_episode_count"] == 48


def test_holdout_schedule_balances_before_after() -> None:
    rows = build_holdout_schedule()
    assert len(rows) == 48
    for case in CASES:
        case_rows = [
            row for row in rows if row["case_id"] == case.case_id
        ]
        assert len(case_rows) == 12
        assert sum(row["condition"] == "before" for row in case_rows) == 6
        assert sum(row["condition"] == "after" for row in case_rows) == 6
        assert {
            row["order_index"]
            for row in case_rows
            if row["condition"] == "before"
        } == {0, 1}
        assert {
            row["order_index"]
            for row in case_rows
            if row["condition"] == "after"
        } == {0, 1}


def test_filter_request_uses_only_frozen_key_whitelist() -> None:
    broad = build_request(CASES[0], condition="broad")
    retained = tuple(
        datum.key
        for datum in broad.context
        if datum.key.startswith("route_open:")
    )
    filtered = filter_request(broad, retained_keys=retained)

    assert filtered.request_id == broad.request_id
    assert filtered.instruction == broad.instruction
    assert filtered.choices == broad.choices
    assert tuple(datum.key for datum in filtered.context) == retained


def test_holdout_changes_experience_surface_without_changing_choices() -> None:
    training = build_request(CASES[0], condition="broad")
    holdout = build_holdout_broad_request(CASES[0], case_index=0)

    assert holdout.request_id != training.request_id
    assert holdout.instruction == training.instruction
    assert holdout.choices == training.choices
    assert tuple(d.key for d in holdout.context) == tuple(
        d.key for d in training.context
    )
    assert any(
        left.value_json != right.value_json
        for left, right in zip(training.context, holdout.context)
    )
