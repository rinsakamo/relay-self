from experiments.nld_linear_spec_matched import (
    build_schedule,
    dry_run_payload,
)


def test_schedule_has_24_balanced_calls() -> None:
    rows = build_schedule()
    assert len(rows) == 24

    counts: dict[str, int] = {}
    for row in rows:
        case_id = str(row["case_id"])
        counts[case_id] = counts.get(case_id, 0) + 1

    assert len(counts) == 4
    assert set(counts.values()) == {6}


def test_dry_run_records_linear_spec_subject() -> None:
    payload = dry_run_payload(
        model_id="example/nld",
        seed=1,
        dtype="bf16",
    )
    assert payload["mode"] == "linear_spec"
    assert payload["measured_observation_count"] == 24
    assert payload["excluded_warmup_count"] == 1
