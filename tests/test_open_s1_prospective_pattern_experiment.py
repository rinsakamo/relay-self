import json

import pytest

from experiments.cognition_consequence_loop import (
    ConsequenceComparisonKind,
    ExpectedEvidence,
)
from experiments.open_s1_prospective_pattern import (
    InvalidProspectiveProposal,
    build_reference_prospective_fixture,
    exact_replay_baseline,
    hidden_future_is_visible,
    parse_expected_evidence,
    score_proposal,
    visible_request_json,
)
from relay_self.relay_engine import OpenCognitionRequest


def test_prospective_request_is_open_and_has_no_finite_choice_surface() -> None:
    fixture = build_reference_prospective_fixture()

    assert isinstance(fixture.request, OpenCognitionRequest)
    assert fixture.request.focus == "PROSPECTIVE_PATTERN"
    assert not hasattr(fixture.request, "choices")
    assert not hasattr(fixture.request, "choice_id")
    assert not hasattr(fixture.request, "think_allowed")

    rendered = visible_request_json(fixture.request)
    assert '"choices"' not in rendered
    assert '"event:lambda"' not in rendered
    assert '"outcome:9"' not in rendered


def test_held_out_future_does_not_change_proposal_request() -> None:
    first = build_reference_prospective_fixture(
        observed_key="event:lambda",
        observed_code="outcome:9",
    )
    second = build_reference_prospective_fixture(
        observed_key="event:tau",
        observed_code="outcome:11",
    )

    assert first.request == second.request
    assert visible_request_json(first.request) == visible_request_json(second.request)
    assert first.observed != second.observed
    assert hidden_future_is_visible(first) is False
    assert hidden_future_is_visible(second) is False


def test_reference_surface_preserves_present_and_memory_provenance() -> None:
    fixture = build_reference_prospective_fixture()
    context = {datum.key: datum for datum in fixture.request.context}

    assert set(context) == {"current_prefix", "selected_memory"}
    assert context["current_prefix"].provenance.source == "fixture.present"
    assert context["selected_memory"].provenance.source == "fixture.memory"

    memory = json.loads(context["selected_memory"].value_json)
    assert memory["later_evidence"]["key"] == "event:kappa"
    assert memory["later_evidence"]["value"] == {"code": "outcome:3"}

    assert fixture.observed.provenance.source == "fixture.world"
    assert fixture.observed.key == "event:lambda"
    assert fixture.observed.value == {"code": "outcome:9"}


def test_fixture_fails_closed_if_held_out_future_is_already_visible() -> None:
    with pytest.raises(
        ValueError,
        match="held-out future must not appear on the proposal surface",
    ):
        build_reference_prospective_fixture(
            observed_key="event:kappa",
            observed_code="outcome:3",
        )


def test_exact_replay_baseline_does_not_solve_reference_surface() -> None:
    fixture = build_reference_prospective_fixture()

    assert exact_replay_baseline(fixture.request) is None


def test_open_proposal_envelope_is_not_a_finite_answer_list() -> None:
    proposal = parse_expected_evidence(
        '{"key":"event:lambda","value":{"code":"outcome:9"}}'
    )

    assert proposal == ExpectedEvidence(
        key="event:lambda",
        value={"code": "outcome:9"},
    )

    with pytest.raises(
        InvalidProspectiveProposal,
        match="exactly key and value",
    ):
        parse_expected_evidence(
            '{"key":"event:lambda","value":{"code":"outcome:9"},"choices":["A","B"]}'
        )


def test_later_world_evidence_scores_match_mismatch_and_unknown() -> None:
    fixture = build_reference_prospective_fixture()

    matched = score_proposal(
        ExpectedEvidence(
            key="event:lambda",
            value={"code": "outcome:9"},
        ),
        fixture.observed,
    )
    mismatched = score_proposal(
        ExpectedEvidence(
            key="event:lambda",
            value={"code": "outcome:8"},
        ),
        fixture.observed,
    )
    unknown = score_proposal(
        ExpectedEvidence(
            key="event:lambda",
            value={"code": "outcome:9"},
        ),
        None,
    )

    assert matched.kind is ConsequenceComparisonKind.MATCH
    assert mismatched.kind is ConsequenceComparisonKind.MISMATCH
    assert unknown.kind is ConsequenceComparisonKind.UNKNOWN

    assert matched.observed is fixture.observed
    assert mismatched.observed is fixture.observed
    assert unknown.observed is None


@pytest.mark.parametrize(
    "text, message",
    [
        ("", "non-empty text"),
        ("not-json", "valid JSON"),
        ('["event:lambda"]', "exactly key and value"),
        ('{"key":"","value":1}', "key must be non-empty text"),
    ],
)
def test_proposal_parser_fails_closed(text: str, message: str) -> None:
    with pytest.raises(InvalidProspectiveProposal, match=message):
        parse_expected_evidence(text)
