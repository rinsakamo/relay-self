import math

import pytest

from experiments.diffusiongemma_bounded_decision import (
    Candidate,
    build_probe_cases,
    checkpoint_records,
    dry_run_payload,
    resolve_single_token_candidates,
    select_cases,
    summarize_candidate_logits,
)


class FakeTokenizer:
    def __init__(self, mapping: dict[str, list[int]]) -> None:
        self.mapping = mapping

    def encode(self, text: str, *, add_special_tokens: bool) -> list[int]:
        assert add_special_tokens is False
        return self.mapping.get(text, [900, 901])


def test_probe_cases_cover_easy_coupled_and_incomplete_focus() -> None:
    cases = build_probe_cases()

    assert [case.case_id for case in cases] == [
        "easy_separable",
        "coupled_constraints",
        "incomplete_focus",
    ]
    assert [case.expected_label for case in cases] == ["A", "B", "C"]
    assert all(
        [candidate.label for candidate in case.candidates] == ["A", "B", "C"]
        for case in cases
    )


def test_candidate_summary_normalizes_only_bounded_candidates() -> None:
    summary = summarize_candidate_logits(("A", "B", "C"), (2.0, 1.0, 0.0))

    assert summary.winner == "A"
    assert summary.winner_probability > summary.probabilities["B"]
    assert summary.margin > 0.0
    assert math.isclose(sum(summary.probabilities.values()), 1.0)
    assert summary.entropy > 0.0


def test_candidate_summary_rejects_malformed_candidate_surface() -> None:
    with pytest.raises(ValueError, match="same length"):
        summarize_candidate_logits(("A", "B"), (1.0,))

    with pytest.raises(ValueError, match="at least two"):
        summarize_candidate_logits(("A",), (1.0,))

    with pytest.raises(ValueError, match="unique"):
        summarize_candidate_logits(("A", "A"), (1.0, 0.0))


def test_single_token_resolution_prefers_space_prefixed_candidate() -> None:
    tokenizer = FakeTokenizer(
        {
            " A": [11],
            " B": [12],
            " C": [13],
            "A": [21],
            "B": [22],
            "C": [23],
        }
    )
    candidates = (
        Candidate("A", "first"),
        Candidate("B", "second"),
        Candidate("C", "third"),
    )

    token_ids, token_texts = resolve_single_token_candidates(tokenizer, candidates)

    assert token_ids == {"A": 11, "B": 12, "C": 13}
    assert token_texts == {"A": " A", "B": " B", "C": " C"}


def test_single_token_resolution_rejects_duplicate_token_ids() -> None:
    tokenizer = FakeTokenizer(
        {
            " A": [11],
            " B": [11],
            " C": [13],
        }
    )
    candidates = (
        Candidate("A", "first"),
        Candidate("B", "second"),
        Candidate("C", "third"),
    )

    with pytest.raises(RuntimeError, match="duplicate token ids"):
        resolve_single_token_candidates(tokenizer, candidates)


def test_checkpoint_records_selects_available_ordinals_only() -> None:
    records = (
        {"ordinal": 1, "winner": "A"},
        {"ordinal": 2, "winner": "B"},
        {"ordinal": 3, "winner": "B"},
        {"ordinal": 4, "winner": "A"},
    )

    checkpoints = checkpoint_records(records, checkpoints=(1, 2, 4, 8))

    assert checkpoints == {
        "1": {"ordinal": 1, "winner": "A"},
        "2": {"ordinal": 2, "winner": "B"},
        "4": {"ordinal": 4, "winner": "A"},
    }


def test_case_selection_is_bounded_and_rejects_unknown_ids() -> None:
    selected = select_cases(("coupled_constraints",))

    assert len(selected) == 1
    assert selected[0].case_id == "coupled_constraints"

    with pytest.raises(ValueError, match="unknown case ids"):
        select_cases(("does_not_exist",))


def test_dry_run_is_plan_evidence_and_does_not_claim_model_result() -> None:
    payload = dry_run_payload(
        model_id="example/model",
        case_ids=("easy_separable",),
        steps=8,
        adaptive=True,
        seed=7,
        quantization="none",
    )

    assert payload["evidence_class"] == "experiment plan only"
    assert payload["model_id"] == "example/model"
    assert payload["checkpoint_ordinals"] == [1, 2, 4, 8]
    assert payload["adaptive_requested"] is True
    assert payload["cases"][0]["case_id"] == "easy_separable"
    assert "dry-run output is not a model result" in payload["non_claims"]
