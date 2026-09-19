import json

from adapters.llama_cpp.relay_engine import render_llama_cpp_request
from experiments.gemma_flee_crystallization import (
    ARTIFACT_ALGORITHM,
    METADATA_BLINDING,
    build_holdout_broad_request,
    build_holdout_schedule,
    build_training_broad_request,
    dry_run_payload,
    filter_request,
    write_protocol_failure,
)
from experiments.gemma_skill_narrowing import CASES, build_request
from relay_self.relay_engine import CognitionMode


def test_dry_run_has_expected_training_and_holdout_shape() -> None:
    payload = dry_run_payload()
    assert payload["artifact_algorithm"] == ARTIFACT_ALGORITHM
    assert payload["metadata_blinding"] == METADATA_BLINDING
    assert payload["provider_visible_semantic_case_ids"] is False
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
    training = build_training_broad_request(CASES[0], case_index=0)
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


def _provider_visible_metadata(request) -> dict[str, object]:
    rendered = render_llama_cpp_request(
        request,
        mode=CognitionMode.BOUNDED,
        model="gemma-local",
    )
    user = json.loads(rendered["messages"][1]["content"])
    return {
        "request_id": user["request_id"],
        "provenance_references": [
            datum["provenance"]["reference"]
            for datum in user["context"]
        ],
    }


def test_source_fixture_contains_semantic_case_label_before_blinding() -> None:
    case = CASES[2]
    source = build_request(case, condition="broad")

    assert case.case_id in source.request_id
    assert any(
        case.case_id in datum.provenance.reference
        for datum in source.context
    )


def test_training_provider_metadata_is_opaque_to_semantic_case_labels() -> None:
    for case_index, case in enumerate(CASES):
        request = build_training_broad_request(
            case,
            case_index=case_index,
        )
        metadata = _provider_visible_metadata(request)
        serialized = json.dumps(metadata, sort_keys=True)

        assert request.request_id == (
            f"crystallization:train:{case_index:02d}"
        )
        assert case.case_id not in serialized
        for other_case in CASES:
            assert other_case.case_id not in serialized


def test_holdout_provider_metadata_is_opaque_to_semantic_case_labels() -> None:
    for case_index, case in enumerate(CASES):
        request = build_holdout_broad_request(
            case,
            case_index=case_index,
        )
        metadata = _provider_visible_metadata(request)
        serialized = json.dumps(metadata, sort_keys=True)

        assert request.request_id == (
            f"crystallization:eval:{case_index:02d}"
        )
        assert case.case_id not in serialized
        for other_case in CASES:
            assert other_case.case_id not in serialized


def test_reconstructed_trial_14_surface_after_first_13_acceptances() -> None:
    candidate_keys = dry_run_payload()["candidate_keys"]
    assert isinstance(candidate_keys, list)
    assert candidate_keys[13] == "route_open:cave"

    broad = build_request(CASES[0], condition="broad")
    filtered = filter_request(
        broad,
        retained_keys=tuple(candidate_keys[14:]),
    )

    assert tuple(datum.key for datum in filtered.context) == (
        "threat_nearby",
        "route_open:ridge",
        "shelter:cave",
        "shelter:ridge",
        "saturation",
        "tool:pickaxe_durability",
        "xp_level",
        "storage_free_slots",
    )


def test_protocol_failure_writer_preserves_record(tmp_path) -> None:
    output = tmp_path / "protocol-failure.json"
    record = {
        "mode": "think",
        "raw_text": "",
        "reasoning_content": "side-channel",
        "protocol_error": "invalid JSON",
    }

    write_protocol_failure(record, str(output))

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["evidence_class"] == (
        "llama.cpp provider protocol failure"
    )
    assert payload["record"] == record
